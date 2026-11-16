#!/usr/bin/env python3
"""Consistency and page-budget checks between a LaTeX paper and its .bib.

Catches the three failure modes that survive a successful compile:

  1. a \\cite key that has no bib entry (produces "?" in the PDF),
  2. a bib entry that nothing cites -- BibTeX silently drops it, so the
     bibliography looks shorter than the .bib file and nobody notices,
  3. the body spilling past the page limit because the new citations pushed it
     over (references are usually exempt, the body is not).

Usage:
    python check_paper.py --tex main.tex --bib main.bib --limit 8
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import parse_bib

CITE = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def collect_tex(root: Path, seen: set | None = None) -> str:
    """Inline \\input/\\include recursively so citations in included files count."""
    seen = seen or set()
    if root in seen or not root.exists():
        return ""
    seen.add(root)
    text = strip_comments(root.read_text(errors="replace"))
    out = [text]
    for m in re.finditer(r"\\(?:input|include)\{([^}]*)\}", text):
        inc = root.parent / m.group(1)
        if inc.suffix != ".tex":
            inc = inc.with_suffix(".tex")
        out.append(collect_tex(inc, seen))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", type=Path, default=Path("main.tex"))
    ap.add_argument("--bib", type=Path, default=Path("main.bib"))
    ap.add_argument("--pdf", type=Path, default=Path("main.pdf"))
    ap.add_argument("--limit", type=int, default=8, help="max body pages (excluding references)")
    ap.add_argument("--allow-uncited", default="", help="comma-separated keys that are legitimately "
                                                       "uncited in this document (e.g. supp-only)")
    args = ap.parse_args()

    text = collect_tex(args.tex)
    cited = set()
    for m in CITE.finditer(text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k and k != "*":
                cited.add(k)

    entries = parse_bib(args.bib)
    keys = [e["key"] for e in entries]
    allow = {k.strip() for k in args.allow_uncited.split(",") if k.strip()}

    missing = sorted(cited - set(keys))
    uncited = [k for k in keys if k not in cited and k not in allow]
    dups = sorted({k for k in keys if keys.count(k) > 1})

    ok = True
    print(f"cite keys in text : {len(cited)}")
    print(f"entries in bib    : {len(keys)}")
    if missing:
        ok = False
        print(f"\n[FAIL] {len(missing)} cited but missing from bib:")
        for k in missing:
            print(f"  - {k}")
    if uncited:
        ok = False
        print(f"\n[WARN] {len(uncited)} entries never cited in this document "
              f"(BibTeX will drop them):")
        for k in uncited:
            print(f"  - {k}")
    if dups:
        ok = False
        print(f"\n[FAIL] duplicate bib keys: {dups}")
    if not missing and not uncited and not dups:
        print("\n[OK] every citation resolves and every entry is used")

    if args.pdf.exists():
        try:
            import pymupdf  # noqa: PLC0415
        except ImportError:
            print("\n(pymupdf not installed; skipped page check)")
            return
        doc = pymupdf.open(args.pdf)
        for i, page in enumerate(doc):
            hit = [b for b in page.get_text("blocks") if b[4].strip().startswith("References")]
            if hit:
                page_no = i + 1
                print(f"\nReferences start on page {page_no} "
                      f"(x={hit[0][0]:.0f}, y={hit[0][1]:.0f}); document has {doc.page_count} pages")
                if page_no > args.limit:
                    ok = False
                    print(f"[FAIL] body exceeds the {args.limit}-page limit")
                else:
                    print(f"[OK] body within the {args.limit}-page limit")
                break
        else:
            print("\n(no References heading found; skipped page check)")

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
