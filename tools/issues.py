"""Sweep github.com/anthropics/claude-code issues for prompt-cache / context / cost topics.

Usage:
    python tools/issues.py [--out DIR] [--pages N] [--top N]

Needs GITHUB_TOKEN or `gh auth token`. Writes issues-<date>.json (raw, deduped)
and issues-<date>.md (ranked, by theme). Score = keyword hits + log(reactions) +
log(comments) + open bonus. No AI, no guessing: everything here is on GitHub.
"""
import argparse, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request
from datetime import date

REPO = "anthropics/claude-code"
API = "https://api.github.com/search/issues"

# (query, theme) -- one GitHub search each, max 100/page
QUERIES = [
    ('"prompt cache"', "cache"),
    ('"prompt caching"', "cache"),
    ('"cache read"', "cache"),
    ('"cache miss"', "cache"),
    ('"cache invalidation"', "cache"),
    ('cache_creation_input_tokens OR cache_read_input_tokens', "cache"),
    ('"cache ttl" OR "1 hour cache" OR "1h cache" OR promptCacheTtl', "cache"),
    ('"cache hit"', "cache"),
    ('"system prompt" tokens', "prefix"),
    ('"CLAUDE.md" tokens', "prefix"),
    ('"tool definitions" tokens OR "MCP tools" tokens', "prefix"),
    ('"context window" usage', "context"),
    ('"auto-compact" OR autocompact OR "auto compact"', "compact"),
    ('compaction context', "compact"),
    ('"/context"', "context"),
    ('"token usage" wrong OR "token usage" inaccurate', "usage"),
    ('"/cost" OR "cost tracking"', "usage"),
    ('"usage limit" cache', "usage"),
    ('additionalContext hook', "hooks"),
    ('subagent cache OR "sub-agent" cache', "subagent"),
    ('skillOverrides OR "skill overrides"', "prefix"),
    ('cold cache OR COLD_COMPACT', "cache"),
    ('cache "5 minute"', "cache"),
    ('cache statusline OR cache "status line"', "usage"),
]

KEYWORDS = {  # weight per hit in title (x2) / body (x1), capped
    r"prompt.?cach": 5, r"cache.?ttl|1.?hour cache|1h cache|promptcachettl": 5,
    r"cache.?(read|write|creation|hit|miss|invalid)": 4, r"\bcache": 2,
    r"compact": 2, r"context window|context usage|/context": 2,
    r"system prompt|claude\.md|tool definition|mcp tool": 2,
    r"token": 1, r"\bcost\b|/cost|usage": 1, r"additionalcontext|hook": 1,
    r"subagent|sub-agent": 1, r"skilloverride": 3,
}


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return ""


def get(url, tok):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lastro"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), r.headers.get("X-RateLimit-Remaining")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                wait = int(e.headers.get("Retry-After", 20))
                print("  rate limit, sleep %ds" % wait, file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("gave up: " + url)


def search(q, theme, pages, tok):
    out = []
    for page in range(1, pages + 1):
        qs = urllib.parse.urlencode({"q": "repo:%s is:issue %s" % (REPO, q), "per_page": 100,
                                     "page": page, "sort": "reactions", "order": "desc"})
        data, rem = get(API + "?" + qs, tok)
        items = data.get("items", [])
        print("  %-50s p%d %3d (total %s, rl %s)" % (q[:50], page, len(items),
                                                    data.get("total_count"), rem), file=sys.stderr)
        for it in items:
            it["_themes"] = {theme}
            out.append(it)
        if len(items) < 100:
            break
        time.sleep(2)  # search API: 30 req/min authenticated
    return out


def score(it):
    title = (it.get("title") or "").lower()
    body = (it.get("body") or "")[:4000].lower()
    s = 0.0
    for pat, w in KEYWORDS.items():
        s += min(len(re.findall(pat, title)), 2) * w * 2
        s += min(len(re.findall(pat, body)), 3) * w
    reactions = (it.get("reactions") or {}).get("total_count", 0)
    s += 3 * math.log1p(reactions) + 1.5 * math.log1p(it.get("comments", 0))
    if it.get("state") == "open":
        s += 3
    return round(s, 1)


def row(r):
    return "| [%d](%s) | %s | %s | %d | %d | %s | %s |" % (
        r["number"], r["url"], r["score"], r["state"][:1], r["reactions"], r["comments"],
        r["created"], r["title"].replace("|", "/")[:90])


def comments(number, tok):
    out, page = [], 1
    while True:
        data, _ = get("https://api.github.com/repos/%s/issues/%d/comments?per_page=100&page=%d"
                      % (REPO, number, page), tok)
        out += data
        if len(data) < 100:
            return out
        page += 1


def fetch(rows, out, tok):
    """One markdown file per issue: front matter, body, every comment. Study copy,
    same shape as a book chapter, so it can be dropped into a knowledge base."""
    md_dir = os.path.join(out, "md")
    os.makedirs(md_dir, exist_ok=True)
    index = ["# issues fetched %s" % date.today().isoformat(), "",
             "| # | score | st | +1 | cmt | title |", "|--|--|--|--|--|--|"]
    for i, r in enumerate(rows, 1):
        path = os.path.join(md_dir, "%d.md" % r["number"])
        if os.path.exists(path):
            print("  %4d/%d #%d cached" % (i, len(rows), r["number"]), file=sys.stderr)
        else:
            it, rem = get("https://api.github.com/repos/%s/issues/%d" % (REPO, r["number"]), tok)
            cs = comments(r["number"], tok) if it.get("comments") else []
            print("  %4d/%d #%d %d comments (rl %s)" % (i, len(rows), r["number"], len(cs), rem),
                  file=sys.stderr)
            lines = ["---", "number: %d" % it["number"], "title: %s" % json.dumps(it["title"]),
                     "state: %s" % it["state"], "state_reason: %s" % it.get("state_reason"),
                     "created: %s" % it["created_at"], "updated: %s" % it["updated_at"],
                     "closed: %s" % it.get("closed_at"),
                     "labels: %s" % json.dumps([l["name"] for l in it.get("labels", [])]),
                     "reactions: %d" % (it.get("reactions") or {}).get("total_count", 0),
                     "comments: %d" % it.get("comments", 0), "url: %s" % it["html_url"],
                     "score: %s" % r["score"], "themes: %s" % json.dumps(r["themes"]), "---", "",
                     "# #%d %s" % (it["number"], it["title"]), "",
                     "*%s, %s, +%d*" % (it["user"]["login"], it["created_at"][:10],
                                        (it.get("reactions") or {}).get("total_count", 0)), "",
                     it.get("body") or "", ""]
            for c in cs:
                lines += ["", "## comment %s %s" % (c["user"]["login"], c["created_at"][:16]), "",
                          c.get("body") or ""]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            time.sleep(0.3)
        index.append("| [%d](md/%d.md) | %s | %s | %d | %d | %s |" % (
            r["number"], r["number"], r["score"], r["state"][:1], r["reactions"], r["comments"],
            r["title"].replace("|", "/")[:100]))
    with open(os.path.join(out, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    print("%d issues -> %s" % (len(rows), md_dir), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--from", dest="src", help="reuse an issues-<date>.json instead of searching")
    ap.add_argument("--fetch", type=int, default=0,
                    help="pull full body + comments for the top N into <out>/md/<number>.md")
    a = ap.parse_args()
    tok = token()
    if not tok:
        print("no token: 10 searches/min, may fail", file=sys.stderr)
    seen = {}
    if a.src:
        rows = json.load(open(a.src, encoding="utf-8"))
        d = date.today().isoformat()
        os.makedirs(a.out, exist_ok=True)
        if a.fetch:
            fetch(rows[:a.fetch], a.out, tok)
        return
    for q, theme in QUERIES:
        for it in search(q, theme, a.pages, tok):
            n = it["number"]
            if n in seen:
                seen[n]["_themes"].add(theme)
            else:
                seen[n] = it
        time.sleep(2)
    rows = []
    for it in seen.values():
        rows.append({
            "number": it["number"], "title": it["title"], "state": it["state"],
            "created": it["created_at"][:10], "updated": it["updated_at"][:10],
            "comments": it.get("comments", 0),
            "reactions": (it.get("reactions") or {}).get("total_count", 0),
            "labels": [l["name"] for l in it.get("labels", [])],
            "themes": sorted(it["_themes"]), "url": it["html_url"],
            "score": score(it), "body": it.get("body") or "",
        })
    rows.sort(key=lambda r: -r["score"])
    d = date.today().isoformat()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "issues-%s.json" % d), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    hdr = ["| # | score | st | +1 | cmt | created | title |", "|--|--|--|--|--|--|--|"]
    md = ["# claude-code issues sweep - %s" % d, "",
          "%d unique issues from %d searches. Open: %d. "
          "Score = keyword hits + log(reactions) + log(comments) + open bonus."
          % (len(rows), len(QUERIES), sum(r["state"] == "open" for r in rows)), ""]
    for theme in sorted({t for r in rows for t in r["themes"]}):
        sub = [r for r in rows if theme in r["themes"]]
        md += ["## %s (%d)" % (theme, len(sub)), ""] + hdr
        md += [row(r) for r in sub[:max(a.top // 3, 10)]]
        md.append("")
    md += ["## top %d overall" % a.top, ""] + hdr + [row(r) for r in rows[:a.top]]
    with open(os.path.join(a.out, "issues-%s.md" % d), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("%d issues -> %s/issues-%s.{json,md}" % (len(rows), a.out, d), file=sys.stderr)
    if a.fetch:
        fetch(rows[:a.fetch], a.out, tok)


if __name__ == "__main__":
    main()
