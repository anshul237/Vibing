# SEO Pipeline

Automated SEO pipeline powered by Claude. Give it your website URL and it:
1. Pulls performance data from Google Search Console (+ GA4 optionally)
2. Does keyword research via **SEMrush** (optional) or **Google Keyword Planner**
3. Runs a Claude analysis agent to generate a recommendations report
4. Lets you review and approve items interactively
5. Generates production-ready content for approved items

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your .env file
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Configure Google APIs
Google auth is handled by the `google_auth.py` script (from [claude-seo](https://github.com/AgriciDaniel/claude-seo)):
```bash
python scripts/google_auth.py --setup     # see what credentials are needed
python scripts/google_auth.py --auth --creds /path/to/client_secret.json  # OAuth flow
python scripts/google_auth.py --check     # verify what's configured
```

### 4. (Optional) Add SEMrush key
Add `SEMRUSH_API_KEY=...` to your `.env`. If not set, the pipeline will use Google Keyword Planner automatically.

## Usage

### Interactive (recommended for first run)
```bash
python main.py
```
The pipeline will prompt you for:
- Website URL
- Whether to use SEMrush
- GA4 property ID (optional)
- Seed keywords for trend research
- Competitor domains (SEMrush only, optional — auto-discovers if not provided)

### CLI flags
```bash
# Full run with SEMrush
python main.py --site https://example.com --semrush --seed-keywords "crm software,sales tools"

# Full run without SEMrush (Google KP fallback)
python main.py --site https://example.com --no-semrush --seed-keywords "crm software"

# With GA4
python main.py --site https://example.com --ga4-property 123456789

# Re-run approval on an existing report (skip data collection)
python main.py --skip-to-approval outputs/reports/2026-03-29_example.com_report.json --site https://example.com
```

## Output Structure

```
outputs/
├── reports/
│   ├── 2026-03-29_example.com_report.json   # Machine-readable recommendations
│   └── 2026-03-29_example.com_report.md     # Human-readable report
└── content/
    └── 2026-03-29_example.com/
        ├── articles/
        │   ├── target-keyword-slug.md        # Full article (markdown)
        │   └── target-keyword-slug.json      # Article + meta + schema
        ├── updates/
        │   └── existing-page-slug.json       # Page update instructions
        └── programmatic/
            └── template-name.json            # Programmatic SEO template
```

## Keyword Research: SEMrush vs Google Keyword Planner

| Feature | SEMrush | Google Keyword Planner |
|---------|---------|----------------------|
| Competitor keyword gap | ✅ | ❌ |
| Competitor auto-discovery | ✅ | ❌ |
| Trending/related keywords | ✅ | ✅ |
| Keyword difficulty scores | ✅ | ❌ |
| Requires paid account | ✅ | Google Ads account |

## Scripts (from claude-seo)

| Script | Purpose |
|--------|---------|
| `scripts/google_auth.py` | Google OAuth + credential management |
| `scripts/gsc_query.py` | Query Google Search Console |
| `scripts/ga4_report.py` | Query Google Analytics 4 |

## Credits

The scripts in `scripts/` (`google_auth.py`, `gsc_query.py`, `ga4_report.py`) are sourced from
[AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo), used under the MIT License.
