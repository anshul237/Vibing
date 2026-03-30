# SEO Pipeline

Automated SEO pipeline powered by Claude. Give it your website URL and it:
1. Pulls performance data from Google Search Console (+ GA4 optionally)
2. Does keyword research via **SEMrush** (optional) or **Google Keyword Planner**
3. Runs a Claude analysis agent to generate a recommendations report
4. Lets you review and approve items interactively
5. Generates production-ready content for approved items

## How it works

```
                         +------------------+
         You run         |   main.py (CLI)  |
         main.py  -----> | Collects inputs  |
                         +--------+---------+
                                  |
               +------------------+------------------+
               |                  |                  |
               v                  v                  v
    Stage 1: Performance   Stage 2: Keywords   (optional)
    +-----------------+   +----------------+   Tone Analyzer
    | Google Search   |   | SEMrush API    |   +-------------+
    | Console (GSC)   |   |  - Organic KWs |   | Fetch ref   |
    | + GA4 (optional)|   |  - KW Gap      |   | article URLs|
    | Quick wins,     |   |  - Competitors |   | Claude      |
    | top pages,      |   |  - KW Diff     |   | extracts    |
    | traffic trends  |   | or Google KP   |   | tone profile|
    +-----------------+   +----------------+   +------+------+
               |                  |                   |
               +--------+---------+                   |
                        |                             |
                        v                             |
              Stage 3: Claude Analysis                |
              +----------------------------+          |
              | claude-opus-4-6            |          |
              | Extended thinking          |          |
              | Produces JSON report:      |          |
              |  - Quick wins (pos 4-10)   |          |
              |  - New content to create   |          |
              |  - Pages to update         |          |
              |  - Programmatic SEO        |          |
              +-------------+--------------+          |
                            |                         |
                            v                         |
                   Approval Gate (CLI)                |
                   +-------------------+              |
                   | Review each item  |              |
                   | Select: all/none/ |              |
                   | 1,3,5 / 1-4       |              |
                   +--------+----------+              |
                            |                         |
                            v                         |
              Stage 4: Content Generation <-----------+
              +----------------------------+
              | Format selector: picks     |
              | ultimate_guide / how_to /  |
              | listicle / comparison /    |
              | problem_solution / faq_hub |
              | / pillar_page              |
              |                            |
              | EEAT-style writing:        |
              |  Experience examples       |
              |  Expertise data points     |
              |  Authoritative citations   |
              |  Trust signals             |
              |                            |
              | Featured snippet bait      |
              | PAA FAQ section            |
              | Article + FAQPage schema   |
              | Social snippets            |
              | Internal link suggestions  |
              |                            |
              | Tone: from reference URLs  |
              | (or HubSpot/Backlinko/     |
              |  Ahrefs composite default) |
              +----------------------------+
                            |
                            v
                      outputs/
                      ├── reports/      <- analysis + recommendations
                      └── content/      <- articles, updates, templates
```

### Stage breakdown

| Stage | What it does |
|-------|-------------|
| **Performance** | Queries GSC for clicks, impressions, CTR, positions (current vs previous period). Flags quick-win pages at positions 4–10. Optionally pulls GA4 organic traffic and top landing pages. |
| **Keyword Research** | SEMrush: organic keyword rankings, competitor gap analysis, trending related terms, keyword difficulty scores, auto-competitor discovery. Fallback: Google Keyword Planner for volume and trend data. |
| **Analysis Agent** | Claude (`claude-opus-4-6`) with adaptive thinking synthesises performance + keyword data into a structured recommendations report (JSON + human-readable Markdown). |
| **Approval Gate** | Interactive CLI review of every recommendation. Supports `all`, `none`, range (`1-4`), and list (`1,3,5`) selection. Only approved items proceed to content generation. |
| **Tone Analyzer** | (Optional) Fetches reference article URLs you provide, uses Claude to extract a tone profile (voice, sentence style, vocabulary, persona signals), then merges profiles into a composite. Injected into the content writer. |
| **Content Generation** | Claude selects the best content format per item, then writes production-ready long-form content with EEAT signals, featured snippet bait, PAA section, JSON-LD schema, and social snippets. |

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
- Reference article URLs for tone matching (optional — paste URLs of top-performing blogs you want to emulate)

### CLI flags
```bash
# Full run with SEMrush
python main.py --site https://example.com --semrush --seed-keywords "crm software,sales tools"

# Full run without SEMrush (Google KP fallback)
python main.py --site https://example.com --no-semrush --seed-keywords "crm software"

# With GA4
python main.py --site https://example.com --ga4-property 123456789

# With tone matching from reference articles
python main.py --site https://example.com --reference-urls "https://blog1.com/article,https://blog2.com/article"

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
