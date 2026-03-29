"""
Stage 3: Claude Analysis Agent
Takes raw GSC + keyword data and produces a structured recommendations report.
"""
import json
from datetime import date
from pathlib import Path

import anthropic

from config import CLAUDE_MODEL, REPORTS_DIR

CLIENT = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a senior SEO strategist. Your job is to analyze website performance
data and keyword research, then produce a clear, actionable recommendations report.

You must respond with ONLY valid JSON — no markdown, no explanation outside the JSON.

The JSON must follow this exact schema:
{
  "summary": "2-3 sentence executive summary of the current SEO situation",
  "quick_wins": [
    {
      "page": "URL path",
      "issue": "What the problem is",
      "action": "What to do to fix it",
      "estimated_effort": "low|medium|high",
      "expected_impact": "low|medium|high",
      "priority": 1
    }
  ],
  "new_content": [
    {
      "title": "Suggested article/page title",
      "target_keyword": "primary keyword",
      "secondary_keywords": ["kw1", "kw2"],
      "search_volume": 0,
      "keyword_difficulty": 0,
      "rationale": "Why this content should be created",
      "content_type": "blog|landing_page|programmatic",
      "word_count_target": 1500,
      "priority": 1
    }
  ],
  "programmatic_seo": [
    {
      "template": "Template pattern, e.g. 'Best [Product] for [Use Case]'",
      "estimated_pages": 0,
      "rationale": "Why this programmatic opportunity exists",
      "data_requirements": "What data is needed to generate these pages"
    }
  ],
  "pages_to_update": [
    {
      "page": "URL path",
      "current_position": 0,
      "target_keyword": "keyword",
      "recommended_changes": ["change 1", "change 2"],
      "priority": 1
    }
  ]
}

Sort all arrays by priority (1 = highest). Limit quick_wins to 10, new_content to 8,
programmatic_seo to 3, pages_to_update to 10."""


def build_prompt(
    site_url: str,
    performance_data: dict,
    keyword_data: dict,
) -> str:
    """Build the analysis prompt from raw data."""
    gsc = performance_data.get("gsc", {})
    ga4 = performance_data.get("ga4")

    kw_source = keyword_data.get("source", "semrush")
    gap_count = len(keyword_data.get("keyword_gap", []))
    trending_count = len(keyword_data.get("trending", []))

    prompt = f"""Analyze the SEO data below for {site_url} and produce the recommendations JSON.

=== GOOGLE SEARCH CONSOLE — CURRENT PERIOD ({gsc.get('date_range', {}).get('start')} to {gsc.get('date_range', {}).get('end')}) ===
{json.dumps(gsc.get('current_period', {}), indent=2)[:8000]}

=== QUICK WIN OPPORTUNITIES (positions 4-10, high impressions) ===
{json.dumps(gsc.get('quick_wins', []), indent=2)[:3000]}
"""

    if ga4:
        prompt += f"""
=== GA4 ORGANIC TRAFFIC ===
{json.dumps(ga4.get('organic_traffic', {}), indent=2)[:2000]}

=== GA4 TOP LANDING PAGES ===
{json.dumps(ga4.get('top_pages', {}), indent=2)[:2000]}
"""

    if kw_source == "semrush" or "keyword_gap" in keyword_data:
        prompt += f"""
=== KEYWORD GAP ANALYSIS (keywords competitors rank for, you don't — {gap_count} found) ===
{json.dumps(keyword_data.get('keyword_gap', [])[:30], indent=2)[:4000]}

=== TRENDING KEYWORDS ({trending_count} found) ===
{json.dumps(keyword_data.get('trending', [])[:20], indent=2)[:2000]}

=== COMPETITOR DOMAINS ===
{json.dumps(keyword_data.get('competitor_domains', []), indent=2)}
"""
    else:
        prompt += f"""
=== GOOGLE KEYWORD PLANNER RESULTS ===
{json.dumps(keyword_data.get('results', []), indent=2)[:4000]}
"""

    prompt += "\n\nNow produce the recommendations JSON:"
    return prompt


def run(
    site_url: str,
    performance_data: dict,
    keyword_data: dict,
) -> dict:
    """
    Run Claude analysis agent and return structured recommendations.
    Also saves the report to outputs/reports/.
    """
    print("\n[Stage 3] Running Claude analysis agent...")

    prompt = build_prompt(site_url, performance_data, keyword_data)

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text block (skip thinking blocks)
    text = next((b.text for b in response.content if b.type == "text"), "")
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    recommendations = json.loads(text)

    # Save report
    report_date = date.today().isoformat()
    domain_slug = site_url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    report_path = REPORTS_DIR / f"{report_date}_{domain_slug}_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2)

    # Also save a human-readable markdown version
    md_path = REPORTS_DIR / f"{report_date}_{domain_slug}_report.md"
    _write_markdown_report(md_path, site_url, recommendations)

    print(f"  [OK] Analysis complete")
    print(f"  [OK] Report saved to {report_path.name}")
    print(f"  [OK] Readable report: {md_path.name}")

    return recommendations


def _write_markdown_report(path: Path, site_url: str, rec: dict) -> None:
    """Write a human-readable markdown version of the report."""
    lines = [
        f"# SEO Recommendations Report — {site_url}",
        f"*Generated: {date.today().isoformat()}*\n",
        f"## Summary\n{rec.get('summary', '')}\n",
    ]

    if rec.get("quick_wins"):
        lines.append("## Quick Wins\n")
        for i, qw in enumerate(rec["quick_wins"], 1):
            lines.append(f"### {i}. {qw['page']}")
            lines.append(f"- **Issue:** {qw['issue']}")
            lines.append(f"- **Action:** {qw['action']}")
            lines.append(f"- **Effort:** {qw['estimated_effort']} | **Impact:** {qw['expected_impact']}\n")

    if rec.get("new_content"):
        lines.append("## New Content to Create\n")
        for i, nc in enumerate(rec["new_content"], 1):
            lines.append(f"### {i}. {nc['title']}")
            lines.append(f"- **Primary keyword:** `{nc['target_keyword']}`")
            lines.append(f"- **Search volume:** {nc.get('search_volume', 'N/A')} | **Difficulty:** {nc.get('keyword_difficulty', 'N/A')}")
            lines.append(f"- **Type:** {nc['content_type']} | **Target words:** {nc.get('word_count_target', 1500)}")
            lines.append(f"- **Rationale:** {nc['rationale']}\n")

    if rec.get("programmatic_seo"):
        lines.append("## Programmatic SEO Opportunities\n")
        for ps in rec["programmatic_seo"]:
            lines.append(f"### Template: `{ps['template']}`")
            lines.append(f"- **Estimated pages:** {ps['estimated_pages']}")
            lines.append(f"- **Rationale:** {ps['rationale']}")
            lines.append(f"- **Data needed:** {ps['data_requirements']}\n")

    if rec.get("pages_to_update"):
        lines.append("## Pages to Update\n")
        for pu in rec["pages_to_update"]:
            lines.append(f"### {pu['page']}")
            lines.append(f"- **Keyword:** `{pu['target_keyword']}` (position {pu.get('current_position', '?')})")
            for change in pu.get("recommended_changes", []):
                lines.append(f"  - {change}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
