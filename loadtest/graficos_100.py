"""Gráficos de la campaña del 100 % (10 000 a 50 000 solicitudes, 100 usuarios).

Lee los CSV de Locust y de recursos versionados en loadtest/resultados/ y escribe
PNG en docs/evidencias/. No contacta ningún servidor.

Uso (sin instalar nada en el equipo):
  docker run --rm -v "$PWD":/w -w /w python:3.12-slim \
    sh -c "pip install -q matplotlib && python loadtest/graficos_100.py"
"""
import csv
import glob
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RES = "loadtest/resultados"
OUT = "docs/evidencias"
TOTALS = [10000, 20000, 30000, 50000]
STAGES = [("antes", "Antes"), ("despues", "Después (contador atómico)")]
COLORS = {"antes": "#b23a48", "despues": "#2a6f97", "preload-1": "#52796f", "preload-2": "#84a98c"}


def find(tag, kind):
    files = sorted(glob.glob(f"{RES}/*_C-{tag}_{kind}.csv"))
    return files[-1] if files else None


def aggregated(tag):
    """Resumen FINAL de Locust (consola). *_stats.csv se escribe cada segundo y omite el último."""
    path = sorted(glob.glob(f"{RES}/*_C-{tag}_consola.txt"))[-1]
    lines = [line.split() for line in open(path) if line.strip().startswith("Aggregated")]
    summary, pct = lines[0], lines[1]
    # Resumen: Aggregated <n> <fallos>(<%>) | <prom> <mín> <máx> <mediana> | <solic/s> <fallos/s>
    # Percentiles: Aggregated 50% 66% 75% 80% 90% 95% 98% 99% 99.9% 99.99% 100% <n>
    return {
        "n": int(summary[1]),
        "fail": int(summary[2].split("(")[0]),
        "rps": float(summary[9]),
        "p50": float(pct[1]),
        "p95": float(pct[6]),
        "p99": float(pct[8]),
        "max": float(summary[6]),
    }


def history(tag):
    rows = [r for r in csv.DictReader(open(find(tag, "stats_history"))) if r["Name"] == "Aggregated"]
    t0 = int(rows[0]["Timestamp"])
    out, last = [], None
    for r in rows:
        if r["95%"] == "N/A":
            continue
        t = int(r["Timestamp"]) - t0
        if last is not None and t - last > 5:
            # Hueco sin datos (equipo suspendido): se corta la línea en vez de unir los extremos.
            out.append((t - 1, float("nan"), float("nan")))
        out.append((t, float(r["Requests/s"]), float(r["95%"])))
        last = t
    return out


def resources(tag):
    path = find(tag, "recursos")
    cpu, mem = [], []
    for r in csv.DictReader(open(path)):
        if r["contenedor"].endswith("backend-1"):
            cpu.append(float(r["cpu"].rstrip("%")))
            mem.append(float(re.match(r"([\d.]+)", r["memoria"]).group(1)))
    return cpu, mem


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=130)
    plt.close(fig)
    print("escrito", name)


def main():
    # 1. Percentiles por volumen, antes y después.
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
    for ax, key, title in zip(axes, ["p50", "p95", "p99"], ["Mediana (p50)", "p95", "p99"]):
        width = 0.38
        for i, (stage, label) in enumerate(STAGES):
            values = [aggregated(f"{t}req-{stage}")[key] for t in TOTALS]
            xs = [x + (i - 0.5) * width for x in range(len(TOTALS))]
            ax.bar(xs, values, width, label=label, color=COLORS[stage])
        ax.set_xticks(range(len(TOTALS)), [f"{t // 1000}k" for t in TOTALS])
        ax.set_title(f"{title} (ms)")
        ax.set_xlabel("solicitudes totales")
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.suptitle("Tiempo de respuesta por volumen — 100 usuarios concurrentes, Docker local")
    save(fig, "graficos-carga-100-percentiles.png")

    # 2. Rendimiento y fallos por volumen.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for i, (stage, label) in enumerate(STAGES):
        data = [aggregated(f"{t}req-{stage}") for t in TOTALS]
        xs = [x + (i - 0.5) * 0.38 for x in range(len(TOTALS))]
        ax1.bar(xs, [d["rps"] for d in data], 0.38, label=label, color=COLORS[stage])
        ax2.bar(xs, [d["fail"] for d in data], 0.38, label=label, color=COLORS[stage])
    for ax, title in [(ax1, "Solicitudes por segundo"), (ax2, "Solicitudes fallidas")]:
        ax.set_xticks(range(len(TOTALS)), [f"{t // 1000}k" for t in TOTALS])
        ax.set_title(title)
        ax.set_xlabel("solicitudes totales")
        ax.grid(axis="y", alpha=0.3)
    ax1.legend(fontsize=8)
    save(fig, "graficos-carga-100-rendimiento.png")

    # 3. Las tres etapas con 50 000 solicitudes, en el tiempo.
    runs = [("50000req-antes", "Antes"), ("50000req-despues", "Contador atómico"),
            ("50000req-preload-1", "Contador + gunicorn --preload")]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for tag, label in runs:
        h = history(tag)
        color = COLORS[tag.split("req-")[1]]
        ax1.plot([x[0] for x in h], [x[1] for x in h], label=label, color=color, lw=1.2)
        ax2.plot([x[0] for x in h], [x[2] for x in h], label=label, color=color, lw=1.2)
    ax1.set_ylabel("solicitudes/s")
    ax2.set_ylabel("p95 (ms)")
    ax2.set_xlabel("segundos desde el inicio")
    ax1.set_title("50 000 solicitudes: rendimiento y p95 durante la prueba")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    save(fig, "graficos-carga-100-50k-tiempo.png")

    # 4. Recursos del backend con 50 000 solicitudes.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for tag, label in runs:
        cpu, mem = resources(tag)
        color = COLORS[tag.split("req-")[1]]
        ax1.plot(cpu, label=label, color=color, lw=1)
        ax2.plot(mem, label=label, color=color, lw=1)
    ax1.set_title("CPU del contenedor backend (%)")
    ax2.set_title("Memoria del contenedor backend (MiB)")
    for ax in (ax1, ax2):
        ax.set_xlabel("muestras (cada ~2 s)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    save(fig, "graficos-carga-100-recursos.png")

    # Tabla para la documentación.
    print("\n| Escenario | Solicitudes | Fallos | Solic./s | p50 | p95 | p99 | Máx. |")
    for tag in [f"{t}req-{s}" for s, _ in STAGES for t in TOTALS] + ["50000req-preload-1", "50000req-preload-2"]:
        a = aggregated(tag)
        print(f"| {tag} | {a['n']} | {a['fail']} | {a['rps']:.1f} | {a['p50']:.0f} | {a['p95']:.0f} | {a['p99']:.0f} | {a['max']:.0f} |")
    for tag, _ in runs + [("50000req-preload-2", "")]:
        cpu, mem = resources(tag)
        print(f"recursos {tag}: cpu máx {max(cpu):.0f}% media {sum(cpu) / len(cpu):.0f}% · memoria máx {max(mem):.0f} MiB")


if __name__ == "__main__":
    main()
