"""
Stage 4: Content Generation Agent
Writes full production-ready content for each approved item.
"""
import json
from datetime import date
from pathlib import Path

import anthropic

from config import CLAUDE_MODEL, CONTENT_DIR

CLIENT = anthropic.Anthropic()

ARTICLE_SYSTEM = """You are an expert SEO content writer. Write high-quality, fully optimized
content that ranks well and genuinely helps readers.

For each piece you write, produce a JSON object with this exact structure:
{
  "slug": "url-friendly-slug",
  "title": "SEO-optimized H1 title",
  "meta_title": "Meta title (50-60 chars)",
  "meta_description": "Meta description (150-160 chars)",
  "content": "Full article in markdown format",
  "schema": { ... },
  "social": {
    "twitter": "Tweet text (280 chars max)",
    "linkedin": "LinkedIn post (3-4 sentences)"
  },
  "internal_links": ["slug-of-related-page-1", "slug-of-related-page-2"],
  "word_count": 0
}

Content requirements:
- Natural keyword placement in H1, first paragraph, 2-3 H2s, conclusion
- FAQ section at the end targeting People Also Ask
- Internal link placeholders as [INTERNAL_LINK: slug]
- No keyword stuffing — write for humans first
- Include a clear CTA near the end
- Schema: use Article type for blogs, FAQPage if FAQ-heavy
"""

UPDATE_SYSTEM = """You are an expert SEO editor. Improve existing page content based on
the recommended changes provided. Return JSON:
{
  "slug": "existing-page-slug",
  "recommended_title": "Improved H1 (if needed)",
  "meta_title": "Improved meta title",
  "meta_description": "Improved meta description",
  "changes_summary": "What was changed and why",
  "additions": "New sections/content to add (markdown)",
  "updated_schema": { ... }
}
"""

PROGRAMMATIC_SYSTEM = """You are an expert in programmatic SEO. Create a content template
and generation rules. Return JSON:
{
  "template_name": "Template identifier",
  "template_content": "Content template with {{variable}} placeholders",
  "variables": {
    "variable_name": "Description of what this variable should contain"
  },
  "slug_pattern": "/path/{{variable1}}-{{variable2}}",
  "meta_title_pattern": "Title pattern with {{variables}}",
  "meta_description_pattern": "Meta description pattern",
  "schema_template": { ... },
  "example": {
    "variables": {"variable1": "example-value"},
    "rendered_slug": "/path/example-rendered",
    "rendered_title": "Example rendered title"
  },
  "generation_notes": "Instructions for populating this template at scale"
}
"""


def _write_content_file(folder: Path, slug: str, content_obj: dict) -> Path:
    """Save generated content to the outputs/content directory."""
    folder.mkdir(parents=True, exist_ok=True)

    # JSON (machine-readable)
    json_path = folder / f"{slug}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(content_obj, f, indent=2)

    # Markdown (human-readable article)
    if "content" in content_obj:
        md_path = folder / f"{slug}.md"
        lines = [
            f"# {content_obj.get('title', slug)}\n",
            f"**Meta title:** {content_obj.get('meta_title', '')}\n",
            f"**Meta description:** {content_obj.get('meta_description', '')}\n",
            "---\n",
            content_obj["content"],
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path


def generate_article(item: dict, site_url: str) -> dict:
    """Generate a full article for a new_content item."""
    prompt = f"""Write a complete SEO article for {site_url}.

Target keyword: {item['target_keyword']}
Secondary keywords: {', '.join(item.get('secondary_keywords', []))}
Title direction: {item['title']}
Content type: {item['content_type']}
Target word count: {item.get('word_count_target', 1500)} words
Rationale / angle: {item['rationale']}

Produce the full JSON content object now."""

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        system=ARTICLE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    result = json.loads(text)
    result.setdefault("word_count", len(result.get("content", "").split()))
    return result


def generate_page_update(item: dict, site_url: str) -> dict:
    """Generate update recommendations for an existing page."""
    prompt = f"""Improve this existing page for {site_url}.

Page URL: {item['page']}
Target keyword: {item['target_keyword']}
Current position: {item.get('current_position', 'unknown')}
Recommended changes:
{chr(10).join(f'- {c}' for c in item.get('recommended_changes', []))}

Produce the update JSON now."""

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=UPDATE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def generate_programmatic_template(item: dict, site_url: str) -> dict:
    """Generate a programmatic SEO template."""
    prompt = f"""Create a programmatic SEO template for {site_url}.

Template pattern: {item['template']}
Estimated pages: {item['estimated_pages']}
Rationale: {item['rationale']}
Data available: {item.get('data_requirements', 'not specified')}

Produce the template JSON now."""

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=PROGRAMMATIC_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def run(approved_items: dict, site_url: str) -> dict:
    """
    Generate content for all approved items.

    Returns summary of all generated files.
    """
    if not approved_items:
        return {}

    date_str = date.today().isoformat()
    domain_slug = site_url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    run_dir = CONTENT_DIR / f"{date_str}_{domain_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    generated = {"articles": [], "page_updates": [], "programmatic_templates": []}
    total = sum(len(v) for v in approved_items.values())
    done = 0

    # -- New articles -----------------------------------------------------------
    for item in approved_items.get("new_content", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Writing article: '{item['title']}'...")
        try:
            content = generate_article(item, site_url)
            slug = content.get("slug", item["target_keyword"].replace(" ", "-"))
            path = _write_content_file(run_dir / "articles", slug, content)
            generated["articles"].append({"slug": slug, "title": content.get("title"), "file": str(path)})
            print(f"  [OK] Saved: articles/{slug}.md ({content.get('word_count', '?')} words)")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")

    # -- Page updates -----------------------------------------------------------
    for item in approved_items.get("pages_to_update", []) + approved_items.get("quick_wins", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Generating update for: {item.get('page', '')}...")
        try:
            content = generate_page_update(item, site_url)
            slug = item.get("page", "").strip("/").replace("/", "_") or "page-update"
            path = _write_content_file(run_dir / "updates", slug, content)
            generated["page_updates"].append({"slug": slug, "file": str(path)})
            print(f"  [OK] Saved: updates/{slug}.json")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")

    # -- Programmatic templates -------------------------------------------------
    for item in approved_items.get("programmatic_seo", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Building programmatic template: '{item['template']}'...")
        try:
            content = generate_programmatic_template(item, site_url)
            slug = content.get("template_name", "template").replace(" ", "-").lower()
            path = _write_content_file(run_dir / "programmatic", slug, content)
            generated["programmatic_templates"].append({"slug": slug, "file": str(path)})
            print(f"  [OK] Saved: programmatic/{slug}.json")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")

    print(f"\n{'='*60}")
    print(f"  CONTENT GENERATION COMPLETE")
    print(f"  Output directory: {run_dir}")
    print(f"  Articles: {len(generated['articles'])}")
    print(f"  Page updates: {len(generated['page_updates'])}")
    print(f"  Programmatic templates: {len(generated['programmatic_templates'])}")
    print(f"{'='*60}\n")

    return generated
