"""Build the Fulcrum Brief website (fulcrumbrief.github.io) from site.json.

  python website/build.py            # writes website/index.html
  python website/build.py --publish  # build, commit and push (GitHub Pages serves it within ~1 min)

Add a new video: download its LIVE YouTube thumbnail (https://i.ytimg.com/vi/<id>/maxresdefault.jpg, the host may change it after upload) to website/thumbs/vN.jpg at 640 px wide and add an entry at the TOP of
"videos" in site.json (only once the video is live). Never add a video that isn't public yet.
"""
import html
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "site.json"), encoding="utf-8"))
e = html.escape

org = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Fulcrum Brief",
    "alternateName": "@FulcrumBrief",
    "url": S["url"],
    "logo": S["url"] + "/logo.png",
    "description": S["description"],
    "slogan": S["tagline"],
    "sameAs": [p["url"] for p in S["profiles"]],
}

cards = "\n".join(
    f'''      <a class="card" href="https://www.youtube.com/watch?v={v["id"]}" target="_blank" rel="noopener">
        <img src="thumbs/{v["thumb"]}?v={int(os.path.getmtime(os.path.join(HERE, "thumbs", v["thumb"])))}" alt="{e(v["title"])}" loading="lazy" width="640" height="360">
        <span class="date">{e(v["date"])}</span>
        <h3>{e(v["title"])}</h3>
        <p>{e(v["blurb"])}</p>
      </a>''' for v in S["videos"])

links = "\n".join(
    f'      <a class="pill" href="{e(p["url"])}" target="_blank" rel="noopener me">{e(p["name"])}</a>'
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
<meta property="og:type" content="website">
<meta property="og:title" content="Fulcrum Brief">
<meta property="og:description" content="{e(S["description"])}">
<meta property="og:url" content="{S["url"]}/">
<meta property="og:image" content="{S["url"]}/og-image.png">
<meta name="twitter:card" content="summary">
<meta name="twitter:site" content="@FulcrumBrief">
<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script>
<style>
@font-face{{font-family:"Barlow Condensed";font-weight:700;src:url(fonts/BarlowCondensed-Bold.ttf)}}
@font-face{{font-family:"Barlow Condensed";font-weight:600;src:url(fonts/BarlowCondensed-SemiBold.ttf)}}
@font-face{{font-family:"Barlow";font-weight:400;src:url(fonts/Barlow-Regular.ttf)}}
@font-face{{font-family:"Barlow";font-weight:500;src:url(fonts/Barlow-Medium.ttf)}}
:root{{--navy:#0B1622;--slate:#1E3148;--amber:#F2A900;--white:#E8E6E1;--steel:#9FB0C3}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--navy);color:var(--white);font:400 17px/1.6 Barlow,system-ui,sans-serif}}
a{{color:inherit}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}
header{{text-align:center;padding:56px 0 28px;border-bottom:1px solid var(--slate)}}
header img{{width:min(460px,90%);height:auto}}
.tag{{font:600 22px "Barlow Condensed",sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--amber);margin:14px 0 0}}
.lead{{max-width:720px;margin:22px auto 0;color:var(--steel);font-size:18px}}
.cta{{display:inline-block;margin-top:26px;background:var(--amber);color:var(--navy);text-decoration:none;
  font:700 20px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase;padding:12px 28px;border-radius:999px}}
h2{{font:700 30px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase;margin:48px 0 18px}}
h2 span{{color:var(--amber)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}}
.card{{display:block;background:var(--slate);border-radius:14px;overflow:hidden;text-decoration:none;transition:transform .15s}}
.card:hover{{transform:translateY(-3px);outline:2px solid var(--amber)}}
.card img{{width:100%;height:auto;display:block;aspect-ratio:16/9;object-fit:cover}}
.card .date{{display:block;padding:12px 16px 0;color:var(--amber);font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.12em;text-transform:uppercase}}
.card h3{{margin:4px 16px 6px;font:700 22px/1.2 "Barlow Condensed",sans-serif}}
.card p{{margin:0 16px 18px;color:var(--steel);font-size:15px}}
.pills{{display:flex;flex-wrap:wrap;gap:12px}}
.pill{{text-decoration:none;border:1px solid var(--steel);border-radius:999px;padding:9px 18px;font:500 16px Barlow,sans-serif}}
.pill:hover{{border-color:var(--amber);color:var(--amber)}}
.about p{{max-width:760px;color:var(--steel)}}
footer{{margin-top:56px;padding:26px 0 40px;border-top:1px solid var(--slate);color:var(--steel);font-size:14px;text-align:center}}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <img src="logo.png" alt="Fulcrum Brief" width="1500" height="500">
    <p class="tag">{e(S["tagline"])}</p>
    <p class="lead">{e(S["description"])}</p>
    <a class="cta" href="https://www.youtube.com/@FulcrumBrief?sub_confirmation=1" target="_blank" rel="noopener">Watch on YouTube</a>
  </div>
</header>
<main class="wrap">
  <h2>Latest <span>briefings</span></h2>
  <div class="grid">
{cards}
  </div>
  <h2>Follow <span>Fulcrum Brief</span></h2>
  <div class="pills">
{links}
  </div>
  <section class="about">
    <h2>About</h2>
    {"".join(f"<p>{e(p)}</p>" for p in S["about"])}
  </section>
</main>
<footer>
  <div class="wrap">Fulcrum Brief &middot; New full videos every Monday, Wednesday and Friday &middot; <a href="https://www.youtube.com/@FulcrumBrief">youtube.com/@FulcrumBrief</a></div>
</footer>
</body>
</html>
'''
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(page)
print("built index.html with", len(S["videos"]), "videos and", len(S["profiles"]), "profiles")

if "--publish" in sys.argv:
    def git(*a):
        return subprocess.run(["git", "-C", HERE, *a], check=True)
    git("add", "-A")
    if subprocess.run(["git", "-C", HERE, "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-m", "Update site")
        git("push", "origin", "main")
    else:
        print("nothing to publish")
