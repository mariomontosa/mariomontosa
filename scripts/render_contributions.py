#!/usr/bin/env python3
"""Render a GitHub-style contribution calendar as a repository-hosted SVG."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import urllib.request
from pathlib import Path

USER = "mariomontosa"
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path("assets/github-activity.svg")

request = urllib.request.Request(
    URL,
    headers={
        "User-Agent": "Mozilla/5.0 GitHub-Contribution-Calendar",
        "Accept": "text/html",
    },
)
with urllib.request.urlopen(request, timeout=30) as response:
    page = response.read().decode("utf-8")

cells = {
    date: int(level)
    for date, level in re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="([0-4])"', page
    )
}
if not cells:
    cells = {
        date: int(level)
        for level, date in re.findall(
            r'data-level="([0-4])"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', page
        )
    }
if not cells:
    raise RuntimeError("GitHub returned no contribution cells")

dates = sorted(dt.date.fromisoformat(value) for value in cells)
start, end = dates[0], dates[-1]
sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
weeks = ((end - sunday).days // 7) + 1

size, gap = 11, 3
step = size + gap
left, top = 54, 54
width = left + weeks * step + 28
height = 184
colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

rects = []
for day in dates:
    week = (day - sunday).days // 7
    row = (day.weekday() + 1) % 7
    x, y = left + week * step, top + row * step
    level = cells[day.isoformat()]
    rects.append(
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" '
        f'fill="{colors[level]}"><title>{html.escape(day.isoformat())}: level {level}</title></rect>'
    )

labels = []
cursor = dt.date(start.year, start.month, 1)
seen_x = -100
while cursor <= end:
    week = max(0, (cursor - sunday).days // 7)
    x = left + week * step
    if x - seen_x >= 28:
        labels.append(
            f'<text x="{x}" y="40" fill="#f0f6fc" font-size="12">{cursor.strftime("%b")}</text>'
        )
        seen_x = x
    cursor = (cursor.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

daily_counts = [int(value) for value in re.findall(r'([\\d,]+)\\s+contributions?\\s+on\\s+', page, re.I)]
count = f"{sum(daily_counts):,}" if daily_counts else "Public GitHub"

legend_x = width - 184
legend = [
    f'<text x="{legend_x}" y="164" fill="#8b949e" font-size="11">Less</text>'
]
for index, color in enumerate(colors):
    legend.append(
        f'<rect x="{legend_x + 30 + index * step}" y="154" width="{size}" height="{size}" rx="2" fill="{color}"/>'
    )
legend.append(
    f'<text x="{legend_x + 30 + len(colors) * step + 3}" y="164" fill="#8b949e" font-size="11">More</text>'
)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{count} contributions in the last year</title>
<desc id="desc">Live GitHub contribution calendar for @{USER}, updated daily.</desc>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>
<text x="18" y="25" fill="#f0f6fc" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="600">{count} contributions in the last year</text>
<g font-family="Segoe UI,Arial,sans-serif">
{''.join(labels)}
<text x="17" y="{top + step + 9}" fill="#8b949e" font-size="11">Mon</text>
<text x="17" y="{top + 3 * step + 9}" fill="#8b949e" font-size="11">Wed</text>
<text x="17" y="{top + 5 * step + 9}" fill="#8b949e" font-size="11">Fri</text>
{''.join(rects)}
{''.join(legend)}
</g>
</svg>
"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"Rendered {len(cells)} days to {OUT}")
