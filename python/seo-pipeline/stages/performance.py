"""
Stage 1: Performance Analysis
Fetches current page metrics from Google Search Console and GA4.
Wraps the scripts copied from claude-seo.
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import date, timedelta

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _run_script(script: str, args: list[str]) -> dict:
    """Run a script from the scripts/ dir and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script} failed:\n{result.stderr}")
    return json.loads(result.stdout)


def fetch_gsc_performance(site_url: str, days: int = 28) -> dict:
    """
    Fetch Search Console data for all pages.

    Returns:
        {
          "top_pages": [...],          # pages sorted by clicks
          "quick_wins": [...],         # positions 4-10, high impressions
          "declining_pages": [...],    # pages losing rank vs previous period
          "low_ctr_pages": [...],      # high impressions, low CTR
        }
    """
    end = date.today()
    start = end - timedelta(days=days)
    prev_start = start - timedelta(days=days)

    # Current period
    current = _run_script("gsc_query.py", [
        "--site", site_url,
        "--start", str(start),
        "--end", str(end),
        "--dimensions", "page,query",
        "--json",
    ])

    # Previous period for trend comparison
    previous = _run_script("gsc_query.py", [
        "--site", site_url,
        "--start", str(prev_start),
        "--end", str(start),
        "--dimensions", "page,query",
        "--json",
    ])

    # Quick wins (positions 4-10 with high impressions)
    quick_wins = _run_script("gsc_query.py", [
        "--site", site_url,
        "--start", str(start),
        "--end", str(end),
        "--quick-wins",
        "--json",
    ])

    return {
        "current_period": current,
        "previous_period": previous,
        "quick_wins": quick_wins,
        "date_range": {"start": str(start), "end": str(end)},
    }


def fetch_ga4_performance(property_id: str, days: int = 28) -> dict:
    """
    Fetch GA4 organic traffic data.

    Returns organic sessions, top landing pages, device breakdown.
    """
    end = date.today()
    start = end - timedelta(days=days)

    top_pages = _run_script("ga4_report.py", [
        "--property", property_id,
        "--report", "top-pages",
        "--start", str(start),
        "--end", str(end),
        "--json",
    ])

    organic = _run_script("ga4_report.py", [
        "--property", property_id,
        "--report", "organic",
        "--start", str(start),
        "--end", str(end),
        "--json",
    ])

    return {
        "organic_traffic": organic,
        "top_pages": top_pages,
        "date_range": {"start": str(start), "end": str(end)},
    }


def run(site_url: str, ga4_property_id: str | None = None) -> dict:
    """
    Run Stage 1 and return combined performance data.
    GA4 is optional — skip if property_id not provided.
    """
    print("\n[Stage 1] Fetching performance data from Google Search Console...")
    gsc_data = fetch_gsc_performance(site_url)
    print(f"  [OK] GSC: fetched data for {site_url}")

    ga4_data = None
    if ga4_property_id:
        print("[Stage 1] Fetching GA4 organic traffic data...")
        ga4_data = fetch_ga4_performance(ga4_property_id)
        print(f"  [OK] GA4: fetched data for property {ga4_property_id}")
    else:
        print("  [WARN] GA4 skipped (no property ID provided)")

    return {"gsc": gsc_data, "ga4": ga4_data}
