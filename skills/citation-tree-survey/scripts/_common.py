"""Shared HTTP + caching helpers for the citation-tree survey scripts.

Every request is cached on disk, so re-running after a crash or after adding a
single seed costs nothing for the seeds already fetched.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "citation-tree-survey/1.0 (https://github.com/williamyuan86)"


def _key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:20]


def get_json(url: str, cache_dir: Path, *, retries: int = 6, pause: float = 1.2,
             headers: dict | None = None, data: bytes | None = None,
             max_wait: float = 25.0) -> dict:
    """GET (or POST when ``data`` is given) and cache the JSON body on disk.

    ``max_wait`` caps the total time spent backing off on 429s. Without a cap a
    rate-limited endpoint can stall for minutes per request and the caller looks
    hung; failing fast with an exception lets the loop move to the next seed.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1((url + str(data)).encode()).hexdigest()[:20]
    path = cache_dir / f"{tag}.json"
    if path.exists():
        return json.loads(path.read_text())

    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    waited, delay = 0.0, 2.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs, data=data)
            with urllib.request.urlopen(req, timeout=45) as r:
                body = json.loads(r.read().decode())
            path.write_text(json.dumps(body))
            time.sleep(pause)
            return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502):
                retry_after = e.headers.get("Retry-After") if e.headers else None
                sleep_for = float(retry_after) if (retry_after or "").isdigit() else delay
                if waited + sleep_for > max_wait:
                    raise RuntimeError(f"rate-limited for {waited:.0f}s, giving up: {url}") from e
                time.sleep(sleep_for)
                waited += sleep_for
                delay *= 2
                continue
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
            waited += delay
            delay *= 2
    raise RuntimeError(f"giving up on {url}")


def norm_title(t: str) -> str:
    """Title key used for de-duplication across providers."""
    t = re.sub(r"\{|\}|\$|\^|_", " ", t or "")
    t = t.lower()
    t = re.sub(r"\\[a-z]+", " ", t)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def arxiv_search(title: str, cache_dir: Path, max_results: int = 3,
                 pause: float = 3.0) -> list[tuple[str, str]]:
    """Title search against the arXiv API -> [(arxiv_id, title)].

    Preferred over Semantic Scholar for title->id resolution: it is the
    authoritative source, it is far less rate-limited, and it returns the exact
    title that the id maps to, which is what the caller checks against.
    """
    q = urllib.parse.quote(f'ti:"{title}"')
    url = f"http://export.arxiv.org/api/query?search_query={q}&max_results={max_results}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".xml")
    if path.exists():
        txt = path.read_text()
    else:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        txt = urllib.request.urlopen(req, timeout=45).read().decode()
        path.write_text(txt)
        time.sleep(pause)
    import xml.etree.ElementTree as ET  # noqa: PLC0415
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(txt).findall("a:entry", ns):
        aid = e.find("a:id", ns).text.rsplit("/abs/", 1)[-1].split("v")[0]
        t = " ".join(e.find("a:title", ns).text.split())
        out.append((aid, t))
    return out


def bib_titles(bib_path: Path) -> set[str]:
    """Normalised titles of every entry already in a .bib file."""
    if not bib_path or not bib_path.exists():
        return set()
    text = bib_path.read_text(errors="replace")
    out = set()
    for m in re.finditer(r"\btitle\s*=\s*\{(.+?)\}\s*,\s*\n", text, re.S):
        out.add(norm_title(m.group(1)))
    return out


def arxiv_id_from_bib_entry(fields: dict) -> str | None:
    """Pull an arXiv id out of eprint/journal/url/note fields."""
    bare = re.fullmatch(r"\s*(\d{4}\.\d{4,5})(v\d+)?\s*", fields.get("eprint", ""))
    if bare:
        return bare.group(1)
    for f in ("eprint", "journal", "url", "note", "howpublished"):
        v = fields.get(f, "")
        if not v:
            continue
        m = re.search(r"arxiv[:./\s]*(\d{4}\.\d{4,5})", v, re.I)
        if m:
            return m.group(1)
        m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", v, re.I)
        if m:
            return m.group(1)
    return None


def parse_bib(path: Path) -> list[dict]:
    """Minimal .bib parser: returns [{type, key, fields{}}] preserving order."""
    text = path.read_text(errors="replace")
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            k = fm.group(1).lower()
            j = fm.end()
            if j >= len(body):
                continue
            if body[j] == "{":
                d, k2 = 1, j + 1
                while k2 < len(body) and d:
                    if body[k2] == "{":
                        d += 1
                    elif body[k2] == "}":
                        d -= 1
                    k2 += 1
                fields[k] = body[j + 1:k2 - 1].strip()
            elif body[j] == '"':
                k2 = body.find('"', j + 1)
                fields[k] = body[j + 1:k2].strip()
            else:
                k2 = body.find(",", j)
                fields[k] = body[j:k2].strip()
        entries.append({"type": m.group(1).lower(), "key": m.group(2), "fields": fields})
    return entries


def pdf_page_of_body_break(pdf: Path) -> tuple[int, float] | None:
    """Where the body ends and References begins, for page-budget checks."""
    try:
        import pymupdf  # noqa: PLC0415
    except ImportError:
        return None
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc):
        for b in page.get_text("blocks"):
            if b[4].strip().startswith("References"):
                return i + 1, b[1]
    return None


def quote(s: str) -> str:
    return urllib.parse.quote(s)
