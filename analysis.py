# %% [markdown]
# # McKinney-Vento: Kannapolis, Cabarrus, Rowan-Salisbury
# Starter analysis. Run `python -m mckinney_vento.pull` first.
# Open in VS Code / Jupyter (cells are `# %%`), or run top-to-bottom: `python analysis.py`.

# %%
import matplotlib
if __name__ == "__main__" and not hasattr(__builtins__, "__IPYTHON__"):
    matplotlib.use("Agg")   # headless when run as a script
import pandas as pd

from mckinney_vento import load, plots

pd.set_option("display.width", 140)
panel = load.focus_panel()        # 3 districts × years
state = load.state_totals()       # NC statewide totals
everyone = load.statewide_panel() # all NC LEAs (peer comparisons)

# %% Homeless students enrolled — counts
print(load.wide(panel, "homeless_enrolled").astype("Int64"))

# %% Data quality: suppressed / missing cells for target districts
print(panel.groupby("district", observed=True)["homeless_status"].value_counts().unstack(fill_value=0))

# %% Rates per 1,000 enrolled
print(load.wide(panel, "homeless_per_1000_enrolled").round(1))

# %% Chart 1: counts
plots.district_lines(
    panel, "homeless_enrolled",
    title="Homeless students enrolled",
    subtitle="Students identified under McKinney-Vento at any point in the school year",
    ylabel="Students", save_as="01_counts.png")

# %% Chart 2: rate per 1,000 enrolled vs NC
plots.district_lines(
    panel, "homeless_per_1000_enrolled", state=state,
    title="Homeless students per 1,000 enrolled",
    subtitle="Adjusts for district size; dashed line is the NC statewide rate",
    ylabel="Per 1,000 students", save_as="02_rate_per_1000.png", label_fmt="{:.1f}")

# %% Chart 3: identification relative to child poverty
plots.district_lines(
    panel, "homeless_per_100_poor_children",
    title="Homeless students identified per 100 children in poverty",
    subtitle="Benchmark for identification; Census SAIPE children ages 5–17 in poverty",
    ylabel="Per 100 children in poverty", save_as="03_per_100_poor.png", label_fmt="{:.1f}")

# %% Chart 4: statewide nighttime residence mix
plots.residence_stacked(load.load_residence(), save_as="04_nc_residence.png")

# %% Peer context: where do the three districts rank among NC LEAs in the latest year?
latest = everyone["school_year"].max()
cur = everyone[(everyone["school_year"] == latest) & everyone["enrollment"].ge(1000)].copy()
cur["rank_rate"] = cur["homeless_per_1000_enrolled"].rank(ascending=False)
print(f"{latest}: {cur['homeless_per_1000_enrolled'].notna().sum()} LEAs with ≥1,000 students and a reported count")
print(cur[cur["leaid"].isin(panel["leaid"])][["lea_name", "homeless_enrolled", "enrollment",
                                              "homeless_per_1000_enrolled", "rank_rate"]].round(1))
