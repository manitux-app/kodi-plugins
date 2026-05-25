# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import base64
import json
import re
import string

import manituxhttp

try:
    from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse
except ImportError:
    from urllib import quote, unquote
    from urlparse import urljoin, urlparse, urlunparse

from . import parsers


class DiziBoxExtractor(object):
    MOLY_DOMAINS = (
        "molystream",
        "sheila.stream",
        "popcornvakti",
        "rufiiguta",
    )

    def __init__(self, user_agent, base_url):
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.session = manituxhttp.Session()

    def resolve(self, url, referer=None, label=""):
        if not url:
            return None, []
        url = self.normalize_url(url)
        referer = referer or self.base_url + "/"
        iframe = self.decode_iframe(url, referer)
        if iframe and iframe != url:
            return self.resolve(iframe, url, label)

        host = urlparse(url).netloc.lower()
        if "vidmoly" in host or "videobin" in host:
            return self.resolve_vidmoly(url, referer)
        if "ok.ru" in host or "odnoklassniki" in host:
            return self.resolve_okru(url)
        if any(domain in host for domain in self.MOLY_DOMAINS):
            return self.resolve_moly(url, referer, label)

        page = self.fetch(url, referer)
        source, subtitles = self.extract_jw(page, url, label or "DiziBox")
        if source:
            return source, subtitles
        return url + self.kodi_headers(referer), []

    def decode_iframe(self, url, referer=None):
        if "/player/haydi.php" in url and "?v=" in url:
            value = url.split("?v=", 1)[1].split("&", 1)[0]
            return self._b64(value)

        if "/player/moly/moly.php" in url:
            player_url = url.replace("moly.php?h=", "moly.php?wmode=opaque&h=")
            page = self.fetch(player_url, referer)
            escaped = self._first(r'unescape\(["\'](.*?)["\']\)', page, re.S)
            if escaped:
                decoded = self._b64(unquote(escaped))
                iframe = parsers.parse_iframe(decoded, player_url)
                if iframe:
                    return iframe
            iframe = parsers.parse_iframe(page, player_url)
            if iframe:
                return iframe

        if "/player/king/king.php" in url:
            player_url = url.replace("king.php?v=", "king.php?wmode=opaque&v=")
            page = self.fetch(player_url, referer)
            iframe = parsers.parse_iframe(page, player_url)
            if iframe:
                nested = self.fetch(iframe, player_url)
                direct = self._first(r"file\s*:\s*['\"]([^'\"]+)['\"]", nested, re.S)
                if direct:
                    return direct
                nested_iframe = parsers.parse_iframe(nested, iframe)
                if nested_iframe:
                    return nested_iframe

        return url

    def resolve_moly(self, url, referer=None, label=""):
        page = self.fetch(url, referer or self.base_url + "/")
        source, subtitles = self.extract_jw(page, url, label or "Molystream")
        if not source:
            source = self._first(r"""https?://[^\s"'<>]+?(?:\.m3u8|\.mp4|master\.txt)[^\s"'<>]*""", page)
        return (source + self.kodi_headers(url) if source else None), subtitles

    def resolve_vidmoly(self, url, referer=None):
        candidates = self.vidmoly_candidates(url)
        page = ""
        page_url = url
        for candidate in candidates:
            try:
                page = self.fetch(candidate, referer or "https://vidmoly.to/")
            except (manituxhttp.HTTPError, manituxhttp.RequestError):
                continue
            page_url = candidate
            if self.has_playable(page):
                break
        if not page:
            return None, []
        if self.needs_number_challenge(page):
            challenged = self.submit_number_challenge(page_url, page, referer)
            if challenged:
                page = challenged
        source, subtitles = self.extract_jw(page, page_url, "VidMoly")
        if not source:
            unpacked = self.unpack_first_eval(page)
            source = self.media_url(unpacked) or self.media_url(page)
        return (source + self.kodi_headers(page_url) if source else None), subtitles

    def resolve_okru(self, url):
        video_id = self._first(r"(?:videoembed/|/video/|mid=)(\d+)", url)
        if not video_id:
            return url + self.kodi_headers("https://ok.ru/"), []
        res = self.session.post(
            "https://www.ok.ru/dk",
            data={"cmd": "videoPlayerMetadata", "mid": video_id},
            headers=self.headers("https://ok.ru/"),
            timeout=25,
        )
        res.raise_for_status()
        source = self._first(r'(?:ultra|quad|full|hd|sd|low|lowest)","url":"(.*?)"', res.text)
        return source.replace(r"\u0026", "&") + self.kodi_headers("https://ok.ru/"), []

    def extract_jw(self, page, page_url, source_name):
        sources = self._extract_sources(page, page_url, source_name)
        subtitles = self._extract_subtitles(page, page_url)
        if sources:
            return sources[0], subtitles
        source = self._first(r"""[:=]\s*["']([^"'\s]+(?:\.m3u8|\.mp4|master\.txt)[^"'\s]*)""", page, re.S)
        return (parsers.fix_url(source.replace("\\/", "/"), page_url) if source else None), subtitles

    def fetch(self, url, referer=None):
        res = self.session.get(
            self.normalize_url(url),
            headers=self.headers(referer),
            timeout=25,
            allow_redirects=True,
        )
        res.raise_for_status()
        return res.text

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "iframe",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def kodi_headers(self, referer=None):
        bits = ["User-Agent=" + quote(self.user_agent)]
        if referer:
            bits.append("Referer=" + quote(referer))
        return "|" + "&".join(bits)

    def normalize_url(self, url):
        url = (url or "").strip()
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = urljoin(self.base_url + "/", url)
        elif url.startswith("www."):
            url = "https://" + url
        elif not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url + "/", url)
        parsed = urlparse(url)
        return urlunparse(parsed._replace(scheme="https"))

    def vidmoly_candidates(self, url):
        candidates = []
        self._add_candidate(candidates, re.sub(r"/w/([a-z0-9]+)/*$", r"/embed-\1.html", url, flags=re.I))
        self._add_candidate(candidates, url)
        normalized = re.sub(r"https?://vidmoly\.[a-z]+", "https://vidmoly.biz", url, flags=re.I)
        self._add_candidate(candidates, re.sub(r"/w/([a-z0-9]+)/*$", r"/embed-\1.html", normalized, flags=re.I))
        self._add_candidate(candidates, normalized)
        self._add_candidate(candidates, re.sub(r"/embed-([a-z0-9]+)\.html", r"/w/\1", normalized, flags=re.I))
        return candidates

    def submit_number_challenge(self, page_url, page, referer=None):
        answer = self._first(r"(?:Please select|Select number)\s+(\d+)", page)
        if not answer:
            answer = self._first(r"<(?:div|span)[^>]+class=['\"][^'\"]*vhint[^'\"]*['\"][^>]*>.*?<b[^>]*>(\d+)</b>", page, re.S)
        body = {
            "op": self._input_value(page, "op"),
            "file_code": self._input_value(page, "file_code"),
            "answer": answer,
        }
        for name in ("ts", "nonce", "ctok"):
            value = self._input_value(page, name)
            if value:
                body[name] = value
        if not body["op"] or not body["file_code"] or not body["answer"]:
            return ""
        res = self.session.post(page_url, data=body, headers=self.headers(referer or page_url), timeout=25)
        res.raise_for_status()
        return res.text

    def _extract_sources(self, page, page_url, source_name):
        result = []
        for block in re.findall(r"""["']?sources["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(block):
                file_url = item.get("file") or item.get("src")
                if not file_url:
                    continue
                label = item.get("label")
                result.append(parsers.fix_url(file_url.replace("\\/", "/"), page_url))
        if not result:
            for match in re.finditer(r"""https?://[^\s"'<>]+?(?:\.m3u8|\.mp4|master\.txt)[^\s"'<>]*""", page or "", re.I):
                result.append(match.group(0).replace("\\/", "/"))
        return list(dict.fromkeys(result))

    def _extract_subtitles(self, page, page_url):
        subtitles = []
        for block in re.findall(r"""["']?tracks["']?\s*:\s*(\[.*?\])""", page or "", re.S | re.I):
            for item in self._parse_js_list(block):
                file_url = item.get("file")
                kind = item.get("kind", "")
                if file_url and ("caption" in kind.lower() or "subtitle" in kind.lower()):
                    subtitles.append(parsers.fix_url(file_url.replace("\\/", "/"), page_url))
        for match in re.finditer(r"""addSrtFile\(["'](?P<url>[^"']+\.srt)["']""", page or "", re.I):
            subtitles.append(parsers.fix_url(match.group("url"), page_url))
        return list(dict.fromkeys(subtitles))

    def _parse_js_list(self, value):
        normalized = (value or "").replace("\\/", "/").replace("'", '"')
        normalized = re.sub(r"(?<!\")\b(file|src|label|type|kind)\b\s*:", r'"\1":', normalized, flags=re.I)
        normalized = re.sub(r",\s*([\]}])", r"\1", normalized)
        try:
            data = json.loads(normalized)
        except ValueError:
            return []
        return data if isinstance(data, list) else []

    def unpack_first_eval(self, page):
        match = re.search(
            r"eval\(function\(p,a,c,k,e,(?:r|d)\).*?\}\(\s*'(?P<payload>(?:\\'|[^'])*)'\s*,\s*(?P<base>\d+)\s*,\s*(?P<count>\d+)\s*,\s*'(?P<symbols>(?:\\'|[^'])*)'\.split\('\|'\)",
            page or "",
            re.S,
        )
        if not match:
            return ""
        payload = match.group("payload").replace("\\'", "'").replace("\\\\", "\\")
        base = int(match.group("base"))
        symbols = match.group("symbols").replace("\\'", "'").replace("\\\\", "\\").split("|")
        return re.sub(r"\b\w+\b", lambda m: self._packed_symbol(m.group(0), base, symbols), payload)

    def media_url(self, text):
        match = re.search(r"""https?://[^\s"'<>]+?\.(?:m3u8|mp4|master\.txt)(?:\?[^\s"'<>]*)?""", text or "", re.I)
        return match.group(0).replace("\\/", "/") if match else ""

    @staticmethod
    def has_playable(page):
        text = page or ""
        return "sources:" in text or ".m3u8" in text or ".mp4" in text or "jwplayer" in text

    @staticmethod
    def needs_number_challenge(page):
        text = page or ""
        return "Select number" in text or "select the number" in text

    @staticmethod
    def _packed_symbol(value, base, symbols):
        alphabet = string.digits + string.ascii_lowercase + string.ascii_uppercase
        index = 0
        for char in value:
            digit = alphabet.find(char)
            if digit < 0 or digit >= base:
                return value
            index = index * base + digit
        return symbols[index] if 0 <= index < len(symbols) and symbols[index] else value

    @staticmethod
    def _input_value(page, name):
        for tag in re.findall(r"<input\b[^>]*>", page or "", re.S | re.I):
            input_name = DiziBoxExtractor._first(r"""name=["']([^"']+)["']""", tag)
            if input_name == name:
                return DiziBoxExtractor._first(r"""value=["']([^"']*)["']""", tag, re.S)
        return ""

    @staticmethod
    def _add_candidate(candidates, url):
        if url and url not in candidates:
            candidates.append(url)

    @staticmethod
    def _b64(value):
        try:
            raw = value.encode("utf-8")
            raw += b"=" * ((4 - len(raw) % 4) % 4)
            return base64.b64decode(raw).decode("utf-8", "replace")
        except Exception:
            return ""

    @staticmethod
    def _first(pattern, text, flags=0):
        match = re.search(pattern, text or "", flags | re.I)
        return match.group(1) if match else ""
