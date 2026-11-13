"""Pull McKinney-Vento data and write tidy CSVs to data/processed/.

    python -m mckinney_vento.pull            # use cache where present
    python -m mckinney_vento.pull --refresh  # re-download everything
"""

from __future__ import annotations

import argparse

from . import ccd, edx
from .config import PROCESSED_DIR, STATE_NAME


def main() -> None:
    """Pull ED Data Express + CCD enrollment, write CSVs, print a data-quality summary."""
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="ignore cache and re-download")
    ap.add_argument("--state", default=STATE_NAME)
    args = ap.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    slug = args.state.lower().replace(" ", "_")

    print(f"ED Data Express — {args.state} LEA homeless counts (EDFacts FS 118)")
    lea, residence = edx.pull_all(args.state, refresh=args.refresh)
    lea.to_csv(PROCESSED_DIR / f"{slug}_lea_homeless.csv", index=False)
    residence.to_csv(PROCESSED_DIR / f"{slug}_state_residence.csv", index=False)

    print("NCES CCD enrollment (via Urban Institute Education Data API)")
    years = sorted(lea["school_year_start"].unique().tolist())
    if args.state == STATE_NAME:   # CCD pull is keyed by FIPS, configured for NC only
        enr = ccd.pull_enrollment(years, refresh=args.refresh)
        enr.to_csv(PROCESSED_DIR / f"{slug}_lea_enrollment.csv", index=False)

    print(f"\nWrote CSVs to {PROCESSED_DIR}")
    print(lea.groupby("school_year")["homeless_status"].value_counts().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
