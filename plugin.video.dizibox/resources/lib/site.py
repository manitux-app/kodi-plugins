# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import time
import re

import manituxhttp
try:
    from urllib.parse import quote_plus, urlparse
except ImportError:
    from urllib import quote_plus
    from urlparse import urlparse

from .extractor import DiziBoxExtractor
from . import parsers


class DiziBoxSite(object):
    ARCHIVE_PATH = "/dizi-arsivi/"

    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = manituxhttp.Session()
        self.extractor = DiziBoxExtractor(user_agent, self.base_url)

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": "isTrustedUser=true; dbxu={0}".format(int(time.time() * 1000)),
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def get(self, url, referer=None):
        res = self.session.get(self.absolute(url), headers=self.headers(referer), timeout=25, allow_redirects=True)
        res.raise_for_status()
        return res.text

    def categories(self):
        return parsers.fallback_genres(self.base_url)

    def get_page_items(self, category_url, page_number=1):
        url = parsers.page_url(category_url, page_number)
        page = self.get(url, referer=self.base_url + self.ARCHIVE_PATH)
        return parsers.parse_page_items(page, self.base_url), parsers.has_next_page(page, page_number)

    def search(self, query):
        page = self.get(self.base_url + "/?s=" + quote_plus(query), referer=self.base_url + "/")
        return parsers.parse_page_items(page, self.base_url), parsers.has_next_page(page, 1)

    def detail(self, url):
        page = self.get(url)
        info = parsers.parse_detail(page, url, self.base_url)
        info["episodes"] = self.sort_episodes(info.get("episodes") or [])
        if not self.is_episode_url(url):
            info["sources"] = [source for source in info.get("sources", []) if source.get("is_trailer")]
        return info

    def parse_detail(self, page, url):
        return parsers.parse_detail(page, url, self.base_url)

    def load_episodes(self, season_links, referer=None):
        episodes = []
        seen = set()
        for season in season_links:
            season_url = season.get("url")
            if not season_url:
                continue
            try:
                page = self.get(season_url, referer=referer or self.base_url)
            except Exception:
                continue
            for episode in parsers.parse_episodes(page, self.base_url):
                episode_url = episode.get("url")
                if not episode_url or episode_url in seen:
                    continue
                seen.add(episode_url)
                episodes.append(episode)
        return episodes

    def fetch_iframe(self, url, referer=None):
        page = self.get(url, referer=referer)
        iframe = parsers.parse_iframe(page, self.base_url)
        if iframe:
            return iframe
        detail = parsers.parse_detail(page, url, self.base_url)
        sources = [source for source in detail.get("sources", []) if not source.get("is_trailer")]
        return sources[0]["url"] if sources else ""

    def resolve_source(self, url, referer=None, label=""):
        target = self.absolute(url)
        if self.is_site_page(target):
            iframe = self.fetch_iframe(target, referer=referer)
            if iframe:
                return self.extractor.resolve(iframe, target, label)
        return self.extractor.resolve(target, referer, label)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def is_site_page(self, url):
        host = urlparse(url or "").netloc.lower()
        base_host = urlparse(self.base_url).netloc.lower()
        return host == base_host and "/player/" not in (url or "")

    @staticmethod
    def is_episode_url(url):
        return bool(re.search(r"(?:\d+-sezon-\d+-bolum|\d+x\d+|bolum(?:-|$))", url or "", re.I))

    @staticmethod
    def sort_episodes(episodes):
        return sorted(
            episodes or [],
            key=lambda item: (
                item.get("season") or 0,
                item.get("episode") or 0,
                item.get("title") or "",
            ),
        )
