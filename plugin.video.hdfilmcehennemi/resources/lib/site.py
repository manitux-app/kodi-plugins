# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import html
import re

import tlsclient

try:
    from urllib.parse import quote_plus, urljoin
except ImportError:
    from urllib import quote_plus
    from urlparse import urljoin


class HDFilmCehennemiSite(object):
    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = tlsclient.Session()

    def headers(self, referer=None, ajax=False):
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if referer:
            headers["Referer"] = referer
        if ajax:
            headers["X-Requested-With"] = "fetch"
            headers["Content-Type"] = "application/json"
        return headers

    def get(self, url, referer=None):
        url = self.absolute(url)
        res = self.session.get(url, headers=self.headers(referer), timeout=25)
        res.raise_for_status()
        return res.text

    def absolute(self, url):
        return urljoin(self.base_url + "/", url)

    def search_url(self, query):
        return self.base_url + "/arama/" + quote_plus(query).replace("+", "-") + "/"

    def parse_movies(self, page):
        items = []
        seen = set()
        for match in re.finditer(r'<a\s+[^>]*class="[^"]*\bposter\b[^"]*"[^>]*>.*?</a>', page, re.S | re.I):
            block = match.group(0)
            href = self._first(r'href="([^"]+)"', block)
            if not href or href in seen:
                continue
            seen.add(href)
            title = self._first(r'<strong[^>]*class="poster-title"[^>]*>(.*?)</strong>', block)
            if not title:
                title = self._first(r'title="([^"]+)"', block)
            image = self._first(r'<img[^>]+(?:data-src|src)="([^"]+)"', block)
            if image and image.startswith("data:image"):
                image = self._first(r'srcset="([^",\s]+)', block)
            meta = self._clean(" ".join(re.findall(r'<span[^>]*>(.*?)</span>', block, re.S)))
            lang = self._clean(self._first(r'<span[^>]*class="poster-lang"[^>]*>(.*?)</span>', block, re.S))
            items.append({
                "title": self._clean(title),
                "url": self.absolute(href),
                "image": self.absolute(image) if image else "",
                "plot": " ".join(x for x in [meta, lang] if x),
            })
        return items

    def parse_next_page(self, page, current_url):
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S | re.I)
        candidates = []
        for href, text in links:
            text = self._clean(text).lower()
            if "sonraki" in text or "daha fazla" in text:
                candidates.append(href)
        numbered = re.findall(r'href="([^"]*(?:page|sayfa)/(\d+)/?[^"]*)"', page, re.I)
        if numbered:
            current_page = self._page_no(current_url)
            bigger = [(int(num), href) for href, num in numbered if int(num) > current_page]
            if bigger:
                return self.absolute(sorted(bigger)[0][1])
        if candidates:
            return self.absolute(candidates[0])
        return None

    def parse_detail(self, page, url):
        title = self._first(r'<h1[^>]*>(.*?)</h1>', page) or self._first(r'<title>(.*?)</title>', page)
        image = self._first(r'<img[^>]+src="([^"]+)"[^>]+alt="[^"]*izle"', page)
        plot = self._first(r'<article[^>]*class="post-info-content"[^>]*>\s*<p>(.*?)</p>', page, re.S)
        sources = []
        for block in re.findall(r'<button[^>]+class="[^"]*alternative-link[^"]*"[^>]*>.*?</button>', page, re.S | re.I):
            video_id = self._first(r'data-video="([^"]+)"', block)
            label = self._clean(block)
            if video_id:
                sources.append({"label": label or video_id, "video_id": video_id, "url": url})
        iframe = self._first(r'<iframe[^>]+(?:data-src|src)="([^"]+)"', page)
        return {
            "title": self._clean(title),
            "image": self.absolute(image) if image else "",
            "plot": self._clean(plot),
            "sources": sources,
            "iframe": iframe,
        }

    def fetch_source_iframe(self, video_id, referer):
        res = self.session.get(
            self.base_url + "/video/{0}/".format(video_id),
            headers=self.headers(referer=referer, ajax=True),
            timeout=25,
        )
        res.raise_for_status()
        data = res.json()
        html_block = data.get("data", {}).get("html", "") if isinstance(data, dict) else ""
        return self._first(r'<iframe[^>]+(?:data-src|src)="([^"]+)"', html_block)

    @staticmethod
    def _page_no(url):
        match = re.search(r'/(?:page|sayfa)/(\d+)/?', url)
        return int(match.group(1)) if match else 1

    @staticmethod
    def _first(pattern, text, flags=0):
        if not text:
            return ""
        match = re.search(pattern, text, flags | re.I)
        return match.group(1) if match else ""

    @staticmethod
    def _clean(text):
        text = re.sub(r'<svg.*?</svg>', ' ', text or '', flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        return re.sub(r'\s+', ' ', text).strip()
