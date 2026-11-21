"""Build the Fulcrum Brief website (fulcrumbrief.github.io) from site.json + the live Medium feed.

  python website/build.py            # writes website/index.html
  python website/build.py --publish  # build, commit and push (GitHub Pages serves it within ~1 min)

New video (only once it's live): download its LIVE YouTube thumbnail (https://i.ytimg.com/vi/<id>/maxresdefault.jpg;
the host may change it after upload) to website/thumbs/vN.jpg at 640 px wide, and add an entry at the TOP of "videos".
New Short (only once public): a frame at ~1.2 s from assets/video/vN_short-K.mp4 -> website/shorts/<id>.jpg (360 px wide; YouTube oardefault frames look odd),
add it at the TOP of "shorts". Medium articles are read automatically from the feed at build time.
"""
import html
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "site.json"), encoding="utf-8"))
e = html.escape


def ver(rel):
    return int(os.path.getmtime(os.path.join(HERE, rel)))


def articles():
    """Latest Medium stories (title, link, date, excerpt). Falls back to the cache if the feed can't be read."""
    cache = os.path.join(HERE, "articles-cache.json")
    try:
        raw = subprocess.run(["curl", "-sf", "-A", "Mozilla/5.0", S["medium_feed"]], capture_output=True,
                             check=True, timeout=30).stdout
        root = ET.fromstring(raw)
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        out = []
        for it in root.iter("item"):
            body = it.findtext("content:encoded", default="", namespaces=ns)
            paras = [re.sub("<[^>]+>", "", p) for p in re.findall(r"<p>(.*?)</p>", body, flags=re.S)]
            paras = [html.unescape(p).strip() for p in paras if len(p) > 80]
            excerpt = paras[0] if paras else ""
            if len(excerpt) > 230:
                excerpt = excerpt[:227].rsplit(" ", 1)[0] + "…"
            out.append(dict(title=it.findtext("title"), link=it.findtext("link").split("?")[0],
                            date=parsedate_to_datetime(it.findtext("pubDate")).strftime("%b %d, %Y"),
                            excerpt=excerpt))
        if out:
            json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return out
    except Exception as ex:  # noqa: BLE001
        print("medium feed not read:", ex)
    return json.load(open(cache, encoding="utf-8")) if os.path.exists(cache) else []


ARTS = articles()
V = S["videos"]
lead = V[0]

org = {
    "@context": "https://schema.org", "@type": "NewsMediaOrganization", "name": "Fulcrum Brief",
    "alternateName": "@FulcrumBrief", "url": S["url"], "logo": S["url"] + "/logo.png",
    "description": S["description"], "slogan": S["tagline"], "sameAs": [p["url"] for p in S["profiles"]],
}
yt = "https://www.youtube.com/watch?v="

video_cards = "\n".join(f'''      <a class="card" href="{yt}{v["id"]}" target="_blank" rel="noopener">
        <div class="thumb"><img src="thumbs/{v["thumb"]}?v={ver("thumbs/" + v["thumb"])}" alt="{e(v["title"])}" loading="lazy" width="640" height="360"><span class="play"></span></div>
        <span class="kicker">{e(v["date"])}</span>
        <h3>{e(v["title"])}</h3>
        <p>{e(v["blurb"])}</p>
      </a>''' for v in V[1:])

article_cards = "\n".join(f'''      <a class="article" href="{e(a["link"])}" target="_blank" rel="noopener">
        <span class="kicker">Article · {e(a["date"])}</span>
        <h3>{e(a["title"])}</h3>
        <p>{e(a["excerpt"])}</p>
        <span class="more">Read on Medium →</span>
      </a>''' for a in ARTS[:6]) or '<p class="muted">Articles are on their way.</p>'

short_cards = "\n".join(f'''      <a class="short" href="https://www.youtube.com/shorts/{s["id"]}" target="_blank" rel="noopener">
        <img src="shorts/{s["id"]}.jpg?v={ver("shorts/" + s["id"] + ".jpg")}" alt="{e(s["title"])}" loading="lazy" width="360" height="640">
        <span>{e(s["title"])}</span>
      </a>''' for s in S["shorts"])

topic_cards = "\n".join(f'''      <a class="topic" href="{e(t["url"])}" target="_blank" rel="noopener">
        <img src="img/{t["img"]}" alt="{e(t["name"])} map" loading="lazy" width="960" height="540">
        <div><h3>{e(t["name"])}</h3><p>{e(t["text"])}</p></div>
      </a>''' for t in S["topics"])

number_cards = "\n".join(f'''      <a class="num" href="{yt}{n["video"]}" target="_blank" rel="noopener">
        <img src="img/{n["img"]}" alt="{e(n["caption"])}" loading="lazy" width="960" height="540">
        <span>{e(n["caption"])}</span>
      </a>''' for n in S["numbers"])

links = "\n".join(f'        <a class="pill" href="{e(p["url"])}" target="_blank" rel="noopener me">{e(p["name"])}</a>'
                  for p in S["profiles"])

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fulcrum Brief | {e(S["tagline"])}</title>
<meta name="description" content="{e(S["description"])}">
<meta name="p:domain_verify" content="{S["pinterest_verify"]}"/>
<link rel="canonical" href="{S["url"]}/">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Fulcrum Brief articles" href="{S["medium_feed"]}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Fulcrum Brief">
<meta property="og:title" content="Fulcrum Brief | {e(S["tagline"])}">
<meta property="og:description" content="{e(S["description"])}">
<meta property="og:url" content="{S["url"]}/">
<meta property="og:image" content="{S["url"]}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@FulcrumBrief">
<meta name="theme-color" content="#0B1622">
<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script>
<style>
@font-face{{font-family:"Barlow Condensed";font-weight:700;font-display:swap;src:url(fonts/BarlowCondensed-Bold.ttf)}}
@font-face{{font-family:"Barlow Condensed";font-weight:600;font-display:swap;src:url(fonts/BarlowCondensed-SemiBold.ttf)}}
@font-face{{font-family:"Barlow";font-weight:400;font-display:swap;src:url(fonts/Barlow-Regular.ttf)}}
@font-face{{font-family:"Barlow";font-weight:500;font-display:swap;src:url(fonts/Barlow-Medium.ttf)}}
:root{{--navy:#0B1622;--navy2:#0F1D2C;--slate:#1E3148;--amber:#F2A900;--white:#E8E6E1;--steel:#9FB0C3}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--navy);color:var(--white);font:400 17px/1.6 Barlow,system-ui,sans-serif}}
a{{color:inherit}}
img{{max-width:100%}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 20px}}
.cond{{font-family:"Barlow Condensed",sans-serif}}
nav{{position:sticky;top:0;z-index:10;background:rgba(11,22,34,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--slate)}}
nav .wrap{{display:flex;align-items:center;gap:22px;height:64px}}
nav .brand{{display:flex;align-items:center;gap:10px;text-decoration:none;font:700 22px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase}}
nav .brand img{{width:30px;height:30px}}
nav .brand b{{color:var(--amber);font-weight:700}}
nav .links{{display:flex;gap:20px;margin-left:auto}}
nav .links a{{text-decoration:none;color:var(--steel);font:600 16px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase}}
nav .links a:hover{{color:var(--amber)}}
.btn{{display:inline-block;background:var(--amber);color:var(--navy);text-decoration:none;font:700 18px "Barlow Condensed",sans-serif;
  letter-spacing:.08em;text-transform:uppercase;padding:11px 24px;border-radius:999px;white-space:nowrap}}
.btn.ghost{{background:transparent;color:var(--white);border:1px solid var(--steel)}}
.btn:hover{{filter:brightness(1.08)}}
.hero{{position:relative;overflow:hidden;border-bottom:1px solid var(--slate);
  background:radial-gradient(1200px 500px at 85% -10%,rgba(242,169,0,.13),transparent 60%),
  repeating-linear-gradient(0deg,transparent 0 59px,rgba(30,49,72,.45) 59px 60px),
  repeating-linear-gradient(90deg,transparent 0 59px,rgba(30,49,72,.45) 59px 60px),var(--navy)}}
.hero .wrap{{display:grid;grid-template-columns:1.05fr 1fr;gap:44px;align-items:center;padding-top:64px;padding-bottom:64px}}
.pillbadge{{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(242,169,0,.5);color:var(--amber);border-radius:999px;
  padding:5px 14px;font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.14em;text-transform:uppercase}}
.pillbadge:before{{content:"";width:8px;height:8px;border-radius:50%;background:var(--amber)}}
.hero h1{{font:700 clamp(44px,6vw,72px)/1.02 "Barlow Condensed",sans-serif;letter-spacing:.01em;text-transform:uppercase;margin:18px 0 14px}}
.hero h1 span{{color:var(--amber)}}
.hero p.lead{{color:var(--steel);font-size:19px;max-width:520px;margin:0 0 26px}}
.hero .ctas{{display:flex;gap:12px;flex-wrap:wrap}}
.feature{{display:block;text-decoration:none;background:var(--slate);border-radius:16px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.45);transition:transform .2s}}
.feature:hover{{transform:translateY(-4px)}}
.feature .meta{{padding:16px 20px 20px}}
.feature h2{{margin:4px 0 0;font:700 26px/1.15 "Barlow Condensed",sans-serif}}
.thumb{{position:relative}}
.thumb img{{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}}
.play{{position:absolute;left:50%;top:50%;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;background:rgba(11,22,34,.75);border:2px solid var(--amber)}}
.play:after{{content:"";position:absolute;left:25px;top:19px;border-left:20px solid var(--amber);border-top:13px solid transparent;border-bottom:13px solid transparent}}
.kicker{{display:block;color:var(--amber);font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.14em;text-transform:uppercase}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--slate);background:var(--navy2)}}
.stats div{{padding:22px 10px;text-align:center;border-right:1px solid var(--slate)}}
.stats div:last-child{{border-right:0}}
.stats b{{display:block;font:700 34px "Barlow Condensed",sans-serif;color:var(--white)}}
.stats span{{color:var(--steel);font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.12em;text-transform:uppercase}}
section{{padding:56px 0 8px}}
.sechead{{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:22px}}
h2.sec{{font:700 34px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase;margin:0}}
h2.sec span{{color:var(--amber)}}
.sechead a{{color:var(--steel);text-decoration:none;font:600 16px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase}}
.sechead a:hover{{color:var(--amber)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:22px}}
.card{{display:block;background:var(--slate);border-radius:14px;overflow:hidden;text-decoration:none;transition:transform .15s}}
.card:hover,.article:hover,.topic:hover,.num:hover{{transform:translateY(-3px);outline:2px solid var(--amber)}}
.card .kicker{{padding:14px 18px 0}}
.card h3{{margin:4px 18px 6px;font:700 23px/1.18 "Barlow Condensed",sans-serif}}
.card p{{margin:0 18px 20px;color:var(--steel);font-size:15px}}
.articles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:22px}}
.article{{display:flex;flex-direction:column;text-decoration:none;background:linear-gradient(180deg,var(--slate),var(--navy2));border-left:4px solid var(--amber);
  border-radius:10px;padding:22px 24px;transition:transform .15s}}
.article h3{{font:700 26px/1.15 "Barlow Condensed",sans-serif;margin:6px 0 10px}}
.article p{{color:var(--steel);font-size:16px;margin:0 0 16px;flex:1}}
.article .more{{color:var(--amber);font:600 16px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase}}
.shorts{{display:grid;grid-auto-flow:column;grid-auto-columns:200px;gap:16px;overflow-x:auto;padding-bottom:12px;scroll-snap-type:x mandatory}}
.short{{scroll-snap-align:start;text-decoration:none;background:var(--slate);border-radius:14px;overflow:hidden}}
.short img{{display:block;width:100%;aspect-ratio:9/16;object-fit:cover}}
.short span{{display:block;padding:10px 12px 14px;font:600 17px/1.2 "Barlow Condensed",sans-serif}}
.nums{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.num{{display:block;text-decoration:none;border-radius:12px;overflow:hidden;background:#fff;transition:transform .15s}}
.num img{{display:block;width:100%;height:auto}}
.num span{{display:block;background:var(--slate);color:var(--steel);padding:10px 14px;font-size:14px}}
.topics{{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}}
.topic{{display:grid;grid-template-columns:1fr 1fr;align-items:center;text-decoration:none;background:var(--slate);border-radius:14px;overflow:hidden;transition:transform .15s}}
.topic img{{display:block;width:100%;height:100%;object-fit:cover;aspect-ratio:16/10}}
.topic div{{padding:18px 20px}}
.topic h3{{font:700 24px "Barlow Condensed",sans-serif;margin:0 0 6px;text-transform:uppercase;letter-spacing:.04em}}
.topic p{{margin:0;color:var(--steel);font-size:15px}}
.method{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}}
.method div{{background:var(--navy2);border:1px solid var(--slate);border-radius:14px;padding:24px}}
.method h3{{font:700 24px "Barlow Condensed",sans-serif;margin:8px 0;text-transform:uppercase;letter-spacing:.04em}}
.method p{{color:var(--steel);margin:0;font-size:16px}}
.method .n{{font:700 44px "Barlow Condensed",sans-serif;color:var(--amber);line-height:1}}
.quote{{display:grid;grid-template-columns:1.1fr 1fr;gap:28px;align-items:center;margin-top:26px;background:var(--slate);border-radius:16px;overflow:hidden}}
.quote img{{display:block;width:100%;height:auto}}
.quote div{{padding:24px 28px 24px 0}}
.quote blockquote{{margin:0 0 10px;font:600 26px/1.25 "Barlow Condensed",sans-serif}}
.quote cite{{color:var(--steel);font-style:normal;font-size:15px}}
.about{{display:grid;grid-template-columns:.8fr 1.2fr;gap:36px;align-items:end;background:radial-gradient(500px 300px at 20% 80%,rgba(242,169,0,.16),transparent 70%),var(--navy2);
  border:1px solid var(--slate);border-radius:18px;padding:30px 30px 0;overflow:hidden}}
.about img{{display:block;width:100%;max-width:380px;height:auto;margin:0 auto}}
.about .txt{{padding-bottom:30px}}
.about p{{color:var(--steel)}}
.pills{{display:flex;flex-wrap:wrap;gap:12px}}
.pill{{text-decoration:none;border:1px solid var(--steel);border-radius:999px;padding:9px 18px;font:500 16px Barlow,sans-serif}}
.pill:hover{{border-color:var(--amber);color:var(--amber)}}
.subscribe{{text-align:center;margin:64px 0 0;padding:48px 20px;border-top:1px solid var(--slate);border-bottom:1px solid var(--slate);
  background:radial-gradient(700px 260px at 50% 0,rgba(242,169,0,.14),transparent 70%)}}
.subscribe h2{{font:700 clamp(32px,4vw,46px) "Barlow Condensed",sans-serif;text-transform:uppercase;margin:0 0 8px}}
.subscribe p{{color:var(--steel);margin:0 0 22px}}
footer{{padding:28px 0 44px;color:var(--steel);font-size:14px}}
footer .wrap{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}
.muted{{color:var(--steel)}}
@media (max-width:860px){{
  nav .links{{display:none}} nav .btn{{margin-left:auto}}
  .hero .wrap,.quote,.about,.topic{{grid-template-columns:1fr}}
  .quote div{{padding:0 22px 22px}}
  .stats{{grid-template-columns:repeat(2,1fr)}} .stats div:nth-child(2){{border-right:0}}
  .nums,.method,.topics{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brand" href="#top"><img src="favicon.svg" alt="">Fulcrum <b>Brief</b></a>
  <div class="links"><a href="#briefings">Briefings</a><a href="#articles">Articles</a><a href="#shorts">Shorts</a><a href="#topics">Topics</a><a href="#about">About</a></div>
  <a class="btn" href="https://www.youtube.com/@FulcrumBrief?sub_confirmation=1" target="_blank" rel="noopener">Subscribe</a>
</div></nav>

<header class="hero" id="top"><div class="wrap">
  <div>
    <span class="pillbadge">Every claim checked</span>
    <h1>Every war has a <span>pivot point.</span></h1>
    <p class="lead">{e(S["description"])}</p>
    <div class="ctas">
      <a class="btn" href="{yt}{lead["id"]}" target="_blank" rel="noopener">Watch the latest</a>
      <a class="btn ghost" href="#articles">Read the articles</a>
    </div>
  </div>
  <a class="feature" href="{yt}{lead["id"]}" target="_blank" rel="noopener">
    <div class="thumb"><img src="thumbs/{lead["thumb"]}?v={ver("thumbs/" + lead["thumb"])}" alt="{e(lead["title"])}" width="640" height="360"><span class="play"></span></div>
    <div class="meta"><span class="kicker">Latest briefing · {e(lead["date"])}</span><h2>{e(lead["title"])}</h2></div>
  </a>
</div></header>

<div class="stats">
  <div><b>{len(V)}</b><span>Full briefings</span></div>
  <div><b>{len(S["shorts"])}+</b><span>Shorts</span></div>
  <div><b>{len(ARTS)}</b><span>Articles</span></div>
  <div><b>Mon · Wed · Fri</b><span>New videos</span></div>
</div>

<main class="wrap">
  <section id="briefings">
    <div class="sechead"><h2 class="sec">More <span>briefings</span></h2><a href="https://www.youtube.com/@FulcrumBrief/videos" target="_blank" rel="noopener">All videos →</a></div>
    <div class="grid">
{video_cards}
    </div>
  </section>

  <section id="articles">
    <div class="sechead"><h2 class="sec">Latest <span>articles</span></h2><a href="https://medium.com/@fulcrumbrief" target="_blank" rel="noopener">All articles →</a></div>
    <div class="articles">
{article_cards}
    </div>
  </section>

  <section id="shorts">
    <div class="sechead"><h2 class="sec">In <span>60 seconds</span></h2><a href="https://www.youtube.com/@FulcrumBrief/shorts" target="_blank" rel="noopener">All Shorts →</a></div>
    <div class="shorts">
{short_cards}
    </div>
  </section>

  <section id="numbers">
    <div class="sechead"><h2 class="sec">What it <span>costs you</span></h2></div>
    <div class="nums">
{number_cards}
    </div>
  </section>

  <section id="topics">
    <div class="sechead"><h2 class="sec">What we <span>cover</span></h2></div>
    <div class="topics">
{topic_cards}
    </div>
  </section>

  <section id="method">
    <div class="sechead"><h2 class="sec">How we <span>work</span></h2></div>
    <div class="method">
      <div><span class="n">01</span><h3>Every claim checked</h3><p>Numbers come from named sources, shown on screen and listed in every description. Claims are labelled as claims.</p></div>
      <div><span class="n">02</span><h3>In Moscow's words</h3><p>When Russian sources matter, we show the original, read it, translate it word for word, then check it against the record.</p></div>
      <div><span class="n">03</span><h3>What it costs you</h3><p>Every story ends on everyday life: the pump, groceries, markets, security. Why a war far away reaches your house.</p></div>
    </div>
    <div class="quote">
      <img src="img/quote-putin.jpg" alt="In Moscow's words: Putin quote card" loading="lazy" width="960" height="540">
      <div><span class="kicker">In Moscow's words</span>
        <blockquote>"We are not going to fight Europe… But if Europe suddenly wants to fight and starts, we are ready right now."</blockquote>
        <cite>Vladimir Putin to reporters, 2 December 2025. Translated word for word, then checked against Danish military intelligence.</cite></div>
    </div>
  </section>

  <section id="about">
    <div class="about">
      <img src="img/host.webp?v={ver('img/host.webp')}" alt="The host of Fulcrum Brief" loading="lazy">
      <div class="txt">
        <span class="kicker">About</span>
        <h2 class="sec" style="margin:6px 0 10px">Analysis from the <span>eastern flank</span></h2>
        {"".join(f"<p>{e(p)}</p>" for p in S["about"])}
        <div class="pills" style="margin-top:18px">
{links}
        </div>
      </div>
    </div>
  </section>

  <div class="subscribe">
    <h2>Find the pivot point first</h2>
    <p>New full briefings every Monday, Wednesday and Friday.</p>
    <a class="btn" href="https://www.youtube.com/@FulcrumBrief?sub_confirmation=1" target="_blank" rel="noopener">Subscribe on YouTube</a>
  </div>
</main>

<footer><div class="wrap">
  <span>© 2026 Fulcrum Brief · The pivot points of global power</span>
  <span><a href="https://www.youtube.com/@FulcrumBrief">YouTube</a> · <a href="https://medium.com/@fulcrumbrief">Medium</a> · <a href="https://x.com/FulcrumBrief">X</a> · <a href="https://www.instagram.com/fulcrumbrief">Instagram</a></span>
</div></footer>
</body>
</html>
'''
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(page)
print("built index.html:", len(V), "videos,", len(S["shorts"]), "shorts,", len(ARTS), "articles,", len(S["profiles"]), "profiles")

if "--publish" in sys.argv:
    def git(*a):
        return subprocess.run(["git", "-C", HERE, *a], check=True)
    git("add", "-A")
    if subprocess.run(["git", "-C", HERE, "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-m", "Update site")
        git("push", "origin", "main")
    else:
        print("nothing to publish")
