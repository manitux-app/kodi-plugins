# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json
import re

import manituxhttp

try:
    from urllib.parse import quote, urljoin, urlparse
except ImportError:
    from urllib import quote
    from urlparse import urljoin, urlparse

from . import parsers


class DiziPalExtractor(object):
    CLIENT_IDENTIFIERS = ("cloudscraper", "chrome_144")

    def __init__(self, user_agent, main_url):
        self.user_agent = user_agent
        self.main_url = main_url.rstrip("/")
        self.session = manituxhttp.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def resolve(self, url, referer=None, label=""):
        if not url:
            return None, []
        url = self.normalize_url(url)
        page = self.fetch(url, referer or self.main_url + "/")
        iframe = parsers.parse_iframe(page, self.main_url)
        if not iframe:
            source, subs = self.extract_jwplayer(page, self.origin(url))
            return (source + self.kodi_headers(url) if source else None), subs

        iframe = self.normalize_url(iframe)
        if self.is_youtube(iframe):
            return iframe + self.kodi_headers(referer), []
        if "videoseyred" in urlparse(iframe).netloc.lower():
            return self.resolve_videoseyred(iframe)

        iframe_page = self.fetch(iframe, self.main_url + "/")
        source = self.resolve_fetch_stream(iframe_page, iframe)
        if not source:
            source = self._first(r"""file\s*:\s*["']([^"']+)""", iframe_page)
        if not source:
            source, subs = self.extract_jwplayer(iframe_page, self.origin(iframe))
        else:
            subs = self.parse_subtitles(iframe_page)
        if not source:
            source = self._first(r"""https?://[^\s"'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>]*)?""", iframe_page)
        return (self.normalize_url(source) + self.kodi_headers(iframe, {"Origin": self.origin(iframe)}) if source else None), subs

    def resolve_fetch_stream(self, page, iframe_url):
        path = ""
        for candidate in re.findall(r"""fetch\(\s*["']([^"']+)["']""", page or "", re.I):
            if "/dl?op=get_stream" in candidate:
                path = candidate
                break
        if not path:
            return ""
        stream_api = urljoin(self.origin(iframe_url) + "/", path.replace("\\/", "/"))
        data = self.fetch_stream_json(stream_api, iframe_url, page)
        return (data.get("url") or "").replace("\\/", "/") if isinstance(data, dict) else ""

    def fetch_stream_json(self, url, referer, page):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Referer": referer,
            "Origin": self.origin(referer),
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }
        cookies = self.parse_js_cookies(page)
        if cookies:
            headers["Cookie"] = cookies
        last_error = None
        for identifier in ("chrome_144", "cloudscraper"):
            try:
                res = self.session.get(
                    url,
                    headers=headers,
                    timeout=25,
                    allow_redirects=True,
                    tls_client_identifier=identifier,
                )
                res.raise_for_status()
                data = json.loads(res.text)
                if data.get("url"):
                    return data
                last_error = manituxhttp.HTTPError(res)
            except (ValueError, manituxhttp.HTTPError, manituxhttp.RequestError) as exc:
                last_error = exc
        if last_error:
            raise last_error
        return {}

    @staticmethod
    def parse_js_cookies(page):
        cookies = []
        for name, value in re.findall(r"""\$\.cookie\(["']([^"']+)["']\s*,\s*["']([^"']+)""", page or "", re.I):
            cookies.append("{0}={1}".format(name, value))
        return "; ".join(cookies)

    def resolve_videoseyred(self, url):
        video_id = self._first(r"/embed/([^/?#]+)", url)
        if not video_id:
            return None, []
        playlist_url = self.origin(url) + "/playlist/" + video_id + ".json"
        payload = self.fetch(playlist_url, self.origin(url) + "/")
        try:
            playlist = json.loads(payload)
        except Exception:
            playlist = []
        item = playlist[0] if playlist else {}
        sources = item.get("sources") or []
        source = ""
        for candidate in sources:
            source = candidate.get("file") or ""
            if source:
                break
        subtitles = []
        for track in item.get("tracks") or []:
            if (track.get("kind") or "").lower() == "captions" and track.get("file"):
                subtitles.append(urljoin(self.origin(url) + "/", track["file"]))
        return (source + self.kodi_headers(self.origin(url) + "/") if source else None), subtitles

    def extract_jwplayer(self, page, base_url):
        source = ""
        subs = []
        for raw in re.findall(r"""["']?sources["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(raw):
                source = item.get("file") or ""
                if source:
                    source = urljoin(base_url.rstrip("/") + "/", source.replace("\\/", "/"))
                    break
            if source:
                break
        for raw in re.findall(r"""["']?tracks["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(raw):
                kind = (item.get("kind") or "").lower()
                file_url = item.get("file")
                if file_url and ("caption" in kind or "subtitle" in kind):
                    subs.append(urljoin(base_url.rstrip("/") + "/", file_url.replace("\\/", "/")))
        return source, list(dict.fromkeys(subs))

    def parse_subtitles(self, page):
        subtitles = []
        raw = self._first(r'"subtitle"\s*:\s*"([^"]+)"', page)
        for item in [x.strip() for x in raw.split(",") if x.strip()]:
            url = re.sub(r"\[[^\]]+\]", "", item).strip()
            if url:
                subtitles.append(self.normalize_url(url))
        if subtitles:
            return subtitles
        for subtitle in re.findall(r"""["']file["']\s*:\s*["']([^"']+)["'][^{}]+["']kind["']\s*:\s*["']captions["']""", page or "", re.S | re.I):
            subtitles.append(self.normalize_url(subtitle.replace("\\/", "/")))
        return list(dict.fromkeys(subtitles))

    def fetch(self, url, referer=None):
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = manituxhttp.Session(client_identifier=identifier)
            try:
                res = self.session.get(
                    url,
                    headers=self.headers(referer),
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

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def kodi_headers(self, referer=None, extra=None):
        bits = ["User-Agent=" + quote(self.user_agent)]
        if referer:
            bits.append("Referer=" + quote(referer))
        if extra:
            bits.extend("{0}={1}".format(key, quote(value)) for key, value in extra.items() if value)
        return "|" + "&".join(bits)

    def normalize_url(self, url):
        if not url:
            return ""
        url = url.replace("\\/", "/").replace("\\u0026", "&")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("www."):
            return "https://" + url
        if not url.startswith(("http://", "https://")):
            return urljoin(self.main_url + "/", url)
        return url

    @staticmethod
    def is_youtube(url):
        host = urlparse(url or "").netloc.lower()
        return "youtube" in host or "youtu.be" in host

    @staticmethod
    def origin(url):
        parsed = urlparse(url)
        return parsed.scheme + "://" + parsed.netloc

    @staticmethod
    def _parse_js_list(value):
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
                    item[key] = DiziPalExtractor._first(r"""["']?%s["']?\s*:\s*["']([^"']+)""" % key, block)
                items.append(item)
            return items

    @staticmethod
    def _first(pattern, text, flags=0):
        match = re.search(pattern, text or "", flags | re.I)
        if not match:
            return ""
        return match.group(1) if match.lastindex else match.group(0)
