#!/usr/bin/env python3
"""Generate publications.tex from an ORCID record.

Pulls the list of works from the ORCID public API, enriches each DOI with
metadata from Crossref, and writes a LaTeX `enumerate` block (newest first,
author name in bold) to publications.tex.

This is what makes the CV self-updating: publish something, add it to your
ORCID record, and the next CI build (or the weekly scheduled run) regenerates
the list automatically. Run locally with:  python3 scripts/fetch_publications.py
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ORCID = "0000-0001-8033-2213"
# Bold the CV owner: surname + a given-name initial that must match.
ME_SURNAME = "wyatt"
ME_GIVEN_INITIAL = "C"
AUTHOR_CAP = 10           # truncate longer author lists with "et al."
OUT = os.path.join(os.path.dirname(__file__), "..", "publications.tex")
MAILTO = "cw13722@gmail.com"
UA = f"cv-builder/1.0 (mailto:{MAILTO})"


def get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def latex_escape(s):
    if not s:
        return ""
    s = html.unescape(s)
    s = s.replace("<i>", " \x01").replace("</i>", "\x02")
    s = s.replace("<I>", " \x01").replace("</I>", "\x02")
    s = re.sub(r"<[^>]+>", "", s)  # strip any other stray tags
    for k, v in {"‐": "-", "‑": "-", "‒": "-", "–": "--", "—": "---",
                 "‘": "`", "’": "'", "“": "``", "”": "''", " ": " "}.items():
        s = s.replace(k, v)
    for k, v in {"&": r"\&", "%": r"\%", "#": r"\#",
                 "_": r"\_", "$": r"\$"}.items():
        s = s.replace(k, v)
    s = s.replace("\x01", r"\textit{").replace("\x02", "}")
    return re.sub(r"\s+", " ", s).strip()


def initials(given):
    if not given:
        return ""
    return "".join(p[0].upper() + "." for p in given.replace(".", " ").split() if p)


def fmt_author(a):
    fam, giv = a.get("family", ""), a.get("given", "")
    name = f"{initials(giv)} {fam}".strip()
    me = fam.lower() == ME_SURNAME and giv[:1].upper() == ME_GIVEN_INITIAL
    return name, me


def author_string(authors):
    def render(pair):
        nm, me = pair
        e = latex_escape(nm)
        return r"\textbf{" + e + "}" if me else e

    if len(authors) > AUTHOR_CAP:
        cut = AUTHOR_CAP
        idx = next((i for i, (_, me) in enumerate(authors) if me), -1)
        if idx >= cut:
            cut = idx + 1
        return ", ".join(render(a) for a in authors[:cut]) + " et al."
    names = [render(a) for a in authors]
    if len(names) > 1:
        return ", ".join(names[:-1]) + r" \& " + names[-1]
    return names[0] if names else ""


def dois_from_orcid():
    data = get_json(f"https://pub.orcid.org/v3.0/{ORCID}/works")
    dois = []
    for g in data.get("group", []):
        for eid in g.get("external-ids", {}).get("external-id", []):
            if eid.get("external-id-type") == "doi":
                dois.append(eid["external-id-value"].strip().lower())
                break
    # de-duplicate, preserve order
    seen, out = set(), []
    for d in dois:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def crossref(doi):
    m = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
                 f"?mailto={MAILTO}")["message"]
    cont = m.get("container-title") or []
    journal = cont[0] if cont else m.get("group-title", "")
    if m.get("type") == "posted-content":
        journal = "bioRxiv"
    dp = m.get("issued", {}).get("date-parts", [[None]])[0]
    return {
        "doi": doi,
        "title": (m.get("title") or [""])[0],
        "journal": journal,
        "year": dp[0] if dp else None,
        "month": dp[1] if len(dp) > 1 else 0,
        "vol": m.get("volume", ""),
        "issue": m.get("issue", ""),
        "page": m.get("page", ""),
        "art": m.get("article-number", ""),
        "type": m.get("type", ""),
        "authors": [fmt_author(a) for a in m.get("author", [])],
    }


def render_item(x):
    astr = author_string(x["authors"])
    t = latex_escape(x["title"])
    venue = rf"\textit{{{latex_escape(x['journal'])}}}"
    if x["vol"]:
        venue += f", {latex_escape(str(x['vol']))}"
        if x["issue"]:
            venue += f"({latex_escape(str(x['issue']))})"
        if x["page"]:
            venue += f", {latex_escape(x['page'])}"
    elif x["art"]:
        venue += f", {latex_escape(x['art'])}"
    if x["type"] == "posted-content":
        venue += " (preprint)"
    return (rf"  \item {astr} ({x['year']}). {t}. {venue}. "
            rf"\href{{https://doi.org/{x['doi']}}}{{doi:{x['doi']}}}")


def main():
    try:
        dois = dois_from_orcid()
    except Exception as e:
        print(f"ERROR: could not read ORCID works: {e}", file=sys.stderr)
        return 1
    works = []
    for d in dois:
        try:
            works.append(crossref(d))
        except Exception as e:
            print(f"WARN: Crossref failed for {d}: {e}", file=sys.stderr)
        time.sleep(0.3)

    if not works:
        # Don't clobber a good file with an empty one if the network failed.
        if os.path.exists(OUT):
            print("WARN: no works fetched; keeping existing publications.tex",
                  file=sys.stderr)
            return 0
        print("ERROR: no works fetched and no existing file", file=sys.stderr)
        return 1

    works.sort(key=lambda x: ((x["year"] or 0), (x["month"] or 0)), reverse=True)

    lines = [
        "% Auto-generated by scripts/fetch_publications.py from ORCID "
        f"{ORCID}.",
        "% Do not edit by hand; re-run the script to refresh.",
        r"\begin{enumerate}[leftmargin=1.4em,labelsep=0.5em,itemsep=5pt,"
        r"topsep=4pt,label=\arabic*.]",
    ]
    lines += [render_item(x) for x in works]
    lines.append(r"\end{enumerate}")
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(works)} publications to {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
