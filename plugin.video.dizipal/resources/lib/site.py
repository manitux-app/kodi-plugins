# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import manituxhttp

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from .extractor import DiziPalExtractor
from . import parsers


class DiziPalSite(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = manituxhttp.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])
        self.extractor = DiziPalExtractor(user_agent, self.base_url)

    def headers(self, referer=None, ajax=False):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if referer:
            headers["Referer"] = referer
        if ajax:
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Origin"] = self.base_url
        return headers

    def categories(self):
        return parsers.categories(self.base_url)

    def get(self, url, referer=None):
        return self._get(self.absolute(url), self.headers(referer)).text

    def get_page_items(self, category_url, page_number=1):
        page = self.get(parsers.page_url(category_url, page_number), referer=self.base_url + "/")
        return parsers.parse_page_items(page, self.base_url)

    def search(self, query):
        page = self.get(self.search_url(query), referer=self.base_url + "/")
        return parsers.parse_page_items(page, self.base_url, "Arama")

    def detail(self, url):
        page = self.get(url, referer=self.base_url + "/")
        info = parsers.parse_media_info(page, url, self.base_url)
        info["episodes"] = self.sort_episodes(info.get("episodes") or [])
        if self.is_series_page(url) and not self.is_episode_page(url):
            info["sources"] = [source for source in info.get("sources", []) if source.get("is_trailer")]
        return info

    def resolve_source(self, url, referer=None, label=""):
        return self.extractor.resolve(self.absolute(url), referer or self.base_url + "/", label)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def search_url(self, query):
        return self.base_url + "/?s=" + quote_plus(query)

    @staticmethod
    def is_series_page(url):
        return "/dizi/" in (url or "").lower()

    @staticmethod
    def is_episode_page(url):
        lowered = (url or "").lower()
        return "/bolum/" in lowered or "/sezon" in lowered

    @staticmethod
    def sort_episodes(episodes):
        return sorted(
            episodes or [],
            key=lambda item: (
                int(item.get("season") or 0),
                int(item.get("episode") or 0),
                item.get("title") or "",
            ),
        )

    def _get(self, url, headers):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = manituxhttp.Session(client_identifier=identifier)
            try:
                res = self.session.get(
                    url,
                    headers=headers,
                    timeout=25,
                    allow_redirects=True,
                    tls_client_identifier=identifier,
                )
                if res.status_code in (403, 429) and identifier != self.CLIENT_IDENTIFIERS[-1]:
                    last_error = manituxhttp.HTTPError(res)
                    continue
                res.raise_for_status()
                return res
            except (manituxhttp.HTTPError, manituxhttp.RequestError) as exc:
                last_error = exc
                if identifier == self.CLIENT_IDENTIFIERS[-1]:
                    raise
        raise last_error
