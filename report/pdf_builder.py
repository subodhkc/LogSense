# report/pdf_builder.py
from __future__ import annotations
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def _draw_header(c: canvas.Canvas, title: str, subtitle: str, x: float, y: float) -> float:
    c.setFont("Times-Bold", 16)
    c.drawString(x, y, title)
    y -= 14
    c.setFont("Times-Roman", 10)
    c.drawString(x, y, subtitle)
    return y - 10


def _kv(c: canvas.Canvas, x: float, y: float, label: str, value: str) -> float:
    c.setFont("Times-Bold", 10)
    c.drawString(x, y, f"{label}:")
    c.setFont("Times-Roman", 10)
    c.drawString(x + 80, y, (value or "")[:90])
    return y - 12


def _bullets(c: canvas.Canvas, x: float, y: float, items: List[str], max_items: int = 6) -> float:
    c.setFont("Times-Roman", 10)
    for it in items[:max_items]:
        c.drawString(x, y, f"- {str(it)[:100]}")
        y -= 12
    return y


def build_pdf(report: Dict[str, Any], out_path: str, include_annexes: bool = True) -> str:
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4
    x, y = inch * 0.75, height - inch * 0.75

    # Header
    y = _draw_header(c, "LogSense - One-Pager", report.get("meta", {}).get("build", "Unnamed Build"), x, y)

    # Meta block
    m = report.get("meta", {})
    y = _kv(c, x, y, "Platform", str(m.get("platform", "")))
    y = _kv(c, x, y, "Versions", str(m.get("versions", "")))
    y = _kv(c, x, y, "Time Range", str(m.get("ts_range", "")))

    # RCA
    rca = report.get("rca", {})
    y -= 4
    c.setFont("Times-Bold", 12); c.drawString(x, y, "Root Cause Analysis"); y -= 14
    y = _kv(c, x, y, "Confidence", f"{rca.get('confidence', 0.0):.2f}")
    y = _bullets(c, x, y, [f"{i+1}. {rca_i}" for i, rca_i in enumerate(rca.get("root_causes", []))])

    # Deltas snapshot
    d = report.get("deltas", {})
    y -= 6
    c.setFont("Times-Bold", 12); c.drawString(x, y, "Deltas"); y -= 12
    y = _bullets(c, x, y, [
        f"New: {len(d.get('new', []))}",
        f"Resolved: {len(d.get('resolved', []))}",
        f"Persisting: {len(d.get('persisting', []))}",
    ])

    # Observations
    obs = report.get("observations", {})
    y -= 6
    c.setFont("Times-Bold", 12); c.drawString(x, y, "Observations"); y -= 12
    y = _bullets(c, x, y, [
        f"Spike windows: {len(obs.get('spikes', []))}",
        f"Time gaps: {len(obs.get('gaps', []))}",
        f"Rare events: {len(obs.get('first_seen', []))}",
        f"Clock anomalies: {len(obs.get('clock_anomalies', []))}",
    ])

    c.showPage()

    # Annexes
    if include_annexes:
        x, y = inch * 0.75, height - inch * 0.75
        c.setFont("Times-Bold", 14); c.drawString(x, y, "Annex - Evidence Packs"); y -= 18
        packs = report.get("evidence", [])[:250]
        c.setFont("Times-Roman", 10)
        for idx, ev in enumerate(packs, 1):
            line = f"[{idx:03d}] {ev.get('ts','')} {ev.get('source','')} {ev.get('level','')} {ev.get('event_id','')}  {str(ev.get('message',''))[:110]}"
            c.drawString(x, y, line)
            y -= 10
            if y < inch * 0.5:
                c.showPage()
                x, y = inch * 0.75, height - inch * 0.75
                c.setFont("Times-Bold", 14); c.drawString(x, y, "Annex - Evidence Packs (cont.)"); y -= 18

    c.save()
    return out_path