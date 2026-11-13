"""Project-wide settings: paths, target districts, and source endpoints.

Overridable via a `.env` file in the project root (see `.env.example`).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")   # real environment variables still win over .env


def _path(var: str, default: Path) -> Path:
    p = Path(os.getenv(var, default)).expanduser()
    return p if p.is_absolute() else ROOT / p


DATA_DIR = _path("MV_DATA_DIR", ROOT / "data")
RAW_DIR = DATA_DIR / "raw"          # cached API responses (safe to delete; re-pulled on demand)
PROCESSED_DIR = DATA_DIR / "processed"
FIGURES_DIR = _path("MV_FIGURES_DIR", ROOT / "figures")

# Federal 7-digit NCES LEA IDs (verified against ED Data Express district map, NC = FIPS 37).
# NC DPI's own 3-digit LEA codes are noted for cross-referencing state reports.
DISTRICTS: dict[str, dict[str, str]] = {
    "3702430": {"name": "Kannapolis City Schools", "short": "Kannapolis", "nc_dpi_code": "132"},
    "3700530": {"name": "Cabarrus County Schools", "short": "Cabarrus", "nc_dpi_code": "130"},
    "3704050": {"name": "Rowan-Salisbury Schools", "short": "Rowan-Salisbury", "nc_dpi_code": "800"},
}

# Optional override: MV_DISTRICTS="3702430:Kannapolis,3700530:Cabarrus"
if os.getenv("MV_DISTRICTS"):
    DISTRICTS = {}
    for item in os.environ["MV_DISTRICTS"].split(","):
        leaid, _, short = item.strip().partition(":")
        DISTRICTS[leaid] = {"name": short or leaid, "short": short or leaid, "nc_dpi_code": ""}

STATE_NAME = "North Carolina"
STATE_FIPS = "37"

# School years ED flags as affected by COVID-19 disruptions to identification.
COVID_YEARS = {"2019-2020", "2020-2021"}

# --- Sources --------------------------------------------------------------------------
# ED Data Express (U.S. Dept. of Education). LEA counts come from EDFacts FS 118
# (Homeless Students Enrolled), subgrant status from FS 170, poverty from Census SAIPE.
EDX_BASE = "https://eddataexpress.ed.gov"
EDX_DASHBOARD = "/dashboard/homeless/2022-2023"   # any year works; ?sy=&s= redirects to the right page

# Urban Institute Education Data Portal — a mirror of NCES Common Core of Data (CCD),
# used only for district enrollment (denominator for rates). `year` = fall of school year.
URBAN_CCD_DIRECTORY = "https://educationdata.urban.org/api/v1/school-districts/ccd/directory/{year}/"

# Generic client identifier; do not put personal contact info here.
USER_AGENT = os.getenv("MV_USER_AGENT", "Mozilla/5.0 (compatible; mckinney-vento-analysis/0.1)")
REQUEST_PAUSE_SEC = float(os.getenv("MV_REQUEST_PAUSE_SEC", "0.5"))   # be polite to federal servers
