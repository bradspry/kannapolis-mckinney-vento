"""District enrollment from NCES Common Core of Data (via the Urban Institute Education Data API).

Used only as a denominator so homeless counts can be expressed as rates.
Urban's ``year`` is the fall of the school year: year=2022 -> 2022-2023.
"""

from __future__ import annotations

import pandas as pd

from .config import RAW_DIR, STATE_FIPS, URBAN_CCD_DIRECTORY
from .http import get_json_cached


def pull_enrollment(start_years: list[int], fips: str = STATE_FIPS, *,
                    refresh: bool = False, verbose: bool = True) -> pd.DataFrame:
    frames = []
    for year in start_years:
        url = URBAN_CCD_DIRECTORY.format(year=year)
        cache = RAW_DIR / "ccd" / f"fips-{fips}" / f"directory_{year}.json"
        try:
            data = get_json_cached(url, cache, params={"fips": int(fips)}, refresh=refresh)
        except Exception as exc:  # a missing year shouldn't sink the whole pull
            print(f"  CCD {year}: unavailable ({exc})")
            continue
        results = list(data.get("results", []))
        nxt = data.get("next")
        page = 2
        while nxt:  # follow pagination (rare for a single state, but handle it)
            more = get_json_cached(nxt, cache.with_name(f"directory_{year}_p{page}.json"), refresh=refresh)
            results += more.get("results", [])
            nxt, page = more.get("next"), page + 1
        df = pd.DataFrame(results)
        if df.empty:
            continue
        df = df[["year", "leaid", "lea_name", "enrollment", "agency_type", "county_name"]].copy()
        df["school_year"] = df["year"].map(lambda y: f"{y}-{y + 1}")
        frames.append(df)
        if verbose:
            print(f"  CCD {year}-{year + 1}: {len(df):>4} LEAs")
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not out.empty:
        # CCD uses negative codes for missing/not-applicable.
        out.loc[out["enrollment"] < 0, "enrollment"] = pd.NA
        out = out.rename(columns={"year": "school_year_start", "lea_name": "ccd_lea_name"})
    return out
