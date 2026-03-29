"""
Human Approval Gate
Shows the recommendations report and lets the user approve items interactively.
"""
import json
from pathlib import Path


def _print_section(title: str, items: list, formatter) -> None:
    if not items:
        return
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")
    for i, item in enumerate(items, 1):
        print(formatter(i, item))


def _fmt_quick_win(i, qw):
    return (
        f"  [{i}] {qw['page']}\n"
        f"      Issue : {qw['issue']}\n"
        f"      Action: {qw['action']}\n"
        f"      Effort: {qw['estimated_effort']} | Impact: {qw['expected_impact']}"
    )


def _fmt_new_content(i, nc):
    kd = nc.get("keyword_difficulty", "?")
    sv = nc.get("search_volume", "?")
    return (
        f"  [{i}] {nc['title']}\n"
        f"      Keyword: {nc['target_keyword']} (vol: {sv}, KD: {kd})\n"
        f"      Type   : {nc['content_type']} | ~{nc.get('word_count_target', 1500)} words\n"
        f"      Why    : {nc['rationale']}"
    )


def _fmt_page_update(i, pu):
    changes = "; ".join(pu.get("recommended_changes", [])[:2])
    return (
        f"  [{i}] {pu['page']} (pos {pu.get('current_position', '?')})\n"
        f"      Keyword: {pu['target_keyword']}\n"
        f"      Changes: {changes}"
    )


def _fmt_programmatic(i, ps):
    return (
        f"  [{i}] Template: {ps['template']}\n"
        f"      Est. pages: {ps['estimated_pages']}\n"
        f"      Why       : {ps['rationale']}"
    )


def _parse_selection(raw: str, max_idx: int) -> list[int]:
    """Parse user input like 'all', '1,3,5', '1-4' into list of 0-based indices."""
    raw = raw.strip().lower()
    if raw in ("all", "a", "yes", "y"):
        return list(range(max_idx))
    if raw in ("none", "n", "no", "skip", ""):
        return []
    indices = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            try:
                lo, hi = part.split("-")
                indices.update(range(int(lo) - 1, int(hi)))
            except ValueError:
                pass
        else:
            try:
                indices.add(int(part) - 1)
            except ValueError:
                pass
    return sorted(i for i in indices if 0 <= i < max_idx)


def run(recommendations: dict) -> dict:
    """
    Show recommendations and collect user approvals.

    Returns dict with same structure as recommendations but only approved items.
    """
    print("\n" + "=" * 60)
    print("  SEO PIPELINE — APPROVAL GATE")
    print("=" * 60)
    print(f"\n Summary:\n  {recommendations.get('summary', '')}\n")
    print("Review each section. Enter item numbers to approve (e.g. '1,3', '1-4', 'all', 'none').\n")

    approved = {}

    # -- Quick Wins -------------------------------------------------------------
    qws = recommendations.get("quick_wins", [])
    if qws:
        _print_section("QUICK WINS (page updates)", qws, _fmt_quick_win)
        raw = input(f"\n  Approve which quick wins? [all/none/numbers]: ").strip()
        indices = _parse_selection(raw, len(qws))
        approved["quick_wins"] = [qws[i] for i in indices]
        print(f"  [OK] Approved {len(approved['quick_wins'])} quick wins")

    # -- New Content ------------------------------------------------------------
    ncs = recommendations.get("new_content", [])
    if ncs:
        _print_section("NEW CONTENT TO CREATE", ncs, _fmt_new_content)
        raw = input(f"\n  Approve which new content pieces? [all/none/numbers]: ").strip()
        indices = _parse_selection(raw, len(ncs))
        approved["new_content"] = [ncs[i] for i in indices]
        print(f"  [OK] Approved {len(approved['new_content'])} new content pieces")

    # -- Pages to Update --------------------------------------------------------
    pus = recommendations.get("pages_to_update", [])
    if pus:
        _print_section("PAGES TO UPDATE", pus, _fmt_page_update)
        raw = input(f"\n  Approve which page updates? [all/none/numbers]: ").strip()
        indices = _parse_selection(raw, len(pus))
        approved["pages_to_update"] = [pus[i] for i in indices]
        print(f"  [OK] Approved {len(approved['pages_to_update'])} page updates")

    # -- Programmatic SEO -------------------------------------------------------
    pss = recommendations.get("programmatic_seo", [])
    if pss:
        _print_section("PROGRAMMATIC SEO OPPORTUNITIES", pss, _fmt_programmatic)
        raw = input(f"\n  Approve which programmatic SEO templates? [all/none/numbers]: ").strip()
        indices = _parse_selection(raw, len(pss))
        approved["programmatic_seo"] = [pss[i] for i in indices]
        print(f"  [OK] Approved {len(approved['programmatic_seo'])} programmatic templates")

    # -- Summary ----------------------------------------------------------------
    total = sum(len(v) for v in approved.values())
    print(f"\n{'='*60}")
    print(f"  APPROVAL COMPLETE — {total} items approved for content generation")
    print(f"{'='*60}\n")

    if total == 0:
        print("  Nothing approved. Exiting pipeline.")
        return {}

    proceed = input("  Proceed to content generation? [y/n]: ").strip().lower()
    if proceed not in ("y", "yes"):
        print("  Exiting. Approved items saved to report.")
        return {}

    return approved
