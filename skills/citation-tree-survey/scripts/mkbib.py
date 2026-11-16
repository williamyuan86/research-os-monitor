#!/usr/bin/env python3
"""Emit .bib entries for selected papers, verified against arXiv + Semantic Scholar.

Author order and the exact title come from the arXiv API; the version of record
(venue, year, pages) comes from Semantic Scholar. Nothing is invented: when a
field cannot be established the script leaves it out and prints a TODO.

Usage:
    python mkbib.py act:2304.13705 octo:2405.12213 -o additions.bib
    python mkbib.py --select selected.txt -o additions.bib      # lines: key arxiv
    python mkbib.py act:2304.13705 --venue-map my_venues.json

Emitted entry type:
    @inproceedings  venue known and mapped to a conference
    @article        venue known and mapped to a journal
    @misc           arXiv preprint (keeps eprint + url, no invented venue)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from _common import get_json

ARXIV = "http://export.arxiv.org/api/query"
S2 = "https://api.semanticscholar.org/graph/v1"

# Semantic Scholar venue strings -> (bibtex type, booktitle/journal, short name)
VENUES = {
    "neural information processing systems": ("inproceedings", "Advances in Neural Information Processing Systems (NeurIPS)"),
    "advances in neural information processing systems": ("inproceedings", "Advances in Neural Information Processing Systems (NeurIPS)"),
    "international conference on learning representations": ("inproceedings", "International Conference on Learning Representations (ICLR)"),
    "international conference on machine learning": ("inproceedings", "International Conference on Machine Learning (ICML)"),
    "conference on robot learning": ("inproceedings", "Conference on Robot Learning (CoRL)"),
    "robotics: science and systems conference": ("inproceedings", "Robotics: Science and Systems (RSS)"),
    "robotics: science and systems": ("inproceedings", "Robotics: Science and Systems (RSS)"),
    "ieee international conference on robotics and automation": ("inproceedings", "IEEE International Conference on Robotics and Automation (ICRA)"),
    "ieee/rsj international conference on intelligent robots and systems": ("inproceedings", "IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)"),
    "computer vision and pattern recognition": ("inproceedings", "IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)"),
    "ieee/cvf conference on computer vision and pattern recognition": ("inproceedings", "IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)"),
    "international conference on computer vision": ("inproceedings", "IEEE/CVF International Conference on Computer Vision (ICCV)"),
    "european conference on computer vision": ("inproceedings", "European Conference on Computer Vision (ECCV)"),
    "aaai conference on artificial intelligence": ("inproceedings", "AAAI Conference on Artificial Intelligence (AAAI)"),
    "annual meeting of the association for computational linguistics": ("inproceedings", "Annual Meeting of the Association for Computational Linguistics (ACL)"),
    "conference on empirical methods in natural language processing": ("inproceedings", "Conference on Empirical Methods in Natural Language Processing (EMNLP)"),
    "trans. mach. learn. res.": ("article", "Transactions on Machine Learning Research"),
    "transactions on machine learning research": ("article", "Transactions on Machine Learning Research"),
    "journal of machine learning research": ("article", "Journal of Machine Learning Research"),
    "proceedings of the ieee": ("article", "Proceedings of the IEEE"),
    "nature": ("article", "Nature"),
    "science robotics": ("article", "Science Robotics"),
    "ieee robotics and automation letters": ("article", "IEEE Robotics and Automation Letters"),
}

ACCENTS = {
    "ö": '{\\"o}', "ü": '{\\"u}', "ä": '{\\"a}', "é": "{\\'e}", "è": "{\\`e}",
    "ñ": "{\\~n}", "ï": '{\\"i}', "ç": "{\\c{c}}", "á": "{\\'a}", "í": "{\\'i}",
    "ó": "{\\'o}", "ú": "{\\'u}", "Ö": '{\\"O}', "Ü": '{\\"U}', "å": "{\\aa}",
    "ø": "{\\o}", "Å": "{\\AA}", "ő": '{\\"o}', "š": "{\\v{s}}", "ć": "{\\'c}",
}
MATH = {"π": r"$\pi$", "α": r"$\alpha$", "β": r"$\beta$", "γ": r"$\gamma$",
        "λ": r"$\lambda$", "μ": r"$\mu$", "σ": r"$\sigma$", "θ": r"$\theta$"}


def esc(s: str) -> str:
    for k, v in {**ACCENTS, **MATH}.items():
        s = s.replace(k, v)
    return s.replace("&", r"\&").replace("–", "--")


def protect(title: str) -> str:
    """Brace-protect acronyms so the style file does not lowercase them."""
    out = []
    for tok in title.split():
        core = re.sub(r"^[^\w]+|[^\w]+$", "", tok).replace("$", "")
        alpha = [c for c in core if c.isalpha()]
        upper = [c for c in alpha if c.isupper()]
        if len(core) > 1 and len(upper) >= 2 and len(upper) / max(len(alpha), 1) >= 0.5:
            tok = tok.replace(core, "{" + core + "}")
        out.append(tok)
    return " ".join(out)


def bib_authors(names: list[str], limit: int) -> str:
    names = [n for n in names if n.strip() and n.strip() != ":"][:limit]
    out = []
    for n in names:
        parts = n.split()
        if len(parts) == 1:
            out.append("{" + n + "}")  # corporate author
        else:
            out.append(f"{esc(parts[-1])}, {' '.join(esc(p) for p in parts[:-1])}")
    if len(names) >= limit:
        out.append("others")
    return " and ".join(out)


def arxiv_meta(ids: list[str], cache: Path) -> dict:
    q = f"{ARXIV}?id_list={','.join(ids)}&max_results={len(ids)}"
    txt = None
    path = cache / (re.sub(r"\W+", "_", q)[-150:] + ".xml")
    if path.exists():
        txt = path.read_text()
    else:
        import urllib.request  # noqa: PLC0415
        from _common import UA  # noqa: PLC0415
        req = urllib.request.Request(q, headers={"User-Agent": UA})
        txt = urllib.request.urlopen(req, timeout=90).read().decode()
        cache.mkdir(parents=True, exist_ok=True)
        path.write_text(txt)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = {}
    for e in ET.fromstring(txt).findall("a:entry", ns):
        aid = e.find("a:id", ns).text.rsplit("/abs/", 1)[-1].split("v")[0]
        out[aid] = {
            "title": " ".join(e.find("a:title", ns).text.split()),
            "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
            "year": e.find("a:published", ns).text[:4],
            "month": int(e.find("a:published", ns).text[5:7]),
        }
    return out


def s2_meta(keys: list[str], ids: list[str], cache: Path) -> dict:
    body = json.dumps({"ids": [f"ARXIV:{i}" for i in ids]}).encode()
    try:
        data = get_json(f"{S2}/paper/batch?fields=title,venue,year,journal,publicationVenue",
                        cache, data=body, headers={"Content-Type": "application/json"},
                        max_wait=90.0)
    except Exception as e:  # noqa: BLE001
        print(f"warning: venue lookup failed ({e}); emitting arXiv @misc entries",
              file=sys.stderr)
        return {}
    return dict(zip(keys, data))


def entry(key: str, aid: str, am: dict, s2: dict, venue_map: dict, limit: int) -> str:
    title = esc(am["title"])
    title = protect(title)
    authors = bib_authors(am["authors"], limit)
    venue_raw = (s2.get("venue") or "").strip()
    journal = s2.get("journal") or {}
    pages = (journal.get("pages") or "").replace("–", "--")
    arxiv_year = am["year"]
    year = str(s2.get("year") or arxiv_year)
    notes = []

    mapped = venue_map.get(venue_raw.lower())
    if mapped and mapped[0] == "inproceedings":
        fields = [("title", title), ("author", authors), ("booktitle", mapped[1])]
        if pages and "-" in pages:
            fields.append(("pages", pages))
        fields.append(("year", year))
        kind = "inproceedings"
    elif mapped and mapped[0] == "article":
        fields = [("title", title), ("author", authors), ("journal", mapped[1])]
        if pages and "-" in pages:
            fields.append(("pages", pages))
        fields.append(("year", year))
        kind = "article"
    else:
        fields = [("title", title), ("author", authors), ("year", year),
                  ("eprint", aid), ("archivePrefix", "arXiv"),
                  ("url", f"https://arxiv.org/abs/{aid}")]
        kind = "misc"
        if venue_raw and "arxiv" not in venue_raw.lower():
            notes.append(f"venue reported as '{venue_raw}' but not mapped; entry left as arXiv")

    if kind != "misc":
        # Semantic Scholar usually carries the first-appearance year. ICLR is the
        # systematic offender: submissions close in late September and the
        # meeting happens the following spring, so every ICLR paper posted after
        # August is one year early. Apply that rule and flag it for confirmation.
        if "learning representations" in (mapped[1] if mapped else "").lower() \
                and int(am.get("month") or 1) >= 9:
            bumped = str(int(year) + 1)
            notes.append(f"CHECK year: s2={s2.get('year')} arxiv={arxiv_year}-{am.get('month'):02d} "
                         f"-> wrote {bumped} (ICLR falls in the year after a Sep+ submission)")
            fields = [(k, bumped if k == "year" else v) for k, v in fields]
            year = bumped
        elif str(s2.get("year")) != arxiv_year:
            notes.append(f"CHECK year: s2={s2.get('year')} arxiv={arxiv_year} -> wrote {year}")

    width = max(len(k) for k, _ in fields)
    body = ",\n".join(f"  {k.ljust(width)} = {{{v}}}" for k, v in fields)
    head = "".join(f"% TODO: {n}\n" for n in notes)
    return f"{head}@{kind}{{{key},\n{body}\n}}\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="*", help="key:arxiv_id")
    ap.add_argument("--select", type=Path, help="file with 'key arxiv_id' per line")
    ap.add_argument("-o", "--out", type=Path, default=Path("additions.bib"))
    ap.add_argument("--authors", type=int, default=8, help="authors before 'and others'")
    ap.add_argument("--venue-map", type=Path, help="JSON {s2 venue: [type, name]}")
    ap.add_argument("--workdir", type=Path, default=Path("lit_work"))
    args = ap.parse_args()

    pairs = [p.split(":", 1) for p in args.pairs]
    if args.select:
        for ln in args.select.read_text().splitlines():
            if ln.strip() and not ln.startswith("#"):
                parts = ln.split()
                pairs.append([parts[0], parts[1]])
    if not pairs:
        ap.error("give key:arxiv pairs or --select")

    venue_map = dict(VENUES)
    if args.venue_map:
        venue_map.update({k.lower(): v for k, v in json.loads(args.venue_map.read_text()).items()})

    cache = args.workdir / "cache"
    keys = [k for k, _ in pairs]
    ids = [a for _, a in pairs]
    am = arxiv_meta(ids, cache)
    sm = s2_meta(keys, ids, cache)

    chunks = []
    for key, aid in pairs:
        if aid not in am:
            print(f"skip {key}: arXiv {aid} not returned", file=sys.stderr)
            continue
        chunks.append(entry(key, aid, am[aid], sm.get(key) or {}, venue_map, args.authors))

    args.out.write_text("\n".join(chunks))
    print(f"{len(chunks)} entries -> {args.out}")
    print("Review before merging: acronym braces, corporate authors, venue string.")


if __name__ == "__main__":
    main()
