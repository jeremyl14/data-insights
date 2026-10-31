"""Render the station activity map as an MP4.

Reads the data embedded in outputs/station-activity-map.html (run analyze.py
first), so the video and the page always show the same numbers, colours and
scale. Frames step evenly through the whole period; each shows the 7-day
rolling activity ending on that day.

Usage:
    python render_video.py [--seconds 14] [--fps 30] [--height 1080] [--crf 18]
                           [--out outputs/station-activity-map.mp4]

    # small file for sharing (~0.3 MB for 7 s)
    python render_video.py --seconds 7 --height 720 --crf 30 --out outputs/station-activity-map-7s.mp4

Needs ffmpeg with libx264 on PATH.
"""

import argparse
import base64
import datetime as dt
import json
import math
import pathlib
import re
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
HTML = HERE / "outputs" / "station-activity-map.html"

# Layout is fixed at 16x9 inches; --height sets the DPI, so 1080 -> 120 dpi, 720 -> 80 dpi
FIG_W_IN, FIG_H_IN = 16, 9

# Light-theme tokens, matching template.html
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
LAND = "#f3f2ee"
WARD_LINE = "#d6d4cc"
WATER = "#e8ecee"
SERIES = "#2a78d6"
SERIES_WASH = (42 / 255, 120 / 255, 214 / 255, 0.14)
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
        "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP = LinearSegmentedColormap.from_list("ramp", RAMP[3:])  # palest steps trimmed, as on the page


def load_payload():
    html = HTML.read_text()
    return json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))


def fmt_k(n):
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{round(n / 1e3)}k"
    return str(int(n))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=14)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--height", type=int, default=1080, help="frame height in px (16:9); e.g. 720")
    parser.add_argument("--crf", type=int, default=18, help="x264 quality: lower is better/larger; ~30 is small")
    parser.add_argument("--out", type=pathlib.Path, default=HERE / "outputs" / "station-activity-map.mp4")
    args = parser.parse_args()
    dpi = args.height / FIG_H_IN
    w_px, h_px = round(FIG_W_IN * dpi), args.height
    w_px += w_px % 2  # x264 with yuv420p needs even dimensions

    d = load_payload()
    start = dt.date.fromisoformat(d["start"])
    ndays = d["ndays"]
    total = np.array(d["total"], dtype=float)
    hi = d["domain"]["count"][1]
    values = np.frombuffer(base64.b64decode(d["values"]), dtype="<u2")

    # Dense (dots x days) matrix of 7-day activity
    dots = d["dots"]
    lon = np.array([x[3] for x in dots])
    lat = np.array([x[2] for x in dots])
    act = np.zeros((len(dots), ndays), dtype=np.float32)
    for i, (_, _, _, _, a, n, off) in enumerate(dots):
        act[i, a:a + n] = values[off:off + n]

    kx = math.cos(math.radians(43.70))
    px, py = lon * kx, lat

    fig = plt.figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi, facecolor=SURFACE)
    fig.text(0.035, 0.945, "Bike Share Toronto station activity, 2018–2026", fontsize=22,
             fontweight="bold", color=INK, va="top")
    fig.text(0.035, 0.895, "Each dot is a station, coloured by trips started + ended there in the 7 days "
             "up to the date shown. Fixed cube-root colour scale.", fontsize=12, color=INK_2, va="top")

    # --- map ---
    ax = fig.add_axes([0.035, 0.24, 0.63, 0.63])
    ax.set_facecolor(SURFACE)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():  # hairline frame, so the cropped wards and lake read as a map panel
        s.set_color(GRID)
        s.set_linewidth(1)
    ward_polys = [[(x * kx, y) for x, y in p[0]] for f in d["wards"]["features"]
                  for p in f["geometry"]["coordinates"]]
    ax.add_collection(PolyCollection(ward_polys, facecolor=LAND, edgecolor=WARD_LINE, linewidth=0.8, zorder=1))
    for f in d["lake"]["features"]:
        rings = [np.array([(x * kx, y) for x, y in r]) for r in f["geometry"]["coordinates"]]
        # outer boundary plus holes in one compound path, so islets stay land
        verts = np.concatenate(rings)
        codes = np.concatenate([[Path.MOVETO] + [Path.LINETO] * (len(r) - 2) + [Path.CLOSEPOLY] for r in rings])
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=WATER, edgecolor="none", zorder=2))
    pad = 0.05 * max(px.max() - px.min(), py.max() - py.min())
    ax.set_xlim(px.min() - pad, px.max() + pad)
    ax.set_ylim(py.min() - pad, py.max() + pad)
    ax.set_aspect("equal")
    scat = ax.scatter([], [], s=[], c=[], cmap=CMAP, vmin=0, vmax=1, linewidths=0.6,
                      edgecolors=SURFACE, zorder=3)

    # --- right panel: date, stats, legend ---
    date_txt = fig.text(0.72, 0.80, "", fontsize=40, fontweight="bold", color=INK)
    sub_txt = fig.text(0.72, 0.765, "", fontsize=13, color=MUTED)
    total_txt = fig.text(0.72, 0.64, "", fontsize=30, fontweight="bold", color=INK)
    fig.text(0.72, 0.615, "trip starts + ends, 7 days", fontsize=12, color=MUTED)
    active_txt = fig.text(0.86, 0.64, "", fontsize=30, fontweight="bold", color=INK)
    fig.text(0.86, 0.615, "active stations", fontsize=12, color=MUTED)

    lax = fig.add_axes([0.72, 0.44, 0.24, 0.025])
    lax.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=CMAP, extent=(0, 1, 0, 1))
    lax.set_yticks([])
    ticks = [0, 10, 100, 500, 1000, hi]
    lax.set_xticks([math.cbrt(v) / math.cbrt(hi) for v in ticks])
    lax.set_xticklabels([fmt_k(v) + ("+" if v == hi else "") for v in ticks], fontsize=11, color=MUTED)
    lax.tick_params(length=0, pad=6)
    for s in lax.spines.values():
        s.set_visible(False)
    fig.text(0.72, 0.48, "Trip starts + ends, 7 days (cube-root scale)", fontsize=12,
             fontweight="bold", color=INK)
    fig.text(0.72, 0.32, "Source: City of Toronto Open Data,\n"
             "Bike Share Toronto Ridership (2018 – Sep 2026).\n"
             "Stations placed at their location on each date\n"
             "(Bike Share Toronto GBFS feed + archived copies).",
             fontsize=10, color=MUTED, va="top", linespacing=1.5)

    # --- system activity strip ---
    sax = fig.add_axes([0.06, 0.06, 0.90, 0.13])
    days = np.arange(ndays)
    sax.fill_between(days, total, color=SERIES_WASH, linewidth=0)
    sax.plot(days, total, color=SERIES, linewidth=1.6)
    sax.set_xlim(0, ndays - 1)
    sax.set_ylim(0, total.max() * 1.08)
    years = range(start.year, (start + dt.timedelta(ndays - 1)).year + 1)
    sax.set_xticks([(dt.date(y, 1, 1) - start).days for y in years])
    sax.set_xticklabels([str(y) for y in years], fontsize=10, color=MUTED)
    step = 250_000
    sax.set_yticks(np.arange(0, total.max() + step, step))
    sax.set_yticklabels([fmt_k(v) for v in np.arange(0, total.max() + step, step)], fontsize=10, color=MUTED)
    sax.grid(axis="y", color=GRID, linewidth=0.8)
    sax.tick_params(length=0)
    for name, s in sax.spines.items():
        s.set_visible(name == "bottom")
        s.set_color(AXIS)
    sax.set_facecolor(SURFACE)
    sax.set_title("System activity — trip starts + ends per 7 days", loc="left", fontsize=11,
                  color=INK, fontweight="bold", pad=6)
    cursor = sax.axvline(0, color=INK, linewidth=1.4)
    (cursor_dot,) = sax.plot([0], [0], "o", color=SERIES, markersize=7, markeredgecolor=SURFACE,
                             markeredgewidth=1.5)

    nframes = round(args.seconds * args.fps)
    frame_days = np.round(np.linspace(0, ndays - 1, nframes)).astype(int)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{w_px}x{h_px}", "-r", str(args.fps), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(args.crf), "-preset", "slow",
         "-movflags", "+faststart", str(args.out)],
        stdin=subprocess.PIPE,
    )
    for k, day in enumerate(frame_days):
        v = act[:, day]
        idx = np.flatnonzero(v > 0)
        idx = idx[np.argsort(v[idx])]  # quiet first, busy on top
        t = np.clip(np.cbrt(v[idx]) / math.cbrt(hi), 0, 1)
        r = 2.0 + 3.4 * t  # radius in points
        scat.set_offsets(np.column_stack([px[idx], py[idx]]))
        scat.set_array(t)
        scat.set_sizes((2 * r) ** 2)

        date = start + dt.timedelta(int(day))
        date_txt.set_text(f"{date:%b} {date.day}, {date.year}")
        sub_txt.set_text(f"7 days ending {date:%A}")
        total_txt.set_text(fmt_k(total[day]))
        active_txt.set_text(f"{len(idx):,}")
        cursor.set_xdata([day, day])
        cursor_dot.set_data([day], [total[day]])

        fig.canvas.draw()
        ffmpeg.stdin.write(fig.canvas.buffer_rgba().tobytes())
        if k % 60 == 0:
            print(f"frame {k}/{nframes} ({date})")
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise SystemExit("ffmpeg failed")
    print(f"Saved {args.out} ({nframes} frames, {args.seconds:g}s at {args.fps} fps, "
          f"{args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
