#!/usr/bin/env python3
"""Rank snowball candidates so the important gaps surface first.

Two independent signals are combined:

  back  number of *your own seeds* that cite the candidate (backward snowballing)
  fwd   number of seeds the candidate cites (forward snowballing)

``back`` answers "the field treats this as a prerequisite"; ``fwd`` answers
"this work sits downstream of several seeds at once". Raw citation count is only
a tie-breaker: a 20k-citation paper outside your argument is still padding.

Usage:
    python rank.py lit_work/graph.json --bib main.bib -o lit_work
    python rank.py lit_work/graph.json --min-back 3 --min-cc 150
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from _common import bib_titles, norm_title


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("graph", type=Path)
    ap.add_argument("--bib", type=Path, help="existing .bib, to mark already-cited work")
    ap.add_argument("-o", "--outdir", type=Path, default=Path("."))
    ap.add_argument("--min-back", type=int, default=3)
    ap.add_argument("--min-fwd", type=int, default=3)
    ap.add_argument("--min-cc", type=int, default=150)
    ap.add_argument("--top", type=int, default=40, help="rows printed per view")
    args = ap.parse_args()

    graph = json.loads(args.graph.read_text())
    have = bib_titles(args.bib)

    back: dict[str, set] = defaultdict(set)
    fwd: dict[str, set] = defaultdict(set)
    meta: dict[str, dict] = {}

    for seed, node in graph.items():
        for p in node.get("references", []):
            k = norm_title(p.get("title", ""))
            if not k:
                continue
            back[k].add(seed)
            meta.setdefault(k, p)
        for p in node.get("citers", []):
            t = p.get("title") or p.get("display_name") or ""
            k = norm_title(t)
            if not k:
                continue
            fwd[k].add(seed)
            if k not in meta:
                meta[k] = {
                    "title": t,
                    "year": p.get("publication_year") or p.get("year"),
                    "venue": p.get("venue", ""),
                    "citationCount": p.get("cited_by_count") or p.get("citationCount"),
                    "externalIds": p.get("externalIds") or {"DOI": p.get("doi")},
                }

    rows = []
    for k in set(back) | set(fwd):
        m = meta[k]
        ext = m.get("externalIds") or {}
        rows.append({
            "title": (m.get("title") or "").replace("\n", " "),
            "year": m.get("year") or m.get("publication_year"),
            "venue": (m.get("venue") or "")[:48],
            "cc": m.get("citationCount") or 0,
            "back": len(back[k]),
            "fwd": len(fwd[k]),
            "back_seeds": ";".join(sorted(back[k])),
            "fwd_seeds": ";".join(sorted(fwd[k])),
            "arxiv": ext.get("ArXiv", ""),
            "doi": ext.get("DOI") or (m.get("doi") or ""),
            "in_bib": k in have,
        })

    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / "candidates.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["title"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (-r["back"], -r["fwd"], -r["cc"])):
            w.writerow(r)

    def line(r: dict) -> str:
        flag = "  [in bib]" if r["in_bib"] else ""
        return (f" b{r['back']:2d} f{r['fwd']:2d} cc{r['cc']:6d} {str(r['year'])[:4]} | "
                f"{r['title'][:92]} | {r['venue'][:34]}{flag}")

    print(f"{len(rows)} unique candidates, {sum(r['in_bib'] for r in rows)} already cited\n")

    print(f"== backward hubs: cited by >= {args.min_back} seeds (not in bib) ==")
    shown = 0
    for r in sorted(rows, key=lambda r: (-r["back"], -r["fwd"], -r["cc"])):
        if r["in_bib"] or r["back"] < args.min_back:
            continue
        print(line(r)); shown += 1
        if shown >= args.top:
            break

    print(f"\n== forward hubs: cite >= {args.min_fwd} seeds, cc >= {args.min_cc} (not in bib) ==")
    shown = 0
    for r in sorted(rows, key=lambda r: (-r["fwd"], -r["cc"])):
        if r["in_bib"] or r["fwd"] < args.min_fwd or r["cc"] < args.min_cc:
            continue
        print(line(r)); shown += 1
        if shown >= args.top:
            break

    print("\n== per-seed top citers (forward view) ==")
    for seed, node in graph.items():
        if node.get("citers_order") == "recency":
            print(f"-- {seed}: skipped (Semantic Scholar recency order, not meaningful)")
            continue
        print(f"-- {seed}")
        n = 0
        for p in node.get("citers", []):
            t = p.get("display_name") or p.get("title") or ""
            if norm_title(t) in have:
                continue
            print(f"   cc{p.get('cited_by_count') or 0:6d} {p.get('publication_year')} | {t[:86]}")
            n += 1
            if n >= 8:
                break

    print(f"\ncandidates -> {csv_path}")


if __name__ == "__main__":
    main()
