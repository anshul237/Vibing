"""
SEMrush API module (optional).
Provides competitor keyword gap analysis and trending keyword data.

SEMrush REST API docs: https://developer.semrush.com/api/v3/

Required env var: SEMRUSH_API_KEY
"""
import os
import time
import requests
from urllib.parse import urlencode

SEMRUSH_BASE = "https://api.semrush.com/"
SEMRUSH_ANALYTICS_BASE = "https://api.semrush.com/analytics/v1/"


class SEMrushClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict, base: str = SEMRUSH_BASE) -> str:
        """Make a GET request and return raw CSV text response."""
        params["key"] = self.api_key
        url = base + endpoint
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_csv(self, raw: str) -> list[dict]:
        """Parse SEMrush pipe-delimited CSV into list of dicts."""
        lines = raw.strip().splitlines()
        if not lines or lines[0].startswith("ERROR"):
            error_msg = lines[0] if lines else "empty response"
            raise ValueError(f"SEMrush API error: {error_msg}")
        headers = lines[0].split(";")
        rows = []
        for line in lines[1:]:
            values = line.split(";")
            rows.append(dict(zip(headers, values)))
        return rows

    def domain_organic_keywords(
        self, domain: str, database: str = "us", limit: int = 100
    ) -> list[dict]:
        """
        Get organic keyword rankings for a domain.
        Returns keyword, position, search_volume, CPC, URL, traffic %.
        """
        params = {
            "type": "domain_organic",
            "domain": domain,
            "database": database,
            "display_limit": limit,
            "export_columns": "Ph,Po,Nq,Cp,Ur,Tr",
            "display_sort": "tr_desc",
        }
        raw = self._get("", params)
        rows = self._parse_csv(raw)
        return [
            {
                "keyword": r.get("Keyword", ""),
                "position": int(r.get("Position", 0)),
                "search_volume": int(r.get("Search Volume", 0)),
                "cpc": float(r.get("CPC", 0) or 0),
                "url": r.get("URL", ""),
                "traffic_pct": float(r.get("Traffic (%)", 0) or 0),
            }
            for r in rows
        ]

    def keyword_gap(
        self,
        target_domain: str,
        competitor_domains: list[str],
        database: str = "us",
        limit: int = 50,
    ) -> list[dict]:
        """
        Find keywords competitors rank for that target domain doesn't.
        Uses the domain_organic endpoint with intersection type 'unique'.
        """
        if not competitor_domains:
            return []

        # SEMrush gap API: target + up to 4 competitors
        competitors = competitor_domains[:4]
        params = {
            "type": "phrase_kdi",  # keyword difficulty
            "database": database,
            "display_limit": limit,
        }

        # Build gap by fetching competitor keywords not in target's set
        target_kws = {
            r["keyword"]
            for r in self.domain_organic_keywords(target_domain, database, limit=500)
        }

        gap_keywords = []
        for comp in competitors:
            comp_kws = self.domain_organic_keywords(comp, database, limit=200)
            for kw in comp_kws:
                if kw["keyword"] not in target_kws:
                    kw["competitor"] = comp
                    gap_keywords.append(kw)
                    target_kws.add(kw["keyword"])  # avoid duplicates across competitors

        # Sort by search volume descending
        gap_keywords.sort(key=lambda x: x["search_volume"], reverse=True)
        return gap_keywords[:limit]

    def trending_keywords(
        self, seed_keyword: str, database: str = "us", limit: int = 30
    ) -> list[dict]:
        """
        Get related and trending keywords for a seed keyword.
        Uses phrase_related endpoint.
        """
        params = {
            "type": "phrase_related",
            "phrase": seed_keyword,
            "database": database,
            "display_limit": limit,
            "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
            "display_sort": "nq_desc",
        }
        raw = self._get("", params)
        rows = self._parse_csv(raw)
        return [
            {
                "keyword": r.get("Keyword", ""),
                "search_volume": int(r.get("Search Volume", 0)),
                "cpc": float(r.get("CPC", 0) or 0),
                "competition": float(r.get("Competition", 0) or 0),
                "results": int(r.get("Number of Results", 0)),
                "trend": r.get("Trends", ""),
            }
            for r in rows
        ]

    def keyword_difficulty(self, keywords: list[str], database: str = "us") -> list[dict]:
        """
        Get keyword difficulty scores for a list of keywords.
        Batches up to 100 keywords per request.
        """
        results = []
        for i in range(0, len(keywords), 100):
            batch = keywords[i : i + 100]
            params = {
                "type": "phrase_these",
                "phrase": ";".join(batch),
                "database": database,
                "export_columns": "Ph,Nq,Cp,Co,Nr,Kd",
            }
            raw = self._get("", params)
            rows = self._parse_csv(raw)
            results.extend(
                {
                    "keyword": r.get("Keyword", ""),
                    "search_volume": int(r.get("Search Volume", 0)),
                    "cpc": float(r.get("CPC", 0) or 0),
                    "competition": float(r.get("Competition", 0) or 0),
                    "keyword_difficulty": int(r.get("Keyword Difficulty Index", 0)),
                }
                for r in rows
            )
            if i + 100 < len(keywords):
                time.sleep(0.5)  # rate limit courtesy
        return results

    def competitor_discovery(
        self, domain: str, database: str = "us", limit: int = 5
    ) -> list[str]:
        """
        Auto-discover top organic competitors for a domain.
        Returns list of competitor domain strings.
        """
        params = {
            "type": "domain_organic_organic",
            "domain": domain,
            "database": database,
            "display_limit": limit,
            "export_columns": "Dn,Co,Np,Or,Ot,Oc,Ad",
        }
        raw = self._get("", params)
        rows = self._parse_csv(raw)
        return [r.get("Domain", "") for r in rows if r.get("Domain")]


def run(
    target_domain: str,
    seed_keywords: list[str],
    competitor_domains: list[str] | None = None,
    database: str = "us",
) -> dict:
    """
    Run SEMrush keyword research stage.

    Args:
        target_domain: Your website domain (e.g. "example.com")
        seed_keywords: 1-3 broad topic keywords to find trending terms
        competitor_domains: List of competitor domains. If None, auto-discovers.
        database: SEMrush regional database (default: "us")

    Returns dict with: your_keywords, competitor_gap, trending, enriched_with_difficulty
    """
    api_key = os.getenv("SEMRUSH_API_KEY", "")
    if not api_key:
        raise EnvironmentError("SEMRUSH_API_KEY environment variable not set")

    client = SEMrushClient(api_key)
    print("\n[Stage 2 / SEMrush] Fetching keyword data...")

    # 1. Your current keyword rankings
    print(f"  Fetching organic keywords for {target_domain}...")
    your_keywords = client.domain_organic_keywords(target_domain, database)
    print(f"  [OK] Found {len(your_keywords)} ranking keywords")

    # 2. Competitor discovery (if not provided)
    if not competitor_domains:
        print("  Auto-discovering competitors...")
        competitor_domains = client.competitor_discovery(target_domain, database)
        print(f"  [OK] Discovered competitors: {', '.join(competitor_domains)}")

    # 3. Keyword gap
    print(f"  Analyzing keyword gap vs {len(competitor_domains)} competitors...")
    gap_keywords = client.keyword_gap(target_domain, competitor_domains, database)
    print(f"  [OK] Found {len(gap_keywords)} gap keywords")

    # 4. Trending keywords per seed
    trending = []
    for seed in seed_keywords[:3]:  # limit to 3 seeds
        print(f"  Fetching trending keywords for '{seed}'...")
        trending.extend(client.trending_keywords(seed, database))
    # deduplicate
    seen = set()
    trending_unique = []
    for t in trending:
        if t["keyword"] not in seen:
            seen.add(t["keyword"])
            trending_unique.append(t)
    print(f"  [OK] Found {len(trending_unique)} trending keywords")

    # 5. Enrich top gap keywords with difficulty scores
    top_gap_kws = [k["keyword"] for k in gap_keywords[:30]]
    if top_gap_kws:
        print("  Fetching keyword difficulty scores...")
        difficulty = client.keyword_difficulty(top_gap_kws, database)
        diff_map = {d["keyword"]: d["keyword_difficulty"] for d in difficulty}
        for kw in gap_keywords:
            kw["keyword_difficulty"] = diff_map.get(kw["keyword"], 0)

    return {
        "your_keywords": your_keywords,
        "competitor_domains": competitor_domains,
        "keyword_gap": gap_keywords,
        "trending": trending_unique,
        "database": database,
    }
