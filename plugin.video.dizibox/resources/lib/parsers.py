# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import html
import re

import manituxhttp

try:
    from urllib.parse import quote_plus, urlencode, urljoin, urlparse, parse_qsl, urlunparse
except ImportError:
    from urllib import quote_plus, urlencode
    from urlparse import urljoin, urlparse, parse_qsl, urlunparse


GENRE_NAMES = [
    "Aile",
    "Aksiyon",
    "Animasyon",
    "Avukat",
    "Belgesel",
    "Bilimkurgu",
    "Biyografi",
    "Casusluk",
    "Dram",
    "Drama",
    "Fantastik",
    "Gerilim",
    "Gizem",
    "Komedi",
    "Korku",
    "Macera",
    "Mahkeme",
    "Müzik",
    "Müzikal",
    "Polisiye",
    "Politika",
    "Reality TV",
    "Romantik",
    "Savaş",
    "Spor",
    "Suç",
    "Talk-Show",
    "Tarih",
    "Western",
    "Yarışma",
]

GENRE_SLUGS = {
    "Aile": "aile",
    "Aksiyon": "aksiyon",
    "Animasyon": "animasyon",
    "Avukat": "avukat",
    "Belgesel": "belgesel",
    "Bilimkurgu": "bilimkurgu",
    "Biyografi": "biyografi",
    "Casusluk": "casusluk",
    "Dram": "dram",
    "Drama": "drama",
    "Fantastik": "fantastik",
    "Gerilim": "gerilim",
    "Gizem": "gizem",
    "Komedi": "komedi",
    "Korku": "korku",
    "Macera": "macera",
    "Mahkeme": "mahkeme",
    "Müzik": "muzik",
    "Müzikal": "muzikal",
    "Polisiye": "polisiye",
    "Politika": "politika",
    "Reality TV": "reality-tv",
    "Romantik": "romantik",
    "Savaş": "savas",
    "Spor": "spor",
    "Suç": "suc",
    "Talk-Show": "talk-show",
    "Tarih": "tarih",
    "Western": "western",
    "Yarışma": "yarisma",
}


def parse_genres(page, base_url, archive_url):
    items = _parse_genres_with_soup(page, base_url, archive_url)
    if items:
        return items
    return _parse_genres_with_regex(page, base_url, archive_url)


def fallback_genres(base_url):
    archive_url = base_url.rstrip("/") + "/dizi-arsivi/"
    items = [("Yerli", _country_filter_url(archive_url, "turkiye"))]
    items.extend((name, _genre_filter_url(archive_url, name)) for name in GENRE_NAMES)
    return items


def page_url(category_url, page_number):
    page_number = int(page_number)
    if "SAYFA" in category_url:
        return category_url.replace("SAYFA", str(page_number))
    if page_number <= 1:
        return category_url
    if "[pageNumber]" in category_url:
        return category_url.replace("[pageNumber]", str(page_number))
    parsed = urlparse(category_url)
    query = dict(parse_qsl(parsed.query))
    query["sayfa"] = str(page_number)
    query["page"] = str(page_number)
    return urlunparse(parsed._replace(query=urlencode(query)))


def parse_page_items(page, base_url):
    soup = _soup(page)
    if soup is not None:
        items = _parse_page_items_with_soup(soup, base_url)
        if items:
            return items
    return _parse_page_items_with_regex(page, base_url)


def has_next_page(page, page_number):
    next_number = int(page_number) + 1
    if re.search(r">\s*{0}\s*<".format(next_number), page or ""):
        return True
    return bool(re.search(r">\s*(?:Sonraki|Son|→|&rarr;)", page or "", re.I))


def parse_detail(page, url, base_url):
    soup = _soup(page)
    title = ""
    poster = ""
    plot = ""
    year = ""
    rating = ""
    tags = []
    actors = []
    if soup is not None:
        h1 = soup.select_one("div.tv-overview h1 a") or soup.find("h1")
        title = _clean(h1.get_text(" ")) if h1 else ""
        image = soup.select_one("div.tv-overview figure img") or soup.find("img", attrs={"src": True})
        poster = fix_url((image.get("data-src") or image.get("src")) if image else "", base_url)
        desc = soup.select_one("div.tv-story p") or soup.find(attrs={"itemprop": "description"}) or soup.find("p")
        plot = _clean(desc.get_text(" ")) if desc else ""
        year_node = soup.select_one("a[href*='/yil/']")
        year = _clean(year_node.get_text(" ")) if year_node else ""
        rating_node = soup.select_one("span.label-imdb b")
        rating = _clean(rating_node.get_text(" ")) if rating_node else ""
        tags = [_clean(x.get_text(" ")) for x in soup.select("a[href*='/tur/']") if _clean(x.get_text(" "))]
        actors = [_clean(x.get_text(" ")) for x in soup.select("a[href*='/oyuncu/']") if _clean(x.get_text(" "))]
    if not title:
        title = _clean(_first(r"<h1[^>]*>(.*?)</h1>", page, re.S))
    if not poster:
        poster = fix_url(_attr(_first(r"<img\b[^>]*>", page, re.S), "src"), base_url)
    if not plot:
        plot = _clean(_first(r"<p[^>]*itemprop=['\"]description['\"][^>]*>(.*?)</p>", page, re.S))
    if not year:
        year = _first(r"\b(19\d{2}|20\d{2})\b", page)
    year = _first(r"\b(19\d{2}|20\d{2})\b", year) or year
    return {
        "title": title,
        "url": url,
        "image": poster,
        "backdrop": poster,
        "plot": plot,
        "year": year,
        "rating": rating,
        "tags": tags,
        "actors": actors,
        "season_links": parse_season_links(page, base_url),
        "episodes": parse_episodes(page, base_url),
        "sources": parse_video_sources(page, url, base_url),
    }


def parse_season_links(page, base_url):
    soup = _soup(page)
    if soup is None:
        return []
    links = []
    seen = set()
    for node in soup.select("div#seasons-list a[href]"):
        url = fix_url(node.get("href"), base_url)
        if not url or url in seen:
            continue
        seen.add(url)
        title = _clean(node.get_text(" ")) or "Sezon"
        links.append({"title": title, "url": url})
    return links


def parse_episodes(page, base_url):
    soup = _soup(page)
    if soup is not None:
        episodes = []
        seen = set()
        for article in soup.select("article.grid-box"):
            link = article.select_one("div.post-title a[href]") or article.find("a", href=True)
            if link is None:
                continue
            title = _clean(link.get_text(" ") or link.get("title") or "")
            url = fix_url(link.get("href"), base_url)
            if not title or not url or url in seen:
                continue
            seen.add(url)
            img = article.find("img")
            image = fix_url((img.get("data-src") or img.get("src")) if img else "", base_url)
            season, episode = parse_episode_numbers(title + " " + url)
            episodes.append({
                "title": title,
                "url": url,
                "image": image,
                "season": season,
                "episode": episode,
            })
        if episodes:
            return episodes

    episodes = []
    seen = set()
    for block in re.findall(r"<article\b[^>]*class=['\"][^'\"]*\bgrid-box\b[^'\"]*['\"][^>]*>.*?</article>", page or "", re.S | re.I):
        link = _first(r"<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>.*?</a>", block, re.S)
        href = _attr(link, "href")
        title = _clean(link)
        url = fix_url(href, base_url)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        season, episode = parse_episode_numbers(title + " " + url)
        episodes.append({"title": title, "url": url, "image": "", "season": season, "episode": episode})
    return episodes


def parse_episode_numbers(value):
    value = value or ""
    patterns = (
        r"(\d+)\.?\s*sezon.*?(\d+)\.?\s*b[oö]l[uü]m",
        r"(\d+)-sezon-(\d+)-bolum",
        r"(\d+)x(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, value, re.I)
        if match:
            return int(match.group(1)), int(match.group(2))
    return 0, 0


def parse_video_sources(page, page_url, base_url):
    soup = _soup(page)
    sources = []
    seen = set()

    def add(label, url, referer=None, is_trailer=False):
        fixed = fix_url(url, base_url)
        if not fixed or fixed in seen:
            return
        trailer = bool(is_trailer) or _is_youtube_url(fixed)
        seen.add(fixed)
        sources.append({
            "label": label or "DiziBox",
            "url": fixed,
            "referer": referer or page_url,
            "is_trailer": trailer,
        })

    if soup is not None:
        for node in soup.select("a[href*='youtube'], a[href*='youtu.be'], a[href*='fragman'], a[data-video_url]"):
            href = node.get("data-video_url") or node.get("href")
            add(_clean(node.get_text(" ")) or "Fragman", href, page_url, True)

        iframe = soup.select_one("div#video-area iframe[src]") or soup.select_one("iframe[src*='/player/']")
        if iframe is not None:
            selected = soup.select_one("div.video-toolbar option[selected]")
            label = _clean(selected.get_text(" ")) if selected else "DiziBox"
            add(label, iframe.get("src"), page_url)

        for option in soup.select("div.video-toolbar option[value]"):
            label = _clean(option.get_text(" ")) or "Alternatif"
            add(label, option.get("value"), page_url)

    if not sources:
        for iframe in re.findall(r"<iframe\b[^>]+src=['\"]([^'\"]+)['\"]", page or "", re.S | re.I):
            add("DiziBox", iframe, page_url)
    return sources


def parse_iframe(page, base_url):
    soup = _soup(page)
    if soup is not None:
        iframe = soup.select_one("div#video-area iframe[src]") or soup.select_one("div#Player iframe[src]") or soup.find("iframe", src=True)
        if iframe is not None:
            return fix_url(iframe.get("src"), base_url)
    return fix_url(_first(r"<iframe\b[^>]+src=['\"]([^'\"]+)['\"]", page, re.S), base_url)


def _is_youtube_url(url):
    return bool(re.search(r"(?:youtube\.com|youtu\.be)", url or "", re.I))


def fix_url(url, base_url):
    if not url:
        return ""
    return urljoin(base_url.rstrip("/") + "/", html.unescape(url).strip())


def _parse_genres_with_soup(page, base_url, archive_url):
    soup = _soup(page)
    if soup is None:
        return []

    genre_root = _find_heading_region(soup, "Tür", stop_texts=("Ülke", "Yapım Yılı", "IMDb", "FİLTRELEME"))
    candidates = genre_root.find_all(["a", "label", "input", "option"]) if genre_root is not None else []

    items = []
    seen = set()
    for node in candidates:
        text = _clean(node.get_text(" "))
        value = ""
        href = ""
        if getattr(node, "name", "") == "input":
            text = _clean(node.get("value") or node.get("data-title") or node.get("title") or "")
            value = node.get("value") or ""
            name = node.get("name") or ""
        else:
            input_node = node.find("input") if hasattr(node, "find") else None
            if input_node is not None:
                text = text or _clean(input_node.get("value") or "")
                value = input_node.get("value") or ""
                name = input_node.get("name") or ""
            else:
                name = node.get("name") or ""
        if getattr(node, "name", "") == "a":
            href = node.get("href") or ""
        if text not in GENRE_NAMES and text.title() not in GENRE_NAMES:
            continue
        title = _canonical_genre_name(text)
        if title in seen:
            continue
        seen.add(title)
        if href:
            url = fix_url(href, base_url)
        elif value and name:
            url = _genre_filter_url(archive_url, title, param=name, value=value)
        else:
            url = _genre_filter_url(archive_url, title)
        items.append((title, url))
    return items


def _parse_genres_with_regex(page, base_url, archive_url):
    block = _first(r"Tür\s*(.*?)(?:Ülke|Yapım Yılı|IMDb|FİLTRELEME)", _html_text_with_links(page), re.S | re.I)
    items = []
    seen = set()
    for name in GENRE_NAMES:
        if re.search(r"(?:^|\n)\s*{0}\s*(?:\n|$)".format(re.escape(name)), block or "", re.I):
            if name not in seen:
                seen.add(name)
                items.append((name, _genre_filter_url(archive_url, name)))
    return items


def _parse_page_items_with_soup(soup, base_url):
    detailed = _parse_detailed_articles(soup, base_url)
    if detailed:
        return detailed

    items = []
    seen = set()
    for link in soup.find_all("a", href=True):
        href = link.get("href") or ""
        if "/diziler/" not in href:
            continue
        title = _clean(link.get_text(" ") or link.get("title") or "")
        if not title:
            img = link.find("img")
            title = _clean((img.get("alt") if img else "") or "")
        title = _clean_title(title)
        if not title:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        img = link.find("img") or _near_image(link)
        image = fix_url((img.get("data-src") or img.get("src")) if img else "", base_url)
        plot = _near_plot(link)
        items.append({"title": title, "url": url, "image": image, "plot": plot})
    return items


def _parse_page_items_with_regex(page, base_url):
    items = []
    seen = set()
    for block in re.findall(r"<article\b[^>]*class=['\"][^'\"]*\bdetailed-article\b[^'\"]*['\"][^>]*>.*?</article>", page or "", re.S | re.I):
        link = _first(r"<h3[^>]*>.*?<a\b[^>]*href=['\"][^'\"]+['\"][^>]*>.*?</a>", block, re.S)
        href = _attr(link, "href")
        title = _clean_title(_clean(link))
        if not title or not href:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        image = fix_url(_attr(_first(r"<img\b[^>]*>", block, re.S), "data-src") or _attr(_first(r"<img\b[^>]*>", block, re.S), "src"), base_url)
        plot = _clean(re.sub(r".*?</h3>", "", block, flags=re.S | re.I))
        items.append({"title": title, "url": url, "image": image, "plot": plot})
    if items:
        return items

    items = []
    seen = set()
    for match in re.finditer(r"<a\b[^>]*href=['\"]([^'\"]*/diziler/[^'\"]+)['\"][^>]*>(.*?)</a>", page or "", re.S | re.I):
        url = fix_url(match.group(1), base_url)
        title = _clean_title(_clean(match.group(2)) or _attr(match.group(0), "title"))
        if not title or url in seen:
            continue
        seen.add(url)
        items.append({"title": title, "url": url, "image": "", "plot": ""})
    return items


def _genre_filter_url(archive_url, title, param="tur", value=None):
    slug = value or GENRE_SLUGS.get(title) or _slug(title)
    if param.startswith("tur"):
        return archive_url.rstrip("/") + "/page/SAYFA/?tur[0]={0}&yil&imdb".format(quote_plus(slug))
    return archive_url.rstrip("/") + "/page/SAYFA/?{0}={1}&yil&imdb".format(param, quote_plus(slug))


def _country_filter_url(archive_url, value):
    return archive_url.rstrip("/") + "/page/SAYFA/?ulke[]={0}&yil=&imdb".format(quote_plus(value))


def _parse_detailed_articles(soup, base_url):
    items = []
    seen = set()
    for article in soup.select("article.detailed-article"):
        link = article.select_one("h3 a[href]") or article.find("a", href=True)
        if link is None:
            continue
        title = _clean_title(link.get_text(" ") or link.get("title") or "")
        href = link.get("href") or ""
        if not title or not href:
            continue
        url = fix_url(href, base_url)
        if url in seen:
            continue
        seen.add(url)
        img = article.find("img")
        image = fix_url((img.get("data-src") or img.get("src")) if img else "", base_url)
        description = article.select_one("p")
        plot = _clean(description.get_text(" ")) if description else ""
        items.append({"title": title, "url": url, "image": image, "plot": plot})
    return items


def _slug(value):
    table = {
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
    text = "".join(table.get(ch, ch) for ch in value.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _soup(page):
    if manituxhttp.BeautifulSoup is None:
        return None
    return manituxhttp.BeautifulSoup(page or "", "html.parser")


def _find_heading_region(soup, text, stop_texts=()):
    marker = soup.find(string=lambda value: _clean(value) == text)
    if marker is None:
        return None
    wrapper = marker.parent
    while wrapper is not None and wrapper.name not in ("body", "form", "aside", "section", "div"):
        wrapper = wrapper.parent
    if wrapper is None:
        return None
    return wrapper


def _canonical_genre_name(text):
    for name in GENRE_NAMES:
        if name.lower() == text.lower():
            return name
    return text


def _near_image(link):
    parent = link.parent
    for _ in range(4):
        if parent is None:
            return None
        img = parent.find("img") if hasattr(parent, "find") else None
        if img is not None:
            return img
        parent = parent.parent
    return None


def _near_plot(link):
    parent = link.parent
    for _ in range(4):
        if parent is None:
            return ""
        text = _clean(parent.get_text(" ")) if hasattr(parent, "get_text") else ""
        if len(text) > 80:
            return text
        parent = parent.parent
    return ""


def _html_text_with_links(page):
    soup = _soup(page)
    if soup is not None:
        return soup.get_text("\n")
    return _clean(page).replace(" * ", "\n")


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


def _clean_title(value):
    value = _clean(value)
    value = re.sub(r"\s+izle\s*$", "", value, flags=re.I).strip()
    return value


def _clean(text):
    text = re.sub(r"<script.*?</script>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
