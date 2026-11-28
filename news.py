"""Newsroom: every news post Fulcrum Brief publishes, on the website (host 28 Nov 2026:
"post everything from everywhere that we do on our website").

Source: our Bluesky feed (public API, no login). Every news story goes out there as a full thread, so it is
the most complete text version. Thread parts are joined; images are saved locally to news/img.
Writes /news/index.html and returns the items for the home page. Falls back to newsroom-cache.json.
"""
import datetime
import html
import json
import os
import subprocess

import briefings

e = html.escape
HERE = os.path.dirname(os.path.abspath(__file__))
ACTOR = "fulcrumbrief.bsky.social"
SKIP = ("card photo", "photo:", "image:", "map:")


def rich(text, facets):
    """Escaped text with Bluesky link facets turned into <a> (facets use UTF-8 byte offsets)."""
    b = text.encode("utf-8")
    links = []
    for f in facets or []:
        for feat in f.get("features", []):
            if feat.get("uri"):
                links.append((f["index"]["byteStart"], f["index"]["byteEnd"], feat["uri"]))
    out, pos = [], 0
    for s, en, uri in sorted(links):
        if s < pos:
            continue
        out.append(e(b[pos:s].decode("utf-8", "ignore")))
        out.append(f'<a href="{e(uri)}" target="_blank" rel="noopener">{e(b[s:en].decode("utf-8", "ignore"))}</a>')
        pos = en
    out.append(e(b[pos:].decode("utf-8", "ignore")))
    return "".join(out)


def fetch(limit=80):
    cache = os.path.join(HERE, "newsroom-cache.json")
    imgdir = os.path.join(HERE, "news", "img")
    os.makedirs(imgdir, exist_ok=True)
    try:
        url = (f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={ACTOR}"
               "&filter=posts_and_author_threads&limit=100")
        feed = json.loads(subprocess.run(["curl", "-sf", url], capture_output=True, check=True, timeout=30).stdout)["feed"]
        roots, parts = {}, {}
        for f in feed:
            if f.get("reason"):
                continue
            p, rec = f["post"], f["post"]["record"]
            if rec.get("reply"):
                parts.setdefault(rec["reply"]["root"]["uri"], []).append((rec["createdAt"], rec.get("text", ""), rich(rec.get("text", ""), rec.get("facets"))))
                continue
            emb = p.get("embed") or {}
            media = emb.get("media") or {}
            img = ""
            for src in (emb, media):
                if src.get("images"):
                    img = src["images"][0].get("fullsize") or src["images"][0].get("thumb", "")
                    break
                if src.get("thumbnail"):
                    img = src["thumbnail"]
                    break
            rkey = p["uri"].rsplit("/", 1)[1]
            roots[p["uri"]] = dict(id=rkey, text=rec.get("text", ""), html=rich(rec.get("text", ""), rec.get("facets")), created=rec["createdAt"], img=img,
                                   link=f"https://bsky.app/profile/{ACTOR}/post/{rkey}")
        out = []
        for uri, r in roots.items():
            pairs = [(r["text"], r["html"])] + [(t, h) for _, t, h in sorted(parts.get(uri, []))]
            pairs = [(t.strip(), h) for t, h in pairs if t.strip() and not t.strip().lower().startswith(SKIP)]
            body = [t for t, _ in pairs]
            htmls = [h for _, h in pairs]
            if not body:
                continue
            local = ""
            if r["img"]:
                local = f"news/img/{r['id']}.jpg"
                fp = os.path.join(HERE, local)
                if not os.path.exists(fp):
                    subprocess.run(["curl", "-sfL", "-o", fp, r["img"]], timeout=30)
                if not os.path.exists(fp) or os.path.getsize(fp) < 2000:
                    local = ""
            dt = datetime.datetime.fromisoformat(r["created"].replace("Z", "+00:00"))
            out.append(dict(id=r["id"], body=body, html=htmls, img=local, link=r["link"], iso=dt.isoformat(),
                            date=dt.strftime("%b %d, %Y")))
        out.sort(key=lambda x: x["iso"], reverse=True)
        out = out[:limit]
        if out:
            json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return out
    except Exception as ex:  # noqa: BLE001
        print("newsroom feed not read:", ex)
    return json.load(open(cache, encoding="utf-8")) if os.path.exists(cache) else []


CSS = """<style>
.news{display:grid;gap:22px;margin-top:24px}
.item{display:grid;grid-template-columns:280px 1fr;gap:22px;background:var(--navy2);border:1px solid var(--slate);border-left:4px solid var(--amber);border-radius:12px;overflow:hidden}
.item.noimg{grid-template-columns:1fr}
.item img{display:block;width:100%;height:100%;object-fit:cover}
.item div{padding:18px 22px 18px 0}
.item.noimg div{padding:18px 22px}
.item .lead{font:600 22px/1.3 "Barlow Condensed",sans-serif;margin:6px 0 10px;color:var(--white)}
.item p{margin:0 0 8px;color:var(--steel);font-size:16px}
.item .src{font:600 15px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase}
@media (max-width:760px){.item{grid-template-columns:1fr}.item div{padding:0 18px 18px}}
</style>"""


def item_html(n):
    hs = n.get("html") or [e(b) for b in n["body"]]
    rest = "".join(f"<p>{h}</p>" for h in hs[1:])
    img = f'<img src="/{n["img"]}" alt="" loading="lazy">' if n["img"] else ""
    return (f'<article class="item{"" if img else " noimg"}" id="n-{e(n["id"])}">{img}<div>'
            f'<span class="kicker">News · {e(n["date"])}</span><p class="lead">{hs[0]}</p>{rest}'
            f'<a class="src" href="{e(n["link"])}" target="_blank" rel="noopener">Discuss on Bluesky →</a></div></article>')


def build(S):
    items = fetch()
    links = " · ".join(f'<a href="{p["url"]}" target="_blank" rel="noopener">{e(p["name"])}</a>' for p in S["profiles"])
    body = f"""{CSS}
<span class="kicker">Newsroom</span>
<h1 class="sec">Latest <span>news</span></h1>
<p class="muted">Every news brief we publish across our pages, in one place. Verified and sourced; claims are labelled. Follow us on {links}.</p>
<div class="news">
{chr(10).join(item_html(n) for n in items) or '<p class="muted">News is on its way.</p>'}
</div>"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Fulcrum Brief newsroom",
          "url": S["url"] + "/news/", "publisher": {"@id": S["url"] + "/#org"}}
    page = briefings.shell(S, "Newsroom · Fulcrum Brief", "Every Fulcrum Brief news brief: verified war and geopolitics news, and what it means for you.",
                           "/news/", body, ld, S["url"] + "/og-image.png")
    os.makedirs(os.path.join(HERE, "news"), exist_ok=True)
    open(os.path.join(HERE, "news", "index.html"), "w", encoding="utf-8").write(page)
    # add /news/ to the sitemap written by briefings
    sm = os.path.join(HERE, "sitemap.xml")
    t = open(sm, encoding="utf-8").read()
    if "/news/" not in t:
        t = t.replace("</urlset>", f"  <url><loc>{S['url']}/news/</loc></url>\n</urlset>")
        open(sm, "w", encoding="utf-8").write(t)
    print(f"newsroom: {len(items)} items")
    return items
