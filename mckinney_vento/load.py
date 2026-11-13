"""Load processed CSVs and build analysis-ready panels with derived metrics."""

from __future__ import annotations

import pandas as pd

from .config import COVID_YEARS, DISTRICTS, PROCESSED_DIR, STATE_NAME

_SLUG = STATE_NAME.lower().replace(" ", "_")


def load_lea() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{_SLUG}_lea_homeless.csv", dtype={"leaid": str})


def load_enrollment() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{_SLUG}_lea_enrollment.csv", dtype={"leaid": str})


def load_residence() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{_SLUG}_state_residence.csv")


def statewide_panel() -> pd.DataFrame:
    """Every LEA × year, with enrollment and rates. Good for peer comparisons."""
    lea = load_lea()
    enr = load_enrollment()[["leaid", "school_year", "enrollment", "agency_type", "county_name"]]
    df = lea.merge(enr, on=["leaid", "school_year"], how="left")
    df["homeless_per_1000_enrolled"] = 1000 * df["homeless_enrolled"] / df["enrollment"]
    # Identification relative to child poverty: how many MV students per 100 poor children (5-17).
    # Not a true rate (different universes) but a common benchmark for under-identification.
    df["homeless_per_100_poor_children"] = 100 * df["homeless_enrolled"] / df["children_5_17_poverty"]
    df["covid_affected"] = df["school_year"].isin(COVID_YEARS)
    return df


def focus_panel() -> pd.DataFrame:
    """Just the target districts (config.DISTRICTS), tidy long format."""
    df = statewide_panel()
    df = df[df["leaid"].isin(DISTRICTS)].copy()
    df["district"] = df["leaid"].map(lambda x: DISTRICTS[x]["short"])
    order = [v["short"] for v in DISTRICTS.values()]
    df["district"] = pd.Categorical(df["district"], categories=order, ordered=True)
    return df.sort_values(["district", "school_year_start"]).reset_index(drop=True)


def state_totals() -> pd.DataFrame:
    """Statewide homeless total (sum of residence categories) and enrollment, by year."""
    res = load_residence()
    tot = (res.groupby(["school_year", "school_year_start"], as_index=False)["students"]
              .sum(min_count=1).rename(columns={"students": "homeless_enrolled"}))
    enr = load_enrollment().groupby("school_year", as_index=False)["enrollment"].sum(min_count=1)
    tot = tot.merge(enr, on="school_year", how="left")
    tot["homeless_per_1000_enrolled"] = 1000 * tot["homeless_enrolled"] / tot["enrollment"]
    tot["covid_affected"] = tot["school_year"].isin(COVID_YEARS)
    return tot


def wide(df: pd.DataFrame, value: str) -> pd.DataFrame:
    """Years as rows, districts as columns — handy for quick tables."""
    return df.pivot_table(index="school_year", columns="district", values=value, observed=True)
