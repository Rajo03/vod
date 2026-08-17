import json
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

SRC = Path(".")
DIST = Path("dist")
TMPL = SRC / "templates"
AFFILIATE_FILE = SRC / ".." / "affiliate_links.json"
BLOG_KEY = "vod"


def load_affiliate() -> dict:
    af = AFFILIATE_FILE.resolve()
    if af.exists():
        with open(af, encoding="utf-8") as f:
            return json.load(f).get(BLOG_KEY, {})
    return {}


def inject_affiliate(data: dict, affiliate: dict) -> None:
    kategorie = affiliate.get("kategorie", {})
    for kat_slug, articles in data.items():
        if kat_slug == "meta":
            continue
        linki = kategorie.get(kat_slug, [])
        for art in articles:
            if not art.get("oferty") and linki:
                art["oferty"] = linki

KAT_NAMES = {
    "rankingi": "Rankingi",
    "gatunki":  "Gatunki",
    "wieczor":  "Wieczór",
}

KAT_ICONS = {
    "rankingi": "🏆",
    "gatunki":  "🎬",
    "wieczor":  "🌙",
}


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    data = json.loads((SRC / "artykuly.json").read_text(encoding="utf-8"))
    affiliate = load_affiliate()
    inject_affiliate(data, affiliate)
    sidebar_oferty = affiliate.get("sidebar", [])
    meta = data["meta"]

    env = Environment(loader=FileSystemLoader(str(TMPL)), autoescape=True)
    env.globals["meta"] = meta

    all_articles = []
    for kat_slug, articles in data.items():
        if kat_slug == "meta":
            continue
        for art in articles:
            all_articles.append({
                "kat_slug": kat_slug,
                "kat_name": KAT_NAMES.get(kat_slug, kat_slug),
                "kat_icon": KAT_ICONS.get(kat_slug, ""),
                **art,
            })

    tmpl_index = env.get_template("index.html")
    index_html = tmpl_index.render(
        meta=meta,
        data=data,
        kat_names=KAT_NAMES,
        kat_icons=KAT_ICONS,
        all_articles=all_articles,
        sidebar_oferty=sidebar_oferty,
    )
    (DIST / "index.html").write_text(index_html, encoding="utf-8")

    tmpl_art = env.get_template("artykul.html")
    for kat_slug, articles in data.items():
        if kat_slug == "meta":
            continue
        kat_name = KAT_NAMES.get(kat_slug, kat_slug)
        kat_icon = KAT_ICONS.get(kat_slug, "")
        kat_dir = DIST / kat_slug
        kat_dir.mkdir()

        for art in articles:
            art_dir = kat_dir / art["slug"]
            art_dir.mkdir()

            related = [
                a for a in all_articles
                if a["slug"] != art["slug"] and a["kat_slug"] == kat_slug
            ][:3]

            html = tmpl_art.render(
                meta=meta,
                art=art,
                kat_slug=kat_slug,
                kategoria=kat_name,
                kat_icon=kat_icon,
                base="../../",
                related=related,
                sidebar_oferty=sidebar_oferty,
            )
            (art_dir / "index.html").write_text(html, encoding="utf-8")

    _write_sitemap(meta, data)
    _write_robots(meta)
    print(f"OK — wygenerowano {len(all_articles)} artykułów + index")


def _write_sitemap(meta, data):
    url = meta["site_url"].rstrip("/")
    urls = [f"  <url><loc>{url}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>"]
    for kat_slug, articles in data.items():
        if kat_slug == "meta":
            continue
        for art in articles:
            urls.append(
                f"  <url><loc>{url}/{kat_slug}/{art['slug']}/</loc>"
                f"<changefreq>monthly</changefreq><priority>0.8</priority></url>"
            )
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(urls)
    sitemap += "\n</urlset>"
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def _write_robots(meta):
    url = meta["site_url"].rstrip("/")
    txt = f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n"
    (DIST / "robots.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    build()
