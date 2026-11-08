import json
import shutil
from datetime import date
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

    legal_urls = build_legal_pages(meta, meta["site_url"].rstrip("/"))
    _write_sitemap(meta, data, legal_urls)
    _write_robots(meta)
    (DIST / "ads.txt").write_text(
        "google.com, pub-9406644927707143, DIRECT, f08c47fec0942fa0\n", encoding="utf-8"
    )
    print(f"OK — wygenerowano {len(all_articles)} artykułów + index")


def _write_sitemap(meta, data, extra_urls=()):
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
    for u in extra_urls:
        urls.append(f"  <url><loc>{u}</loc><changefreq>yearly</changefreq><priority>0.3</priority></url>")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(urls)
    sitemap += "\n</urlset>"
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def _write_robots(meta):
    url = meta["site_url"].rstrip("/")
    txt = f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n"
    (DIST / "robots.txt").write_text(txt, encoding="utf-8")




def build_legal_pages(meta, site_url):
    """Strony wymagane przez AdSense: polityka prywatności, o nas, kontakt."""
    name = meta["site_name"]
    desc = meta["description"]
    email = "biuro@fitnesspromo.online"
    css = (
        "*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:#0f0f1a;color:#e2e8f0;line-height:1.75}"
        "header{border-bottom:1px solid #2a2a40;padding:16px 20px}header a{font-weight:800;font-size:20px;color:#fff;text-decoration:none}"
        "main{max-width:760px;margin:0 auto;padding:32px 20px 64px}h1{font-size:32px;line-height:1.2;margin:0 0 8px;color:#fff}"
        "h2{font-size:21px;margin:32px 0 8px;color:#fff}p,li{font-size:16px}a{color:#8b9cff}"
        ".upd{color:#94a3b8;font-size:14px;margin-bottom:24px}footer{border-top:1px solid #2a2a40;padding:24px 20px;text-align:center;font-size:14px;color:#94a3b8}"
        "footer a{color:#94a3b8;margin:0 8px}"
    )
    footer = (
        f'<footer><a href="/o-nas/">O nas</a><a href="/kontakt/">Kontakt</a>'
        f'<a href="/polityka-prywatnosci/">Polityka prywatności</a><p>© {date.today().year} {name}</p></footer>'
    )

    def page(slug, title, body):
        html = (
            f'<!DOCTYPE html>\n<html lang="pl">\n<head>\n<meta charset="UTF-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'<title>{title} | {name}</title>\n<meta name="description" content="{title} — {name}. {desc}">\n'
            f'<meta name="robots" content="index, follow">\n<link rel="canonical" href="{site_url}/{slug}/">\n'
            f'<!-- Google AdSense -->\n<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9406644927707143"\n'
            f'     crossorigin="anonymous"></script>\n<style>{css}</style>\n</head>\n<body>\n'
            f'<header><a href="/">{name}</a></header>\n<main>\n<h1>{title}</h1>\n{body}\n</main>\n{footer}\n</body>\n</html>\n'
        )
        out = DIST / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")

    today = date.today().isoformat()
    page("polityka-prywatnosci", "Polityka prywatności", f"""
<p class="upd">Ostatnia aktualizacja: {today}</p>
<h2>1. Administrator serwisu</h2>
<p>Administratorem serwisu {name} ({site_url}) jest jego redakcja. Kontakt w sprawach prywatności i danych osobowych: <a href="mailto:{email}">{email}</a>.</p>
<h2>2. Jakie dane zbieramy</h2>
<p>Serwis nie wymaga rejestracji i nie prowadzi kont użytkowników. Podczas korzystania ze strony automatycznie przetwarzane są dane techniczne: adres IP, typ przeglądarki i urządzenia, odwiedzane podstrony, czas wizyty oraz źródło wejścia. Jeśli napiszesz do nas wiadomość e-mail, przetwarzamy Twój adres e-mail i treść wiadomości wyłącznie w celu odpowiedzi.</p>
<h2>3. Pliki cookies i technologie śledzące</h2>
<p>Serwis korzysta z plików cookies i podobnych technologii własnych oraz podmiotów trzecich, w celu analizy ruchu, wyświetlania reklam i rozliczania programów partnerskich. Możesz w każdej chwili usunąć lub zablokować pliki cookies w ustawieniach przeglądarki. Zablokowanie cookies nie uniemożliwia czytania serwisu.</p>
<h2>4. Reklamy — Google AdSense i inne sieci reklamowe</h2>
<p>W serwisie wyświetlane są reklamy dostarczane przez Google AdSense oraz inne sieci reklamowe. Dostawcy zewnętrzni, w tym Google, używają plików cookies do wyświetlania reklam na podstawie wcześniejszych odwiedzin użytkownika w tym i innych serwisach. Spersonalizowane reklamy możesz wyłączyć w <a href="https://adssettings.google.com" rel="noopener nofollow">Ustawieniach reklam Google</a>. Więcej informacji: <a href="https://policies.google.com/technologies/ads" rel="noopener nofollow">jak Google wykorzystuje dane z witryn partnerów</a>.</p>
<h2>5. Linki partnerskie</h2>
<p>Część linków w serwisie to linki partnerskie (afiliacyjne), np. do platform streamingowych. Jeśli klikniesz taki link i skorzystasz z oferty, możemy otrzymać prowizję. Nie zwiększa to ceny, którą płacisz. Linki są oznaczone, a prowizja nie wpływa na treść rekomendacji.</p>
<h2>6. Twoje prawa</h2>
<p>Zgodnie z RODO masz prawo dostępu do swoich danych, ich sprostowania, usunięcia, ograniczenia przetwarzania, przenoszenia, wniesienia sprzeciwu oraz wniesienia skargi do Prezesa Urzędu Ochrony Danych Osobowych. Aby skorzystać z tych praw, napisz na <a href="mailto:{email}">{email}</a>.</p>
<h2>7. Zmiany polityki</h2>
<p>Możemy aktualizować niniejszą politykę. Aktualna wersja jest zawsze dostępna na tej stronie, a data ostatniej zmiany widnieje na górze.</p>
""")
    page("o-nas", "O nas", f"""
<p>{name} to serwis z rekomendacjami filmów i seriali. {desc}</p>
<h2>Cel serwisu</h2>
<p>Pomagamy szybciej wybrać, co obejrzeć: przygotowujemy rankingi, listy tematyczne i rekomendacje bez spoilerów. Nie promujemy piractwa — linki prowadzą wyłącznie do legalnych platform streamingowych.</p>
<h2>Jak się utrzymujemy</h2>
<p>Serwis jest bezpłatny dla czytelników. Utrzymujemy go z reklam oraz z prowizji od linków partnerskich. Oznaczamy takie linki, a prowizja nie decyduje o tym, co polecamy.</p>
<h2>Błędy i uwagi</h2>
<p>Dostępność tytułów zmienia się w zależności od platformy i regionu. Jeśli zauważysz nieaktualne informacje, napisz do nas: <a href="mailto:{email}">{email}</a>.</p>
""")
    page("kontakt", "Kontakt", f"""
<p>Masz pytanie, uwagę do artykułu albo propozycję współpracy? Napisz do nas.</p>
<h2>E-mail</h2>
<p><a href="mailto:{email}">{email}</a></p>
<p>Odpowiadamy zwykle w ciągu kilku dni roboczych. W sprawach dotyczących danych osobowych zobacz <a href="/polityka-prywatnosci/">Politykę prywatności</a>.</p>
""")
    return [f"{site_url}/polityka-prywatnosci/", f"{site_url}/o-nas/", f"{site_url}/kontakt/"]


if __name__ == "__main__":
    build()
