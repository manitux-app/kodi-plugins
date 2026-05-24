# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import base64
import json
import re

import tlsclient

try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse


class VideoExtractor(object):
    def __init__(self, user_agent):
        self.user_agent = user_agent
        self.session = tlsclient.Session()

    def headers(self, referer=None):
        headers = {"User-Agent": self.user_agent}
        if referer:
            headers["Referer"] = referer
        return headers

    def resolve(self, url, referer=None):
        if not url:
            return None, []
        url = self.normalize_url(url)
        if "hdfilmcehennemi" in url or "playmix" in url:
            return self.resolve_hdfilm_embed(url, referer)
        if "vidmoly" in url or "flmplayer" in url:
            return self.resolve_vidmoly(url)
        if "odnoklassniki" in url or "ok.ru" in url:
            return self.resolve_okru(url)
        return url + self.kodi_headers(referer), []

    def resolve_hdfilm_embed(self, url, referer=None):
        page = self.fetch(url, referer)
        source = self._first(r'"contentUrl"\s*:\s*"([^"]+)"', page)
        if not source:
            source = self._decode_obfuscated_source(page)
        if not source:
            iframe = self._first(r'<iframe[^>]+(?:src|data-src)="([^"]+)"', page)
            if iframe:
                return self.resolve(iframe, url)
        subtitles = []
        for track in re.findall(r'\{[^{}]*"file"\s*:\s*"([^"]+)"[^{}]*"kind"\s*:\s*"captions"[^{}]*\}', page):
            subtitles.append(track.replace("\\/", "/"))
        return source + self.kodi_headers(url), subtitles

    def resolve_vidmoly(self, url):
        url = self.normalize_url(url).replace(".top", ".to")
        page = self.fetch(url, "https://vidmoly.to/")
        redirect = self._first(r"window\.location\s*=\s*'([^']+)'", page)
        if redirect:
            page = self.fetch(url.replace("embed-", redirect), url)
        source = self._first(r"([^'\"\s]+\.m3u8[^'\"\s]*)", page)
        subtitles = re.findall(r"file\s*:\s*'([^']+/srt[^']*)'", page)
        return source + self.kodi_headers("https://vidmoly.to/"), subtitles

    def resolve_okru(self, url):
        url = self.normalize_url(url)
        video_id = self._first(r'(?:videoembed/|mid=)(\d+)', url)
        if not video_id:
            return url + self.kodi_headers("https://ok.ru/"), []
        res = self.session.post(
            "https://www.ok.ru/dk",
            data={"cmd": "videoPlayerMetadata", "mid": video_id},
            headers=self.headers("https://ok.ru/"),
            timeout=25,
        )
        res.raise_for_status()
        data = res.text
        source = self._first(r'(?:ultra|quad|full|hd|sd|low|lowest)","url":"(.*?)"', data)
        return source.replace(r"\u0026", "&") + self.kodi_headers("https://ok.ru/"), []

    def fetch(self, url, referer=None):
        res = self.session.get(url, headers=self.headers(referer), timeout=25, allow_redirects=True)
        res.raise_for_status()
        return res.text

    def normalize_url(self, url):
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("www."):
            url = "https://" + url
        elif not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        return urlunparse(parsed._replace(scheme="https"))

    def kodi_headers(self, referer=None):
        bits = ["User-Agent=" + self.user_agent]
        if referer:
            bits.append("Referer=" + referer)
        return "|" + "&".join(bits)

    def _decode_obfuscated_source(self, page):
        match = re.search(r'var\s+(s_[A-Za-z0-9_]+)\s*=\s*(dc_[A-Za-z0-9_]+)\((\[.*?\])\)', page, re.S)
        if not match:
            return ""
        parts = json.loads(match.group(3).replace("\\/", "/"))
        value = "".join(parts)
        value = self._rot13(value)[::-1]
        decoded = base64.b64decode(value).decode("latin-1")
        chars = []
        for idx, char in enumerate(decoded):
            code = (ord(char) - (399756995 % (idx + 5)) + 256) % 256
            chars.append(chr(code))
        return "".join(chars)

    @staticmethod
    def _rot13(value):
        out = []
        for char in value:
            code = ord(char)
            if 65 <= code <= 90:
                out.append(chr(((code - 65 + 13) % 26) + 65))
            elif 97 <= code <= 122:
                out.append(chr(((code - 97 + 13) % 26) + 97))
            else:
                out.append(char)
        return "".join(out)

    @staticmethod
    def _first(pattern, text, flags=0):
        match = re.search(pattern, text or "", flags | re.I)
        return match.group(1) if match else ""
