"""Render article/charts/cost-quality-table.png — three-tier buyer's guide.

Highlighted middle row is the article's headline finding.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Data --------------------------------------------------------------------

ROWS = [
    {
        "budget": "$0.50",
        "budget_sub": "per cell",
        "pick": "Plan Mode + Sonnet",
        "why": (
            "Mean 4.17 quality, n=12. Lives with the Task 2 amount-field\n"
            "miss (catches it 30% of the time). Otherwise indistinguishable\n"
            "from more expensive options on simple/clear tasks."
        ),
        "highlight": False,
    },
    {
        "budget": "$2–3",
        "budget_sub": "per cell",
        "pick": "Plan Mode + Opus  ≈  BMAD + Sonnet",
        "why": (
            "A-Opus mean 4.84 (n=19) at $2.24/cell. C-Sonnet mean 4.83 (n=12)\n"
            "at $2.67/cell. Functionally tied on quality. Opus + Plan Mode\n"
            "is ~16% cheaper per cell."
        ),
        "highlight": True,
    },
    {
        "budget": "$5+",
        "budget_sub": "per cell",
        "pick": "BMAD + Opus  (flagship work)",
        "why": (
            "Cleanest single implementation in the benchmark. Decimal ×\n"
            "ROUND_HALF_UP, separate discounts.py module, 36 passing\n"
            "tests, $5.22 for the cell."
        ),
        "highlight": False,
    },
]

# Palette (matches predictions table) -------------------------------------

INK = "#0f172a"           # slate-900
INK_MUTED = "#475569"     # slate-600
INK_ACCENT = "#1d4ed8"    # blue-700 (for the highlighted row's "Pick")
HEADER_BG = "#1e293b"     # slate-800
HEADER_INK = "#f8fafc"    # slate-50
ROW_BG_A = "#ffffff"
ROW_BG_B = "#f8fafc"      # slate-50
HIGHLIGHT_BG = "#eff6ff"  # blue-50 — subtle tint
HIGHLIGHT_BAR = "#1d4ed8" # blue-700 — thin left accent bar
BORDER = "#e2e8f0"        # slate-200

# Layout (1200 × 500 px at dpi=150) --------------------------------------

FIG_W = 8.0          # × 150 = 1200 px
FIG_H = 3.3333       # × 150 ≈ 500 px
LEFT = 0.02
RIGHT = 0.98
TOP = 0.93
BOTTOM = 0.05

COL_FRACS = [0.13, 0.40, 0.47]
COL_NAMES = ["Budget", "Pick", "Why"]


def column_xs(usable_left: float, usable_w: float) -> list[float]:
    xs = [usable_left]
    for f in COL_FRACS[:-1]:
        xs.append(xs[-1] + f * usable_w)
    xs.append(usable_left + usable_w)
    return xs


def render() -> None:
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    usable_left = LEFT
    usable_right = RIGHT
    usable_w = usable_right - usable_left
    xs = column_xs(usable_left, usable_w)

    header_h = 0.11
    n_rows = len(ROWS)
    body_top = TOP - header_h
    body_h = body_top - BOTTOM
    row_h = body_h / n_rows

    # ---- Header --------------------------------------------------------
    ax.add_patch(
        Rectangle(
            (usable_left, body_top),
            usable_w,
            header_h,
            facecolor=HEADER_BG,
            edgecolor="none",
        )
    )
    for i, name in enumerate(COL_NAMES):
        cx_left = xs[i] + 0.014
        cy = body_top + header_h / 2
        ax.text(
            cx_left,
            cy,
            name.upper(),
            color=HEADER_INK,
            fontsize=10,
            fontweight="bold",
            ha="left",
            va="center",
            family="DejaVu Sans",
            fontstretch="condensed",
        )

    # ---- Body rows -----------------------------------------------------
    accent_bar_w = 0.005  # thin accent bar width for highlighted row
    for ri, row in enumerate(ROWS):
        y_top = body_top - (ri + 1) * row_h
        if row["highlight"]:
            bg = HIGHLIGHT_BG
        else:
            bg = ROW_BG_A if ri % 2 == 0 else ROW_BG_B

        ax.add_patch(
            Rectangle(
                (usable_left, y_top),
                usable_w,
                row_h,
                facecolor=bg,
                edgecolor="none",
            )
        )

        # Thin accent bar on the highlighted row (left edge, inside the
        # outer border).
        if row["highlight"]:
            ax.add_patch(
                Rectangle(
                    (usable_left, y_top),
                    accent_bar_w,
                    row_h,
                    facecolor=HIGHLIGHT_BAR,
                    edgecolor="none",
                )
            )

        cy = y_top + row_h / 2

        # Budget cell: big amount + subtitle
        ax.text(
            xs[0] + 0.014,
            cy + 0.025,
            row["budget"],
            color=INK,
            fontsize=15,
            fontweight="bold",
            ha="left",
            va="center",
            family="DejaVu Sans",
        )
        ax.text(
            xs[0] + 0.014,
            cy - 0.025,
            row["budget_sub"],
            color=INK_MUTED,
            fontsize=8,
            ha="left",
            va="center",
            family="DejaVu Sans",
            style="italic",
        )

        # Pick cell
        pick_color = INK_ACCENT if row["highlight"] else INK
        pick_weight = "bold" if row["highlight"] else "semibold"
        ax.text(
            xs[1] + 0.014,
            cy,
            row["pick"],
            color=pick_color,
            fontsize=10,
            fontweight=pick_weight,
            ha="left",
            va="center",
            family="DejaVu Sans",
        )

        # Why cell — multiline
        ax.text(
            xs[2] + 0.014,
            cy,
            row["why"],
            color=INK,
            fontsize=9,
            ha="left",
            va="center",
            family="DejaVu Sans",
            linespacing=1.4,
        )

    # ---- Borders / dividers -------------------------------------------
    ax.add_patch(
        Rectangle(
            (usable_left, BOTTOM),
            usable_w,
            TOP - BOTTOM,
            facecolor="none",
            edgecolor=BORDER,
            linewidth=1.0,
        )
    )
    ax.plot(
        [usable_left, usable_left + usable_w],
        [body_top, body_top],
        color=BORDER,
        linewidth=1.0,
    )
    for ri in range(1, n_rows):
        y = body_top - ri * row_h
        ax.plot(
            [usable_left, usable_left + usable_w],
            [y, y],
            color=BORDER,
            linewidth=0.6,
        )
    for i in range(1, len(COL_NAMES)):
        x = xs[i]
        ax.plot([x, x], [BOTTOM, TOP], color=BORDER, linewidth=0.6)

    fig.savefig(
        "article/charts/cost-quality-table.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


if __name__ == "__main__":
    render()
    print("wrote article/charts/cost-quality-table.png")
