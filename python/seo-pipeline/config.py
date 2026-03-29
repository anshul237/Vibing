"""
SEO Pipeline Configuration
Loads settings from environment variables or .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── SEMrush ───────────────────────────────────────────────────────────────────
SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY", "")

# ── Google (reuses claude-seo config path) ────────────────────────────────────
GOOGLE_CONFIG_PATH = os.path.expanduser("~/.config/claude-seo/google-api.json")

# ── Output directories ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
CONTENT_DIR = OUTPUTS_DIR / "content"

for d in (REPORTS_DIR, CONTENT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Claude model ──────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-opus-4-6"
