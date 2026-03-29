"""
Stage 2: Keyword Research — modular router.

Routes to SEMrush or Google Keyword Planner based on user preference.
"""
import sys
import json
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _run_kp_script(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "keyword_planner.py")] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"keyword_planner.py failed:\n{result.stderr}")
    return json.loads(result.stdout)


def run_google_keyword_planner(
    seed_keywords: list[str],
    language_id: str = "1000",
    location_ids: list[str] | None = None,
) -> dict:
    """
    Fallback: use Google Keyword Planner for keyword ideas.
    Requires Google Ads API credentials configured in claude-seo config.
    """
    print("\n[Stage 2 / Google KP] Fetching keyword ideas...")
    location_ids = location_ids or ["2840"]  # US

    results = []
    for seed in seed_keywords[:5]:
        data = _run_kp_script([
            "--seed", seed,
            "--language", language_id,
            "--locations", ",".join(location_ids),
            "--json",
        ])
        results.append({"seed": seed, "ideas": data})
        print(f"  [OK] Keyword Planner: got ideas for '{seed}'")

    return {
        "source": "google_keyword_planner",
        "results": results,
    }


def run(
    target_domain: str,
    seed_keywords: list[str],
    use_semrush: bool,
    competitor_domains: list[str] | None = None,
    semrush_database: str = "us",
) -> dict:
    """
    Route keyword research to SEMrush or Google Keyword Planner.

    Args:
        target_domain: Your domain (e.g. "example.com")
        seed_keywords: Topic seeds for trend discovery
        use_semrush: True → SEMrush, False → Google Keyword Planner
        competitor_domains: Optional explicit competitor list (SEMrush only)
        semrush_database: SEMrush regional DB (SEMrush only)
    """
    if use_semrush:
        from stages import semrush
        return semrush.run(
            target_domain=target_domain,
            seed_keywords=seed_keywords,
            competitor_domains=competitor_domains,
            database=semrush_database,
        )
    else:
        return run_google_keyword_planner(seed_keywords)
