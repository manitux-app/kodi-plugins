# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import manituxhttp

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from . import parsers


class HDFilmCehennemiSite(object):
    
    def __init__(self, base_url, user_agent):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

        #headers = self.headers(ajax=True)
        # self.session = manituxhttp.Session(headers=new_headers, use_cloudscraper=True)
        self.session = manituxhttp.Session()
        
    def headers(self, referer=None, ajax=False):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if referer:
            headers["Referer"] = referer
        else:
            headers["Referer"] = self.base_url + "/"

        if ajax:
            headers["X-Requested-With"] = "fetch"
            # headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
            # headers["Content-Type"] = "application/json"
            # #headers["Origin"] = self.base_url
            # headers["Connection"] = "keep-alive"
            # headers["Sec-Fetch-Dest"] = "empty"
            # headers["Sec-Fetch-Mode"] = "cors"
            # headers["Sec-Fetch-Site"] = "same-origin"
            #h eaders.pop("Upgrade-Insecure-Requests", None)
        return headers
    
    def get_headers(self, referer=None, ajax=False):
        headers_dict = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive"
        }
        if referer:
            headers_dict["Referer"] = referer
        if ajax:
            headers_dict["Accept"] = "*/*"
            headers_dict["X-Requested-With"] = "XMLHttpRequest"
            headers_dict["Sec-Fetch-Dest"] = "empty"
            headers_dict["Sec-Fetch-Mode"] = "cors"
            headers_dict["Sec-Fetch-Site"] = "same-origin"
            if "Upgrade-Insecure-Requests" in headers_dict:
                del headers_dict["Upgrade-Insecure-Requests"]
                
        return headers_dict

    def get(self, url, referer=None, ajax=False):
        url = self.absolute(url)
        return self._get(url, headers=self.headers(referer, ajax=ajax)).text

    def categories(self):
        return parsers.categories(self.base_url)

    def page_url(self, category_url, page_number):
        return parsers.page_api_url(category_url, page_number)

    def get_page_items(self, category_url, page_number=1, title=""):
        api_url = self.page_url(category_url, page_number)
        page = self.get_ajax(api_url)
        print(page)
        html_block = parsers.html_from_load_response(page)
        return parsers.parse_page_items(html_block, self.base_url, title)

    def absolute(self, url):
        return parsers.fix_url(url, self.base_url)

    def search_url(self, query):
        return self.base_url + "/search/?q=" + urlparse.quote_plus(query)

    def search(self, query):
        res = self._get(
            self.search_url(query),
            headers=self.headers(referer=self.base_url + "/", ajax=True),
        )
        return parsers.parse_search_results(res.text, self.base_url)

    def parse_movies(self, page):
        return parsers.parse_page_items(page, self.base_url)

    def parse_next_page(self, page, current_url):
        return None

    def parse_detail(self, page, url):
        return parsers.parse_media_info(page, url, self.base_url)

    def fetch_source_iframe(self, video_id, referer):
        page = self.get_ajax(self.base_url + "/video/{0}/".format(video_id), referer=referer)
        return parsers.parse_iframe_from_video_response(page)

    def get_ajax(self, url, referer=None):
        url = self.absolute(url)
        try:
            return self._get(url, headers=self.headers(referer, ajax=True)).text
        except manituxhttp.HTTPError as exc:
            if getattr(exc.response, "status_code", None) != 403:
                raise
            self._prime_session()
            return self._get(url, headers=self.headers(self.base_url + "/", ajax=True)).text

    def _prime_session(self):
        try:
            self._get(self.base_url + "/", headers=self.headers(self.base_url + "/"))
        except Exception:
            pass

    def _get(self, url, headers):
        res = self.session.get(url, headers=headers, timeout=25)
        res.raise_for_status()
        return res
    
    def url_to_host(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        
        if ":" in host and not host.split(":")[-1].isdigit():
            host = host.split(":")[0]
            
        return host
