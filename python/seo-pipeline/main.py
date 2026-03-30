#!/usr/bin/env python3
"""
SEO Pipeline — Main Orchestrator

Usage:
    python main.py                        # Interactive prompts for all options
    python main.py --site https://example.com
    python main.py --site https://example.com --semrush
    python main.py --site https://example.com --no-semrush
    python main.py --skip-to-approval     # Re-run approval on latest report
"""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Validate env before importing stages ──────────────────────────────────────
def _check_env():
    missing = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("  Create a .env file (see .env.example) and add your keys.")
        sys.exit(1)


def _ask(prompt: str, default: str = "") -> str:
    val = input(prompt).strip()
    return val if val else default


def _ask_bool(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    val = input(prompt + suffix + ": ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def _collect_inputs(args) -> dict:
    """Interactively collect required inputs if not provided via CLI."""
    print("\n" + "═" * 60)
    print("  SEO PIPELINE")
    print("═" * 60 + "\n")

    site_url = args.site or _ask("  Website URL (e.g. https://example.com): ")
    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    # SEMrush decision
    if args.semrush:
        use_semrush = True
    elif args.no_semrush:
        use_semrush = False
    else:
        semrush_key = os.getenv("SEMRUSH_API_KEY", "")
        if semrush_key:
            use_semrush = _ask_bool("  Use SEMrush for keyword research?", default=True)
        else:
            print("  [INFO] SEMRUSH_API_KEY not set — falling back to Google Keyword Planner")
            use_semrush = False

    if use_semrush and not os.getenv("SEMRUSH_API_KEY"):
        print("  [ERROR] SEMrush selected but SEMRUSH_API_KEY is not set in .env")
        sys.exit(1)

    # GA4 property (optional)
    ga4_property = args.ga4_property or _ask("  GA4 property ID (optional, press Enter to skip): ")

    # Seed keywords for trend research
    seeds_raw = args.seed_keywords or _ask(
        "  Seed keywords for trend research (comma-separated, e.g. 'crm software,sales tools'): "
    )
    seed_keywords = [k.strip() for k in seeds_raw.split(",") if k.strip()]

    # Competitors (SEMrush only — optional)
    competitor_domains = []
    if use_semrush:
        comps_raw = args.competitors or _ask(
            "  Competitor domains (optional, comma-separated, Enter to auto-discover): "
        )
        competitor_domains = [c.strip() for c in comps_raw.split(",") if c.strip()]

    # Tone matching — optional reference article URLs
    ref_urls_raw = (
        args.reference_urls
        or _ask("  Reference article URLs for tone matching (optional, comma-separated, Enter to skip): ")
    )
    reference_urls = [u.strip() for u in ref_urls_raw.split(",") if u.strip()]

    return {
        "site_url": site_url,
        "use_semrush": use_semrush,
        "ga4_property": ga4_property or None,
        "seed_keywords": seed_keywords,
        "competitor_domains": competitor_domains or None,
        "reference_urls": reference_urls,
    }


def run_pipeline(inputs: dict):
    from stages import performance as perf_stage
    from stages import keyword_research as kw_stage
    from stages import analysis_agent
    from approval import gate
    from content import content_agent

    site_url = inputs["site_url"]
    domain = site_url.replace("https://", "").replace("http://", "").split("/")[0]

    print(f"\n  Target  : {site_url}")
    print(f"  SEMrush : {'Yes' if inputs['use_semrush'] else 'No (Google Keyword Planner)'}")
    print(f"  GA4     : {inputs['ga4_property'] or 'Skipped'}")
    print(f"  Seeds   : {', '.join(inputs['seed_keywords']) or 'None'}\n")

    # ── Stage 1: Performance ───────────────────────────────────────────────────
    performance_data = perf_stage.run(
        site_url=site_url,
        ga4_property_id=inputs.get("ga4_property"),
    )

    # ── Stage 2: Keyword Research ──────────────────────────────────────────────
    keyword_data = kw_stage.run(
        target_domain=domain,
        seed_keywords=inputs["seed_keywords"],
        use_semrush=inputs["use_semrush"],
        competitor_domains=inputs.get("competitor_domains"),
    )

    # ── Stage 3: Claude Analysis ───────────────────────────────────────────────
    recommendations = analysis_agent.run(
        site_url=site_url,
        performance_data=performance_data,
        keyword_data=keyword_data,
    )

    # ── Approval Gate ──────────────────────────────────────────────────────────
    approved = gate.run(recommendations)
    if not approved:
        print("  Pipeline stopped at approval gate.")
        return

    # ── Tone Analysis (optional) ───────────────────────────────────────────────
    tone_profile = {}
    if inputs.get("reference_urls"):
        from stages import tone_analyzer
        print("\n  [INFO] Analysing tone from reference articles...")
        tone_profile = tone_analyzer.run(inputs["reference_urls"])

    # ── Stage 4: Content Generation ────────────────────────────────────────────
    content_agent.run(approved_items=approved, site_url=site_url, tone_profile=tone_profile)


def main():
    parser = argparse.ArgumentParser(description="SEO Pipeline")
    parser.add_argument("--site", help="Website URL")
    parser.add_argument("--semrush", action="store_true", help="Use SEMrush")
    parser.add_argument("--no-semrush", action="store_true", help="Skip SEMrush")
    parser.add_argument("--ga4-property", help="GA4 property ID")
    parser.add_argument("--seed-keywords", help="Comma-separated seed keywords")
    parser.add_argument("--competitors", help="Comma-separated competitor domains")
    parser.add_argument("--reference-urls", help="Comma-separated reference article URLs for tone matching")
    parser.add_argument(
        "--skip-to-approval",
        metavar="REPORT_PATH",
        help="Skip data collection, load a saved report JSON and go straight to approval",
    )
    args = parser.parse_args()

    _check_env()

    # Shortcut: re-run approval on an existing report
    if args.skip_to_approval:
        from approval import gate
        from content import content_agent

        report_path = Path(args.skip_to_approval)
        if not report_path.exists():
            print(f"[ERROR] Report not found: {report_path}")
            sys.exit(1)

        with open(report_path, encoding="utf-8") as f:
            recommendations = json.load(f)

        site_url = args.site or _ask("  Website URL (needed for content generation): ")
        approved = gate.run(recommendations)
        if approved:
            content_agent.run(approved_items=approved, site_url=site_url)
        return

    inputs = _collect_inputs(args)
    run_pipeline(inputs)


if __name__ == "__main__":
    main()
