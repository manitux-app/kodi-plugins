# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import html
import re

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


def categories(base_url):
    base_url = base_url.rstrip("/")
    return [
        ("Son Filmler", base_url + "/filmler-1/"),
        ("Aksiyon", base_url + "/tur/aksiyon-fm1/film/"),
        ("Aile", base_url + "/tur/aile-fm1/film/"),
        ("Animasyon", base_url + "/tur/animasyon-fm2/film/"),
        ("Belgesel", base_url + "/tur/belgesel/film/"),
        ("Biyografi", base_url + "/tur/biyografi/film/"),
        ("Bilim Kurgu", base_url + "/tur/bilim-kurgu-fm3/film/"),
        ("Dram", base_url + "/tur/dram-fm1/film/"),
        ("Fantastik", base_url + "/tur/fantastik-fm1/film/"),
        ("Gerilim", base_url + "/tur/gerilim-fm1/film/"),
        ("Gizem", base_url + "/tur/gizem/film/"),
        ("Komedi", base_url + "/tur/komedi-fm1/film/"),
        ("Korku", base_url + "/tur/korku-fm1/film/"),
        ("Macera", base_url + "/tur/macera-fm1/film/"),
        ("Müzik", base_url + "/tur/muzik/film/"),
        ("Polisiye", base_url + "/tur/polisiye/film/"),
        ("Romantik", base_url + "/tur/romantik-fm1/film/"),
        ("Savaş", base_url + "/tur/savas-fm1/film/"),
        ("Spor", base_url + "/tur/spor/film/"),
        ("Tarih", base_url + "/tur/tarih/film/"),
        ("Western", base_url + "/tur/western-fm1/film/"),
        ("Netflix", base_url + "/kanal/netflix-fm1/"),
        ("Disney", base_url + "/kanal/disney-fm2/"),
        ("Amazon", base_url + "/kanal/amazon/"),
        ("Apple", base_url + "/kanal/apple/"),
        ("Hulu", base_url + "/kanal/hulu/"),
        ("Paramount", base_url + "/kanal/paramount/"),
        ("Hbo", base_url + "/kanal/hbo/"),
        ("Peacock", base_url + "/kanal/peacock/"),
    ]


def page_url(category_url, page_number):
    if int(page_number) <= 1:
        return _ensure_slash(category_url)
    return _ensure_slash(category_url.rstrip("/") + "/sayfa/{0}/".format(page_number))


def parse_page_items(page, base_url, category_title=""):
    items = []
    seen = set()
    for block in _item_blocks(page):
        anchor = _first(r"<a\b[^>]*>", block, re.S)
        href = _attr(anchor, "href")
        title = _clean(_first(r'<div[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</div>', block, re.S))
        image_tag = _first(r"<img\b[^>]*>", block, re.S)
        poster = _attr(image_tag, "data-src") or _attr(image_tag, "src")
        poster = poster.replace("liste", "detay") if poster else ""
        rating = _clean(_first(r'<div[^>]*class="[^"]*\brating\b[^"]*"[^>]*>(.*?)</div>', block, re.S))
        year = _clean(_first(r'<div[^>]*class="[^"]*\binfo\b[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>', block, re.S))
        if not title:
            title = _clean(_attr(anchor, "data-title"))
        if not title or not href:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        items.append({
            "category": category_title,
            "title": title,
            "url": url,
            "image": fix_url(poster, base_url) if poster else "",
            "rating": rating,
            "year": year,
            "plot": " ".join(x for x in [year, rating] if x),
        })
    return items


def parse_media_info(page, url, base_url):
    title = _clean(_first(r'<h1[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</h1>', page, re.S))
    cover = _first(r'<img[^>]*class="[^"]*\bcover-img\b[^"]*"[^>]*>', page, re.S)
    poster = _attr(cover, "src")
    picture = _first(r"<picture\b[^>]*>.*?</picture>", page, re.S)
    source_tag = _first(r"<source\b[^>]*>", picture, re.S)
    img_tag = _first(r"<img\b[^>]*>", picture, re.S)
    backdrop = _attr(source_tag, "srcset") or _attr(img_tag, "src")
    plot = _clean(_first(r'<div[^>]*class="[^"]*\binfo-description\b[^"]*"[^>]*>(.*?)</div>', page, re.S))
    rating = _clean(_first(r'<div[^>]*class="[^"]*\bimdb\b[^"]*"[^>]*>.*?<b[^>]*>(.*?)</b>', page, re.S))
    year = _clean(_first(r'<span[^>]*class="[^"]*\bdate\b[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', page, re.S))
    actors = ", ".join(_clean(x) for x in re.findall(r'<div[^>]*class="[^"]*\bcast-name\b[^"]*"[^>]*>(.*?)</div>', page, re.S))
    tags = ", ".join(_clean(x) for x in re.findall(r'<div[^>]*class="[^"]*\btype\b[^"]*"[^>]*>.*?<a[^>]*href="[^"]*/tur/[^"]*"[^>]*>(.*?)</a>', page, re.S))
    country = _clean(_first(r'<div[^>]*class="[^"]*\bcountry\b[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', page, re.S))
    duration = _first(r"(\d+)", _clean(_first(r'<div[^>]*class="[^"]*\btime\b[^"]*"[^>]*>(.*?)</div>', page, re.S)))
    sources = parse_video_sources(page, base_url)
    episodes = parse_episodes(page, base_url)
    related = parse_related(page, base_url)
    return {
        "title": title,
        "url": url,
        "image": fix_url(poster, base_url) if poster else "",
        "backdrop": fix_url(backdrop, base_url) if backdrop else "",
        "plot": plot,
        "rating": rating,
        "year": year,
        "actors": actors,
        "tags": tags,
        "country": country,
        "duration": duration or "0",
        "sources": sources,
        "episodes": episodes,
        "related": related,
    }


def parse_video_sources(page, base_url):
    sources = []
    trailer = _attr(_first(r'<a[^>]*class="[^"]*\btrailer-button\b[^"]*"[^>]*>', page, re.S), "data-video_url")
    if trailer:
        sources.append({"label": "Fragman", "url": fix_url(trailer, base_url), "is_trailer": True})
    for tag in re.findall(r'<a\b[^>]*data-video_url="[^"]+"[^>]*>.*?</a>', page, re.S):
        url = _attr(tag, "data-video_url")
        label = _clean(tag) or "Play"
        if url and "youtube" not in url.lower():
            sources.append({"label": label, "url": fix_url(url, base_url), "is_trailer": False})
    if len(sources) <= 1:
        iframe = _first(r'<iframe\b[^>]*(?:data-src|src)="[^"]+"[^>]*>', page, re.S)
        iframe_url = _attr(iframe, "data-src") or _attr(iframe, "src")
        if iframe_url and "youtube" not in iframe_url.lower():
            sources.append({"label": "Play", "url": fix_url(iframe_url, base_url), "is_trailer": False})
    return sources


def parse_episodes(page, base_url):
    episodes = []
    seen = set()
    for tag in re.findall(r'<a\b[^>]*href="[^"]+"[^>]*>.*?</a>', page, re.S):
        href = _attr(tag, "href")
        season = _first(r"(\d+)-sezon", href)
        episode = _first(r"(\d+)-bolum", href)
        if not season or not episode:
            continue
        key = (season, episode)
        if key in seen:
            continue
        seen.add(key)
        title = _clean(tag)
        if "Bölüm" in title:
            title = title.split("Bölüm")[-1].strip()
        episodes.append({"title": title or "{0}. Sezon {1}. Bölüm".format(season, episode), "url": fix_url(href, base_url), "season": season, "episode": episode})
    return sorted(episodes, key=lambda item: (int(item["season"]), int(item["episode"])))


def parse_related(page, base_url):
    related = []
    for block in _item_blocks(page):
        title = _clean(_first(r'<div[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</div>', block, re.S))
        anchor = _first(r'<a\b[^>]*class="[^"]*\bitem\b[^"]*"[^>]*>', block, re.S) or _first(r"<a\b[^>]*>", block, re.S)
        href = _attr(anchor, "href")
        image = _attr(_first(r"<img\b[^>]*>", block, re.S), "src")
        if title and href:
            related.append({"title": title, "url": fix_url(href, base_url), "image": fix_url(image, base_url) if image else ""})
    return related


def fix_url(url, base_url):
    if not url:
        return ""
    return urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())


def _item_blocks(page):
    starts = [match.start() for match in re.finditer(r'<div[^>]*class="[^"]*\bitem-relative\b[^"]*"[^>]*>', page or "", re.I)]
    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(page)
        blocks.append(page[start:end])
    return blocks


def _ensure_slash(url):
    return url if url.endswith("/") else url + "/"


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
