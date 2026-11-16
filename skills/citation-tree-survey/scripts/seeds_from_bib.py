#!/usr/bin/env python3
"""Turn an existing .bib into a seed list for citation-tree snowballing.

Entries carrying an arXiv id in eprint/url/journal/note are used directly. The
rest are resolved by title against Semantic Scholar, and a candidate is only
accepted when the returned title matches closely -- a wrong arXiv id produces a
real-looking citation for the wrong paper, which is worse than no seed at all.

Usage:
    python seeds_from_bib.py main.bib -o seeds.json
    python seeds_from_bib.py main.bib -o seeds.json --no-resolve   # offline / fast
    python seeds_from_bib.py main.bib -o seeds.json --min-sim 0.92
"""
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from _common import (arxiv_id_from_bib_entry, arxiv_search, get_json,
                     norm_title, parse_bib, quote)

S2 = "https://api.semanticscholar.org/graph/v1"


def resolve(title: str, cache: Path) -> tuple[str, float] | None:
    """Title -> arXiv id. arXiv first (authoritative), Semantic Scholar second."""
    best: tuple[str, float] | None = None
    try:
        for aid, t in arxiv_search(title, cache):
            sim = SequenceMatcher(None, norm_title(title), norm_title(t)).ratio()
            if best is None or sim > best[1]:
                best = (aid, sim)
    except Exception:  # noqa: BLE001
        pass
    if best and best[1] >= 0.95:
        return best

    url = (f"{S2}/paper/search?query={quote(title)}&limit=3"
           "&fields=title,externalIds,year,venue")
    try:
        d = get_json(url, cache)
    except Exception:  # noqa: BLE001
        return best
    for p in d.get("data", []):
        aid = (p.get("externalIds") or {}).get("ArXiv")
        if not aid:
            continue
        sim = SequenceMatcher(None, norm_title(title), norm_title(p.get("title", ""))).ratio()
        if best is None or sim > best[1]:
            best = (aid, sim)
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bib", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("seeds.json"))
    ap.add_argument("--note", default="", help="free-text label stored in the file")
    ap.add_argument("--no-resolve", action="store_true", help="skip title lookup")
    ap.add_argument("--min-sim", type=float, default=0.90, help="title similarity floor")
    ap.add_argument("--workdir", type=Path, default=Path("lit_work"))
    args = ap.parse_args()

    seeds, unresolved = {}, []
    for e in parse_bib(args.bib):
        aid = arxiv_id_from_bib_entry(e["fields"])
        title = e["fields"].get("title", e["key"]).replace("{", "").replace("}", "")
        if aid:
            seeds[e["key"]] = {"arxiv": aid, "title": title, "source": "bib-field"}
            continue
        if args.no_resolve:
            unresolved.append((e["key"], title))
            continue
        hit = resolve(title, args.workdir / "cache")
        if hit and hit[1] >= args.min_sim:
            seeds[e["key"]] = {"arxiv": hit[0], "title": title,
                               "source": f"title-match {hit[1]:.2f}"}
            print(f"resolved {e['key']} -> {hit[0]} ({hit[1]:.2f})", file=sys.stderr)
        else:
            unresolved.append((e["key"], title))

    args.out.write_text(json.dumps({"_note": args.note, "seeds": seeds}, indent=1))
    print(f"\n{len(seeds)} seeds -> {args.out}")
    if unresolved:
        print(f"{len(unresolved)} unresolved (no arXiv id, no confident match):")
        for k, t in unresolved:
            print(f"  {k:28s} {t[:78]}")


if __name__ == "__main__":
    main()
