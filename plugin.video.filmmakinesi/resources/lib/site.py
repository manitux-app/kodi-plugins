# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import manituxhttp

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import parsers


class FilmMakinesiSite(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = manituxhttp.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def categories(self):
        return parsers.categories(self.base_url)

    def page_url(self, category_url, page_number):
        return parsers.page_url(category_url, page_number)

    def get(self, url, referer=None):
        return self._get(self.absolute(url), self.headers(referer)).text

    def get_page_items(self, category_url, page_number=1, title=""):
        url = self.page_url(category_url, page_number)
        page = self.get(url, referer=category_url)
        return parsers.parse_page_items(page, self.base_url, title)

    def search(self, query):
        page = self.get(self.base_url + "/arama/?s=" + quote_plus(query), referer=self.base_url + "/")
        return parsers.parse_page_items(page, self.base_url, "Arama")

    def parse_detail(self, page, url):
        return parsers.parse_media_info(page, url, self.base_url)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def _get(self, url, headers):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = manituxhttp.Session(client_identifier=identifier)
            try:
                res = self.session.get(url, headers=headers, timeout=25, tls_client_identifier=identifier)
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
