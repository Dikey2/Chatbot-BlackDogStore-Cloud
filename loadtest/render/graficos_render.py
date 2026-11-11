"""Gráfico de la prueba controlada contra Render (100, 1000 y 5000 solicitudes).

Uso: docker run --rm -v "$PWD":/w -w /w python:3.12-slim \
       sh -c "pip install -q matplotlib && python loadtest/render/graficos_render.py"
"""
import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

STAGES = [(100, 10), (1000, 20), (5000, 25)]


def aggregated(total, users):
    """Resumen FINAL de la consola de Locust (el CSV se escribe cada segundo y omite el último)."""
    path = sorted(glob.glob(f"loadtest/resultados/render/*_R-{total}req-{users}u_consola.txt"))[-1]
    lines = [line.split() for line in open(path) if line.strip().startswith("Aggregated")]
    summary, pct = lines[0], lines[1]
    # Resumen: Aggregated <reqs> <fails>(<%>) | <avg> <min> <max> <med> | <req/s> <fails/s>
    # Percentiles: Aggregated 50% 66% 75% 80% 90% 95% 98% 99% 99.9% 99.99% 100% <reqs>
    return {
        "Request Count": summary[1], "Failure Count": summary[2].split("(")[0],
        "Requests/s": summary[9], "Max Response Time": summary[6],
        "50%": pct[1], "95%": pct[6], "99%": pct[8],
    }


rows = [aggregated(t, u) for t, u in STAGES]
labels = [f"{t:,}".replace(",", " ") + f"\n({u} usuarios)" for t, u in STAGES]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
width = 0.25
for i, (key, name, color) in enumerate([("50%", "p50", "#2a6f97"), ("95%", "p95", "#52796f"), ("99%", "p99", "#b23a48")]):
    ax1.bar([x + (i - 1) * width for x in range(3)], [float(r[key]) for r in rows], width, label=name, color=color)
ax1.set_xticks(range(3), labels)
ax1.set_title("Tiempo de respuesta en Render (ms)")
ax1.legend()
ax1.grid(axis="y", alpha=0.3)
ax2.bar(range(3), [float(r["Requests/s"]) for r in rows], color="#2a6f97")
for x, r in enumerate(rows):
    ax2.text(x, float(r["Requests/s"]), f"{int(r['Request Count'])} sol.\n{int(r['Failure Count'])} fallos",
             ha="center", va="bottom", fontsize=8)
ax2.set_xticks(range(3), labels)
ax2.set_title("Solicitudes por segundo y fallos")
ax2.set_ylim(0, max(float(r["Requests/s"]) for r in rows) * 1.35)
ax2.grid(axis="y", alpha=0.3)
fig.suptitle("Prueba controlada contra Render (solo lectura) — 11 de noviembre de 2026")
fig.tight_layout()
fig.savefig("docs/evidencias/graficos-carga-render.png", dpi=130)
for (t, u), r in zip(STAGES, rows):
    print(f"| {t} | {u} | {r['Request Count']} | {r['Failure Count']} | {float(r['Requests/s']):.1f} | {r['50%']} | {r['95%']} | {r['99%']} | {float(r['Max Response Time']):.0f} |")
