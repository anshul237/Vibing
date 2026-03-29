#!/usr/bin/env python3
"""
SEO Pipeline — Test Suite

Tests each component independently so you can identify exactly what's working
and what still needs credentials configured.

Usage:
    py -3 test_pipeline.py              # run all tests
    py -3 test_pipeline.py imports      # only check imports
    py -3 test_pipeline.py claude       # only test Claude API
    py -3 test_pipeline.py analysis     # test Stage 3 with mock data
    py -3 test_pipeline.py content      # test Stage 4 with mock data
    py -3 test_pipeline.py approval     # test approval gate interactively
    py -3 test_pipeline.py gsc          # test Google Search Console connection
    py -3 test_pipeline.py semrush      # test SEMrush API connection
"""
import json
import os
import sys
from pathlib import Path

# ── Colour helpers ─────────────────────────────────────────────────────────────
def ok(msg):  print(f"  [OK]   {msg}")
def fail(msg):print(f"  [FAIL] {msg}")
def info(msg):print(f"  [INFO] {msg}")
def head(msg):print(f"\n{'='*50}\n  {msg}\n{'='*50}")

# ── Mock data ──────────────────────────────────────────────────────────────────
MOCK_PERFORMANCE = {
    "gsc": {
        "current_period": {
            "rows": [
                {"page": "/blog/crm-software", "clicks": 420, "impressions": 8500, "ctr": 0.049, "position": 6.2},
                {"page": "/pricing", "clicks": 310, "impressions": 4200, "ctr": 0.074, "position": 3.1},
                {"page": "/blog/sales-tools", "clicks": 180, "impressions": 9100, "ctr": 0.020, "position": 14.3},
                {"page": "/features", "clicks": 95, "impressions": 2100, "ctr": 0.045, "position": 8.8},
            ]
        },
        "previous_period": {"rows": []},
        "quick_wins": [
            {"page": "/blog/crm-software", "keyword": "best crm software", "position": 6.2, "impressions": 3400},
            {"page": "/features", "keyword": "crm features list", "position": 8.8, "impressions": 1200},
        ],
        "date_range": {"start": "2026-03-01", "end": "2026-03-29"},
    },
    "ga4": None,
}

MOCK_KEYWORD_DATA_SEMRUSH = {
    "source": "semrush",
    "your_keywords": [
        {"keyword": "crm software", "position": 6, "search_volume": 18000},
        {"keyword": "sales crm", "position": 12, "search_volume": 8100},
    ],
    "competitor_domains": ["hubspot.com", "salesforce.com"],
    "keyword_gap": [
        {"keyword": "crm for small business", "search_volume": 5400, "keyword_difficulty": 38, "competitor": "hubspot.com"},
        {"keyword": "free crm software", "search_volume": 12000, "keyword_difficulty": 52, "competitor": "hubspot.com"},
        {"keyword": "crm automation", "search_volume": 3200, "keyword_difficulty": 41, "competitor": "salesforce.com"},
        {"keyword": "best crm for startups", "search_volume": 2900, "keyword_difficulty": 35, "competitor": "hubspot.com"},
    ],
    "trending": [
        {"keyword": "ai crm software", "search_volume": 4400, "competition": 0.3},
        {"keyword": "crm with ai features", "search_volume": 1900, "competition": 0.25},
    ],
    "database": "us",
}

MOCK_KEYWORD_DATA_KP = {
    "source": "google_keyword_planner",
    "results": [
        {"seed": "crm software", "ideas": [
            {"keyword": "crm for small business", "monthly_searches": "1K-10K"},
            {"keyword": "free crm tools", "monthly_searches": "10K-100K"},
        ]},
    ],
}

# ── Test 1: Imports ─────────────────────────────────────────────────────────────
def test_imports():
    head("TEST 1: Imports & Environment")
    errors = 0

    for pkg, import_name in [
        ("anthropic", "anthropic"),
        ("python-dotenv", "dotenv"),
        ("requests", "requests"),
        ("google-api-python-client", "googleapiclient"),
        ("google-auth", "google.auth"),
        ("google-analytics-data", "google.analytics.data"),
        ("beautifulsoup4", "bs4"),
    ]:
        try:
            __import__(import_name)
            ok(f"{pkg}")
        except ImportError:
            fail(f"{pkg} — run: pip install -r requirements.txt")
            errors += 1

    # Check pipeline modules
    sys.path.insert(0, str(Path(__file__).parent))
    for module in ["config", "stages.performance", "stages.keyword_research",
                   "stages.analysis_agent", "stages.semrush",
                   "approval.gate", "content.content_agent"]:
        try:
            __import__(module)
            ok(f"pipeline/{module}")
        except ImportError as e:
            fail(f"pipeline/{module} — {e}")
            errors += 1

    return errors == 0


# ── Test 2: Environment Variables ──────────────────────────────────────────────
def test_env():
    head("TEST 2: Environment Variables")
    from dotenv import load_dotenv
    load_dotenv()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    semrush_key = os.getenv("SEMRUSH_API_KEY", "")

    if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
        ok(f"ANTHROPIC_API_KEY is set ({anthropic_key[:8]}...)")
    else:
        fail("ANTHROPIC_API_KEY not set — add it to your .env file")
        info("Create .env from .env.example and add your key")

    if semrush_key and semrush_key != "your_semrush_api_key_here":
        ok(f"SEMRUSH_API_KEY is set ({semrush_key[:8]}...)")
    else:
        info("SEMRUSH_API_KEY not set — SEMrush features will be unavailable (optional)")

    return bool(anthropic_key and anthropic_key != "your_anthropic_api_key_here")


# ── Test 3: Claude API — quick ping ────────────────────────────────────────────
def test_claude():
    head("TEST 3: Claude API Connection")
    from dotenv import load_dotenv
    load_dotenv()

    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        fail("ANTHROPIC_API_KEY not set — skipping")
        return False

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=50,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
        )
        reply = next(b.text for b in response.content if b.type == "text")
        ok(f"Claude API responded: '{reply.strip()}'")
        ok(f"Tokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
        return True
    except anthropic.AuthenticationError:
        fail("Invalid API key — check ANTHROPIC_API_KEY in .env")
    except Exception as e:
        fail(f"Unexpected error: {e}")
    return False


# ── Test 4: Analysis Agent (mock data, no Google/SEMrush needed) ───────────────
def test_analysis():
    head("TEST 4: Stage 3 — Analysis Agent (mock data)")
    from dotenv import load_dotenv
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        fail("ANTHROPIC_API_KEY not set — skipping")
        return False

    sys.path.insert(0, str(Path(__file__).parent))
    from stages import analysis_agent

    print("  Running Claude analysis on mock GSC + SEMrush data...")
    print("  (This will take ~15-30 seconds and use ~3000 tokens)\n")

    try:
        rec = analysis_agent.run(
            site_url="https://example-crm.com",
            performance_data=MOCK_PERFORMANCE,
            keyword_data=MOCK_KEYWORD_DATA_SEMRUSH,
        )
        ok(f"Analysis completed")
        ok(f"Summary: {rec.get('summary', '')[:80]}...")
        ok(f"Quick wins: {len(rec.get('quick_wins', []))}")
        ok(f"New content items: {len(rec.get('new_content', []))}")
        ok(f"Programmatic SEO: {len(rec.get('programmatic_seo', []))}")
        ok(f"Pages to update: {len(rec.get('pages_to_update', []))}")

        # Show report file location
        from config import REPORTS_DIR
        reports = sorted(REPORTS_DIR.glob("*example-crm*"))
        if reports:
            ok(f"Report saved: {reports[-1].name}")

        return rec
    except Exception as e:
        fail(f"Analysis failed: {e}")
        import traceback; traceback.print_exc()
        return False


# ── Test 5: Approval Gate (interactive) ────────────────────────────────────────
def test_approval(recommendations=None):
    head("TEST 5: Approval Gate (interactive)")

    if recommendations is None:
        # Use minimal mock data
        recommendations = {
            "summary": "Mock test: 2 quick wins and 1 new article identified.",
            "quick_wins": [
                {"page": "/blog/crm-software", "issue": "Title tag missing primary keyword",
                 "action": "Update H1 to include 'best CRM software'",
                 "estimated_effort": "low", "expected_impact": "medium", "priority": 1},
            ],
            "new_content": [
                {"title": "Best CRM for Small Business in 2026", "target_keyword": "crm for small business",
                 "secondary_keywords": ["small business crm", "crm tools"], "search_volume": 5400,
                 "keyword_difficulty": 38, "rationale": "High volume gap keyword competitors rank for",
                 "content_type": "blog", "word_count_target": 2000, "priority": 1},
            ],
            "pages_to_update": [],
            "programmatic_seo": [],
        }

    sys.path.insert(0, str(Path(__file__).parent))
    from approval import gate

    approved = gate.run(recommendations)
    if approved:
        ok(f"Approval gate works — {sum(len(v) for v in approved.values())} items approved")
    else:
        info("Nothing approved or gate exited — that's fine for a test")
    return approved


# ── Test 6: Content Agent (mock approved items) ────────────────────────────────
def test_content(approved_items=None):
    head("TEST 6: Stage 4 — Content Agent (mock approved items)")
    from dotenv import load_dotenv
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        fail("ANTHROPIC_API_KEY not set — skipping")
        return False

    if not approved_items:
        approved_items = {
            "new_content": [
                {"title": "Best CRM for Small Business in 2026",
                 "target_keyword": "crm for small business",
                 "secondary_keywords": ["small business crm", "affordable crm"],
                 "search_volume": 5400, "keyword_difficulty": 38,
                 "rationale": "Gap keyword vs HubSpot with high volume",
                 "content_type": "blog", "word_count_target": 1500, "priority": 1},
            ],
            "quick_wins": [],
            "pages_to_update": [],
            "programmatic_seo": [],
        }

    sys.path.insert(0, str(Path(__file__).parent))
    from content import content_agent

    print("  Generating 1 article via Claude...")
    print("  (This will take ~30-60 seconds and use ~2000-4000 tokens)\n")

    try:
        result = content_agent.run(
            approved_items=approved_items,
            site_url="https://example-crm.com",
        )
        if result.get("articles"):
            ok(f"Article generated: {result['articles'][0]['title']}")
            ok(f"File: {result['articles'][0]['file']}")
        return True
    except Exception as e:
        fail(f"Content generation failed: {e}")
        import traceback; traceback.print_exc()
        return False


# ── Test 7: Google Search Console ──────────────────────────────────────────────
def test_gsc():
    head("TEST 7: Google Search Console Connection")
    import subprocess

    scripts_dir = Path(__file__).parent / "scripts"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "google_auth.py"), "--check", "gsc"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        ok("GSC credentials are configured")
        print(result.stdout[:300])
    else:
        fail("GSC credentials not configured")
        info("Run: py -3 scripts/google_auth.py --setup")
        info("Then: py -3 scripts/google_auth.py --auth --creds /path/to/client_secret.json")
    return result.returncode == 0


# ── Test 8: SEMrush API ────────────────────────────────────────────────────────
def test_semrush():
    head("TEST 8: SEMrush API Connection")
    from dotenv import load_dotenv
    load_dotenv()

    key = os.getenv("SEMRUSH_API_KEY", "")
    if not key:
        info("SEMRUSH_API_KEY not set — skipping")
        info("Add SEMRUSH_API_KEY to .env to enable SEMrush")
        return None  # not a failure, it's optional

    sys.path.insert(0, str(Path(__file__).parent))
    from stages.semrush import SEMrushClient

    try:
        client = SEMrushClient(key)
        # Cheap test: fetch 5 keywords for a known domain
        print("  Fetching 5 organic keywords for example.com...")
        kws = client.domain_organic_keywords("example.com", limit=5)
        ok(f"SEMrush API works — got {len(kws)} keywords")
        for kw in kws[:3]:
            print(f"    {kw['keyword']} (pos {kw['position']}, vol {kw['search_volume']})")
        return True
    except ValueError as e:
        fail(f"SEMrush API error: {e}")
        info("Check your SEMRUSH_API_KEY is valid and has API units remaining")
    except Exception as e:
        fail(f"Unexpected error: {e}")
    return False


# ── Runner ─────────────────────────────────────────────────────────────────────
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    dispatch = {
        "imports":  test_imports,
        "env":      test_env,
        "claude":   test_claude,
        "analysis": test_analysis,
        "approval": test_approval,
        "content":  test_content,
        "gsc":      test_gsc,
        "semrush":  test_semrush,
    }

    if cmd in dispatch:
        dispatch[cmd]()
        return

    # Run all — but chain analysis → approval → content so results flow through
    print("\n\033[1mSEO Pipeline — Full Test Suite\033[0m")

    results = {}
    results["imports"] = test_imports()
    results["env"] = test_env()
    results["claude"] = test_claude()

    recommendations = None
    approved = None

    if results.get("claude"):
        recommendations = test_analysis()
        results["analysis"] = bool(recommendations)

    print("\n  [Approval gate test uses minimal mock data — enter numbers or 'all']")
    approved = test_approval(recommendations if recommendations else None)
    results["approval"] = True  # always passes if it ran

    if results.get("claude") and approved:
        results["content"] = test_content(approved)
    else:
        info("Skipping content test (no approvals or Claude not available)")

    results["gsc"] = test_gsc()
    results["semrush"] = test_semrush()

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'═'*50}")
    print("  TEST SUMMARY")
    print(f"{'═'*50}")
    for name, passed in results.items():
        if passed is None:
            print(f"  [-] {name}: skipped (optional)")
        elif passed:
            print(f"  [OK] {name}: passed")
        else:
            print(f"  [FAIL] {name}: failed")
    print()


if __name__ == "__main__":
    main()
