# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import tlsclient

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import parsers


class FilmEkseniSite(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = tlsclient.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def headers(self, referer=None, ajax=False):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

    def post(self, url, data, referer=None):
        return self._post(self.absolute(url), data, self.headers(referer, ajax=True)).text

    def get_page_items(self, category_url, page_number=1, title=""):
        page = self.get(parsers.page_url(category_url, page_number), referer=category_url)
        return parsers.parse_page_items(page, self.base_url, title)

    def search(self, query):
        payload = self.post(self.base_url + "/search/", {"query": query}, referer=self.base_url + "/")
        return parsers.parse_search_results(payload, self.base_url)

    def parse_detail(self, page, url):
        return parsers.parse_media_info(page, url, self.base_url)

    def fetch_iframe(self, source_url, referer=None):
        page = self.get(source_url, referer=referer or self.base_url + "/")
        return parsers.parse_iframe(page, self.base_url)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def search_url(self, query):
        return self.base_url + "/search/?q=" + quote_plus(query)

    def _get(self, url, headers):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = tlsclient.Session(client_identifier=identifier)
            try:
                res = self.session.get(url, headers=headers, timeout=25, tls_client_identifier=identifier)
                if res.status_code in (403, 429) and identifier != self.CLIENT_IDENTIFIERS[-1]:
                    last_error = tlsclient.HTTPError(res)
                    continue
                res.raise_for_status()
                return res
            except (tlsclient.HTTPError, tlsclient.RequestError) as exc:
                last_error = exc
                if identifier == self.CLIENT_IDENTIFIERS[-1]:
                    raise
        raise last_error

    def _post(self, url, data, headers):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = tlsclient.Session(client_identifier=identifier)
            try:
                res = self.session.post(url, data=data, headers=headers, timeout=25, tls_client_identifier=identifier)
                if res.status_code in (403, 429) and identifier != self.CLIENT_IDENTIFIERS[-1]:
                    last_error = tlsclient.HTTPError(res)
                    continue
                res.raise_for_status()
                return res
            except (tlsclient.HTTPError, tlsclient.RequestError) as exc:
                last_error = exc
                if identifier == self.CLIENT_IDENTIFIERS[-1]:
                    raise
        raise last_error
