"""Render article/charts/predictions-table.png — hypothesis vs actual."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# Data --------------------------------------------------------------------

ROWS = [
    {
        "task": "Task 1",
        "task_sub": "trivial bug",
        "predicted": "Plan Mode wins on cost / time / score",
        "actual": "Plan Mode & BMAD tied at 5/5;\nPlan Mode won on cost",
        "verdict": "✓",
        "verdict_kind": "partial",
        "verdict_label": "partial",
    },
    {
        "task": "Task 2",
        "task_sub": "medium feature",
        "predicted": "Plan Mode wins on cost / time / score",
        "actual": "Plan Mode caught amount field 3/10 on Sonnet;\nBMAD 3/3",
        "verdict": "✗",
        "verdict_kind": "miss",
        "verdict_label": "miss on score",
    },
    {
        "task": "Task 3",
        "task_sub": "ambiguous brief",
        "predicted": "BMAD wins on score",
        "actual": "BMAD 5/5/5; Spec Kit 4/5/5",
        "verdict": "✓",
        "verdict_kind": "match",
        "verdict_label": "mostly",
    },
    {
        "task": "Task 4",
        "task_sub": "brownfield trap",
        "predicted": "Spec Kit wins on score",
        "actual": "Spec Kit worst at 3.67 mean;\nPlan Mode & BMAD tied at 4.33",
        "verdict": "✗",
        "verdict_kind": "miss",
        "verdict_label": "miss on score",
    },
]

# Palette (shadcn-ish neutrals + semantic) --------------------------------

INK = "#0f172a"              # slate-900
INK_MUTED = "#475569"        # slate-600
HEADER_BG = "#1e293b"        # slate-800
HEADER_INK = "#f8fafc"       # slate-50
ROW_BG_A = "#ffffff"
ROW_BG_B = "#f8fafc"         # slate-50
BORDER = "#e2e8f0"           # slate-200
SUCCESS = "#16a34a"          # green-600
SUCCESS_BG = "#dcfce7"       # green-100
FAIL = "#dc2626"             # red-600
FAIL_BG = "#fee2e2"          # red-100
PARTIAL = "#ca8a04"          # yellow-600
PARTIAL_BG = "#fef9c3"       # yellow-100

# Layout (figure in inches at dpi=150 → 1200 × 600 px) --------------------

FIG_W = 8.0   # inches × 150 = 1200 px
FIG_H = 4.0   # inches × 150 = 600 px
LEFT = 0.02
RIGHT = 0.98
TOP = 0.92
BOTTOM = 0.06

# Column fractions of usable width.
COL_FRACS = [0.13, 0.34, 0.43, 0.10]
COL_NAMES = ["Task", "Predicted", "Actual", "Verdict"]


def column_xs(usable_left: float, usable_w: float) -> list[float]:
    xs = [usable_left]
    for f in COL_FRACS[:-1]:
        xs.append(xs[-1] + f * usable_w)
    xs.append(usable_left + usable_w)
    return xs  # length n_cols + 1 (boundaries)


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

    # Vertical layout
    header_h = 0.10
    n_rows = len(ROWS)
    body_top = TOP - header_h
    body_h = body_top - BOTTOM
    row_h = body_h / n_rows

    # ---- Header row -----------------------------------------------------
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
        cx_left = xs[i] + 0.012
        cy = body_top + header_h / 2
        ha = "left" if i < 3 else "center"
        cx = cx_left if i < 3 else (xs[i] + xs[i + 1]) / 2
        ax.text(
            cx,
            cy,
            name.upper(),
            color=HEADER_INK,
            fontsize=9,
            fontweight="bold",
            ha=ha,
            va="center",
            family="DejaVu Sans",
            fontstretch="condensed",
        )

    # ---- Body rows ------------------------------------------------------
    for ri, row in enumerate(ROWS):
        y_top = body_top - (ri + 1) * row_h
        y_bot = body_top - ri * row_h  # actually top edge of next
        # rect from (left, y_top) with height row_h
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

        cy = y_top + row_h / 2

        # Task cell: big number + sub-label
        ax.text(
            xs[0] + 0.012,
            cy + 0.012,
            row["task"],
            color=INK,
            fontsize=11,
            fontweight="bold",
            ha="left",
            va="center",
            family="DejaVu Sans",
        )
        ax.text(
            xs[0] + 0.012,
            cy - 0.022,
            row["task_sub"],
            color=INK_MUTED,
            fontsize=8,
            ha="left",
            va="center",
            family="DejaVu Sans",
            style="italic",
        )

        # Predicted cell
        ax.text(
            xs[1] + 0.012,
            cy,
            row["predicted"],
            color=INK,
            fontsize=9,
            ha="left",
            va="center",
            family="DejaVu Sans",
            wrap=True,
        )

        # Actual cell
        ax.text(
            xs[2] + 0.012,
            cy,
            row["actual"],
            color=INK,
            fontsize=9,
            ha="left",
            va="center",
            family="DejaVu Sans",
            wrap=True,
        )

        # Verdict cell — pill
        kind = row["verdict_kind"]
        if kind == "match":
            fg, bg_pill = SUCCESS, SUCCESS_BG
        elif kind == "partial":
            fg, bg_pill = PARTIAL, PARTIAL_BG
        else:
            fg, bg_pill = FAIL, FAIL_BG

        pill_cx = (xs[3] + xs[4]) / 2
        pill_w = (xs[4] - xs[3]) * 0.72
        pill_h = row_h * 0.45
        pill_x = pill_cx - pill_w / 2
        pill_y = cy - pill_h / 2
        ax.add_patch(
            FancyBboxPatch(
                (pill_x, pill_y),
                pill_w,
                pill_h,
                boxstyle="round,pad=0.005,rounding_size=0.01",
                facecolor=bg_pill,
                edgecolor=fg,
                linewidth=0.8,
            )
        )
        ax.text(
            pill_cx,
            cy + 0.002,
            row["verdict"],
            color=fg,
            fontsize=14,
            fontweight="bold",
            ha="center",
            va="center",
            family="DejaVu Sans",
        )

    # ---- Borders / dividers --------------------------------------------
    # Outer border
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
    # Horizontal divider under header
    ax.plot(
        [usable_left, usable_left + usable_w],
        [body_top, body_top],
        color=BORDER,
        linewidth=1.0,
    )
    # Row dividers
    for ri in range(1, n_rows):
        y = body_top - ri * row_h
        ax.plot(
            [usable_left, usable_left + usable_w],
            [y, y],
            color=BORDER,
            linewidth=0.6,
        )
    # Column dividers (between body cells, excluding outer)
    for i in range(1, len(COL_NAMES)):
        x = xs[i]
        ax.plot(
            [x, x],
            [BOTTOM, TOP],
            color=BORDER,
            linewidth=0.6,
        )

    fig.savefig(
        "article/charts/predictions-table.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


if __name__ == "__main__":
    render()
    print("wrote article/charts/predictions-table.png")
