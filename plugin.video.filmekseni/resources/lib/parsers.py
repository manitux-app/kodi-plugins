# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import html
import json
import re

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


def categories(base_url):
    base_url = base_url.rstrip("/")
    return [
        ("Anasayfa", base_url + "/"),
        ("Diziler", base_url + "/diziler/"),
        ("En Cok Izlenenler", base_url + "/en-cok-izlenenler/"),
        ("Tavsiye Filmler", base_url + "/kategori/tavsiye-filmler"),
        ("Aile", base_url + "/tur/aile-filmleri/"),
        ("Aksiyon", base_url + "/tur/aksiyon-filmleri/"),
        ("Animasyon", base_url + "/tur/animasyon-film-izle/"),
        ("Belgesel", base_url + "/tur/belgesel-filmleri/"),
        ("Bilim Kurgu", base_url + "/tur/bilim-kurgu-filmleri/"),
        ("Biyografi", base_url + "/tur/biyografi-filmleri/"),
        ("Dram", base_url + "/tur/dram-filmleri-izle/"),
        ("Fantastik", base_url + "/tur/fantastik-filmler/"),
        ("Gerilim", base_url + "/tur/gerilim-filmleri/"),
        ("Gizem", base_url + "/tur/gizem-filmleri/"),
        ("Komedi", base_url + "/tur/komedi-filmleri/"),
        ("Korku", base_url + "/tur/korku-filmleri/"),
        ("Macera", base_url + "/tur/macera-filmleri/"),
        ("Muzik", base_url + "/tur/muzik-filmleri/"),
        ("Muzikal", base_url + "/tur/muzikal/"),
        ("Romantik", base_url + "/tur/romantik-filmler/"),
        ("Savas", base_url + "/tur/savas-filmleri/"),
        ("Spor", base_url + "/tur/spor-filmleri/"),
        ("Suc", base_url + "/tur/suc-filmleri/"),
        ("Tarih", base_url + "/tur/tarih-filmleri/"),
        ("Western", base_url + "/tur/western-filmler/"),
    ]


def page_url(category_url, page_number):
    return category_url if int(page_number) <= 1 else category_url.rstrip("/") + "/page/{0}/".format(page_number)


def parse_page_items(page, base_url, category_title=""):
    items = []
    seen = set()
    for block in _poster_blocks(page):
        anchor = _first(r"<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>", block, re.S)
        href = _attr(anchor, "href")
        title = _clean(
            _first(r'<[^>]*class=["\'][^"\']*\bposter-title\b[^"\']*["\'][^>]*>.*?<[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>(.*?)</', block, re.S)
            or _attr(anchor, "title")
            or _attr(_first(r"<img\b[^>]*>", block, re.S), "alt")
        )
        poster = _poster_from(block, base_url)
        year = _clean(_first(r'<[^>]*class=["\'][^"\']*\bposter-year\b[^"\']*["\'][^>]*>(.*?)</', block, re.S))
        rating = _rating(_clean(_first(r'<[^>]*class=["\'][^"\']*\bposter-imdb\b[^"\']*["\'][^>]*>(.*?)</', block, re.S)))
        if not title or not href:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        items.append({
            "category": category_title,
            "title": _clean_title(title),
            "url": url,
            "image": poster or "",
            "rating": rating,
            "year": year,
            "plot": " ".join(x for x in [year, rating] if x),
        })
    return items


def parse_search_results(payload, base_url):
    try:
        data = json.loads(payload)
    except Exception:
        data = {}
    results = data.get("result", []) if isinstance(data, dict) else []
    items = []
    for item in results:
        title = item.get("title")
        slug = item.get("slug")
        if not title or not slug:
            continue
        prefix = item.get("slug_prefix") or ""
        poster = item.get("poster") or item.get("cover") or ""
        image = base_url.rstrip("/") + "/uploads/poster/" + poster if poster else ""
        url = (base_url.rstrip("/") + "/" + prefix + slug).rstrip("/") + "/"
        items.append({
            "title": _clean_title(title),
            "url": url,
            "image": image,
            "year": item.get("year") or "",
            "rating": _rating(str(item.get("imdb") or "")),
            "plot": "",
        })
    return items


def parse_media_info(page, url, base_url):
    movie = _parse_movie_json_ld(page)
    title = _clean_title(_clean(_first(r'<div[^>]*class=["\'][^"\']*\bpage-title\b[^"\']*["\'][^>]*>.*?<h1[^>]*>(.*?)</h1>', page, re.S)) or movie.get("title") or "")
    poster = _detail_poster_from(page, base_url) or movie.get("image") or _poster_from(page, base_url)
    plot = movie.get("description") or _clean(_first(r"<article[^>]*>\s*<p[^>]*>(.*?)</p>", page, re.S))
    rating = _rating(movie.get("rating") or _clean(_first(r'<div[^>]*class=["\'][^"\']*\brate\b[^"\']*["\'][^>]*>(.*?)</div>', page, re.S)))
    year = movie.get("year") or _first(r"\b(\d{4})\b", _clean(_first(r'<div[^>]*class=["\'][^"\']*\bpage-title\b[^"\']*["\'][^>]*>.*?<strong[^>]*>.*?</strong>', page, re.S)))
    duration = movie.get("duration") or _first(r"(\d+)", _clean(_first(r'<div[^>]*class=["\'][^"\']*text-nowrap[^"\']*["\'][^>]*>(.*?)</div>', page, re.S)))
    trailer = movie.get("trailer") or _normalize_youtube(_attr(_first(r"<[^>]+data-trailer=['\"][^'\"]+['\"][^>]*>", page, re.S), "data-trailer"))
    sources = parse_video_sources(page, url, base_url)
    episodes = parse_episodes(page, base_url)
    if trailer:
        sources.insert(0, {"label": "Fragman", "url": trailer, "referer": url, "is_trailer": True})
    backdrop = _attr(_first(r'<[^>]*class=["\'][^"\']*\bplay-that-video\b[^"\']*["\'][^>]*>.*?<img\b[^>]*>', page, re.S), "src")
    tags = ", ".join(dict.fromkeys(_clean(x).replace("✅", "").strip() for x in re.findall(r'<a[^>]+href=["\'][^"\']*/tur/[^"\']*["\'][^>]*>(.*?)</a>', page, re.S) if _clean(x)))
    actors = ", ".join(dict.fromkeys(_clean(x) for x in re.findall(r'<[^>]*class=["\'][^"\']*\bstory-item-title\b[^"\']*["\'][^>]*>(.*?)</', page, re.S) if _clean(x)))
    related = [x for x in parse_page_items(page, base_url, "Related") if x["url"] != url][:12]
    return {
        "title": title,
        "url": url,
        "image": fix_url(poster, base_url) if poster else "",
        "backdrop": fix_url(backdrop, base_url) if backdrop else (fix_url(poster, base_url) if poster else ""),
        "plot": plot,
        "rating": rating,
        "year": year,
        "duration": duration,
        "tags": tags,
        "actors": actors or movie.get("actors", ""),
        "sources": sources,
        "episodes": episodes,
        "related": related,
    }


def parse_video_sources(page, page_url, base_url):
    sources = []
    if not re.search(r'<div[^>]*class=["\'][^"\']*\bcard-video\b[^"\']*["\'][^>]*>.*?<iframe\b', page or "", re.S | re.I):
        return sources
    tabs = re.findall(r'<a\b[^>]*class=["\'][^"\']*\bnav-link\b[^"\']*["\'][^>]*>.*?</a>', _first(r'<ul[^>]*class=["\'][^"\']*\bnav-tabs\b[^"\']*["\'][^>]*>.*?</ul>', page, re.S), re.S)
    tabs = [x for x in tabs if "fragman" not in _clean(x).lower()]
    player_nav = _player_nav_block(page)
    panes = re.findall(r'<div\b[^>]*class=["\'][^"\']*\btab-pane\b[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*\btab-pane\b|$)', player_nav, re.S | re.I)
    for idx, pane in enumerate(panes):
        lang = _clean(tabs[idx]) if idx < len(tabs) else ""
        for link in re.findall(r'<a\b[^>]*class=["\'][^"\']*\bnav-link\b[^"\']*["\'][^>]*href=["\'][^"\']+["\'][^>]*>.*?</a>', pane, re.S | re.I):
            _add_source(sources, link, lang, page_url, base_url)
    if not sources:
        for link in re.findall(r'<nav\b[^>]*class=["\'][^"\']*\bcard-nav\b[^"\']*["\'][^>]*>.*?</nav>', player_nav, re.S | re.I):
            for anchor in re.findall(r'<a\b[^>]*href=["\'][^"\']+["\'][^>]*>.*?</a>', link, re.S | re.I):
                _add_source(sources, anchor, "", page_url, base_url)
    if not sources and re.search(r'<div[^>]*class=["\'][^"\']*\bcard-video\b[^"\']*["\'][^>]*>.*?<iframe\b', page or "", re.S | re.I):
        sources.append({"label": "VIP", "url": page_url, "referer": page_url, "is_trailer": False})
    result = []
    seen = set()
    for source in sources:
        key = (source["label"].lower(), source["url"].lower())
        if key not in seen:
            seen.add(key)
            result.append(source)
    return result


def parse_episodes(page, base_url):
    episodes = []
    seen = set()
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page or "", re.S | re.I):
        if "containsSeason" not in raw and "TVEpisode" not in raw:
            continue
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        seasons = data.get("containsSeason") or []
        if isinstance(seasons, dict):
            seasons = [seasons]
        for season_data in seasons:
            season = str(season_data.get("seasonNumber") or "1")
            items = season_data.get("episode") or []
            if isinstance(items, dict):
                items = [items]
            for item in items:
                href = item.get("url") or ""
                episode = str(item.get("episodeNumber") or _first(r"/bolum-(\d+)/", href) or "1")
                title = _clean(item.get("name") or "{0}. Sezon {1}. Bolum".format(season, episode))
                _add_episode(episodes, seen, title, href, season, episode, base_url)
    for match in re.finditer(r'<a\b[^>]*href=["\'][^"\']*/sezon-\d+/bolum-\d+/[^"\']*["\'][^>]*>.*?</a>', page or "", re.S | re.I):
        tag = match.group(0)
        href = _attr(tag, "href")
        season = _first(r"/sezon-(\d+)/", href) or "1"
        episode = _first(r"/bolum-(\d+)/", href) or "1"
        title = _clean(tag) or "{0}. Sezon {1}. Bolum".format(season, episode)
        _add_episode(episodes, seen, title, href, season, episode, base_url)
    return sorted(episodes, key=lambda item: (int(item["season"]), int(item["episode"])))


def _add_episode(episodes, seen, title, href, season, episode, base_url):
    if not href:
        return
    key = (season, episode)
    if key in seen:
        return
    seen.add(key)
    episodes.append({
        "title": title,
        "url": fix_url(href, base_url),
        "season": season,
        "episode": episode,
    })


def _player_nav_block(page):
    page = page or ""
    start = page.find('class="nav card-nav')
    if start < 0:
        start = page.find("class='nav card-nav")
    if start < 0:
        return ""
    start = page.rfind("<nav", 0, start)
    end = page.find('<div class="card card-dark"', start)
    if end < 0:
        end = page.find("<div class='card card-dark'", start)
    block = page[start:end] if end > start else page[start:]
    return block if "card-video" in page[end:end + 3000] or "tab-pane" in block else ""


def parse_iframe(page, base_url):
    iframe = _first(r'<div[^>]*class=["\'][^"\']*\bcard-video\b[^"\']*["\'][^>]*>.*?<iframe\b[^>]*(?:data-src|src)=["\'][^"\']+["\'][^>]*>', page or "", re.S | re.I)
    return fix_url(_attr(iframe, "data-src") or _attr(iframe, "src"), base_url)


def fix_url(url, base_url):
    if not url:
        return ""
    return urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())


def _add_source(sources, link, lang, page_url, base_url):
    name = _clean(link)
    href = _attr(link, "href")
    lowered = name.lower()
    href_lowered = href.lower()
    if not name or not href or href == "#" or any(x in lowered for x in ("paylas", "paylaş", "indir", "hata", "sinema modu", "fragman")):
        return
    if any(x in href_lowered for x in ("/tur/", "/kategori/", "/diziler/", "/en-cok-izlenenler/", "/imdb-250/", "/yil/", "/ulke/")):
        return
    label = "{0} | {1}".format(name, lang).strip(" |") if lang else name
    sources.append({"label": label, "url": fix_url(href, base_url), "referer": page_url, "is_trailer": False})


def _parse_movie_json_ld(page):
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page or "", re.S | re.I):
        if '"@type":"Movie"' not in raw and '"@type": "Movie"' not in raw:
            continue
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        rating = data.get("aggregateRating", {}).get("ratingValue") if isinstance(data.get("aggregateRating"), dict) else ""
        trailer = data.get("trailer", {}).get("embedUrl") if isinstance(data.get("trailer"), dict) else ""
        actors = data.get("actor") or []
        actor_names = ", ".join(x.get("name", "") for x in actors if isinstance(x, dict) and x.get("name"))
        return {
            "title": data.get("name") or "",
            "image": data.get("image") or "",
            "description": data.get("description") or "",
            "duration": _first(r"PT(\d+)M", data.get("duration") or ""),
            "rating": _rating(str(rating or "")),
            "trailer": _normalize_youtube(trailer),
            "actors": actor_names,
            "year": _first(r"\b(\d{4})\b", data.get("datePublished") or ""),
        }
    return {}


def _poster_blocks(page):
    starts = [m.start() for m in re.finditer(r'<div[^>]*class=["\'][^"\']*\bposter\b[^"\']*["\'][^>]*>', page or "", re.I)]
    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(page)
        block = page[start:end]
        if "poster-container" in (page[max(0, start - 300):start] + block):
            blocks.append(block)
    return blocks


def _poster_from(block, base_url):
    img = _first(r"<img\b[^>]*>", block or "", re.S)
    source = _first(r"<source\b[^>]*type=['\"]image/jpeg['\"][^>]*>", block or "", re.S) or _first(r"<source\b[^>]*>", block or "", re.S)
    poster = _attr(img, "data-src") or _attr(img, "src") or _attr(source, "data-srcset") or _attr(source, "srcset")
    if poster and not poster.lower().startswith("data:image"):
        return fix_url(poster.split()[0], base_url)
    return ""


def _detail_poster_from(page, base_url):
    picture = _first(r'<picture\b[^>]*class=["\'][^"\']*\bposter-auto\b[^"\']*["\'][^>]*>.*?</picture>', page or "", re.S)
    if not picture:
        return ""
    img = _first(r"<img\b[^>]*>", picture, re.S)
    source = _first(r"<source\b[^>]*type=['\"]image/jpeg['\"][^>]*>", picture, re.S) or _first(r"<source\b[^>]*>", picture, re.S)
    poster = _attr(img, "data-src") or _attr(source, "data-srcset") or _attr(img, "src") or _attr(source, "srcset")
    if poster and not poster.lower().startswith("data:image"):
        return fix_url(poster.split()[0], base_url)
    return ""


def _normalize_youtube(value):
    if not value:
        return ""
    return value if value.lower().startswith("http") else "https://youtube.com/embed/" + value.strip("/")


def _rating(value):
    match = re.search(r"\d+(?:[.,]\d+)?", value or "")
    return match.group(0).replace(",", ".") if match else ""


def _clean_title(value):
    return re.sub(r"\s+izle\s*$", "", value or "", flags=re.I).strip()


def _attr(tag, name):
    if not tag:
        return ""
    match = re.search(r'\b{0}=["\']([^"\']+)["\']'.format(re.escape(name)), tag, re.I)
    return html.unescape(match.group(1)) if match else ""


def _first(pattern, text, flags=0):
    match = re.search(pattern, text or "", flags | re.I)
    if not match:
        return ""
    return match.group(1) if match.lastindex else match.group(0)


def _clean(text):
    text = re.sub(r"<svg.*?</svg>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
