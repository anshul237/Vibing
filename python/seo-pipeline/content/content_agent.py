"""
Stage 4: Sophisticated Content Generation Agent

Writes production-ready SEO content using:
- EEAT (Experience, Expertise, Authoritativeness, Trustworthiness) principles
- Optimal format selection per content type
- Semantic SEO (entities, topic depth, related terms)
- Featured snippet + People Also Ask optimisation
- Google AI Overviews optimisation
- Tone matching from analysed reference articles
"""
import json
from datetime import date
from pathlib import Path

import anthropic

from config import CLAUDE_MODEL, CONTENT_DIR

CLIENT = anthropic.Anthropic()


# ── Format selector prompt ────────────────────────────────────────────────────

FORMAT_SELECTOR_SYSTEM = """You are a senior content strategist. Given a content brief,
select the single best content format and return ONLY valid JSON:

{
  "format": "ultimate_guide | how_to | listicle | comparison | problem_solution | faq_hub | pillar_page",
  "rationale": "one sentence why",
  "target_word_count": 2000,
  "h2_count_target": 6,
  "needs_table": true,
  "needs_comparison": false,
  "intro_hook_type": "stat | question | problem_statement | bold_claim | story"
}

Format guide:
- ultimate_guide: comprehensive resource for broad informational queries (2500-3500w)
- how_to: step-by-step process, numbered structure (1500-2500w)
- listicle: enumerated items with depth per item (1500-2500w)
- comparison: head-to-head product/solution analysis with table (1500-2500w)
- problem_solution: PAS formula, specific pain point (1200-2000w)
- faq_hub: question-clustered, PAA-optimised (1200-2000w)
- pillar_page: broad topic hub with links to cluster articles (3000-4000w)"""


# ── Master content writer prompt ──────────────────────────────────────────────

def _build_article_system(tone_profile: dict, fmt: dict) -> str:
    tone_instructions = ""
    if tone_profile:
        ri = tone_profile.get("replication_instructions", "")
        voice = tone_profile.get("overall_voice", "")
        bb = tone_profile.get("structure_patterns", {}).get("bucket_brigade_examples", [])
        sentence = tone_profile.get("sentence_style", {})
        persona = tone_profile.get("persona_signals", {})

        tone_instructions = f"""
## TONE INSTRUCTIONS (derived from top-performing reference articles)

Overall voice: {voice}
Replication guide: {ri}

Sentence style: {sentence.get("pattern", "mix of short and medium")}
Avg sentence length: {sentence.get("avg_length", "medium")}
Use fragments: {sentence.get("use_of_fragments", True)}

Persona:
- Address reader directly as "you": {persona.get("directly_addresses_reader", True)}
- Share first-hand experience ("I tested / we found"): {persona.get("shares_experience", True)}
- Use rhetorical questions: {persona.get("rhetorical_questions", True)}
- Use humour sparingly: {persona.get("uses_humour", False)}

Bucket brigades to use naturally: {", ".join(bb) if bb else "Here's the thing:, But here's why that matters:, Let me explain:"}
"""
    else:
        tone_instructions = """
## TONE INSTRUCTIONS (default — top-blog composite)

Write like the best performing blogs (HubSpot, Backlinko, Ahrefs):
- Conversational but authoritative — talk WITH the reader, not AT them
- Short paragraphs: 2-3 sentences max
- Mix punchy short sentences with occasional longer explanatory ones
- Address the reader as "you" throughout
- Use bucket brigades to maintain momentum: "Here's the thing:", "But wait:", "Here's why that matters:"
- Share perspective with "I" or "we" where it adds credibility
- Pose rhetorical questions to create engagement
- Active voice always — never passive if you can avoid it
- Avoid corporate jargon — if you must use a technical term, define it immediately
"""

    format_name = fmt.get("format", "ultimate_guide")
    hook_type = fmt.get("intro_hook_type", "problem_statement")
    word_count = fmt.get("target_word_count", 2000)
    h2_count = fmt.get("h2_count_target", 6)

    return f"""You are a world-class SEO content writer who has written for HubSpot, Ahrefs, and Backlinko.
You write content that ranks on page 1, earns backlinks, and readers actually enjoy reading.
You must return ONLY valid JSON — no text outside the JSON object.

{tone_instructions}

## EEAT REQUIREMENTS (non-negotiable)

### Experience (E)
- Write in first or second person where natural ("when I tested...", "if you've ever...")
- Include at least 2 real-world examples or mini case studies
- Reference specific scenarios, tools, or outcomes — not vague generalities
- Use phrases like "in practice", "in our experience", "based on real data"

### Expertise (E)
- Demonstrate mastery: go deeper than surface-level explanation
- Include at least one non-obvious insight competitors won't cover
- Use precise, specific language — avoid wishy-washy hedging
- Include at least 3 specific statistics or data points with source attribution
- Cover nuances, edge cases, and "it depends" situations where relevant

### Authoritativeness (A)
- Cite 4-6 authoritative external sources (inline, e.g. "according to [Source]")
- Reference recognised industry frameworks, studies, or standards
- Write with confidence — definitive statements, not "might" or "could"

### Trustworthiness (T)
- Be transparent about limitations and tradeoffs
- Acknowledge when something is opinion vs established fact
- Include a "Last updated" note placeholder: [LAST_UPDATED]
- Never overstate benefits — balanced, honest assessments build trust

## FORMAT: {format_name.upper().replace("_", " ")}
Target word count: {word_count} words
H2 sections: {h2_count}
Intro hook type: {hook_type}

## STRUCTURAL REQUIREMENTS

### Introduction (150-200 words)
- Hook immediately: {_hook_instruction(hook_type)}
- Establish the problem/opportunity in 2-3 sentences
- State exactly what the reader will get from this article ("By the end of this, you'll know...")
- NO "In this article we will..." filler — make the promise specific and compelling
- Primary keyword must appear naturally in first 100 words

### Body Sections
- Each H2 addresses a distinct user question or subtopic
- Open each section with a 1-2 sentence direct answer (inverted pyramid — Google AI Overviews extract this)
- Then expand with evidence, examples, data
- Vary section depth: some sections are comprehensive, some are punchy and fast
- Short paragraphs throughout — never more than 3 sentences in a row without a break, list, or visual

### Featured Snippet Bait
- Include at least one 40-60 word paragraph that directly defines or answers the primary keyword
- Format it as: [H2 question] → [direct 40-60 word answer] → detailed expansion
- Include at least one properly formatted HTML table or structured comparison if relevant

### People Also Ask Section
- Create a dedicated H2: "Frequently Asked Questions About [topic]"
- Include 4-6 questions derived from common search queries
- Each answer: 2-3 sentences, direct, conversational
- This section should qualify for FAQ schema

### Conclusion (100-150 words)
- Summarise the 3 most important takeaways as bullet points
- End with a clear, specific CTA (not generic "let us know in the comments")
- Forward-look: one sentence on what to do next

## OUTPUT JSON SCHEMA

{{
  "slug": "url-friendly-slug-with-primary-keyword",
  "title": "H1 — compelling, includes primary keyword, under 60 chars",
  "meta_title": "Meta title 50-60 chars with primary keyword near front",
  "meta_description": "Meta description 150-160 chars — includes primary keyword, a benefit, and implicit CTA",
  "content": "Full article in markdown. Use ## for H2, ### for H3. Use **bold** for key terms. Use > for callout boxes. Use --- for section dividers where needed.",
  "word_count": 0,
  "target_keyword": "",
  "secondary_keywords_used": [],
  "eeat_signals": {{
    "experience_examples": ["list of specific experience signals included"],
    "data_points": ["stat 1 with source", "stat 2 with source"],
    "external_citations": ["source 1", "source 2"],
    "unique_insight": "the one non-obvious thing this article says that competitors don't"
  }},
  "featured_snippet_section": "the H2 heading that targets the featured snippet",
  "paa_questions": ["q1", "q2", "q3", "q4"],
  "internal_link_suggestions": [
    {{"anchor": "suggested anchor text", "target_topic": "topic of page to link to"}}
  ],
  "schema": {{
    "article": {{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "",
      "author": {{"@type": "Person", "name": "[AUTHOR_NAME]", "url": "[AUTHOR_URL]"}},
      "publisher": {{"@type": "Organization", "name": "[SITE_NAME]"}},
      "datePublished": "[DATE]",
      "dateModified": "[DATE]"
    }},
    "faq": {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": []
    }}
  }},
  "social": {{
    "twitter": "Tweet — under 280 chars, hook + link",
    "linkedin": "3-4 sentence LinkedIn post — insight-led, not salesy"
  }}
}}"""


def _hook_instruction(hook_type: str) -> str:
    hooks = {
        "stat": "open with a surprising or counter-intuitive statistic that reframes the problem",
        "question": "open with a direct question the reader is already asking themselves",
        "problem_statement": "open by naming the exact painful problem the reader has right now",
        "bold_claim": "open with a bold, specific, defensible claim that challenges conventional wisdom",
        "story": "open with a 2-3 sentence relatable scenario or micro-story",
    }
    return hooks.get(hook_type, hooks["problem_statement"])


# ── Format selector ───────────────────────────────────────────────────────────

def select_format(item: dict) -> dict:
    """Ask Claude to select the best format for this content piece."""
    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=FORMAT_SELECTOR_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Content type: {item.get('content_type', 'blog')}\n"
            f"Primary keyword: {item.get('target_keyword', '')}\n"
            f"Title direction: {item.get('title', '')}\n"
            f"Rationale: {item.get('rationale', '')}\n"
            f"Target word count: {item.get('word_count_target', 1500)}\n"
            "Select the best format."
        )}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"format": item.get("content_type", "ultimate_guide"), "target_word_count": item.get("word_count_target", 1500), "intro_hook_type": "problem_statement"}


# ── Content generators ────────────────────────────────────────────────────────

def generate_article(item: dict, site_url: str, tone_profile: dict) -> dict:
    """Generate a full EEAT-optimised article."""
    fmt = select_format(item)
    system = _build_article_system(tone_profile, fmt)

    prompt = (
        f"Write a complete SEO article for {site_url}.\n\n"
        f"Primary keyword: {item['target_keyword']}\n"
        f"Secondary keywords to weave in naturally: {', '.join(item.get('secondary_keywords', []))}\n"
        f"Title direction: {item['title']}\n"
        f"Content format: {fmt.get('format', 'ultimate_guide')}\n"
        f"Target word count: {fmt.get('target_word_count', item.get('word_count_target', 2000))} words\n"
        f"Angle / rationale: {item['rationale']}\n"
        f"Audience: people searching for '{item['target_keyword']}'\n\n"
        "Apply ALL EEAT requirements, tone instructions, and structural requirements from the system prompt.\n"
        "Produce the complete JSON output now."
    )

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    result = json.loads(text)
    result["format_used"] = fmt.get("format")
    result.setdefault("word_count", len(result.get("content", "").split()))
    return result


def generate_page_update(item: dict, site_url: str, tone_profile: dict) -> dict:
    """Generate update recommendations for an existing page."""
    tone_note = ""
    if tone_profile:
        tone_note = f"\nTone to match: {tone_profile.get('replication_instructions', '')}"

    system = f"""You are an expert SEO editor applying EEAT principles and semantic SEO.
Improve existing page content based on the recommended changes.{tone_note}
Return ONLY valid JSON:
{{
  "slug": "existing-page-slug",
  "recommended_title": "improved H1 if needed",
  "meta_title": "improved meta title 50-60 chars",
  "meta_description": "improved meta description 150-160 chars",
  "changes_summary": "what was changed and why",
  "new_intro": "rewritten introduction applying EEAT hook and tone",
  "sections_to_add": [
    {{"h2": "section heading", "content": "full section content in markdown"}}
  ],
  "faq_to_add": [
    {{"question": "q", "answer": "2-3 sentence direct answer"}}
  ],
  "eeat_additions": ["specific EEAT signals to add"],
  "updated_schema": {{}}
}}"""

    prompt = (
        f"Improve this page for {site_url}.\n\n"
        f"Page URL: {item.get('page', '')}\n"
        f"Target keyword: {item.get('target_keyword', '')}\n"
        f"Current position: {item.get('current_position', 'unknown')}\n"
        f"Recommended changes:\n"
        + "\n".join(f"- {c}" for c in item.get("recommended_changes", []))
    )

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=6000,
        system=system,
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
    system = """You are a programmatic SEO expert. Create a scalable content template.
Return ONLY valid JSON:
{
  "template_name": "identifier",
  "template_content": "markdown template with {{variable}} placeholders — must include EEAT signals, FAQ section, and schema placeholders",
  "variables": {"variable_name": "description of what goes here"},
  "slug_pattern": "/path/{{var1}}-{{var2}}",
  "meta_title_pattern": "pattern with {{variables}}",
  "meta_description_pattern": "pattern with {{variables}}",
  "schema_template": {},
  "example": {"variables": {}, "rendered_slug": "", "rendered_title": ""},
  "generation_notes": "how to populate at scale",
  "eeat_notes": "how EEAT is maintained across generated pages"
}"""

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": (
            f"Create a programmatic SEO template for {site_url}.\n"
            f"Template pattern: {item['template']}\n"
            f"Estimated pages: {item['estimated_pages']}\n"
            f"Rationale: {item['rationale']}\n"
            f"Data available: {item.get('data_requirements', 'not specified')}"
        )}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── File writer ───────────────────────────────────────────────────────────────

def _write_content_file(folder: Path, slug: str, content_obj: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)

    json_path = folder / f"{slug}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(content_obj, f, indent=2, ensure_ascii=False)

    if "content" in content_obj:
        md_path = folder / f"{slug}.md"
        eeat = content_obj.get("eeat_signals", {})
        lines = [
            f"# {content_obj.get('title', slug)}\n",
            f"**Meta title:** {content_obj.get('meta_title', '')}\n",
            f"**Meta description:** {content_obj.get('meta_description', '')}\n",
            f"**Format:** {content_obj.get('format_used', 'article')} | "
            f"**Words:** {content_obj.get('word_count', '?')}\n",
        ]
        if eeat.get("unique_insight"):
            lines.append(f"**Unique insight:** {eeat['unique_insight']}\n")
        lines += ["---\n", content_obj["content"]]
        md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path


# ── Main runner ───────────────────────────────────────────────────────────────

def run(approved_items: dict, site_url: str, tone_profile: dict | None = None) -> dict:
    """
    Generate content for all approved items.

    Args:
        approved_items: Dict of approved recommendations from the approval gate
        site_url: Target website URL
        tone_profile: Optional composite tone profile from tone_analyzer.run()
    """
    if not approved_items:
        return {}

    tone_profile = tone_profile or {}

    date_str = date.today().isoformat()
    domain_slug = site_url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    run_dir = CONTENT_DIR / f"{date_str}_{domain_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    generated = {"articles": [], "page_updates": [], "programmatic_templates": []}
    total = sum(len(v) for v in approved_items.values())
    done = 0

    if tone_profile:
        print(f"  Using tone profile: {tone_profile.get('overall_voice', 'custom')}")
    else:
        print("  Using default tone (top-blog composite)")

    # -- New articles ----------------------------------------------------------
    for item in approved_items.get("new_content", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Writing: '{item['title']}'")
        print(f"  Format selection in progress...")
        try:
            content = generate_article(item, site_url, tone_profile)
            slug = content.get("slug", item["target_keyword"].replace(" ", "-"))
            path = _write_content_file(run_dir / "articles", slug, content)
            generated["articles"].append({
                "slug": slug,
                "title": content.get("title"),
                "format": content.get("format_used"),
                "word_count": content.get("word_count"),
                "file": str(path),
            })
            print(f"  [OK] {content.get('format_used', 'article')} | {content.get('word_count', '?')} words | {slug}.md")
            if content.get("eeat_signals", {}).get("unique_insight"):
                print(f"  Unique insight: {content['eeat_signals']['unique_insight'][:80]}...")
        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback; traceback.print_exc()

    # -- Page updates ----------------------------------------------------------
    for item in approved_items.get("pages_to_update", []) + approved_items.get("quick_wins", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Updating: {item.get('page', '')}")
        try:
            content = generate_page_update(item, site_url, tone_profile)
            slug = item.get("page", "").strip("/").replace("/", "_") or "page-update"
            path = _write_content_file(run_dir / "updates", slug, content)
            generated["page_updates"].append({"slug": slug, "file": str(path)})
            print(f"  [OK] Saved: updates/{slug}.json")
        except Exception as e:
            print(f"  [FAIL] {e}")

    # -- Programmatic templates ------------------------------------------------
    for item in approved_items.get("programmatic_seo", []):
        done += 1
        print(f"\n[Stage 4] ({done}/{total}) Building template: '{item['template']}'")
        try:
            content = generate_programmatic_template(item, site_url)
            slug = content.get("template_name", "template").replace(" ", "-").lower()
            path = _write_content_file(run_dir / "programmatic", slug, content)
            generated["programmatic_templates"].append({"slug": slug, "file": str(path)})
            print(f"  [OK] Saved: programmatic/{slug}.json")
        except Exception as e:
            print(f"  [FAIL] {e}")

    print(f"\n{'='*60}")
    print(f"  CONTENT GENERATION COMPLETE")
    print(f"  Output directory: {run_dir}")
    print(f"  Articles: {len(generated['articles'])}")
    print(f"  Page updates: {len(generated['page_updates'])}")
    print(f"  Programmatic templates: {len(generated['programmatic_templates'])}")
    print(f"{'='*60}\n")

    return generated
