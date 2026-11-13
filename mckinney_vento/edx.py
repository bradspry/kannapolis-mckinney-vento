"""Client for ED Data Express's McKinney-Vento (homeless) dashboard.

ED Data Express has no documented public API, but its dashboard is backed by JSON
endpoints of the form ``/api/v2/{dataset_id}/{viz_id}?sy={year_tid}&s={state_tid}``.
Each school year has its own dataset/viz IDs, which are discovered by loading the
dashboard page for that year and reading the ``paramnum`` attributes.

Endpoints used
--------------
* primary viz  -> every LEA in the state: homeless students enrolled (EDFacts FS 118),
                  McKinney-Vento subgrant status (FS 170), Census SAIPE child poverty.
* participate  -> state-level counts by primary nighttime residence, ~10 years.
                  (District-level residence breakdown is NOT exposed by this API.)

If the site changes its markup, the regexes in ``_page_ids`` are the place to look.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .config import EDX_BASE, EDX_DASHBOARD, RAW_DIR, STATE_NAME
from .http import get_json_cached, get_text


@dataclass(frozen=True)
class YearPage:
    school_year: str      # e.g. "2022-2023"
    sy_tid: str           # Drupal term id for the year
    dataset_id: str       # <article paramnum=...>
    primary_id: str       # <section id="primary" paramnum=...>
    participate_id: str | None


def _select_options(html: str, name: str) -> dict[str, str]:
    """Parse a dashboard <select> into {label: value} (e.g. "2022-2023" -> "2955")."""
    m =re.search(rf'<select[^>]*name="{name}"[^>]*>(.*?)</select>', html, re.S)
    if not m:
        raise RuntimeError(f"Could not find <select name={name!r}> on Data Express page")
    return {label.strip(): value for value, label in
            re.findall(r'<option\s+value="([^"]*)"[^>]*>([^<]*)</option>', m.group(1))}


def discover() -> tuple[dict[str, str], dict[str, str]]:
    """Return ({school_year_label: sy_tid}, {state_name: state_tid}) from the live dashboard."""
    html, _ = get_text(EDX_BASE + EDX_DASHBOARD)
    years = {k: v for k, v in _select_options(html, "school_year").items() if re.fullmatch(r"\d{4}-\d{4}", k)}
    states = _select_options(html, "state")
    return years, states


def _page_ids(sy_tid: str, state_tid: str, school_year: str) -> YearPage:
    """Load the dashboard for one year/state and read the API ids from `paramnum` attributes."""
    html, _ =get_text(EDX_BASE + EDX_DASHBOARD, params={"sy": sy_tid, "s": state_tid})

    def attr(pattern: str) -> str | None:
        m = re.search(pattern, html)
        return m.group(1) if m else None

    dataset = attr(r'<article[^>]*paramnum="(\d+)"')
    primary = attr(r'<section[^>]*id="primary"[^>]*paramnum="(\d+)"')
    participate = attr(r'<section[^>]*id="participate"[^>]*paramnum="(\d+)"')
    if not (dataset and primary):
        raise RuntimeError(f"Could not find dataset/viz ids for {school_year}")
    return YearPage(school_year, sy_tid, dataset, primary, participate)


# --- Parsing helpers -------------------------------------------------------------------

def _num(display: str | None) -> tuple[float | None, str]:
    """Convert a Data Express display value to (number, status)."""
    if display is None:
        return None, "not_available"
    s = str(display).strip().replace(",", "")
    if s.upper() in {"S", "SUPPRESSED"}:
        return None, "suppressed"
    if s.upper() in {"N/A", "NA", "", "."}:
        return None, "not_available"
    try:
        return float(s), "reported"
    except ValueError:
        return None, f"other:{s}"


def _subgrantee(raw: str | None) -> bool | None:
    """Normalize subgrant status; wording changed from "Yes" to "McKinney-Vento Subgrantee" in 2019-20."""
    if raw is None:
        return None
    r = raw.strip().lower()
    if r in {"yes", "mckinney-vento subgrantee"}:
        return True
    if r in {"no"} or "non" in r or "not" in r:
        return False
    return None


def _display(field: list | None) -> str | None:
    # Each field is [raw_value, display_value]; display is the human-facing one
    # (older years store the SAIPE *rate* in raw slot of t2, so raw is unreliable).
    if not field:
        return None
    return field[1] if len(field) > 1 else field[0]


# --- Public pulls ----------------------------------------------------------------------

def pull_lea_year(page: YearPage, state_tid: str, *, refresh: bool = False) -> pd.DataFrame:
    """All LEAs in a state for one school year, one row per LEA.

    Fields in the response: t0 homeless enrolled, t1 subgrant status,
    t2 children 5-17 in poverty, t3 SAIPE poverty rate (%).
    """
    url = f"{EDX_BASE}/api/v2/{page.dataset_id}/{page.primary_id}"
    cache = RAW_DIR / "edx" / f"state-{state_tid}" / f"lea_{page.school_year}.json"
    data = get_json_cached(url, cache, params={"sy": page.sy_tid, "s": state_tid, "type": "json"},
                           refresh=refresh)
    leas = data.get("leas") if isinstance(data, dict) else None
    if not isinstance(leas, dict):
        return pd.DataFrame()

    rows = []
    for leaid, rec in leas.items():
        d = rec.get("data", {})
        homeless, h_status = _num(_display(d.get("t0")))
        poverty, _ = _num(_display(d.get("t2")))
        saipe_rate, _ = _num(_display(d.get("t3")))
        sub_raw = _display(d.get("t1"))
        rows.append({
            "school_year": page.school_year,
            "leaid": leaid,
            "lea_name": rec.get("n"),
            "homeless_enrolled": homeless,
            "homeless_status": h_status,
            "subgrant_status_raw": sub_raw,
            "mv_subgrantee": _subgrantee(sub_raw),
            "children_5_17_poverty": poverty,
            "saipe_poverty_rate_pct": saipe_rate,
        })
    return pd.DataFrame(rows)


def pull_state_residence(page: YearPage, state_tid: str, *, refresh: bool = False) -> pd.DataFrame:
    """State-level homeless students by primary nighttime residence (multi-year series)."""
    if not page.participate_id:
        return pd.DataFrame()
    url = f"{EDX_BASE}/api/v2/{page.dataset_id}/{page.participate_id}"
    cache = RAW_DIR / "edx" / f"state-{state_tid}" / f"residence_{page.school_year}.json"
    data = get_json_cached(url, cache, params={"sy": page.sy_tid, "s": state_tid, "type": "json"},
                           refresh=refresh)
    d = data["api_v2"]["data"]
    years = [_sy_from_label(x) for x in d["xCategories"]]
    rows = []
    for series in d["values"]:
        key, *vals = series
        label = d["names"].get(key, key)
        for yr, v in zip(years, vals):
            n, status = _num(v)
            rows.append({"school_year": yr, "residence_detail": label, "students": n, "status": status})
    df = pd.DataFrame(rows)
    df["residence"] = df["residence_detail"].map(_residence_group)
    return df


def _sy_from_label(label: str) -> str:
    # "SY 13-14" -> "2013-2014"
    m = re.search(r"(\d{2})-(\d{2})", label)
    return f"20{m.group(1)}-20{m.group(2)}" if m else label


def _residence_group(label: str) -> str:
    # ED changed the shelter category definition in 2016-17 ("awaiting foster care"
    # was dropped); group both under "Shelters" for a continuous series.
    lab = label.lower()
    if "unsheltered" in lab:          # check first: "unsheltered" contains "shelter"
        return "Unsheltered"
    if "shelter" in lab:
        return "Shelters / transitional housing"
    if "hotel" in lab or "motel" in lab:
        return "Hotels / motels"
    if "doubled" in lab:
        return "Doubled-up"
    return label


def pull_all(state_name: str = STATE_NAME, *, refresh: bool = False,
             verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pull every available school year. Returns (lea_df, state_residence_df)."""
    years, states = discover()
    state_tid = states.get(state_name)
    if state_tid is None:
        raise KeyError(f"{state_name!r} not in Data Express state list")

    lea_frames, latest_page = [], None
    for school_year, sy_tid in sorted(years.items()):
        page = _page_ids(sy_tid, state_tid, school_year)
        df = pull_lea_year(page, state_tid, refresh=refresh)
        if verbose:
            print(f"  {school_year}: {len(df):>4} LEAs  (dataset {page.dataset_id}/{page.primary_id})")
        lea_frames.append(df)
        latest_page = page  # years are sorted, so this ends on the most recent

    # The newest page's residence chart already carries the full multi-year series.
    residence = pull_state_residence(latest_page, state_tid, refresh=refresh)
    lea = pd.concat(lea_frames, ignore_index=True)
    lea.insert(1, "school_year_start", lea["school_year"].str[:4].astype(int))
    if not residence.empty:
        residence.insert(1, "school_year_start", residence["school_year"].str[:4].astype(int))
    return lea, residence
