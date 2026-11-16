#!/usr/bin/env python3
"""Run reference-audit over the .bib and triage what it reports.

reference-audit answers "does this reference exist and is the metadata right".
It also produces four recurring false positives; this wrapper prints them next
to the findings so a P0 is not deleted before it is understood.

Usage:
    python audit_bib.py main.bib --outdir /tmp/audit
    python audit_bib.py main.bib --skip        # print the command only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path.home() / ".workbuddy/skills/reference-audit/scripts/audit.py"

TRIAGE = """
Triage checklist -- check these before deleting or rewriting an entry
--------------------------------------------------------------------
1. Title contains math or LaTeX ($\\pi_{0.5}$, $\\alpha$): the matcher strips
   math, so a correct entry can score ~0.7 against an unrelated paper.
   Verify by arXiv id instead of by title.
2. Corporate author ({NVIDIA}, {Open X-Embodiment Collaboration}): author
   coverage is 0 by construction, not an error.
3. GitHub repository / dataset release / technical report: never indexed by
   OpenAlex or Crossref. A P0 here is expected; keep if the URL resolves.
4. Pre-1985 proceedings (NIPS 1, etc.): absent from OpenAlex. Confirm on the
   publisher page and add a url field so the next run is checkable.
5. Accented or compound surnames (Sch\\"olkopf, van Elteren): coverage counts a
   miss. Not an error.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bib", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("audit_out"))
    ap.add_argument("--apis", default="openalex,crossref,arxiv")
    ap.add_argument("--skip", action="store_true", help="do not run, just show the command")
    args = ap.parse_args()

    if not SKILL.exists():
        print(f"reference-audit not installed at {SKILL}\n"
              "Install: cp -r bibcheck-ref/skills/reference-audit ~/.workbuddy/skills/",
              file=sys.stderr)
        raise SystemExit(2)

    cmd = [sys.executable, str(SKILL), str(args.bib),
           "--output-dir", str(args.outdir), "--apis", args.apis, "--format", "json"]
    print(" ".join(cmd) + "\n", flush=True)
    if args.skip:
        print(TRIAGE)
        return

    rc = subprocess.call(cmd)
    report = args.outdir / (args.bib.stem + ".audit.json")
    if report.exists():
        data = json.loads(report.read_text())
        print("\nsummary:", data.get("summary"))
        findings = data.get("findings", [])
        hard = [f for f in findings if f.get("level") in ("P0", "P1", "not_found", "mismatch")]
        for f in hard:
            print(f"  [{f.get('level')}] {f.get('key')}: {f.get('title') or f.get('bib', {}).get('title', '')}")
    print(TRIAGE)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
