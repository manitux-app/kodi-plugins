# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json
import re
import string

import manituxhttp

try:
    from urllib.parse import quote, urljoin, urlparse
except ImportError:
    from urllib import quote
    from urlparse import urljoin, urlparse


class VideoExtractor(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, user_agent, main_url):
        self.user_agent = user_agent
        self.main_url = main_url.rstrip("/")
        self.session = manituxhttp.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def resolve(self, url, referer=None, label=""):
        if not url:
            return None, []
        url = self.normalize_url(url)
        host = urlparse(url).netloc.lower()
        if "youtube" in host or "youtu.be" in host:
            return url + self.kodi_headers(referer), []
        if "eksenload" in host:
            return self.resolve_eksenload(url, referer, label)
        if "vidmoly" in host or "videobin" in host:
            return self.resolve_vidmoly(url, referer)
        if "ok.ru" in host or "odnoklassniki" in host:
            return self.resolve_okru(url)
        if "streamtape" in host or "watchadsontape" in host or "shavetape" in host:
            return self.resolve_streamtape(url, referer)
        page = self.fetch(url, referer)
        source, subs = self.extract_jwplayer(page, self.origin(url))
        if source:
            return source + self.kodi_headers(url), subs
        direct = self._first(r"""https?://[^\s"'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>]*)?""", page)
        return (direct + self.kodi_headers(url) if direct else url + self.kodi_headers(referer)), []

    def resolve_eksenload(self, url, referer=None, label=""):
        page = self.fetch(url, referer, origin=self.main_url)
        origin = self.origin(url)
        headers = {"User-Agent": self.user_agent, "Origin": origin}
        source, subs = self.extract_jwplayer(page, origin, headers)
        if not source:
            video_id = url.rstrip("/").split("/")[-1]
            if video_id:
                source = origin + "/uploads/encode/" + video_id + "/master.m3u8"
        if not source:
            return None, subs
        return source + self.kodi_headers(url, headers), subs

    def resolve_vidmoly(self, url, referer=None):
        url = self.normalize_url(url)
        candidates = [url]
        match = re.search(r"/w/([a-z0-9]+)/*$", url, re.I)
        if match:
            candidates.insert(0, re.sub(r"/w/([a-z0-9]+)/*$", r"/embed-\1.html", url, flags=re.I))
        html = ""
        page_url = url
        for candidate in candidates:
            html = self.fetch(candidate, referer)
            page_url = candidate
            if ".m3u8" in html or "sources" in html or "jwplayer" in html:
                break
        source, subs = self.extract_jwplayer(html, self.origin(page_url), {"User-Agent": self.user_agent})
        if not source:
            source = self._first(r"""https?://[^\s"'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>]*)?""", html)
        return (source + self.kodi_headers(page_url) if source else None), subs

    def resolve_okru(self, url):
        url = self.normalize_url(url)
        video_id = self._first(r"(?:videoembed/|video/|mid=)(\d+)", url)
        if not video_id:
            return url + self.kodi_headers("https://ok.ru/"), []
        res = self.session.post(
            "https://www.ok.ru/dk",
            data={"cmd": "videoPlayerMetadata", "mid": video_id},
            headers=self.headers("https://ok.ru/"),
            timeout=25,
        )
        res.raise_for_status()
        data = res.text.replace("\\u0026", "&").replace("\\/", "/")
        source = self._first(r'"(?:ondemandHls|ondemandDash)"\s*:\s*"([^"]+)"', data)
        if not source:
            source = self._first(r'"(?:name|quality)"\s*:\s*"(?:ultra|quad|full|hd|sd|low|mobile)"[^{}]*"url"\s*:\s*"([^"]+)"', data, re.S)
        return (source + self.kodi_headers("https://ok.ru/") if source else None), []

    def resolve_streamtape(self, url, referer=None):
        page = self.fetch(url, referer)
        line = ""
        for candidate in page.splitlines():
            if "botlink').innerHTML" in candidate or 'botlink").innerHTML' in candidate:
                line = candidate
                break
        literals = re.findall(r"""['"]([^'"]*)['"]""", line)
        parts = [x for x in literals if "/" in x or "&" in x or "=" in x]
        source = "".join(parts)
        if source.startswith("//"):
            source = "https:" + source
        if source:
            source += "&stream=1"
        return (source + self.kodi_headers(url) if source else None), []

    def extract_jwplayer(self, page, base_url, headers=None):
        source = ""
        subs = []
        for raw in re.findall(r"""["']?sources["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(raw):
                url = item.get("file")
                if url:
                    source = urljoin(base_url.rstrip("/") + "/", url.replace("\\/", "/"))
                    break
            if source:
                break
        if not source:
            match = re.search(r"""[:=]\s*["']([^"'\s]+(?:\.m3u8|master\.txt)[^"'\s]*)""", page or "", re.S | re.I)
            if match:
                source = urljoin(base_url.rstrip("/") + "/", match.group(1).replace("\\/", "/"))
        for raw in re.findall(r"""["']?tracks["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(raw):
                kind = (item.get("kind") or "").lower()
                file_url = item.get("file")
                if file_url and ("caption" in kind or "subtitle" in kind):
                    subs.append(urljoin(base_url.rstrip("/") + "/", file_url.replace("\\/", "/")))
        return source, list(dict.fromkeys(subs))

    def _parse_js_list(self, value):
        normalized = value.replace("\\/", "/")
        normalized = re.sub(r"([{,]\s*)(file|label|type|kind)\s*:", r'\1"\2":', normalized)
        normalized = normalized.replace("'", '"')
        normalized = re.sub(r",\s*([\]}])", r"\1", normalized)
        try:
            data = json.loads(normalized)
            return data if isinstance(data, list) else []
        except Exception:
            items = []
            for block in re.findall(r"\{(.*?)\}", value, re.S):
                item = {}
                for key in ("file", "label", "type", "kind"):
                    item[key] = self._first(r"""["']?%s["']?\s*:\s*["']([^"']+)""" % key, block)
                items.append(item)
            return items

    def fetch(self, url, referer=None, origin=None):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = manituxhttp.Session(client_identifier=identifier)
            try:
                res = self.session.get(
                    url,
                    headers=self.headers(referer, origin),
                    timeout=25,
                    allow_redirects=True,
                    tls_client_identifier=identifier,
                )
                if res.status_code in (403, 429) and identifier != self.CLIENT_IDENTIFIERS[-1]:
                    last_error = manituxhttp.HTTPError(res)
                    continue
                res.raise_for_status()
                return res.text
            except (manituxhttp.HTTPError, manituxhttp.RequestError) as exc:
                last_error = exc
                if identifier == self.CLIENT_IDENTIFIERS[-1]:
                    raise
        raise last_error

    def headers(self, referer=None, origin=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin
        return headers

    def kodi_headers(self, referer=None, extra=None):
        headers = {"User-Agent": self.user_agent}
        if referer:
            headers["Referer"] = referer
        if extra:
            headers.update(extra)
        return "|" + "&".join("{0}={1}".format(key, quote(value)) for key, value in headers.items() if value)

    def normalize_url(self, url):
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("www."):
            return "https://" + url
        if not url.startswith(("http://", "https://")):
            return urljoin(self.main_url + "/", url)
        return url

    def origin(self, url):
        parsed = urlparse(url)
        return parsed.scheme + "://" + parsed.netloc

    @staticmethod
    def _first(pattern, text, flags=0):
        match = re.search(pattern, text or "", flags | re.I)
        if not match:
            return ""
        return match.group(1) if match.lastindex else match.group(0)
