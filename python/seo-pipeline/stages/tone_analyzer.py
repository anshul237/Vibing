"""
Tone Analyzer
Fetches reference articles (top-performing blogs in your niche) and extracts
a tone profile that the content writer uses to match their style.
"""
import json
import re
import urllib.request
from html.parser import HTMLParser

import anthropic

from config import CLAUDE_MODEL

CLIENT = anthropic.Anthropic()

TONE_SYSTEM = """You are an expert content strategist and copywriter. Analyse the provided
article and extract a precise, actionable tone profile. Return ONLY valid JSON.

{
  "tone_profile": {
    "source_url": "",
    "overall_voice": "e.g. conversational-authoritative / casual-expert / formal-analytical",
    "sentence_style": {
      "avg_length": "short (under 15 words) | medium (15-25) | long (25+)",
      "pattern": "e.g. mix of short punchy + longer explanatory",
      "use_of_fragments": true
    },
    "paragraph_style": {
      "avg_lines": "1-2 | 2-3 | 3-5",
      "rhythm": "e.g. intro sentence + supporting evidence + micro-conclusion"
    },
    "vocabulary": {
      "complexity": "simple | intermediate | technical",
      "jargon_approach": "e.g. uses industry terms and immediately defines them",
      "power_words": ["list", "of", "recurring", "strong", "words"]
    },
    "persona_signals": {
      "use_of_we_i": "heavy | moderate | rare",
      "directly_addresses_reader": true,
      "shares_experience": true,
      "uses_humour": false,
      "rhetorical_questions": true
    },
    "structure_patterns": {
      "intro_hook_style": "e.g. bold stat + problem statement + promise",
      "uses_bucket_brigades": true,
      "bucket_brigade_examples": ["Here's the thing:", "But wait:", "Here's why that matters:"],
      "transition_style": "e.g. plain connectors like 'but', 'so', 'here's the thing'",
      "cta_style": "e.g. soft CTA embedded mid-article + direct CTA at end"
    },
    "data_and_proof": {
      "uses_statistics": true,
      "cites_sources": true,
      "uses_examples": true,
      "uses_case_studies": false
    },
    "formatting": {
      "uses_bold_emphasis": true,
      "list_frequency": "heavy | moderate | rare",
      "uses_tables": false,
      "uses_callout_boxes": false
    },
    "replication_instructions": "2-3 sentence plain-English guide for a writer to replicate this exact tone"
  }
}"""


class _TextExtractor(HTMLParser):
    """Minimal HTML to text extractor."""
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False
        if tag in ("p", "h1", "h2", "h3", "h4", "li"):
            self._text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self):
        return re.sub(r"\n{3,}", "\n\n", "".join(self._text)).strip()


def _fetch_article_text(url: str, max_chars: int = 8000) -> str:
    """Fetch a URL and return plain text (first max_chars characters)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SEOPipeline/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    return text[:max_chars]


def analyze_url(url: str) -> dict:
    """Fetch a URL and return its tone profile dict."""
    print(f"  Fetching: {url}")
    try:
        article_text = _fetch_article_text(url)
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return {}

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=TONE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Analyse this article from {url}:\n\n{article_text}",
        }],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  [WARN] Could not parse tone profile for {url}")
        return {}


def merge_profiles(profiles: list[dict]) -> dict:
    """
    Ask Claude to synthesise multiple tone profiles into one composite profile
    the content writer should emulate.
    """
    if not profiles:
        return {}
    if len(profiles) == 1:
        return profiles[0].get("tone_profile", profiles[0])

    response = CLIENT.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system="""You are an expert content strategist. Given multiple tone profiles from
top-performing articles, synthesise ONE composite tone profile that captures the
shared best practices. Return ONLY valid JSON matching the same tone_profile schema.""",
        messages=[{
            "role": "user",
            "content": (
                "Synthesise these tone profiles into one composite guide:\n\n"
                + json.dumps(profiles, indent=2)
            ),
        }],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
        return data.get("tone_profile", data)
    except json.JSONDecodeError:
        return profiles[0].get("tone_profile", profiles[0])


def run(reference_urls: list[str]) -> dict:
    """
    Analyse a list of reference article URLs and return a composite tone profile.

    Args:
        reference_urls: URLs of top-performing articles to emulate (1-5 recommended)

    Returns:
        Composite tone profile dict, or {} if no URLs provided.
    """
    if not reference_urls:
        return {}

    print(f"\n[Tone Analyzer] Analysing {len(reference_urls)} reference article(s)...")
    profiles = []
    for url in reference_urls[:5]:  # cap at 5
        profile = analyze_url(url)
        if profile:
            profiles.append(profile)
            print(f"  [OK] Profile extracted")

    if not profiles:
        print("  [WARN] No profiles extracted — using default tone")
        return {}

    composite = merge_profiles(profiles)
    print(f"  [OK] Composite tone profile ready")
    return composite
