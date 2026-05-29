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
        ("Aile", base_url + "/kategori/aile/page/"),
        ("Aksiyon", base_url + "/kategori/aksiyon/page/"),
        ("Animasyon", base_url + "/kategori/animasyon/page/"),
        ("Belgesel", base_url + "/kategori/belgesel/page/"),
        ("Bilim Kurgu", base_url + "/kategori/bilim-kurgu/page/"),
        ("Dram", base_url + "/kategori/dram/page/"),
        ("Fantastik", base_url + "/kategori/fantastik/page/"),
        ("Gerilim", base_url + "/kategori/gerilim/page/"),
        ("Gizem", base_url + "/kategori/gizem/page/"),
        ("Komedi", base_url + "/kategori/komedi/page/"),
        ("Korku", base_url + "/kategori/korku/page/"),
        ("Macera", base_url + "/kategori/macera/page/"),
        ("Muzik", base_url + "/kategori/muzik/page/"),
        ("Romantik", base_url + "/kategori/romantik/page/"),
        ("Savas", base_url + "/kategori/savas/page/"),
        ("Suc", base_url + "/kategori/suc/page/"),
        ("Tarih", base_url + "/kategori/tarih/page/"),
        ("Vahsi Bati", base_url + "/kategori/vahsi-bati/page/"),
        ("Yerli", base_url + "/kategori/yerli/page/"),
    ]


def page_url(category_url, page_number):
    if int(page_number) <= 1:
        return category_url if not category_url.endswith("/page/") else category_url + "1/"
    return category_url.rstrip("/") + "/" + str(page_number) + "/" if category_url.endswith("/page/") else category_url.rstrip("/") + "/page/{0}/".format(page_number)


def parse_page_items(page, base_url, category_title=""):
    items = []
    seen = set()
    for block in _post_blocks(page):
        anchor = _first(r"<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>", block, re.S)
        href = _attr(anchor, "href")
        title = _clean(_attr(anchor, "title") or _attr(_first(r"<img\b[^>]*>", block, re.S), "alt"))
        poster = _poster_from(block, base_url)
        if not title or not href:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        items.append({
            "category": category_title,
            "title": clean_title(title),
            "url": url,
            "image": poster,
            "plot": "",
        })
    return items


def parse_media_info(page, url, base_url):
    title = clean_title(
        _clean(_first(r"<main\b[^>]*>.*?<h1[^>]*>(.*?)</h1>", page, re.S))
        or _clean(_first(r"<body\b[^>]*>.*?<h1[^>]*>(.*?)</h1>", page, re.S))
        or _meta(page, "property", "og:title")
    )
    poster = _meta(page, "property", "og:image") or _poster_from(page, base_url)
    plot = _meta(page, "property", "og:description") or _meta(page, "name", "description")
    year = _first(r"\b(\d{4})\b", _detail_value(page, "Yapım Yılı"))
    rating = _detail_value(page, "IMDB Puanı")
    duration = parse_duration(_detail_value(page, "Süre"))
    episodes = parse_episodes(page, base_url)
    sources = parse_video_sources(page, url, base_url, bool(episodes))
    trailer = find_trailer_url(page, base_url)
    if trailer:
        sources.insert(0, {"label": "Fragman", "url": trailer, "referer": url, "is_trailer": True})
    return {
        "title": title,
        "url": url,
        "image": fix_url(poster, base_url) if poster else "",
        "plot": _clean(plot),
        "year": year,
        "rating": rating,
        "duration": duration,
        "tags": _meta_list(page, "Tür"),
        "actors": _meta_list(page, "Oyuncular"),
        "sources": sources,
        "episodes": episodes,
    }


def parse_video_sources(page, page_url, base_url, has_episodes=False):
    if has_episodes:
        return []
    if "/dizi/" in (page_url or "").lower() and "/bolum/" not in (page_url or "").lower():
        return []
    return [{"label": "Oynat", "url": page_url, "referer": base_url.rstrip("/") + "/", "is_trailer": False}]


def parse_episodes(page, base_url):
    episodes = []
    seen = set()
    for block in re.findall(r'<div\b[^>]*class=["\'][^"\']*\bepisode-item\b[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*\bepisode-item\b|$)', page or "", re.S | re.I):
        anchor = _first(r"<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>", block, re.S)
        href = _attr(anchor, "href")
        if not href:
            continue
        title_attr = _attr(anchor, "title")
        img_alt = _attr(_first(r"<img\b[^>]*>", block, re.S), "alt")
        title = _clean(_first(r"<h4\b[^>]*>.*?<a\b[^>]*>(.*?)</a>", block, re.S)) or img_alt or title_attr
        season = _first(r"(\d+)\.\s*Sezon", title_attr) or _first(r"/sezon-?(\d+)", href) or "0"
        episode = _first(r"(\d+)\.\s*B[öo]l[üu]m", title_attr) or _first(r"/bolum-?(\d+)", href) or "0"
        key = (season, episode, href)
        if key in seen:
            continue
        seen.add(key)
        episodes.append({
            "title": title or "{0}. Sezon {1}. Bolum".format(season, episode),
            "url": fix_url(href, base_url),
            "image": _poster_from(block, base_url),
            "season": season,
            "episode": episode,
        })
    return episodes


def find_trailer_url(page, base_url):
    source = _first(r'<div\b[^>]*id=["\']trailer-iframe-source["\'][^>]*>', page or "", re.S)
    iframe_html = _attr(source, "data-iframe")
    trailer = _attr(_first(r"<iframe\b[^>]*(?:src|data-src)=['\"][^'\"]+['\"][^>]*>", iframe_html, re.S), "data-src")
    trailer = trailer or _attr(_first(r"<iframe\b[^>]*(?:src|data-src)=['\"][^'\"]+['\"][^>]*>", iframe_html, re.S), "src")
    if trailer:
        return fix_url(trailer, base_url)

    iframe = _first(r'<iframe\b[^>]*(?:src|data-src)=["\'][^"\']*(?:youtube|youtu\.be)[^"\']+["\'][^>]*>', page or "", re.S)
    trailer = _attr(iframe, "data-src") or _attr(iframe, "src")
    if trailer:
        return fix_url(trailer, base_url)

    tag = _first(r"<a\b[^>]*(?:href|data-video_url)=['\"][^'\"]*(?:youtube|youtu\.be|fragman)[^'\"]*['\"][^>]*>", page or "", re.S)
    value = _attr(tag, "data-video_url") or _attr(tag, "href")
    return fix_url(value, base_url) if value else ""


def parse_iframe(page, base_url):
    iframe = (
        _first(r'<[^>]*class=["\'][^"\']*\bseries-player-container\b[^"\']*["\'][^>]*>.*?<iframe\b[^>]*(?:src|data-src)=["\'][^"\']+["\'][^>]*>', page or "", re.S)
        or _first(r'<div[^>]*id=["\']vast_new["\'][^>]*>.*?<iframe\b[^>]*(?:src|data-src)=["\'][^"\']+["\'][^>]*>', page or "", re.S)
        or _first(r'<[^>]*class=["\'][^"\']*\bvideo-player-area\b[^"\']*["\'][^>]*>.*?<iframe\b[^>]*(?:src|data-src)=["\'][^"\']+["\'][^>]*>', page or "", re.S)
        or _first(r'<[^>]*class=["\'][^"\']*\bresponsive-player\b[^"\']*["\'][^>]*>.*?<iframe\b[^>]*(?:src|data-src)=["\'][^"\']+["\'][^>]*>', page or "", re.S)
        or _first(r"<iframe\b[^>]*(?:src|data-src)=['\"][^'\"]+['\"][^>]*>", page or "", re.S)
    )
    return fix_url(_attr(iframe, "data-src") or _attr(iframe, "src"), base_url)


def fix_url(url, base_url):
    if not url:
        return ""
    return urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())


def clean_title(value):
    value = _clean(value)
    value = re.sub(r"\s+izle\s*-\s*Dizipal\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+-\s*Dizipal\s*$", "", value, flags=re.I)
    return value.strip()


def parse_duration(value):
    total = 0
    hours = _first(r"(\d+)\s*s", value)
    minutes = _first(r"(\d+)\s*dk", value)
    if hours:
        total += int(hours) * 60
    if minutes:
        total += int(minutes)
    if total:
        return str(total)
    return _first(r"(\d+)", value)


def _post_blocks(page):
    return re.findall(r'<div\b[^>]*class=["\'][^"\']*\bpost-item\b[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*\bpost-item\b|$)', page or "", re.S | re.I)


def _poster_from(block, base_url):
    img = _first(r"<img\b[^>]*>", block or "", re.S)
    poster = _attr(img, "data-src") or _attr(img, "src")
    return fix_url(poster, base_url) if poster and not poster.lower().startswith("data:image") else ""


def _detail_value(page, label):
    for match in re.finditer(r"<span\b[^>]*>(.*?)</span>(?P<tail>.{0,400})", page or "", re.S | re.I):
        if _clean(match.group(1)).lower() == label.lower():
            return _clean(match.group("tail").split("</", 1)[0])
    return ""


def _meta_list(page, label):
    value = _detail_value(page, label)
    return re.sub(r"^{0}\s*".format(re.escape(label)), "", value, flags=re.I).strip()


def _meta(page, attr_name, attr_value):
    pattern = r'<meta\b[^>]*\b{0}=["\']{1}["\'][^>]*>'.format(re.escape(attr_name), re.escape(attr_value))
    tag = _first(pattern, page or "", re.S)
    return _attr(tag, "content")


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
    text = re.sub(r"<script.*?</script>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<svg.*?</svg>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
