"""One-page PNG report: McKinney-Vento + child poverty for the target districts.

    python3 report.py          # -> figures/district_report.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from mckinney_vento import load, plots
from mckinney_vento.config import DISTRICTS, FIGURES_DIR

plots.use_style()
panel = load.focus_panel()
state = load.state_totals()
everyone = load.statewide_panel()
years = sorted(panel["school_year"].unique())
first, latest = years[0], years[-1]

# --- Snapshot numbers ------------------------------------------------------------------
cur = everyone[(everyone["school_year"] == latest) & everyone["enrollment"].ge(1000)
               & everyone["homeless_per_1000_enrolled"].notna()].copy()
cur["rank"] = cur["homeless_per_1000_enrolled"].rank(ascending=False, method="min").astype(int)
n_ranked = len(cur)
rank = dict(zip(cur["leaid"], cur["rank"]))
nc_rate = state.loc[state["school_year"] == latest, "homeless_per_1000_enrolled"].iloc[0]


def row(name: str) -> list[str]:
    g = panel[panel["district"] == name].set_index("school_year")
    a, b = g.loc[first], g.loc[latest]
    chg = (b.homeless_enrolled / a.homeless_enrolled - 1) * 100
    return [
        DISTRICTS[b.leaid]["name"],
        f"{b.enrollment:,.0f}",
        f"{b.homeless_enrolled:,.0f}",
        f"{chg:+.0f}%",
        f"{b.homeless_per_1000_enrolled:.1f}",
        f"{rank.get(b.leaid, '–')} of {n_ranked}",
        f"{b.saipe_poverty_rate_pct:.1f}%",
        f"{b.children_5_17_poverty:,.0f}",
        f"{b.homeless_per_100_poor_children:.1f}",
        "Yes" if b.mv_subgrantee else "No",
    ]


names = [v["short"] for v in DISTRICTS.values()]
table_rows = [row(n) for n in names]

# --- Layout ----------------------------------------------------------------------------
fig = plt.figure(figsize=(16, 19))
gs = fig.add_gridspec(5, 2, height_ratios=[0.75, 1, 1, 1, 0.75], hspace=0.55, wspace=0.16,
                      left=0.05, right=0.95, top=0.95, bottom=0.05)

fig.text(0.05, 0.975, "Student homelessness & child poverty — Kannapolis, Cabarrus, Rowan-Salisbury",
         fontsize=20, fontweight="bold", color=plots.TEXT)
fig.text(0.05, 0.961, f"McKinney-Vento identified students, school years {first} to {latest}, "
         "from federal EDFacts data (U.S. Dept. of Education)", fontsize=12, color=plots.TEXT_2)

# Takeaways box
tk = fig.add_subplot(gs[0, :]); tk.axis("off")
g = panel.set_index(["district", "school_year"])
def v(d, y, c): return g.loc[(d, y), c]
C, K, R = "Cabarrus", "Kannapolis", "Rowan-Salisbury"
takeaways = [
    f"Cabarrus identified {v(C, latest, 'homeless_enrolled'):,.0f} homeless students in {latest}, up "
    f"{(v(C, latest, 'homeless_enrolled') / v(C, years[-2], 'homeless_enrolled') - 1) * 100:.0f}% in one year and nearly 3× its "
    f"{first} count — despite the lowest child-poverty rate of the three ({v(C, latest, 'saipe_poverty_rate_pct'):.1f}%). "
    "Worth confirming with the district whether this reflects real growth or improved identification.",
    f"Kannapolis's rate fell by half, from {v(K, first, 'homeless_per_1000_enrolled'):.0f} to "
    f"{v(K, latest, 'homeless_per_1000_enrolled'):.0f} per 1,000 students, as its child poverty fell "
    f"({v(K, first, 'saipe_poverty_rate_pct'):.0f}% → {v(K, latest, 'saipe_poverty_rate_pct'):.1f}%). It now sits just below the NC rate ({nc_rate:.1f}).",
    f"Rowan-Salisbury has the highest child poverty of the three ({v(R, latest, 'saipe_poverty_rate_pct'):.1f}%) yet the lowest identification: "
    f"{v(R, latest, 'homeless_per_1000_enrolled'):.1f} per 1,000 students (NC: {nc_rate:.1f}) and "
    f"{v(R, latest, 'homeless_per_100_poor_children'):.1f} per 100 poor children — a possible under-identification signal.",
    "All three districts are McKinney-Vento subgrantees and reported un-suppressed counts in every year.",
]
import textwrap
tk.text(0, 1.0, "Key takeaways", fontsize=13, fontweight="bold", va="top", color=plots.TEXT)
y = 0.80
for t in takeaways:
    lines = textwrap.wrap(t, 165)
    tk.text(0.01, y, "•  " + "\n    ".join(lines), fontsize=11, va="top", color=plots.TEXT, linespacing=1.4)
    y -= 0.13 + 0.11 * len(lines)

specs = [
    ("homeless_enrolled", "Homeless students enrolled (count)", None, "{:,.0f}", "Students"),
    ("homeless_per_1000_enrolled", "Homeless students per 1,000 enrolled (dashed = NC)", state, "{:.1f}", "Per 1,000"),
    ("saipe_poverty_rate_pct", "Child poverty rate, ages 5–17 (Census SAIPE)", None, "{:.1f}%", "Percent"),
    ("children_5_17_poverty", "Children ages 5–17 living in poverty (count)", None, "{:,.0f}", "Children"),
    ("homeless_per_100_poor_children", "Homeless students identified per 100 children in poverty", None, "{:.1f}", "Per 100"),
    ("enrollment", "Total district enrollment (NCES CCD)", None, "{:,.0f}", "Students"),
]
for i, (col, title, st, fmt, yl) in enumerate(specs):
    ax = fig.add_subplot(gs[1 + i // 2, i % 2])
    plots.line_panel(ax, panel, col, years, title=title, state=st, label_fmt=fmt, ylabel=yl)

# Shared legend
handles = [Line2D([], [], color=plots.DISTRICT_COLORS[n], marker=plots.MARKERS[n], lw=2, label=n) for n in names]
handles.append(Line2D([], [], color=plots.STATE_GRAY, ls="--", lw=1.5, label="North Carolina (statewide)"))
handles.append(plt.Rectangle((0, 0), 1, 1, color=plots.COVID_FILL, label="COVID-affected years (ED flag)"))
fig.legend(handles=handles, loc="lower left", ncol=5, bbox_to_anchor=(0.045, 0.792), fontsize=10.5)

# Snapshot table
tb = fig.add_subplot(gs[4, :]); tb.axis("off")
tb.set_title(f"Snapshot, {latest}", fontsize=13, fontweight="bold", loc="left", pad=6)
cols = ["District", "Enrollment", "Homeless\nstudents", f"Change since\n{first}", "Per 1,000\nenrolled",
        "NC rank by rate\n(LEAs ≥1,000)", "Child poverty\nrate", "Children in\npoverty",
        "Homeless per 100\npoor children", "MV\nsubgrantee"]
t = tb.table(cellText=table_rows, colLabels=cols, loc="upper center", cellLoc="center",
             colWidths=[0.17, 0.08, 0.08, 0.09, 0.08, 0.10, 0.08, 0.08, 0.12, 0.07])
t.auto_set_font_size(False); t.set_fontsize(10.5); t.scale(1, 2.6)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor(plots.GRID)
    cell.set_facecolor(plots.SURFACE)
    if r == 0:
        cell.set_text_props(fontweight="bold", color=plots.TEXT_2, fontsize=9.5)
        cell.set_height(cell.get_height() * 1.25)
    elif c == 0:
        cell.set_text_props(ha="left", color=plots.TEXT, fontweight="bold")
        cell.PAD = 0.03

notes = (
    "Notes: Homeless counts are cumulative (any time during the year) per EDFacts FS 118. Rates use NCES CCD fall enrollment. "
    "“Per 100 children in poverty” compares two different populations (enrolled homeless students vs. Census estimate of resident children 5–17 in poverty) "
    "and is a benchmark for identification, not a true rate. ED Data Express shows identical SAIPE figures for 2018–19 and 2019–20. "
    "NC statewide total = sum of nighttime-residence categories (available from 2013–14).\n"
    "Sources: U.S. Department of Education, ED Data Express — EDFacts File Specifications 118 & 170; U.S. Census Bureau SAIPE; "
    "NCES Common Core of Data via Urban Institute Education Data Portal. NCES LEA IDs: Kannapolis 3702430, Cabarrus 3700530, Rowan-Salisbury 3704050."
)
fig.text(0.05, 0.022, notes, fontsize=8.5, color=plots.TEXT_2, va="top", wrap=True)

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
out = FIGURES_DIR / "district_report.png"
fig.savefig(out, dpi=150)
print(f"saved {out}")
