#!/usr/bin/env python3
"""Bidirectional citation snowballing from a seed list.

Backward: Semantic Scholar reference lists (one request per seed).
Forward:  OpenAlex citing works *sorted by citation count*, which is the only
          way to surface important descendants -- Semantic Scholar returns its
          citation window newest-first, so its top entries are 2026 preprints
          with zero citations and the "important downstream work" never appears.

Output: <workdir>/graph.json
    {seed: {"arxiv": ..., "references": [...], "citers": [...]}}

Usage:
    python snowball.py seeds.json --workdir lit_work
    python snowball.py seeds.json --workdir lit_work --only act,dp   # subset
    python snowball.py seeds.json --workdir lit_work --forward-top 60
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import get_json

S2 = "https://api.semanticscholar.org/graph/v1"
OA = "https://api.openalex.org"

REF_FIELDS = "title,year,venue,citationCount,authors,externalIds"


def s2_refs(arxiv: str, cache: Path, limit: int = 100) -> list[dict]:
    d = get_json(f"{S2}/paper/arXiv:{arxiv}/references?fields={REF_FIELDS}&limit={limit}", cache)
    return [x["citedPaper"] for x in d.get("data", []) if x.get("citedPaper")]


def s2_citers(arxiv: str, cache: Path, limit: int = 200) -> list[dict]:
    d = get_json(f"{S2}/paper/arXiv:{arxiv}/citations?fields={REF_FIELDS}&limit={limit}", cache)
    return [x["citingPaper"] for x in d.get("data", []) if x.get("citingPaper")]


def openalex_id(arxiv: str, cache: Path) -> str | None:
    for doi in (f"10.48550/arxiv.{arxiv}", f"10.48550/arXiv.{arxiv}"):
        d = get_json(f"{OA}/works?filter=doi:{doi}&per-page=1&select=id,display_name", cache)
        if d.get("results"):
            return d["results"][0]["id"].rsplit("/", 1)[-1]
    return None


def openalex_citers(wid: str, cache: Path, top: int = 40) -> list[dict]:
    url = (f"{OA}/works?filter=cites:{wid}&sort=cited_by_count:desc&per-page={top}"
           "&select=id,display_name,publication_year,cited_by_count,doi,type")
    d = get_json(url, cache)
    return d.get("results", [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("seeds", type=Path, help="JSON from seeds_from_bib.py or a {key: {arxiv}} map")
    ap.add_argument("--workdir", type=Path, default=Path("lit_work"))
    ap.add_argument("--forward-top", type=int, default=40, help="top-cited citers per seed")
    ap.add_argument("--refs-limit", type=int, default=100)
    ap.add_argument("--only", default="", help="comma-separated seed keys to restrict to")
    ap.add_argument("--no-forward", action="store_true", help="backward only (saves OpenAlex budget)")
    args = ap.parse_args()

    raw = json.loads(args.seeds.read_text())
    seeds = raw.get("seeds", raw)
    if args.only:
        keep = {k.strip() for k in args.only.split(",")}
        seeds = {k: v for k, v in seeds.items() if k in keep}

    cache = args.workdir / "cache"
    out_path = args.workdir / "graph.json"
    graph = json.loads(out_path.read_text()) if out_path.exists() else {}

    for key, meta in seeds.items():
        arxiv = meta["arxiv"] if isinstance(meta, dict) else meta
        if key in graph and graph[key].get("citers"):
            print(f"skip {key} (cached)")
            continue
        node = graph.get(key, {"arxiv": arxiv})
        try:
            if not node.get("references"):
                node["references"] = s2_refs(arxiv, cache, args.refs_limit)
            if not node.get("citers") and not args.no_forward:
                wid = openalex_id(arxiv, cache)
                if wid:
                    node["openalex"] = wid
                    node["citers"] = openalex_citers(wid, cache, args.forward_top)
                else:
                    print(f"  ! no OpenAlex record for {key}; falling back to S2 (recency order)",
                          file=sys.stderr)
                    node["citers"] = s2_citers(arxiv, cache)
                    node["citers_order"] = "recency"
            graph[key] = node
            print(f"ok {key}: {len(node.get('references', []))} refs, "
                  f"{len(node.get('citers', []))} citers", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {key}: {e}", file=sys.stderr)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(graph, indent=1))

    print(f"\nwrote {out_path} ({len(graph)} seeds)")


if __name__ == "__main__":
    main()
