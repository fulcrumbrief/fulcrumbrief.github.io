"""Per-video briefing pages + the Standards page + sitemap/robots for fulcrumbrief.github.io (host OK 22 Nov 2026).

Called from build.py. For every video in site.json that has a "code" (its delivery folder name, e.g.
"05_2026-11-20_russia-oil-war"), it writes website/briefing/<slug>/index.html with:
  the embedded video, the live title/summary/chapters (YouTube Data API, read-only), the section-by-section notes,
  the full source list with links (the delivery folder's SOURCES.md, reporting sections only), the corrected
  transcript (captions.en.srt), and VideoObject + chapter (Clip) structured data.
Inputs are only READ from D:/Claude/Ready-to-Upload (never edited). Parsed content is cached in briefings-cache.json,
so the site still builds when D: or the API is unavailable.
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DELIV = "D:/Claude/Ready-to-Upload"
CACHE = os.path.join(HERE, "briefings-cache.json")
e = html.escape
SKIP_SECTIONS = ("footage", "photo", "music", "sound", "thumbnail")
INTERNAL = re.compile(r"vidiq|claude|\bAI\b|host'?s|bought by", re.I)


def slug_of(code):
    return re.sub(r"^\d+_\d{4}-\d{2}-\d{2}_", "", code)


def secs(ts):
    p = [int(x) for x in ts.split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]


def iso_dur(s):
    return f"PT{s // 60}M{s % 60}S"


# ---------- reading the delivery folder ----------
def parse_description(text):
    """Summary paragraphs, chapters [(sec, label)], and the optional section-by-section notes."""
    lines = text.replace("\r", "").split("\n")
    summary, chapters, notes = [], [], []
    mode = "summary"
    para = []

    def flush(target):
        if para:
            target.append(" ".join(para).strip())
            para.clear()

    for ln in lines:
        s = ln.strip()
        low = s.lower()
        if low.startswith("chapters"):
            flush(summary)
            mode = "chapters"
            continue
        if "section by section" in low:
            mode = "notes"
            continue
        if re.match(r"^(sources|footage|music|video and photos|intro music|fulcrum brief:|#|---|©)", low):
            flush(notes if mode == "notes" else summary)
            mode = "end"
        if mode == "summary":
            if s:
                para.append(s)
            else:
                flush(summary)
        elif mode == "chapters":
            m = re.match(r"^(\d+:\d{2}(?::\d{2})?)\s+(.+)", s)
            if m:
                chapters.append((secs(m.group(1)), m.group(2)))
            elif chapters and not s:
                mode = "after_chapters"
        elif mode == "notes":
            if s:
                para.append(s)
            else:
                flush(notes)
    flush(summary if mode == "summary" else notes)
    return summary, chapters, notes


def md_inline(s):
    out = e(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener nofollow">\1</a>', out)
    out = re.sub(r'(?<!href=")(https?://[^\s<|)]+)',
                 lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener nofollow">{re.sub(r"^https?://(www\.)?", "", m.group(1)).split("/")[0]}</a>', out)
    return out


# Public wording for internal notes in SOURCES.md (credits are never dropped, only reworded).
PUBLIC = [
    (re.compile(r"\s*\(cut out and relit onto the host'?s vidIQ thumbnail\)", re.I), " (thumbnail)"),
    (re.compile(r"the host'?s SZ Whooshes & Risers pack \(bought, no credit needed\)", re.I), "SZ Whooshes & Risers pack (licensed)"),
    (re.compile(r"SZ Whooshes & Risers pack,? \(?bought by the host,? no (?:attribution|credit) needed\)?\.?", re.I), "SZ Whooshes & Risers pack (licensed)."),
    (re.compile(r"`fulcrum-brief-outro\.mp4` uses", re.I), "The channel outro uses"),
    (re.compile(r",? so that credit stays in the description", re.I), ""),
    (re.compile(r"No intro sting \([^)]*\)\.\s*", re.I), ""),
    (re.compile(r"Built by the host in vidIQ.*$", re.I), "Fulcrum Brief (own design)"),
    (re.compile(r"^`?thumbnail\.png`?:? made by the host with vidIQ.*$", re.I), "Thumbnail: Fulcrum Brief (own design)."),
    (re.compile(r"\bvidIQ\b ?", re.I), ""),
]
DROP_LINE = re.compile(r"^(\|\s*)?(not used|downloaded, not used)|no intro sting in this video|^\*\*?note", re.I)


def public(s):
    for rx, rep in PUBLIC:
        s = rx.sub(rep, s)
    return s


def parse_sources(md):
    """All of SOURCES.md as HTML: reporting, quotes, footage, photos, maps, music and sound, every credit and licence."""
    out, table = [], []

    def end_table():
        if not table:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table if not re.match(r"^\|?\s*:?-{3,}", r.strip())]
        head, body = rows[0], rows[1:]
        drop = [i for i, h in enumerate(head) if h.lower() == "file" and len(head) >= 3]
        keep = [i for i in range(len(head)) if i not in drop]
        h = "".join(f"<th>{e(head[i])}</th>" for i in keep)
        b = "".join("<tr>" + "".join(f"<td>{md_inline(public(r[i]))}</td>" for i in keep if i < len(r)) + "</tr>" for r in body)
        out.append(f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
        table.clear()

    intro_done = False
    for ln in md.replace("\r", "").split("\n"):
        s = ln.strip()
        if s.startswith("# "):
            continue
        if s.startswith("## "):
            end_table()
            out.append(f"<h3>{e(re.sub(r'\s*\(.*?\)\s*$', '', s[3:]))}</h3>")
            intro_done = True
            continue
        if DROP_LINE.search(s):
            continue
        if not intro_done:
            if s and not INTERNAL.search(s):
                out.append(f'<p class="muted">{md_inline(s)}</p>')
            continue
        if s.startswith("|"):
            table.append(s)
            continue
        end_table()
        if s.startswith(("- ", "* ")):
            out.append(f"<p>• {md_inline(public(s[2:]))}</p>")
        elif s and s != "---":
            out.append(f"<p>{md_inline(public(s))}</p>")
    end_table()
    return "\n".join(out)


def parse_srt(text):
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "").strip()):
        ls = block.split("\n")
        if len(ls) >= 3 and "-->" in ls[1]:
            h, m, rest = ls[1].split(" --> ")[0].split(":")
            t = int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))
            cues.append((t, re.sub(r"\{[^}]*\}", "", " ".join(ls[2:])).strip()))
    return cues


def transcript_html(cues, chapters, vid):
    """Transcript split under the chapter headings, in readable paragraphs (~4 sentences)."""
    bounds = chapters or [(0, "")]
    parts = []
    for i, (start, label) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else 10 ** 9
        text = " ".join(c for t, c in cues if start <= t < end)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        sents = re.split(r"(?<=[.!?…])\s+(?=[A-Z\"“])", text)
        paras = [" ".join(sents[k:k + 4]) for k in range(0, len(sents), 4)]
        if label:
            parts.append(f'<h3><a href="https://www.youtube.com/watch?v={vid}&amp;t={start}s" target="_blank" rel="noopener">'
                         f'{start // 60}:{start % 60:02d}</a> {e(label)}</h3>')
        parts += [f"<p>{e(p)}</p>" for p in paras]
    return "\n".join(parts)


def live_meta(ids):
    """Title, description, publish date, duration for each id (YouTube Data API, read-only)."""
    sys.path.insert(0, "D:/Claude/Fulcrum-Brief/pipeline")
    import yt_api  # noqa: E402
    r = yt_api.service().videos().list(part="snippet,contentDetails,status", id=",".join(ids)).execute()
    out = {}
    for v in r["items"]:
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", v["contentDetails"]["duration"])
        out[v["id"]] = dict(title=v["snippet"]["title"], description=v["snippet"]["description"],
                            published=v["snippet"]["publishedAt"], public=v["status"]["privacyStatus"] == "public",
                            seconds=int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0))
    return out


def gather(S):
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    vids = [v for v in S["videos"] if v.get("code")]
    try:
        meta = live_meta([v["id"] for v in vids])
    except Exception as ex:  # noqa: BLE001
        print("briefings: API not reached, using cache:", ex)
        meta = {}
    for v in vids:
        d = os.path.join(DELIV, v["code"])
        c = cache.get(v["id"], {})
        try:
            m = meta.get(v["id"])
            desc = m["description"] if m else open(os.path.join(d, "description-live.txt"), encoding="utf-8").read()
            summary, chapters, notes = parse_description(desc)
            c.update(summary=summary, chapters=chapters, notes=notes,
                     sources=parse_sources(open(os.path.join(d, "SOURCES.md"), encoding="utf-8").read()))
            srt = os.path.join(d, "captions.en.srt")
            if os.path.exists(srt):
                c["cues"] = parse_srt(open(srt, encoding="utf-8").read())
            if m:
                c.update(title=m["title"], published=m["published"], seconds=m["seconds"], public=m["public"])
        except OSError as ex:
            print("briefings: delivery folder not read for", v["code"], ex)
        cache[v["id"]] = c
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return [(v, cache[v["id"]]) for v in vids if cache[v["id"]].get("summary") and cache[v["id"]].get("public", True)]


# ---------- page shell ----------
def shell(S, title, desc, path, body, ld, og_image):
    url = f'{S["url"]}{path}'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/page.css">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Fulcrum Brief">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@FulcrumBrief">
<meta name="theme-color" content="#0B1622">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<nav><div class="wrap">
  <a class="brand" href="/"><img src="/favicon.svg" alt="">Fulcrum <b>Brief</b></a>
  <div class="links"><a href="/#briefings">Briefings</a><a href="/standards/">Standards</a><a href="/#about">About</a><a href="/#contact">Contact</a></div>
  <a class="btn" href="https://www.youtube.com/@FulcrumBrief?sub_confirmation=1" target="_blank" rel="noopener">Subscribe</a>
</div></nav>
<main class="wrap page">
{body}
</main>
<footer><div class="wrap">
  <span>© 2026 Fulcrum Brief · The pivot points of global power</span>
  <span><a href="/">Home</a> · <a href="/standards/">Standards &amp; corrections</a> · <a href="mailto:{S["contact"]["email"]}">Contact</a></span>
</div></footer>
</body>
</html>
'''


def host_ld(S):
    h = S["host"]
    return {"@type": "Person", "@id": S["url"] + "/#host", "name": h["name"], "jobTitle": "Host",
            "worksFor": {"@id": S["url"] + "/#org"}, "sameAs": h.get("sameAs", [])}


def briefing_page(S, v, c):
    vid = v["id"]
    title = c.get("title") or v["title"]
    secs_total = c.get("seconds") or 0
    chapters = [tuple(x) for x in c.get("chapters", [])]
    summary = c["summary"]
    desc = summary[0][:300].rsplit(" ", 1)[0] + "…" if len(summary[0]) > 300 else summary[0]
    pub = (c.get("published") or "")[:10]
    thumb = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
    clips = []
    for i, (st, label) in enumerate(chapters):
        en = chapters[i + 1][0] if i + 1 < len(chapters) else secs_total or st + 60
        clips.append({"@type": "Clip", "name": label, "startOffset": st, "endOffset": en,
                      "url": f"https://www.youtube.com/watch?v={vid}&t={st}s"})
    transcript_text = " ".join(t for _, t in c.get("cues", []))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "VideoObject", "name": title, "description": " ".join(summary)[:4900], "thumbnailUrl": [thumb],
         "uploadDate": c.get("published") or pub, "duration": iso_dur(secs_total) if secs_total else None,
         "embedUrl": f"https://www.youtube-nocookie.com/embed/{vid}", "contentUrl": f"https://www.youtube.com/watch?v={vid}",
         "publisher": {"@id": S["url"] + "/#org"}, "creator": {"@id": S["url"] + "/#host"},
         "hasPart": clips, "transcript": transcript_text[:20000] or None, "inLanguage": "en"},
        host_ld(S),
        {"@type": "NewsMediaOrganization", "@id": S["url"] + "/#org", "name": "Fulcrum Brief", "url": S["url"],
         "logo": S["url"] + "/logo.png", "correctionsPolicy": S["url"] + "/standards/#corrections",
         "verificationFactCheckingPolicy": S["url"] + "/standards/", "ethicsPolicy": S["url"] + "/standards/"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Fulcrum Brief", "item": S["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": title}]}]}
    ld["@graph"][0] = {k: val for k, val in ld["@graph"][0].items() if val}
    chap = "".join(f'<li><a href="https://www.youtube.com/watch?v={vid}&amp;t={st}s" target="_blank" rel="noopener">'
                   f'<span>{st // 60}:{st % 60:02d}</span>{e(label)}</a></li>' for st, label in chapters)
    notes = "".join(f"<p>{e(p)}</p>" for p in c.get("notes", []))
    trans = transcript_html(c.get("cues", []), chapters, vid)
    datestr = ""
    if pub:
        y, mo, d = pub.split("-")
        datestr = f'{int(d)} {["January","February","March","April","May","June","July","August","September","October","November","December"][int(mo)-1]} {y}'
    body = f'''<article>
  <a class="back" href="/#briefings">← All briefings</a>
  <span class="kicker">Briefing{" · " + datestr if datestr else ""}{f" · {secs_total // 60} min" if secs_total else ""}</span>
  <h1>{e(title)}</h1>
  <p class="byline">Presented by <a href="/#about">{e(S["host"]["name"])}</a> · <a href="/standards/">Every claim checked</a></p>
  <div class="player"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{e(title)}" loading="lazy" allowfullscreen
    allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe></div>
  <div class="cols">
    <div>
      <h2>The briefing</h2>
      {"".join(f"<p>{e(p)}</p>" for p in summary)}
      {f"<h2>Section by section</h2>{notes}" if notes else ""}
    </div>
    <aside>
      <h2>Chapters</h2>
      <ol class="chap">{chap}</ol>
      <a class="btn" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">Watch on YouTube</a>
    </aside>
  </div>
  <section id="sources"><h2>Sources &amp; resources</h2>
    <p class="muted">Every report, document, quote, photo, clip, map and piece of music used in this video, with its licence. Spotted an error? <a href="/standards/#corrections">Tell us</a> and we will correct it in public.</p>
    {c.get("sources", "")}</section>
  {f'<section id="transcript"><details><summary><h2>Full transcript</h2></summary>{trans}</details></section>' if trans else ""}
</article>'''
    path = f"/briefing/{slug_of(v['code'])}/"
    return path, shell(S, f"{title} | Fulcrum Brief", desc, path, body, ld, thumb)


def standards_page(S):
    st = S["standards"]
    corr = st.get("corrections", [])
    corr_html = ("<ul>" + "".join(f"<li><b>{e(x['date'])}</b> · <a href=\"{e(x['url'])}\">{e(x['video'])}</a>: {e(x['text'])}</li>" for x in corr) + "</ul>"
                 if corr else "<p>No corrections so far. If we get something wrong, it is logged here with the date and what changed.</p>")
    blocks = "".join(f'<div class="std"><h2>{e(b["h"])}</h2>' + "".join(f"<p>{e(p)}</p>" for p in b["p"]) + "</div>" for b in st["sections"])
    body = f'''<article>
  <span class="kicker">Standards &amp; corrections</span>
  <h1>How we check what we publish</h1>
  <p class="lead">{e(st["intro"])}</p>
  {blocks}
  <div class="std" id="corrections"><h2>Corrections</h2>
    <p>{e(st["corrections_policy"])}</p>
    <p><a class="btn" href="mailto:{S["contact"]["email"]}?subject=Correction">Report an error</a></p>
    <h3>Corrections log</h3>{corr_html}</div>
</article>'''
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": "Standards & corrections", "url": S["url"] + "/standards/", "about": {"@id": S["url"] + "/#org"}},
        {"@type": "NewsMediaOrganization", "@id": S["url"] + "/#org", "name": "Fulcrum Brief", "url": S["url"],
         "correctionsPolicy": S["url"] + "/standards/#corrections", "verificationFactCheckingPolicy": S["url"] + "/standards/",
         "ethicsPolicy": S["url"] + "/standards/", "email": S["contact"]["email"]}]}
    return "/standards/", shell(S, "Standards & corrections | Fulcrum Brief", st["intro"], "/standards/", body, ld, S["url"] + "/og-cover.png")


PAGE_CSS = '''@font-face{font-family:"Barlow Condensed";font-weight:700;font-display:swap;src:url(/fonts/BarlowCondensed-Bold.ttf)}
@font-face{font-family:"Barlow Condensed";font-weight:600;font-display:swap;src:url(/fonts/BarlowCondensed-SemiBold.ttf)}
@font-face{font-family:"Barlow";font-weight:400;font-display:swap;src:url(/fonts/Barlow-Regular.ttf)}
@font-face{font-family:"Barlow";font-weight:500;font-display:swap;src:url(/fonts/Barlow-Medium.ttf)}
:root{--navy:#0B1622;--navy2:#0F1D2C;--slate:#1E3148;--amber:#F2A900;--white:#E8E6E1;--steel:#9FB0C3}
*{box-sizing:border-box}
body{margin:0;background:var(--navy);color:var(--white);font:400 17px/1.65 Barlow,system-ui,sans-serif}
a{color:var(--amber)}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
nav{position:sticky;top:0;z-index:10;background:rgba(11,22,34,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--slate)}
nav .wrap{display:flex;align-items:center;gap:22px;height:64px}
nav .brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--white);font:700 22px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase}
nav .brand img{width:30px;height:30px}
nav .brand b{color:var(--amber)}
nav .links{display:flex;gap:20px;margin-left:auto}
nav .links a{text-decoration:none;color:var(--steel);font:600 16px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase}
nav .links a:hover{color:var(--amber)}
.btn{display:inline-block;background:var(--amber);color:var(--navy);text-decoration:none;font:700 18px "Barlow Condensed",sans-serif;letter-spacing:.08em;text-transform:uppercase;padding:11px 24px;border-radius:999px;white-space:nowrap}
.page{padding:34px 20px 20px}
.back{display:inline-block;margin-bottom:18px;color:var(--steel);text-decoration:none;font:600 15px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase}
.kicker{display:block;color:var(--amber);font:600 15px "Barlow Condensed",sans-serif;letter-spacing:.14em;text-transform:uppercase}
h1{font:700 clamp(36px,5vw,58px)/1.05 "Barlow Condensed",sans-serif;margin:8px 0 10px}
h2{font:700 28px "Barlow Condensed",sans-serif;letter-spacing:.06em;text-transform:uppercase;margin:34px 0 12px}
h3{font:700 22px "Barlow Condensed",sans-serif;margin:26px 0 8px}
h3 a{text-decoration:none;margin-right:8px}
.byline,.muted{color:var(--steel)}
.byline a{color:var(--white)}
.lead{color:var(--steel);font-size:20px;max-width:760px}
.player{position:relative;aspect-ratio:16/9;margin:22px 0 4px;border-radius:14px;overflow:hidden;background:#000;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.cols{display:grid;grid-template-columns:1.6fr 1fr;gap:44px}
.cols p{max-width:72ch}
aside{position:sticky;top:84px;align-self:start;background:var(--navy2);border:1px solid var(--slate);border-radius:14px;padding:4px 22px 24px}
.chap{list-style:none;padding:0;margin:0 0 20px}
.chap a{display:flex;gap:12px;padding:7px 0;border-bottom:1px solid var(--slate);color:var(--white);text-decoration:none;font-size:16px}
.chap a:hover{color:var(--amber)}
.chap span{color:var(--amber);font:600 16px "Barlow Condensed",sans-serif;min-width:42px}
.tbl{overflow-x:auto;margin:10px 0 18px}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--slate);vertical-align:top}
th{color:var(--steel);font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.1em;text-transform:uppercase}
details summary{cursor:pointer;list-style:none}
details summary h2{display:inline-block}
details summary h2:after{content:" +";color:var(--amber)}
details[open] summary h2:after{content:" −"}
#transcript p{color:#cfd3d6;max-width:78ch}
.std{background:var(--navy2);border:1px solid var(--slate);border-radius:14px;padding:4px 26px 18px;margin:20px 0}
.std p{color:#cfd3d6;max-width:78ch}
footer{padding:40px 0 44px;color:var(--steel);font-size:14px;border-top:1px solid var(--slate);margin-top:50px}
footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer a{color:var(--steel)}
@media (max-width:860px){nav .links{display:none} nav .btn{margin-left:auto} .cols{grid-template-columns:1fr} aside{position:static}}
'''


def build_all(S):
    pages = gather(S)
    open(os.path.join(HERE, "page.css"), "w", encoding="utf-8").write(PAGE_CSS)
    written, links = [], {}
    for v, c in pages:
        path, page = briefing_page(S, v, c)
        out = os.path.join(HERE, path.strip("/").replace("/", os.sep))
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page)
        written.append((path, (c.get("published") or "")[:10]))
        links[v["id"]] = path
    path, page = standards_page(S)
    os.makedirs(os.path.join(HERE, "standards"), exist_ok=True)
    open(os.path.join(HERE, "standards", "index.html"), "w", encoding="utf-8").write(page)
    urls = [("/", ""), ("/standards/", "")] + written
    sm = "\n".join(f"  <url><loc>{S['url']}{p}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for p, d in urls)
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sm}\n</urlset>\n')
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {S['url']}/sitemap.xml\n")
    print(f"briefings: {len(written)} briefing pages, standards page, sitemap ({len(urls)} urls)")
    return links
