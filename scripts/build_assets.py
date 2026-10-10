#!/usr/bin/env python3
"""Build the animated SVG assets used by the profile README.

GitHub renders README images without JavaScript, so all motion here is plain
SVG: SMIL <animate> for the 3D projections and CSS @keyframes for the rest.
Icons are embedded as inline paths, so no image depends on an external CDN.

    npm install --no-save simple-icons@16 devicon@2
    python3 scripts/build_assets.py [path/to/node_modules]
"""
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MODULES = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "node_modules"

FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"
CYAN = "#38BDF8"
VIOLET = "#818CF8"


# --------------------------------------------------------------------------
# helpers


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(hex_color, factor):
    return "#" + "".join(f"{min(255, int(c * factor)):02X}" for c in rgb(hex_color))


def luminance(hex_color):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def svg(width, height, body, title, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title>"
        + (f"<style>{style}</style>" if style else "")
        + body
        + "</svg>\n"
    )


def loop(attr, values, dur, extra=""):
    return (
        f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
        f'values="{";".join(values)}"{extra}/>'
    )


def simple_icon(slug):
    text = (MODULES / "simple-icons" / "icons" / f"{slug}.svg").read_text()
    return [(re.search(r' d="([^"]+)"', text).group(1), None)]


def devicon(name, variant):
    text = (MODULES / "devicon" / "icons" / name / f"{name}-{variant}.svg").read_text()
    return [(d, fill) for fill, d in re.findall(r'<path[^>]*?fill="([^"]+)"[^>]*? d="([^"]+)"', text)]


def icon(paths, size, view_box, x, y, fill, recolor=None):
    """Place icon paths in a size x size box at (x, y)."""
    out = f'<g transform="translate({n(x)} {n(y)}) scale({size / view_box:.4f})">'
    for d, own in paths:
        color = (recolor or {}).get(own, fill) if own else fill
        out += f'<path d="{d}" fill="{color}"/>'
    return out + "</g>"


# --------------------------------------------------------------------------
# hero banner: perspective grid floor + rotating 3D neural sphere


def fibonacci_sphere(count):
    golden = math.pi * (3 - math.sqrt(5))
    points = []
    for i in range(count):
        y = 1 - 2 * (i + 0.5) / count
        r = math.sqrt(1 - y * y)
        points.append((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    return points


def nearest_edges(points, k):
    edges = set()
    for i, p in enumerate(points):
        near = sorted((math.dist(p, q), j) for j, q in enumerate(points) if j != i)
        for _, j in near[:k]:
            edges.add((min(i, j), max(i, j)))
    return sorted(edges)


def project(point, theta, tilt, cx, cy, radius, camera=4.0):
    x, y, z = point
    x, z = x * math.cos(theta) + z * math.sin(theta), -x * math.sin(theta) + z * math.cos(theta)
    y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
    scale = camera / (camera - z)
    return cx + radius * x * scale, cy + radius * y * scale, (z + 1) / 2


def hero():
    W, H = 1000, 380
    horizon, cx, cy, radius = 300, 770, 168, 100
    rng = random.Random(1120)
    parts = []

    defs = f"""<defs>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#060A14"/><stop offset=".78" stop-color="#101735"/><stop offset="1" stop-color="#0B1024"/>
</linearGradient>
<radialGradient id="haze" cx=".5" cy=".5" r=".5">
  <stop offset="0" stop-color="{VIOLET}" stop-opacity=".35"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
</radialGradient>
<radialGradient id="core" cx=".5" cy=".5" r=".5">
  <stop offset="0" stop-color="{CYAN}" stop-opacity=".32"/><stop offset=".6" stop-color="{CYAN}" stop-opacity=".07"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
</radialGradient>
<linearGradient id="horizonLine" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
</linearGradient>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#000"/><stop offset=".55" stop-color="#fff"/>
</linearGradient>
<mask id="floor"><rect y="{horizon}" width="{W}" height="{H - horizon}" fill="url(#fade)"/></mask>
<linearGradient id="title" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="#C084FC"/>
</linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
  <feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="blur8"><feGaussianBlur stdDeviation="8"/></filter>
</defs>"""

    parts.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    parts.append(f'<ellipse cx="{W / 2}" cy="{horizon}" rx="560" ry="120" fill="url(#haze)"/>')

    # twinkling stars
    for _ in range(70):
        x, y = rng.uniform(0, W), rng.uniform(0, horizon - 20)
        r, dur = rng.uniform(0.5, 1.5), rng.uniform(2.5, 6)
        parts.append(
            f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="#CBD5F5">'
            + loop("opacity", [".15", "1", ".15"], f"{dur:.1f}", f' begin="-{rng.uniform(0, dur):.1f}s"')
            + "</circle>"
        )

    # perspective grid floor: rays to the vanishing point + rows scrolling toward the viewer
    floor = [f'<g mask="url(#floor)" stroke="{VIOLET}" stroke-width="1" opacity=".55">']
    for xb in range(-1800, W + 1801, 90):
        floor.append(f'<line x1="{W / 2}" y1="{horizon}" x2="{xb}" y2="{H}"/>')
    depth_k, frames, rows = H - horizon, 24, 16
    for i in range(rows):
        ys = []
        for f in range(frames + 1):
            dist = max(0.4, 1 + i - f / frames)
            ys.append(f"0 {n(horizon + depth_k / dist)}")
        floor.append(
            f'<line x1="0" y1="0" x2="{W}" y2="0">'
            f'<animateTransform attributeName="transform" type="translate" dur="2.8s" '
            f'repeatCount="indefinite" values="{";".join(ys)}"/></line>'
        )
    floor.append("</g>")
    parts += floor
    parts.append(f'<rect x="0" y="{horizon - 6}" width="{W}" height="12" fill="url(#horizonLine)" opacity=".5" filter="url(#blur8)"/>')
    parts.append(f'<rect x="0" y="{horizon - 0.75}" width="{W}" height="1.5" fill="url(#horizonLine)"/>')

    # orbit ring (back half drawn before the sphere, front half after it)
    rx, ry = radius * 1.75, radius * 0.36
    left, right = f"{n(cx - rx)} {cy}", f"{n(cx + rx)} {cy}"
    ring_rot = f"rotate(-14 {cx} {cy})"
    back_arc = f"M{right} A{n(rx)} {n(ry)} 0 0 0 {left}"
    front_arc = f"M{left} A{n(rx)} {n(ry)} 0 0 0 {right}"
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius * 1.9}" fill="url(#core)"/>')
    parts.append(
        f'<path d="{back_arc}" transform="{ring_rot}" fill="none" stroke="{CYAN}" '
        f'stroke-opacity=".22" stroke-width="1.2" stroke-dasharray="3 6"/>'
    )

    # rotating 3D sphere of connected nodes
    points = fibonacci_sphere(38)
    edges = nearest_edges(points, 3)
    frames, dur, tilt = 60, 24, -0.38
    thetas = [2 * math.pi * f / frames for f in range(frames + 1)]
    proj = [[project(p, t, tilt, cx, cy, radius) for t in thetas] for p in points]

    parts.append(f'<g stroke="{VIOLET}" stroke-width="1">')
    for a, b in edges:
        pa, pb = proj[a], proj[b]
        attrs = {
            "x1": [n(p[0]) for p in pa],
            "y1": [n(p[1]) for p in pa],
            "x2": [n(p[0]) for p in pb],
            "y2": [n(p[1]) for p in pb],
            "stroke-opacity": [f"{0.06 + 0.55 * ((p[2] + q[2]) / 2) ** 2:.2f}" for p, q in zip(pa, pb)],
        }
        parts.append(
            f'<line x1="{attrs["x1"][0]}" y1="{attrs["y1"][0]}" x2="{attrs["x2"][0]}" y2="{attrs["y2"][0]}">'
            + "".join(loop(k, v, dur) for k, v in attrs.items())
            + "</line>"
        )
    parts.append("</g>")

    parts.append('<g fill="#A5E8FF" filter="url(#glow)">')
    for track in proj:
        attrs = {
            "cx": [n(p[0]) for p in track],
            "cy": [n(p[1]) for p in track],
            "r": [n(1.4 + 3.2 * p[2]) for p in track],
            "opacity": [f"{0.18 + 0.82 * p[2]:.2f}" for p in track],
        }
        parts.append(
            f'<circle cx="{attrs["cx"][0]}" cy="{attrs["cy"][0]}" r="{attrs["r"][0]}">'
            + "".join(loop(k, v, dur) for k, v in attrs.items())
            + "</circle>"
        )
    parts.append("</g>")

    parts.append(
        f'<path d="{front_arc}" transform="{ring_rot}" fill="none" stroke="{CYAN}" '
        f'stroke-opacity=".55" stroke-width="1.4"/>'
    )
    orbit = f"M{left} A{n(rx)} {n(ry)} 0 0 0 {right} A{n(rx)} {n(ry)} 0 0 0 {left}"
    parts.append(
        f'<g transform="{ring_rot}"><circle r="4" fill="#E0F7FF" filter="url(#glow)">'
        f'<animateMotion dur="9s" repeatCount="indefinite" path="{orbit}"/>'
        + loop("opacity", ["1", "1", ".25", ".25", "1"], 9, ' keyTimes="0;.46;.54;.96;1"')
        + "</circle></g>"
    )

    # headline
    chips = ["Python", "LLMs", "Computer Vision", "MLOps"]
    x0 = 56
    text = [
        f'<g class="up" style="animation-delay:.05s">'
        f'<rect x="{x0}" y="40" width="206" height="30" rx="15" fill="#22C55E" fill-opacity=".1" stroke="#22C55E" stroke-opacity=".45"/>'
        f'<circle cx="{x0 + 18}" cy="55" r="4.5" fill="#22C55E"/>'
        f'<circle cx="{x0 + 18}" cy="55" r="4.5" fill="none" stroke="#22C55E">'
        + loop("r", ["4.5", "11"], 2)
        + loop("opacity", [".8", "0"], 2)
        + f'</circle><text x="{x0 + 32}" y="60" font-size="14" fill="#86EFAC">Open to collaboration</text></g>',
        f'<text class="up" style="animation-delay:.15s" x="{x0 - 3}" y="132" font-size="62" font-weight="800" fill="{TEXT}" letter-spacing="-1">AI1120</text>',
        f'<text class="up" style="animation-delay:.3s" x="{x0}" y="178" font-size="28" font-weight="600" fill="url(#title)">AI &amp; Software Engineer</text>',
        f'<text class="up" style="animation-delay:.45s" font-size="18" fill="{MUTED}">'
        f'<tspan x="{x0}" y="216">I build production-ready AI systems, from LLM</tspan>'
        f'<tspan x="{x0}" y="241">applications to computer vision and MLOps pipelines.</tspan></text>',
    ]
    cx_chip = x0
    chip_parts = [f'<g class="up" style="animation-delay:.6s" font-size="14">']
    for label in chips:
        w = len(label) * 7.8 + 28
        chip_parts.append(
            f'<rect x="{n(cx_chip)}" y="258" width="{n(w)}" height="28" rx="8" fill="{CYAN}" fill-opacity=".08" stroke="{CYAN}" stroke-opacity=".35"/>'
            f'<text x="{n(cx_chip + w / 2)}" y="277" text-anchor="middle" fill="#BAE6FD">{label}</text>'
        )
        cx_chip += w + 10
    chip_parts.append("</g>")
    text += chip_parts

    style = (
        f"text{{font-family:{FONT}}}"
        ".up{animation:up .9s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
    )
    body = defs + '<g clip-path="url(#frame)">' + "".join(parts) + "".join(text) + "</g>"
    body += f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="#1E293B"/>'
    return svg(W, H, body, "AI1120 - AI & Software Engineer", style)


# --------------------------------------------------------------------------
# about: terminal card with a typing animation


def terminal():
    W, H = 820, 290
    size, char_w, line_h, x0, y0 = 16, 9.9, 30, 30, 92
    p, kw, cls, attr, op, st = "#C9D1D9", "#FF7B72", "#D2A8FF", "#79C0FF", "#FF7B72", "#A5D6FF"
    lines = [
        [("~/AI1120", "#7EE787"), (" $ ", "#8B949E"), ("cat about.py", p)],
        [("class", kw), (" ", p), ("Engineer", cls), (":", p)],
        [("    role    ", attr), ("=", op), (' "AI & Software Engineer"', st)],
        [("    focus   ", attr), ("=", op), (" [", p), ('"LLM apps"', st), (", ", p), ('"Computer Vision"', st), (", ", p), ('"MLOps"', st), ("]", p)],
        [("    tools   ", attr), ("=", op), (" [", p), ('"Python"', st), (", ", p), ('"PyTorch"', st), (", ", p), ('"FastAPI"', st), (", ", p), ('"Docker"', st), ("]", p)],
        [("    mission ", attr), ("=", op), (' "Turn research into reliable products"', st)],
    ]
    cycle, per_char, gap, start = 15.0, 0.022, 0.25, 0.4
    defs, body = ["<defs>"], []
    t = start
    for i, segments in enumerate(lines):
        chars = sum(len(s) for s, _ in segments)
        full = W - x0
        times, widths = ["0"], ["0"]
        typing_speed = per_char * (2 if i == 0 else 1)
        for k in range(1, chars + 1):
            times.append(f"{(t + k * typing_speed) / cycle:.4f}")
            widths.append(n(full if k == chars else k * char_w))
        t += chars * typing_speed + gap
        y = y0 + i * line_h
        defs.append(
            f'<clipPath id="l{i}"><rect x="{x0}" y="{y - 22}" width="{full}" height="{line_h}">'
            f'<animate attributeName="width" dur="{cycle}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(times)}" values="{";".join(widths)}"/></rect></clipPath>'
        )
        spans = "".join(f'<tspan fill="{c}">{esc(s)}</tspan>' for s, c in segments)
        body.append(f'<text clip-path="url(#l{i})" x="{x0}" y="{y}" xml:space="preserve">{spans}</text>')
    defs.append("</defs>")

    # final prompt with a blinking cursor once typing has finished
    done = t / cycle
    y_last = y0 + len(lines) * line_h
    body.append(
        f'<g opacity="1">'
        + loop("opacity", ["0", "0", "1", "1"], cycle, f' calcMode="discrete" keyTimes="0;{done:.3f};{done:.3f};1"')
        + f'<text x="{x0}" y="{y_last}" xml:space="preserve"><tspan fill="#7EE787">~/AI1120</tspan><tspan fill="#8B949E"> $ </tspan></text>'
        f'<rect class="cursor" x="{n(x0 + 11 * char_w)}" y="{y_last - 16}" width="9" height="20" fill="{CYAN}"/></g>'
    )

    chrome = (
        f'<rect x="10" y="14" width="{W - 20}" height="{H - 20}" rx="14" fill="{VIOLET}" opacity=".18" filter="url(#soft)"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 6}" rx="14" fill="#0D1117" stroke="#30363D"/>'
        f'<path d="M1 15a14 14 0 0 1 14-14h{W - 32}a14 14 0 0 1 14 14v27H1z" fill="#161B22"/>'
        f'<line x1="1" y1="42" x2="{W - 1}" y2="42" stroke="#30363D"/>'
        '<circle cx="24" cy="22" r="6" fill="#FF5F56"/><circle cx="44" cy="22" r="6" fill="#FFBD2E"/><circle cx="64" cy="22" r="6" fill="#27C93F"/>'
        f'<text x="{W / 2}" y="27" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#8B949E">about.py - zsh</text>'
    )
    filt = '<defs><filter id="soft" x="-10%" y="-10%" width="120%" height="130%"><feGaussianBlur stdDeviation="9"/></filter></defs>'
    style = (
        f"text{{font-family:{MONO};font-size:{size}px;white-space:pre}}"
        ".cursor{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    )
    return svg(W, H, filt + "".join(defs) + chrome + "".join(body), "about.py: AI & Software Engineer", style)


# --------------------------------------------------------------------------
# tech stack: floating 3D keycaps


STACK = [
    ("Languages", [("Python", "python"), ("C++", "cplusplus"), ("JavaScript", "javascript"), ("TypeScript", "typescript")]),
    ("AI / ML", [("PyTorch", "pytorch"), ("TensorFlow", "tensorflow"), ("Hugging Face", "huggingface"), ("LangChain", "langchain"), ("OpenCV", "opencv")]),
    ("Backend & Data", [("FastAPI", "fastapi"), ("Django", "django"), ("PostgreSQL", "postgresql"), ("Redis", "redis")]),
    ("DevOps & Cloud", [("Docker", "docker"), ("Kubernetes", "kubernetes"), ("AWS", "aws"), ("Linux", "linux"), ("Git", "git")]),
]
TILE_COLORS = {  # brand colours, lifted where the official one vanishes on a dark card
    "python": "#3776AB", "cplusplus": "#00599C", "javascript": "#F7DF1E", "typescript": "#3178C6",
    "pytorch": "#EE4C2C", "tensorflow": "#FF6F00", "huggingface": "#FFD21E", "langchain": "#1C9C8C",
    "opencv": "#5C3EE8", "fastapi": "#009688", "django": "#0C4B33", "postgresql": "#4169E1",
    "redis": "#FF4438", "docker": "#2496ED", "kubernetes": "#326CE5", "aws": "#232F3E",
    "linux": "#FCC624", "git": "#F03C2E", "jupyter": "#F37626",
}


def keycap(slug, x, y, size, depth, delay):
    color = TILE_COLORS[slug]
    glyph = "#0B1120" if luminance(color) > 0.4 else "#FFFFFF"
    if slug == "aws":
        art = icon(devicon("amazonwebservices", "original-wordmark"), size * 0.66, 128, x + size * 0.17, y + size * 0.15,
                   glyph, {"#252f3e": "#FFFFFF", "#f90": "#FF9900"})
    else:
        art = icon(simple_icon(slug), size * 0.5, 24, x + size * 0.25, y + size * 0.25, glyph)
    r = size * 0.24
    return (
        f'<ellipse class="shadow" style="animation-delay:{delay}s" cx="{n(x + size / 2)}" cy="{n(y + size + depth + 9)}" '
        f'rx="{n(size * 0.42)}" ry="5" fill="#000" opacity=".55" filter="url(#blur)"/>'
        f'<g class="float" style="animation-delay:{delay}s">'
        f'<rect x="{n(x)}" y="{n(y + depth)}" width="{size}" height="{size}" rx="{n(r)}" fill="{shade(color, 0.55)}"/>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{size}" height="{size}" rx="{n(r)}" fill="{color}"/>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{size}" height="{size}" rx="{n(r)}" fill="url(#gloss)" stroke="#FFFFFF" stroke-opacity=".18"/>'
        + art
        + "</g>"
    )


def tech_stack():
    W, size, depth, pitch, row_h, top, left = 900, 54, 7, 118, 118, 34, 228
    H = top + row_h * len(STACK) + 6
    body = [
        '<defs><linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity=".32"/><stop offset=".5" stop-color="#fff" stop-opacity=".04"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".12"/></linearGradient>'
        '<filter id="blur" x="-50%" y="-100%" width="200%" height="300%"><feGaussianBlur stdDeviation="3"/></filter>'
        '<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#1E293B"/></pattern>'
        f'<linearGradient id="accent" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="#0B1120" stroke="#1E293B"/>',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="url(#dots)" opacity=".7"/>',
    ]
    k = 0
    for r, (category, tools) in enumerate(STACK):
        y = top + r * row_h
        if r:
            body.append(f'<line x1="32" y1="{y - 22}" x2="{W - 32}" y2="{y - 22}" stroke="#1E293B"/>')
        body.append(
            f'<rect x="36" y="{y + 16}" width="4" height="22" rx="2" fill="url(#accent)"/>'
            f'<text x="52" y="{y + 33}" font-size="15" font-weight="600" fill="#E2E8F0" letter-spacing=".6">{esc(category.upper())}</text>'
        )
        for c, (label, slug) in enumerate(tools):
            x = left + c * pitch + (pitch - size) / 2
            body.append(keycap(slug, x, y, size, depth, -(k * 0.37) % 4))
            body.append(f'<text x="{n(x + size / 2)}" y="{y + size + depth + 26}" text-anchor="middle" font-size="13" fill="{MUTED}">{esc(label)}</text>')
            k += 1
    style = (
        f"text{{font-family:{FONT}}}"
        ".float{animation:float 4s ease-in-out infinite both}"
        "@keyframes float{50%{transform:translateY(-7px)}}"
        ".shadow{animation:shadow 4s ease-in-out infinite both;transform-box:fill-box;transform-origin:center}"
        "@keyframes shadow{50%{transform:scale(.8);opacity:.3}}"
    )
    return svg(W, H, "".join(body), "Tech stack", style)


# --------------------------------------------------------------------------
# featured project cards

PROJECTS = [
    ("integrated_production_management_system", "Integrated Production Management System",
     "End-to-end system for planning, tracking and reporting production workflows.", "Python", "python"),
    ("computer_vision", "Computer Vision",
     "Computer vision experiments and detection pipelines for images and video.", "Python", "python"),
    ("face_and_clothes_recognition", "Face & Clothes Recognition",
     "Deep-learning models that recognise faces and clothing in images.", "Jupyter Notebook", "jupyter"),
    ("chatbot_child", "Conversational Chatbot",
     "Conversational AI chatbot application built in Python.", "Python", "python"),
    ("pdf_fine_tuning", "PDF Fine-Tuning",
     "Fine-tuning language models on knowledge extracted from PDF documents.", "Jupyter Notebook", "jupyter"),
    ("voice-translator", "Voice Translator",
     "Web app that translates speech between languages.", "JavaScript", "javascript"),
]


def wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line]


def project_card(index, repo, title, description, language, slug):
    W, H, cw, ch = 500, 190, 484, 174
    color = TILE_COLORS[slug]
    title_size = 19 if len(title) * 19 * 0.55 < cw - 104 else 17
    desc = "".join(
        f'<tspan x="24" y="{106 + i * 22}">{esc(line)}</tspan>' for i, line in enumerate(wrap(description, 54)[:2])
    )
    body = (
        '<defs>'
        f'<linearGradient id="face" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#131C31"/><stop offset="1" stop-color="#0C1222"/></linearGradient>'
        f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity=".6"/><stop offset="1" stop-color="{VIOLET}" stop-opacity=".25"/></linearGradient>'
        '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="card"><rect x="1" y="1" width="{cw}" height="{ch}" rx="16"/></clipPath>'
        '<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".3"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '</defs>'
        # stacked layer behind the card gives it depth
        f'<rect x="14" y="14" width="{cw}" height="{ch}" rx="16" fill="#0A0F1C" stroke="#1E293B"/>'
        f'<rect x="1" y="1" width="{cw}" height="{ch}" rx="16" fill="url(#face)" stroke="url(#edge)" stroke-width="1.5"/>'
        f'<g clip-path="url(#card)"><rect x="-220" y="0" width="200" height="{ch + 2}" fill="url(#shine)" transform="skewX(-20)">'
        f'<animate attributeName="x" values="-220;-220;{cw + 120}" keyTimes="0;.6;1" dur="7s" begin="{index * 0.8:.1f}s" repeatCount="indefinite"/></rect></g>'
        # language keycap
        f'<rect x="24" y="27" width="44" height="44" rx="11" fill="{shade(color, 0.55)}"/>'
        f'<rect x="24" y="22" width="44" height="44" rx="11" fill="{color}"/>'
        f'<rect x="24" y="22" width="44" height="44" rx="11" fill="url(#gloss)" stroke="#fff" stroke-opacity=".18"/>'
        + icon(simple_icon(slug), 24, 24, 34, 32, "#0B1120" if luminance(color) > 0.4 else "#FFFFFF")
        + f'<text x="84" y="45" font-size="{title_size}" font-weight="700" fill="{TEXT}">{esc(title)}</text>'
        f'<text x="84" y="66" font-family="{MONO}" font-size="12" fill="#64748B">AI1120/{esc(repo)}</text>'
        f'<text font-size="14.5" fill="{MUTED}">{desc}</text>'
        f'<circle cx="30" cy="{ch - 22}" r="5.5" fill="{color}"/>'
        f'<text x="42" y="{ch - 17}" font-size="13" fill="#CBD5E1">{esc(language)}</text>'
        f'<text x="{cw - 22}" y="{ch - 17}" text-anchor="end" font-size="13" font-weight="600" fill="{CYAN}">View repository &#8594;</text>'
    )
    return svg(W, H, body, f"{title}: {description}", f"text{{font-family:{FONT}}}")


# --------------------------------------------------------------------------
# footer waves


def footer():
    W, H = 1200, 110

    def wave(amp, period, phase, base):
        pts = [f"{x},{n(base + amp * math.sin(2 * math.pi * x / period + phase))}" for x in range(0, 2 * W + 1, 20)]
        return f"M{pts[0]} L" + " ".join(pts[1:]) + f" L{2 * W},{H} L0,{H} Z"

    layers = [(10, 600, 0.0, 46, ".22", 16), (12, 400, 1.3, 58, ".35", 11), (9, 300, 2.4, 72, ".85", 8)]
    body = (
        f'<defs><linearGradient id="wave" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>'
    )
    for amp, period, phase, base, opacity, dur in layers:
        body += (
            f'<path d="{wave(amp, period, phase, base)}" fill="url(#wave)" opacity="{opacity}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;-{W} 0" dur="{dur}s" repeatCount="indefinite"/></path>'
        )
    return svg(W, H, body, "Footer")


def main():
    (ASSETS / "projects").mkdir(parents=True, exist_ok=True)
    outputs = {
        "hero.svg": hero(),
        "about.svg": terminal(),
        "tech-stack.svg": tech_stack(),
        "footer.svg": footer(),
    }
    for i, project in enumerate(PROJECTS):
        outputs[f"projects/{project[0]}.svg"] = project_card(i, *project)
    for name, content in outputs.items():
        (ASSETS / name).write_text(content)
        print(f"{name:55} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
