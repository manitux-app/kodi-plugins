# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import tlsclient

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import parsers


class HDFilmCehennemiSite(object):
    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.session = tlsclient.Session()

    def headers(self, referer=None, ajax=False):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
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

    def categories(self):
        return parsers.categories(self.base_url)

    def page_url(self, category_url, page_number):
        return parsers.page_api_url(category_url, page_number)

    def get_page_items(self, category_url, page_number=1, title=""):
        api_url = self.page_url(category_url, page_number)
        page = self.get(api_url, referer=category_url)
        html_block = parsers.html_from_load_response(page)
        return parsers.parse_page_items(html_block, self.base_url, title)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def search_url(self, query):
        return self.base_url + "/search/?q=" + quote_plus(query)

    def search(self, query):
        res = self.session.get(
            self.search_url(query),
            headers=self.headers(referer=self.base_url + "/", ajax=True),
            timeout=25,
        )
        res.raise_for_status()
        return parsers.parse_search_results(res.text, self.base_url)

    def parse_movies(self, page):
        return parsers.parse_page_items(page, self.base_url)

    def parse_next_page(self, page, current_url):
        return None

    def parse_detail(self, page, url):
        return parsers.parse_media_info(page, url, self.base_url)

    def fetch_source_iframe(self, video_id, referer):
        res = self.session.get(
            self.base_url + "/video/{0}/".format(video_id),
            headers=self.headers(referer=referer, ajax=True),
            timeout=25,
        )
        res.raise_for_status()
        return parsers.parse_iframe_from_video_response(res.text)
