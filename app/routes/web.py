"""Web page routes."""

from __future__ import annotations

from flask import Blueprint, Response, render_template


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return render_template("index.html")


@web_bp.get("/overlaps")
def overlaps():
    return render_template("overlaps.html")


@web_bp.get("/frequency")
def frequency():
    return render_template("frequency.html")


@web_bp.get("/simulator")
def simulator():
    return render_template("simulator.html")


@web_bp.get("/favicon.ico")
def favicon() -> Response:
        svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
    <defs>
        <radialGradient id='g' cx='35%' cy='30%' r='80%'>
            <stop offset='0%' stop-color='#2dd4bf'/>
            <stop offset='55%' stop-color='#7c5cff'/>
            <stop offset='100%' stop-color='#0b1220'/>
        </radialGradient>
    </defs>
    <circle cx='32' cy='32' r='28' fill='url(#g)'/>
    <circle cx='32' cy='32' r='28' fill='none' stroke='rgba(234,240,255,0.25)' stroke-width='2'/>
    <text x='32' y='38' text-anchor='middle' font-family='system-ui,Segoe UI,Arial' font-size='18' font-weight='800' fill='#eaf0ff'>6/45</text>
</svg>"""

        return Response(svg, mimetype="image/svg+xml")
