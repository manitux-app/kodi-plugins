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
        ("Yeni Eklenen Filmler", base_url + "/load/page/[pageNumber]/home/"),
        ("Yeni Eklenen Diziler", base_url + "/load/page/[pageNumber]/home-series/"),
        ("Türkçe Dublaj Filmler", base_url + "/load/page/[pageNumber]/languages/turkce-dublajli-film-izleyin-5/"),
        ("Türkçe Altyazılı Filmler", base_url + "/load/page/[pageNumber]/languages/turkce-altyazili-filmleri-izleme-sitesi-3/"),
        ("Aile Filmleri", base_url + "/tur/aile-filmleri-izleyin-7"),
        ("Aksiyon Filmleri", base_url + "/tur/aksiyon-filmleri-izleyin-7"),
        ("Animasyon Filmleri", base_url + "/tur/animasyon-filmlerini-izleyin-5"),
        ("Belgesel Filmleri", base_url + "/tur/belgesel-filmlerini-izle-2"),
        ("Bilim Kurgu Filmleri", base_url + "/tur/bilim-kurgu-filmlerini-izleyin-5"),
        ("Biyografi Filmleri", base_url + "/tur/biyografi-filmleri-izle-3"),
        ("Dram Filmleri", base_url + "/tur/dram-filmlerini-izle-2"),
        ("Fantastik Filmleri", base_url + "/tur/fantastik-filmlerini-izleyin-3"),
        ("Gerilim Filmleri", base_url + "/tur/gerilim-filmlerini-izle-2"),
        ("Gizem Filmleri", base_url + "/tur/gizem-filmleri-izle-3"),
        ("Komedi Filmleri", base_url + "/tur/komedi-filmlerini-izleyin-2"),
        ("Korku Filmleri", base_url + "/tur/korku-filmlerini-izle-5"),
        ("Macera Filmleri", base_url + "/tur/macera-filmlerini-izleyin-4"),
        ("Romantik Filmleri", base_url + "/tur/romantik-filmleri-izle-3"),
        ("Savaş Filmleri", base_url + "/tur/savas-filmleri-izle-5"),
        ("Spor Filmleri", base_url + "/tur/spor-filmleri-izle-3"),
        ("Suç Filmleri", base_url + "/tur/suc-filmleri-izle-3"),
        ("Tarih Filmleri", base_url + "/tur/tarih-filmleri-izle-5"),
        ("Western Filmleri", base_url + "/tur/western-filmleri-izle-3"),
    ]


def page_api_url(category_url, page_number):
    url = category_url
    if "/tur/" in url:
        url = url.replace("/tur/", "/load/page/[pageNumber]/genres/")
    return url.replace("[pageNumber]", str(page_number))


def html_from_load_response(payload):
    try:
        data = json.loads(payload)
    except Exception:
        return payload
    return data.get("html", "") if isinstance(data, dict) else ""


def parse_page_items(fragment, base_url, category_title=""):
    items = []
    seen = set()
    for block in _poster_blocks(fragment):
        href = _attr(block, "href")
        title = _clean(_first(r'<strong[^>]*class="[^"]*\bposter-title\b[^"]*"[^>]*>(.*?)</strong>', block, re.S))
        poster = _attr(_first(r"<img\b[^>]*>", block, re.S), "data-src") or _attr(_first(r"<img\b[^>]*>", block, re.S), "src")
        year = _clean(_first(r'<div[^>]*class="[^"]*\bposter-info\b[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>', block, re.S))
        rating = _clean(_first(r'<span[^>]*class="[^"]*\bimdb\b[^"]*"[^>]*>(.*?)</span>', block, re.S))

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


def parse_search_results(payload, base_url):
    items = []
    try:
        data = json.loads(payload)
    except Exception:
        data = {}
    for raw_html in data.get("results", []) if isinstance(data, dict) else []:
        title = _clean(_first(r'<h4[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</h4>', raw_html, re.S))
        anchor = _first(r"<a\b[^>]*>", raw_html, re.S)
        href = _attr(anchor, "href")
        image_tag = _first(r"<img\b[^>]*>", raw_html, re.S)
        poster = _attr(image_tag, "data-src") or _attr(image_tag, "src")
        if title and href:
            image = fix_url(poster, base_url).replace("/thumb/", "/list/") if poster else ""
            items.append({"title": title, "url": fix_url(href, base_url), "image": image, "plot": ""})
    return items


def parse_media_info(page, url, base_url):
    title = _clean(_first(r'<h1[^>]*class="[^"]*\bsection-title\b[^"]*"[^>]*>(.*?)</h1>', page, re.S))
    poster_block = _first(r'<aside[^>]*class="[^"]*\bpost-info-poster\b[^"]*"[^>]*>.*?</aside>', page, re.S)
    poster_tag = _first(r"<img\b[^>]*>", poster_block, re.S)
    poster = _attr(poster_tag, "data-src") or _attr(poster_tag, "src")
    backdrop = _extract_backdrop(page)
    plot = _clean(_first(r'<article[^>]*class="[^"]*\bpost-info-content\b[^"]*"[^>]*>\s*<p[^>]*>(.*?)</p>', page, re.S))
    tags = ", ".join(_clean(x) for x in re.findall(r'<div[^>]*class="[^"]*\bpost-info-genres\b[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', page, re.S))
    rating = _clean(_first(r'<div[^>]*class="[^"]*\bpost-info-imdb-rating\b[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>', page, re.S)).split("(")[0].strip()
    year_country = _first(r'<div[^>]*class="[^"]*\bpost-info-year-country\b[^"]*"[^>]*>(.*?)</div>', page, re.S)
    year = _clean(_first(r"<a[^>]*>(.*?)</a>", year_country, re.S))
    country = _clean(_first(r'<a[^>]*href="[^"]*/ulke/[^"]*"[^>]*>(.*?)</a>', year_country, re.S))
    actors = ", ".join(_clean(x) for x in re.findall(r'<div[^>]*class="[^"]*\bpost-info-cast\b[^"]*"[^>]*>.*?<a[^>]*>\s*<strong[^>]*>(.*?)</strong>', page, re.S))
    duration = _first(r'<div[^>]*class="[^"]*\bpost-info-duration\b[^"]*"[^>]*>(.*?)</div>', page, re.S)
    duration = _first(r"(\d+)", _clean(duration))

    episodes = parse_episodes(page, base_url)
    related = parse_related(page, base_url)
    sources = parse_video_sources(page, base_url)
    trailer = _first(r'data-modal="trailer/([^"]+)"', page)
    if trailer and trailer != "0":
        sources.insert(0, {"label": "Fragman", "url": "https://www.youtube.com/embed/" + trailer, "video_id": "", "is_trailer": True})

    if not backdrop or backdrop.startswith("data:image"):
        backdrop = poster

    return {
        "title": title,
        "url": url,
        "image": fix_url(poster, base_url) if poster else "",
        "backdrop": fix_url(backdrop, base_url) if backdrop else "",
        "plot": plot,
        "tags": tags,
        "rating": rating,
        "year": year,
        "country": country,
        "actors": actors,
        "duration": duration,
        "sources": sources,
        "episodes": episodes,
        "related": related,
    }


def parse_episodes(page, base_url):
    episodes = []
    seen = set()
    for block in re.findall(r'<a\b[^>]*class="[^"]*\bmini-poster\b[^"]*"[^>]*>.*?</a>', page or "", re.S | re.I):
        title = _clean(_first(r"<h4[^>]*>(.*?)</h4>", block, re.S))
        href = _attr(block, "href")
        if not href or not re.search(r"/sezon-\d+/bolum-\d+/", href, re.I):
            continue
        season = _first(r"(\d+)\.?\s*Sezon", title, re.I) or _first(r"/sezon-(\d+)/", href, re.I) or "1"
        episode = _first(r"(\d+)\.?\s*B[oö]l[uü]m", title, re.I) or _first(r"/bolum-(\d+)/", href, re.I) or "1"
        key = (season, episode)
        if key in seen:
            continue
        seen.add(key)
        episodes.append({
            "title": title or "{0}. Sezon {1}. Bolum".format(season, episode),
            "url": fix_url(href, base_url),
            "season": season,
            "episode": episode,
        })
    return sorted(episodes, key=lambda item: (int(item["season"]), int(item["episode"])))


def parse_related(page, base_url):
    related = []
    for block in re.findall(r'<div[^>]*class="[^"]*\bslider-slide\b[^"]*"[^>]*>.*?</div>', page, re.S):
        title = _clean(_first(r'<strong[^>]*class="[^"]*\bposter-title\b[^"]*"[^>]*>(.*?)</strong>', block, re.S))
        href = _attr(_first(r"<a\b[^>]*>", block, re.S), "href")
        img = _first(r"<img\b[^>]*>", block, re.S)
        poster = _attr(img, "data-src") or (_attr(img, "data-srcset").split("1x")[0].strip() if _attr(img, "data-srcset") else "") or _attr(img, "src")
        if title and href:
            related.append({"title": title, "url": fix_url(href, base_url), "image": fix_url(poster, base_url) if poster else ""})
    return related


def parse_video_sources(page, base_url):
    sources = []
    seen_video_ids = set()
    language_labels = {}
    for button in re.findall(r'<button\b[^>]*class="[^"]*\blanguage-link\b[^"]*"[^>]*>.*?</button>', page, re.S):
        lang = (_attr(button, "data-lang") or "").lower()
        label = _clean(button)
        if lang:
            language_labels[lang] = "DUAL" if "dual" in label.lower() else label

    for group in re.findall(r'<div\b[^>]*class="[^"]*\balternative-links\b[^"]*"[^>]*>.*?</div>', page, re.S):
        lang_code = (_attr(group, "data-lang") or "").lower()
        lang_label = language_labels.get(lang_code, lang_code.upper())
        for button in re.findall(r'<button\b[^>]*class="[^"]*\balternative-link\b[^"]*"[^>]*>.*?</button>', group, re.S):
            video_id = _attr(button, "data-video")
            source_text = _clean(button).replace("(HDrip Xbet)", "").strip()
            label = " | ".join(x for x in [lang_label, source_text] if x).strip(" |")
            if video_id and video_id not in seen_video_ids:
                seen_video_ids.add(video_id)
                sources.append({
                    "label": label or video_id,
                    "video_id": video_id,
                    "url": base_url.rstrip("/") + "/video/{0}/".format(video_id),
                    "is_trailer": False,
                })
    if len([x for x in sources if not x.get("is_trailer")]) <= 1:
        sources = sources[:1] if sources and sources[0].get("is_trailer") else []
        seen_video_ids = set()
        for match in re.finditer(r'<button\b[^>]*class=["\'][^"\']*\balternative-link\b[^"\']*["\'][^>]*>.*?</button>', page or "", re.S | re.I):
            button = match.group(0)
            video_id = _attr(button, "data-video")
            if not video_id or video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)
            lang_code = _nearest_language_code(page, match.start())
            lang_label = language_labels.get(lang_code, lang_code.upper())
            source_text = _clean(button).replace("(HDrip Xbet)", "").strip()
            label = " | ".join(x for x in [lang_label, source_text] if x).strip(" |")
            sources.append({
                "label": label or video_id,
                "video_id": video_id,
                "url": base_url.rstrip("/") + "/video/{0}/".format(video_id),
                "is_trailer": False,
            })
    return sources


def _nearest_language_code(page, position):
    before = (page or "")[:position]
    matches = list(re.finditer(r'<div\b[^>]*class=["\'][^"\']*\balternative-links\b[^"\']*["\'][^>]*\bdata-lang=["\']([^"\']+)["\']', before, re.I))
    return matches[-1].group(1).lower() if matches else ""


def parse_iframe_from_video_response(payload):
    try:
        data = json.loads(payload)
        html_block = data.get("data", {}).get("html", "") if isinstance(data, dict) else ""
    except Exception:
        html_block = payload or ""
    iframe = _first(r'<iframe[^>]+(?:data-src|src)="([^"]+)"', html_block)
    return iframe.replace("\\/", "/") if iframe else ""


def fix_url(url, base_url):
    if not url:
        return ""
    return urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())


def _poster_blocks(fragment):
    return re.findall(r'<a\s+[^>]*class="[^"]*\bposter\b[^"]*"[^>]*>.*?</a>', fragment or "", re.S | re.I)


def _extract_backdrop(page):
    block = _first(r'<div[^>]*class="[^"]*\bplay-that-video\b[^"]*"[^>]*>.*?</div>', page, re.S)
    img = _first(r"<img\b[^>]*>", block, re.S)
    value = _attr(img, "data-src") or _attr(img, "srcset") or _attr(img, "src")
    if "1x," in value:
        match = re.search(r"1x,\s*(https?://\S+)", value)
        if match:
            value = match.group(1)
    return value


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
