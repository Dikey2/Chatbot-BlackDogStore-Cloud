"""Resumen y gráficos comparativos de las pruebas de Locust (solo biblioteca estándar).

    python3 loadtest/resumen.py

Lee ``loadtest/resultados/*_consola.txt`` (resumen final de Locust) y
``*_recursos.csv`` (CPU, memoria y conexiones), y escribe:

- ``loadtest/resultados/resumen.md``: tabla con todas las métricas.
- ``loadtest/resultados/comparativa.html``: gráficos SVG autocontenidos.

Si un escenario se repitió, se usa la ejecución más reciente.
"""
import csv
import html
import re
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "resultados"
NAME = re.compile(r"^(\d{8}-\d{6})_(.+)_consola\.txt$")


def parse_console(path):
    text = path.read_text(errors="replace")
    rows = [line for line in text.splitlines() if line.strip().startswith("Aggregated")]
    if len(rows) < 2:
        return None
    stats = rows[0].replace("|", " ").replace("(", " ").replace(")", " ").replace("%", " ").split()
    pct = rows[1].split()
    errors = defaultdict(int)
    in_errors = False
    for line in text.splitlines():
        if line.startswith("Error report"):
            in_errors = True
            continue
        if in_errors:
            match = re.match(r"^\s*(\d+)\s+(\S+) (.+?): (.*)$", line)
            if match:
                status = re.search(r"\b(\d{3}) (Client|Server) Error", match.group(4))
                kind = status.group(1) if status else match.group(4).split("(")[0]
                errors[kind] += int(match.group(1))
    return {
        "requests": int(stats[1]),
        "failures": int(stats[2]),
        "fail_pct": float(stats[3]),
        "avg": float(stats[4]),
        "median": float(stats[7]),
        "rps": float(stats[8]),
        "p95": float(pct[6]),
        "p99": float(pct[8]),
        "errors": dict(errors),
    }


def mib(value):
    number = float(re.match(r"[\d.]+", value).group())
    if "GiB" in value:
        return number * 1024
    if "KiB" in value or "kB" in value:
        return number / 1024
    return number


def parse_resources(path):
    cpu, mem = defaultdict(list), defaultdict(list)
    conns = []
    if not path.exists():
        return {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            name = row["contenedor"].replace("blackdog-chatbot-", "").replace("-1", "")
            cpu[name].append(float(row["cpu"].rstrip("%") or 0))
            mem[name].append(mib(row["memoria"].split("/")[0]))
            if row["conexiones_pg"].strip().isdigit():
                conns.append(int(row["conexiones_pg"]))
    return {
        "cpu_avg": {k: sum(v) / len(v) for k, v in cpu.items()},
        "cpu_max": {k: max(v) for k, v in cpu.items()},
        "mem_max": {k: max(v) for k, v in mem.items()},
        "pg_max": max(conns) if conns else None,
    }


def load():
    latest = {}
    for path in sorted(RESULTS.glob("*_consola.txt")):
        match = NAME.match(path.name)
        if not match:
            continue
        stamp, scenario = match.groups()
        data = parse_console(path)
        if data is None:
            continue
        data["stamp"] = stamp
        data["files"] = f"{stamp}_{scenario}"
        data.update(parse_resources(RESULTS / f"{stamp}_{scenario}_recursos.csv"))
        latest[scenario] = data
    return latest


def fmt(value, digits=0):
    return f"{value:,.{digits}f}".replace(",", " ")


def table(results):
    lines = [
        "| Escenario | Solicitudes | Exitosas | Fallidas | Errores | req/s | Media | Mediana | p95 | p99 | CPU backend (media/máx.) | CPU PostgreSQL (media/máx.) | RAM backend máx. | Conexiones PG máx. | Archivos |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for scenario, r in results.items():
        cpu = r.get("cpu_avg", {})
        cmax = r.get("cpu_max", {})
        mem = r.get("mem_max", {})
        errors = ", ".join(f"{k}: {v}" for k, v in r["errors"].items()) or "—"
        lines.append(
            f"| {scenario} | {fmt(r['requests'])} | {fmt(r['requests'] - r['failures'])} | "
            f"{fmt(r['failures'])} ({r['fail_pct']:.2f} %) | {errors} | {r['rps']:.1f} | "
            f"{fmt(r['avg'])} ms | {fmt(r['median'])} ms | {fmt(r['p95'])} ms | {fmt(r['p99'])} ms | "
            f"{cpu.get('backend', 0):.0f} % / {cmax.get('backend', 0):.0f} % | "
            f"{cpu.get('db', 0):.0f} % / {cmax.get('db', 0):.0f} % | "
            f"{mem.get('backend', 0):.0f} MiB | {r.get('pg_max') or '—'} | `{r['files']}` |"
        )
    return "\n".join(lines)


def bar_chart(title, series, unit, width=760):
    """series: list of (label, [(group, value), ...]) — barras agrupadas."""
    groups = [g for g, _ in series[0][1]] if series else []
    colors = ["#2563eb", "#d97706", "#059669", "#7c3aed"]
    peak = max((v for _, values in series for _, v in values), default=1) or 1
    left, top, height = 60, 40, 220
    slot = (width - left - 20) / max(len(groups), 1)
    bar = slot * 0.8 / max(len(series), 1)
    parts = [
        f'<svg viewBox="0 0 {width} {top + height + 60}" role="img" aria-label="{html.escape(title)}">',
        f'<text x="{left}" y="22" class="t">{html.escape(title)}</text>',
    ]
    for i in range(5):
        y = top + height - height * i / 4
        parts.append(f'<line x1="{left}" x2="{width - 20}" y1="{y}" y2="{y}" class="g"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 4}" class="a" text-anchor="end">{fmt(peak * i / 4)}</text>')
    for gi, group in enumerate(groups):
        x0 = left + gi * slot + slot * 0.1
        for si, (_, values) in enumerate(series):
            value = values[gi][1]
            h = height * value / peak
            x = x0 + si * bar
            parts.append(
                f'<rect x="{x:.1f}" y="{top + height - h:.1f}" width="{bar - 2:.1f}" height="{h:.1f}" '
                f'fill="{colors[si % 4]}"><title>{html.escape(series[si][0])} {html.escape(group)}: '
                f'{fmt(value, 1)} {unit}</title></rect>'
            )
        parts.append(
            f'<text x="{x0 + slot * 0.4:.1f}" y="{top + height + 16}" class="a" text-anchor="middle">'
            f"{html.escape(group)}</text>"
        )
    for si, (label, _) in enumerate(series):
        x = left + si * 170
        parts.append(f'<rect x="{x}" y="{top + height + 30}" width="12" height="12" fill="{colors[si % 4]}"/>')
        parts.append(f'<text x="{x + 18}" y="{top + height + 41}" class="a">{html.escape(label)} ({unit})</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def pick(results, prefix, keys, metric):
    return [(k, results.get(f"{prefix}{k}", {}).get(metric, 0)) for k in keys]


def main():
    results = load()
    users = [u for u in ("50u", "100u", "200u", "300u", "500u")
             if any(k.startswith(f"B-{u}-") for k in results)]
    totals = [t for t in ("1000req", "2000req", "3000req", "5000req")
              if any(k.startswith(f"A-{t}-") for k in results)]

    charts = []
    if users:
        for metric, title, unit in (
            ("median", "Modalidad B: mediana por usuarios concurrentes", "ms"),
            ("p95", "Modalidad B: percentil 95 por usuarios concurrentes", "ms"),
            ("rps", "Modalidad B: solicitudes por segundo", "req/s"),
        ):
            charts.append(bar_chart(title, [
                ("Lectura", [(u, results.get(f"B-{u}-lectura", {}).get(metric, 0)) for u in users]),
                ("Escritura", [(u, results.get(f"B-{u}-escritura", {}).get(metric, 0)) for u in users]),
            ], unit))
    if totals:
        charts.append(bar_chart("Modalidad A: mediana por solicitudes totales", [
            ("Lectura", [(t, results.get(f"A-{t}-lectura", {}).get("median", 0)) for t in totals]),
            ("Escritura", [(t, results.get(f"A-{t}-escritura", {}).get("median", 0)) for t in totals]),
        ], "ms"))
    before_after = [k for k in ("B-100u-lectura", "B-100u-escritura") if f"antes-{k}" in results]
    if before_after:
        charts.append(bar_chart("Antes y después de optimizar (100 usuarios): mediana", [
            ("Antes", [(k, results[f"antes-{k}"]["median"]) for k in before_after]),
            ("Después", [(k, results.get(f"despues-{k}", {}).get("median", 0)) for k in before_after]),
        ], "ms"))
        charts.append(bar_chart("Antes y después de optimizar (100 usuarios): solicitudes por segundo", [
            ("Antes", [(k, results[f"antes-{k}"]["rps"]) for k in before_after]),
            ("Después", [(k, results.get(f"despues-{k}", {}).get("rps", 0)) for k in before_after]),
        ], "req/s"))

    (RESULTS / "resumen.md").write_text(
        "# Resumen de pruebas de carga (Locust, Docker Compose local)\n\n"
        "Generado con `python3 loadtest/resumen.py`. Una fila por escenario (la ejecución más reciente).\n\n"
        + table(results) + "\n"
    )
    page = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comparativa de carga</title>
<style>
body{{font-family:system-ui,sans-serif;margin:16px;max-width:820px;color:#111;background:#fff}}
svg{{width:100%;height:auto;margin:16px 0;border:1px solid #e5e7eb;border-radius:8px}}
.t{{font-size:15px;font-weight:600}} .a{{font-size:11px;fill:#374151}} .g{{stroke:#e5e7eb}}
</style></head><body>
<h1>Pruebas de carga con Locust</h1>
<p>Entorno local: Docker Compose, gunicorn y PostgreSQL 17. Datos ficticios. Tabla completa en <code>resumen.md</code>.</p>
{''.join(charts)}
</body></html>"""
    (RESULTS / "comparativa.html").write_text(page)
    print(f"{len(results)} escenarios -> resumen.md y comparativa.html")


if __name__ == "__main__":
    main()
