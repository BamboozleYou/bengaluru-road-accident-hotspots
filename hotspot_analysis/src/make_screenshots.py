"""Render implementation screenshots (code cell + its printed output) for the report.

The code is cut straight from the module source files and the output is the text that
the same block printed when run_all.py executed it, so every screenshot matches the run.
"""
import ast
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import PythonLexer, TextLexer

from common import CONSOLE, PROJECT

SRC = Path(__file__).resolve().parent
OUT = PROJECT / "outputs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
MAX_OUT_LINES = 34


def block(file, name):
    """Code inside `with step("name"):` (dedented) or the full source of function `name`."""
    src = (SRC / file).read_text()
    tree = ast.parse(src)
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.With) and ast.unparse(node.items[0].context_expr) == f"step('{name}')":
            return textwrap.dedent("\n".join(lines[node.body[0].lineno - 1: node.end_lineno]))
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(lines[node.lineno - 1: node.end_lineno])
    raise KeyError(name)


def render(code, fmt_lexer, font_size=20, line_numbers=True):
    fmt = ImageFormatter(font_name="Menlo", font_size=font_size, line_numbers=line_numbers, style="friendly",
                         line_pad=4, image_pad=14, line_number_bg="#eef0f2", line_number_fg="#8a8f98")
    import io
    return Image.open(io.BytesIO(highlight(code, fmt_lexer, fmt))).convert("RGB")


def label_strip(text, width, bg):
    im = Image.new("RGB", (width, 34), bg)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 17)
    except OSError:
        f = ImageFont.load_default()
    d.text((12, 7), text, fill="white", font=f)
    return im


def shot(sid, file, name, output=None, cell_no=1):
    code = block(file, name)
    parts = [("In [%d]:  %s  —  %s" % (cell_no, file, name), "#2a5d9f", render(code, PythonLexer()))]
    out_name = output if output is not None else name
    if out_name:
        txt = (CONSOLE / f"{out_name}.txt").read_text().rstrip("\n")
        tl = txt.splitlines()
        if len(tl) > MAX_OUT_LINES:
            tl = tl[:MAX_OUT_LINES] + [f"... ({len(tl) - MAX_OUT_LINES} more lines)"]
        parts.append(("Out [%d]:" % cell_no, "#52514e", render("\n".join(tl), TextLexer(), 18, False)))
    width = max(p[2].width for p in parts) + 4
    height = sum(p[2].height + 34 for p in parts) + 4
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    for lab, colr, im in parts:
        canvas.paste(label_strip(lab, width, colr), (0, y))
        y += 34
        bg = Image.new("RGB", (width, im.height), "#f7f7f5" if "Out" in lab else "#ffffff")
        bg.paste(im, (2, 0))
        canvas.paste(bg, (0, y))
        y += im.height
    ImageDraw.Draw(canvas).rectangle([0, 0, width - 1, height - 1], outline="#c3c2b7", width=2)
    canvas.save(OUT / f"{sid}.png")


SHOTS = [
    ("ss01_load", "m1_data_acquisition.py", "m1_load", None),
    ("ss02_inspect", "m1_data_acquisition.py", "m1_inspect", None),
    ("ss03_tidy_fn", "m1_data_acquisition.py", "tidy_wide", ""),
    ("ss04_reshape", "m1_data_acquisition.py", "m1_reshape", None),
    ("ss05_info", "m1_data_acquisition.py", "m1_info", None),
    ("ss06_aggregates", "m2_preprocessing.py", "m2_aggregates", None),
    ("ss07_dtypes", "m2_preprocessing.py", "m2_dtypes", None),
    ("ss08_names", "m2_preprocessing.py", "m2_names", None),
    ("ss09_missing", "m2_preprocessing.py", "m2_missing", None),
    ("ss10_duplicates", "m2_preprocessing.py", "m2_duplicates", None),
    ("ss11_validity", "m2_preprocessing.py", "m2_validity", None),
    ("ss12_iqr_fn", "m2_preprocessing.py", "iqr_bounds", ""),
    ("ss13_outliers", "m2_preprocessing.py", "m2_outliers", None),
    ("ss14_features", "m2_preprocessing.py", "m2_features", None),
    ("ss15_supporting", "m2_preprocessing.py", "m2_supporting", None),
    ("ss16_central", "m3_univariate_bivariate.py", "m3_central_tendency", None),
    ("ss17_concentration", "m3_univariate_bivariate.py", "m3_concentration", None),
    ("ss18_city_trend", "m3_univariate_bivariate.py", "m3_city_trend", None),
    ("ss19_severity", "m3_univariate_bivariate.py", "m3_severity_trend", None),
    ("ss20_zone_year", "m3_univariate_bivariate.py", "m3_zone_year", None),
    ("ss21_kruskal", "m3_univariate_bivariate.py", "m3_zone_kruskal", None),
    ("ss22_top", "m3_univariate_bivariate.py", "m3_top_stations", None),
    ("ss23_fatal_total", "m3_univariate_bivariate.py", "m3_fatal_vs_total", None),
    ("ss24_change", "m3_univariate_bivariate.py", "m3_change", None),
    ("ss25_describe", "m4_multivariate_statistics.py", "m4_describe", None),
    ("ss26_period", "m4_multivariate_statistics.py", "m4_period_stats", None),
    ("ss27_corr", "m4_multivariate_statistics.py", "m4_correlation", None),
    ("ss28_persistence", "m4_multivariate_statistics.py", "m4_persistence", None),
    ("ss29_zone_year_fr", "m4_multivariate_statistics.py", "m4_zone_year_fr", None),
    ("ss30_hpi", "m4_multivariate_statistics.py", "m4_priority_index", None),
    ("ss31_karnataka", "m4_multivariate_statistics.py", "m4_karnataka", None),
    ("ss32_india", "m4_multivariate_statistics.py", "m4_india", None),
]

if __name__ == "__main__":
    for i, (sid, f, n, o) in enumerate(SHOTS, 1):
        shot(sid, f, n, o, i)
    print(f"{len(SHOTS)} screenshots written to {OUT}")
