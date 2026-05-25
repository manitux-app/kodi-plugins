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
        ("4K", base_url + "/film-tur/4k-film-izle?page=[pageNumber]"),
        ("Aile", base_url + "/film-tur/aile-filmleri?page=[pageNumber]"),
        ("Aksiyon", base_url + "/film-tur/aksiyon?page=[pageNumber]"),
        ("Animasyon", base_url + "/film-tur/animasyon?page=[pageNumber]"),
        ("Belgesel", base_url + "/film-tur/belgeseller?page=[pageNumber]"),
        ("Bilim-Kurgu", base_url + "/film-tur/bilim-kurgu-filmleri?page=[pageNumber]"),
        ("Dram", base_url + "/film-tur/dram-filmleri?page=[pageNumber]"),
        ("Fantastik", base_url + "/film-tur/fantastik-filmler?page=[pageNumber]"),
        ("Gerilim", base_url + "/film-tur/gerilim?page=[pageNumber]"),
        ("Gizem", base_url + "/film-tur/gizem-filmleri?page=[pageNumber]"),
        ("Hint Filmleri", base_url + "/film-tur/hd-hint-filmleri?page=[pageNumber]"),
        ("Kısa Film", base_url + "/film-tur/kisa-film?page=[pageNumber]"),
        ("Komedi", base_url + "/film-tur/hd-komedi-filmleri?page=[pageNumber]"),
        ("Korku", base_url + "/film-tur/korku-filmleri?page=[pageNumber]"),
        ("Kült Filmler", base_url + "/film-tur/kult-filmler-izle?page=[pageNumber]"),
        ("Macera", base_url + "/film-tur/macera-filmleri?page=[pageNumber]"),
        ("Müzik", base_url + "/film-tur/muzik?page=[pageNumber]"),
        ("Oscar Ödüllü Filmler", base_url + "/film-tur/odullu-filmler-izle?page=[pageNumber]"),
        ("Romantik", base_url + "/film-tur/romantik-filmler?page=[pageNumber]"),
        ("Savaş", base_url + "/film-tur/savas-filmleri?page=[pageNumber]"),
        ("Stand Up", base_url + "/film-tur/stand-up?page=[pageNumber]"),
        ("Suç", base_url + "/film-tur/suc-filmleri?page=[pageNumber]"),
        ("Tarih", base_url + "/film-tur/tarih?page=[pageNumber]"),
        ("Tavsiye Filmler", base_url + "/film-tur/tavsiye-filmler?page=[pageNumber]"),
        ("TV film", base_url + "/film-tur/tv-film?page=[pageNumber]"),
        ("Vahşi Batı", base_url + "/film-tur/vahsi-bati-filmleri?page=[pageNumber]"),
    ]


def page_url(category_url, page_number):
    return category_url.replace("[pageNumber]", str(page_number))


def parse_page_items(page, base_url, category_title=""):
    items = []
    seen = set()
    for block in re.findall(r'<div\b[^>]*class=["\'][^"\']*\bmovie\b[^"\']*["\'][^>]*>.*?(?=<div\b[^>]*class=["\'][^"\']*\bmovie\b|$)', page or "", re.S | re.I):
        anchor = _first(r"<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>", block, re.S)
        href = _attr(anchor, "href")
        title = _clean(anchor) or _attr(anchor, "title") or _attr(_first(r"<img\b[^>]*>", block, re.S), "alt")
        poster = _poster_from(block, base_url)
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
            "image": poster,
            "plot": "",
        })
    return items


def parse_media_info(page, url, base_url):
    title = _clean(_first(r'<div[^>]*class=["\'][^"\']*\btitles\b[^"\']*["\'][^>]*>.*?<h1[^>]*>(.*?)</h1>', page, re.S))
    alt_title = _clean(_first(r'<div[^>]*class=["\'][^"\']*\btitles\b[^"\']*["\'][^>]*>.*?<h2[^>]*>(.*?)</h2>', page, re.S))
    poster = fix_url(_attr(_first(r"<img\b[^>]*class=['\"][^'\"]*\bimg-responsive\b[^'\"]*['\"][^>]*>", page, re.S), "src"), base_url)
    backdrop = fix_url(_attr(_first(r'<div[^>]*class=["\'][^"\']*\bembed-responsive\b[^"\']*["\'][^>]*>.*?<div\b[^>]*poster=["\'][^"\']+["\'][^>]*>', page, re.S), "poster"), base_url)
    plot = _clean(_first(r"<p\b[^>]*itemprop=['\"]description['\"][^>]*>(.*?)</p>", page, re.S))
    rating = _clean(_first(r"<span\b[^>]*itemprop=['\"]ratingValue['\"][^>]*>(.*?)</span>", page, re.S))
    year = _first(r"\b(\d{4})\b", _clean(_first(r"<span\b[^>]*itemprop=['\"]dateCreated['\"][^>]*>(.*?)</span>", page, re.S)))
    actors = ", ".join(dict.fromkeys(_clean(x) for x in re.findall(r"<a\b[^>]*itemprop=['\"]actor['\"][^>]*>.*?<span[^>]*>(.*?)</span>", page, re.S) if _clean(x)))
    tags = ", ".join(dict.fromkeys(_clean(x) for x in re.findall(r"<a\b[^>]*href=['\"][^'\"]*film-tur/[^'\"]*['\"][^>]*>(.*?)</a>", page, re.S) if _clean(x)))
    trailer = _youtube_from_page(page)
    source_pages = []
    for tag in re.findall(r'<div\b[^>]*class=["\'][^"\']*\balternates\b[^"\']*["\'][^>]*>.*?</div>', page or "", re.S | re.I):
        for link in re.findall(r'<a\b[^>]*href=["\'][^"\']+["\'][^>]*>.*?</a>', tag, re.S | re.I):
            href = _attr(link, "href")
            label = _clean(link) or "Play"
            if href and "fragman" not in label.lower():
                source_pages.append({"label": label, "url": fix_url(href, base_url)})
    sources = []
    if trailer:
        sources.append({"label": "Fragman", "url": trailer, "referer": url, "is_trailer": True})
    return {
        "title": title or alt_title,
        "url": url,
        "image": poster,
        "backdrop": backdrop or poster,
        "plot": plot,
        "rating": rating,
        "year": year,
        "actors": actors,
        "tags": tags,
        "sources": sources,
        "source_pages": source_pages,
    }


def parse_video_config(page):
    video_id = _first(r"var\s+videoId\s*=\s*['\"]([^'\"]*)", page)
    video_type = _first(r"var\s+videoType\s*=\s*['\"]([^'\"]*)", page)
    return video_id, video_type


def parse_source_response(payload, label, base_url, referer=None):
    try:
        data = json.loads(payload)
    except Exception:
        data = {}
    subtitle = fix_url(data.get("subtitle") or "", base_url)
    sources = []
    for item in data.get("sources", []) if isinstance(data, dict) else []:
        src = item.get("src") or item.get("file") or ""
        quality = item.get("label") or item.get("quality") or ""
        if not src:
            continue
        name = " | ".join(x for x in (label, quality) if x)
        sources.append({
            "label": name or label,
            "url": fix_url(src, base_url),
            "referer": referer or base_url,
            "subtitle": subtitle,
            "is_trailer": False,
        })
    return sources


def fix_url(url, base_url):
    if not url:
        return ""
    value = urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())
    return value.replace("https://www.filmmodu.one", base_url.rstrip("/")).replace("http://www.filmmodu.one", base_url.rstrip("/"))


def _poster_from(block, base_url):
    img = _first(r"<picture\b[^>]*>.*?<img\b[^>]*>", block or "", re.S) or _first(r"<img\b[^>]*>", block or "", re.S)
    poster = _attr(img, "data-src") or _attr(img, "src")
    if poster and not poster.lower().startswith("data:image"):
        return fix_url(poster, base_url)
    return ""


def _youtube_from_page(page):
    for pattern in (
        r"(?:youtube\.com/embed/|youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})",
        r"data-trailer=['\"]([A-Za-z0-9_-]{6,})",
    ):
        match = re.search(pattern, page or "", re.I)
        if match:
            return "https://youtube.com/embed/" + match.group(1)
    return ""


def _clean_title(value):
    return re.sub(r"\s+izle\s*$", "", _clean(value), flags=re.I).strip()


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
