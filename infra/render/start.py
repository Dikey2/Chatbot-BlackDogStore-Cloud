
"""Inicio del backend y del chatbot en una instancia Render."""

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
CHATBOT_DIR = BASE_DIR / "services" / "chatbot"

CHATBOT_PORT = 8001
WEB_PORT = int(os.environ.get("PORT", "8000"))

# Comunicación interna entre los dos servicios.
os.environ["CHATBOT_SERVICE_URL"] = (
    f"http://127.0.0.1:{CHATBOT_PORT}"
)

PROCESSES = {}
STOPPING = False


def handle_shutdown(signum, frame):
    """Solicita detener todos los procesos."""
    global STOPPING
    STOPPING = True

    for process in PROCESSES.values():
        if process.poll() is None:
            process.terminate()


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def start_process(name, command, directory):
    """Inicia un proceso y registra su identificador."""
    print(f"[START] {name}", flush=True)

    process = subprocess.Popen(
        command,
        cwd=str(directory),
        env=os.environ.copy(),
    )

    PROCESSES[name] = process
    return process


def run_migrations():
    """Aplica las migraciones antes de iniciar la API."""
    process = start_process(
        "migrations",
        [
            sys.executable,
            "manage.py",
            "migrate",
            "--noinput",
        ],
        BACKEND_DIR,
    )

    while process.poll() is None:
        if STOPPING:
            return False
        time.sleep(0.2)

    if process.returncode != 0:
        raise RuntimeError(
            "No se pudieron aplicar las migraciones."
        )

    del PROCESSES["migrations"]

    print("[OK] Migraciones completadas", flush=True)
    return True


def start_chatbot():
    """Inicia el chatbot solo en la red local."""
    return start_process(
        "chatbot",
        [
            sys.executable,
            "-m",
            "gunicorn",
            "config.wsgi:application",
            "--bind",
            f"127.0.0.1:{CHATBOT_PORT}",
            "--workers",
            "1",
            "--timeout",
            "30",
            "--access-logfile",
            "-",
        ],
        CHATBOT_DIR,
    )


def wait_for_chatbot():
    """Espera hasta que el chatbot responda correctamente."""
    url = f"http://127.0.0.1:{CHATBOT_PORT}/health/"

    for _ in range(60):
        if STOPPING:
            return False

        if PROCESSES["chatbot"].poll() is not None:
            raise RuntimeError(
                "El proceso del chatbot terminó inesperadamente."
            )

        try:
            with urllib.request.urlopen(
                url, timeout=2
            ) as response:
                if response.status == 200:
                    print(
                        "[OK] Chatbot disponible",
                        flush=True,
                    )
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass

        time.sleep(0.5)

    raise RuntimeError(
        "El chatbot no respondió a tiempo."
    )


def start_backend():
    """Publica la API principal en el puerto de Render."""
    workers = os.environ.get("GUNICORN_WORKERS", "1")

    return start_process(
        "backend",
        [
            sys.executable,
            "-m",
            "gunicorn",
            "config.wsgi:application",
            "--bind",
            f"0.0.0.0:{WEB_PORT}",
            "--workers",
            workers,
            "--timeout",
            "30",
            "--access-logfile",
            "-",
        ],
        BACKEND_DIR,
    )


def stop_processes():
    """Cierra los procesos al finalizar."""
    for process in PROCESSES.values():
        if process.poll() is None:
            process.terminate()

    for process in PROCESSES.values():
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    try:
        if not run_migrations():
            return 1

        start_chatbot()

        if not wait_for_chatbot():
            return 1

        start_backend()

        print(
            f"[OK] API disponible en el puerto {WEB_PORT}",
            flush=True,
        )

        while not STOPPING:
            for name in ("backend", "chatbot"):
                process = PROCESSES[name]

                if process.poll() is not None:
                    print(
                        f"[ERROR] {name} terminó "
                        f"con código {process.returncode}",
                        flush=True,
                    )
                    return 1

            time.sleep(1)

        return 0

    except Exception as error:
        print(f"[ERROR] {error}", flush=True)
        return 1

    finally:
        stop_processes()


if __name__ == "__main__":
    sys.exit(main())
