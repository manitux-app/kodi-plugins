# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import manituxhttp

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import parsers


class FilmModuSite(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = manituxhttp.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def categories(self):
        return parsers.categories(self.base_url)

    def get_page_items(self, category_url, page_number=1, title=""):
        page = self.get(parsers.page_url(category_url, page_number), referer=category_url)
        return parsers.parse_page_items(page, self.base_url, title)

    def search(self, query):
        page = self.get(self.base_url + "/?s=" + quote_plus(query), referer=self.base_url + "/")
        return parsers.parse_page_items(page, self.base_url, "Arama")

    def get(self, url, referer=None):
        return self._get(self.absolute(url), self.headers(referer)).text

    def parse_detail(self, page, url):
        info = parsers.parse_media_info(page, url, self.base_url)
        info["sources"] = info.get("sources", []) + self.resolve_sources(info.get("source_pages", []), url)
        return info

    def resolve_sources(self, source_pages, referer):
        sources = []
        for item in source_pages:
            alt_page = self.get(item["url"], referer=referer)
            video_id, video_type = parsers.parse_video_config(alt_page)
            if not video_id or not video_type:
                continue
            payload = self.get(
                self.base_url + "/get-source?movie_id={0}&type={1}".format(video_id, video_type),
                referer=item["url"],
            )
            sources.extend(parsers.parse_source_response(payload, item["label"], self.base_url, item["url"]))
        return sources

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

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
