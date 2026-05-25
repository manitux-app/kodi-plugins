# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import base64
import binascii
import json
import re
import string

import tlsclient

try:
    from urllib.parse import quote, urlparse, urlunparse
except ImportError:
    from urllib import quote
    from urlparse import urlparse, urlunparse


class VideoExtractor(object):
    CLIENT_IDENTIFIERS = ("chrome_144", "cloudscraper")

    def __init__(self, user_agent):
        self.user_agent = user_agent
        self.session = tlsclient.Session(client_identifier=self.CLIENT_IDENTIFIERS[0])

    def headers(self, referer=None):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if referer:
            headers["Referer"] = referer
        return headers
    
    def hdfilmcehennemi_extractor(self, url, referer=None):
        url = self.normalize_url(url)
        referer = referer or url
        page = self.fetch(url, referer)
        embed_origin = self.origin(url)
        subs = []

        source = self._extract_obfuscated_video_link(page)
        unpacked = self._unpack_first_eval(page)
        if unpacked:
            if not source:
                source = self._extract_obfuscated_video_link(unpacked)
            if not source:
                source = self._first(r"sources\s*:\s*\[\s*\{\s*file\s*:\s*['\"]([^'\"]+)", unpacked, re.S)
            if not source:
                b64_source = self._first(r'["\'](aHR0c[^"\']+)["\']', unpacked)
                if b64_source:
                    source = base64.b64decode(b64_source).decode("utf-8", "replace")
            subs = self._extract_subtitles(page + "\n" + unpacked, embed_origin)
        else:
            source = self._first(r'"contentUrl"\s*:\s*"([^"]+)"', page)
            if not source:
                source = self._first(r'(?:"file"|file)\s*:\s*["\']([^"\']+)', page)
            subs = self._extract_subtitles(page, embed_origin)

        if not source:
            iframe = self._first(r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)', page)
            if iframe and iframe != url:
                return self.resolve(iframe.replace("\\/", "/"), url)
            return None, subs

        source = source.replace("\\/", "/").replace("\\u0026", "&")
        return source + self.kodi_headers(embed_origin), subs


    def resolve(self, url, referer=None):
        if not url:
            return None, []
        url = self.normalize_url(url)
        if self.is_hdfilm_url(url):
            return self.hdfilmcehennemi_extractor(url, referer)
        if "vidmoly" in url or "flmplayer" in url:
            return self.resolve_vidmoly(url)
        if "odnoklassniki" in url or "ok.ru" in url:
            return self.resolve_okru(url)
        return url + self.kodi_headers(referer), []

    def resolve_hdfilm_embed(self, url, referer=None):
        return self.hdfilmcehennemi_extractor(url, referer)

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
        last_error = None
        for identifier in self.CLIENT_IDENTIFIERS:
            if self.session.client_identifier != identifier:
                self.session = tlsclient.Session(client_identifier=identifier)
            try:
                res = self.session.get(
                    url,
                    headers=self.headers(referer),
                    timeout=25,
                    allow_redirects=True,
                    tls_client_identifier=identifier,
                )
                if res.status_code in (403, 429) and identifier != self.CLIENT_IDENTIFIERS[-1]:
                    last_error = tlsclient.HTTPError(res)
                    continue
                res.raise_for_status()
                return res.text
            except (tlsclient.HTTPError, tlsclient.RequestError) as exc:
                last_error = exc
                if identifier == self.CLIENT_IDENTIFIERS[-1]:
                    raise
        raise last_error

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
        bits = ["User-Agent=" + quote(self.user_agent)]
        if referer:
            bits.append("Referer=" + quote(referer))
        return "|" + "&".join(bits)

    def is_hdfilm_url(self, url):
        host = urlparse(url).netloc.lower()
        return (
            "hdfilmcehennemi" in host
            or "filmmakinesi" in host
            or "dizicehennemi" in host
            or "closeload" in host
            or "playmix" in host
            or "rapidrame" in host
        )

    def origin(self, url):
        parsed = urlparse(url)
        return parsed.scheme + "://" + parsed.netloc

    def _extract_subtitles(self, page, origin):
        subtitles = []
        for subtitle in re.findall(r'"file"\s*:\s*"([^"]+)"[^{}]*"kind"\s*:\s*"captions"', page, re.S):
            subtitles.append(self._absolute_url(subtitle.replace("\\/", "/"), origin))
        for tracks in re.findall(r"tracks\s*:\s*(\[.*?\])\s*,", page, re.S):
            for subtitle in re.findall(r'"file"\s*:\s*"([^"]+)"', tracks):
                subtitles.append(self._absolute_url(subtitle.replace("\\/", "/"), origin))
        for subtitle in re.findall(r"track\s+src=['\"]([^'\"]+)", page, re.S | re.I):
            subtitles.append(self._absolute_url(subtitle.replace("\\/", "/"), origin))
        return list(dict.fromkeys(subtitles))

    def _absolute_url(self, url, origin):
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return origin.rstrip("/") + url
        return url

    def _unpack_first_eval(self, page):
        match = re.search(
            r"eval\(function\(p,a,c,k,e,d\).*?\}\((?P<payload>['\"].*?['\"])\s*,\s*(?P<base>\d+)\s*,\s*(?P<count>\d+)\s*,\s*(?P<symbols>['\"].*?['\"])\.split\(['\"]\|['\"]\)",
            page,
            re.S,
        )
        if not match:
            return ""
        payload = self._js_string(match.group("payload"))
        base = int(match.group("base"))
        count = int(match.group("count"))
        symbols = self._js_string(match.group("symbols")).split("|")
        if count > len(symbols):
            symbols.extend([""] * (count - len(symbols)))
        for index in range(count - 1, -1, -1):
            word = self._base_n(index, base)
            if symbols[index]:
                payload = re.sub(r"\b" + re.escape(word) + r"\b", symbols[index], payload)
        return payload

    def _js_string(self, value):
        quote_char = value[0]
        if value[-1] == quote_char:
            value = value[1:-1]
        return bytes(value, "utf-8").decode("unicode_escape")

    def _base_n(self, number, base):
        alphabet = string.digits + string.ascii_lowercase + string.ascii_uppercase
        if number == 0:
            return "0"
        result = ""
        while number:
            number, remainder = divmod(number, base)
            result = alphabet[remainder] + result
        return result

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

    def _extract_obfuscated_video_link(self, html):
        for candidate in self._get_base64_candidates_from_html(html):
            source = self._try_decrypt_candidate(candidate)
            if source:
                return source
        source = self._decode_obfuscated_source(html)
        if source:
            return self._get_url(source)
        return self._direct_video_link(html)

    def _try_decrypt_candidate(self, value):
        strategies = (
            lambda x: self._unmix(self._rot13(self._base64_decode_js(x[::-1]))),
            lambda x: self._unmix(self._base64_decode_js(self._rot13(x))[::-1]),
            lambda x: self._unmix(self._rot13(self._base64_decode_js(x))[::-1]),
            lambda x: self._unmix(self._base64_decode_js(self._base64_decode_js(x[::-1]))),
            lambda x: self._unmix(self._base64_decode_js(self._rot13(x)[::-1])),
            self._decrypt_rot13_base64_reverse_unmix,
            self._decrypt_reversed_double_base64_unmix,
            self._decrypt_text_base64_rot13_reverse_unmix,
            self._decrypt_rot13_reversed_base64_unmix,
        )
        for decoder in strategies:
            try:
                decoded = decoder(value)
            except Exception:
                decoded = None
            source = self._get_url(decoded)
            if source:
                return source
        return None

    def _decrypt_rot13_base64_reverse_unmix(self, value):
        decoded = self._base64_decode_js(self._rot13(value))
        if not decoded:
            return None
        return self._get_url(self._unmix(decoded[::-1]))

    def _decrypt_reversed_double_base64_unmix(self, value):
        first = self._base64_decode_js(value[::-1])
        if not first:
            return None
        second = self._base64_decode_js(first)
        if not second:
            return None
        return self._get_url(self._unmix(second))

    def _decrypt_text_base64_rot13_reverse_unmix(self, value):
        decoded = self._base64_decode_js(value)
        if not decoded or self._printable_ratio(decoded) <= 0.75:
            return None
        return self._get_url(self._unmix(self._rot13(decoded)[::-1]))

    def _decrypt_rot13_reversed_base64_unmix(self, value):
        decoded = self._base64_decode_js(self._rot13(value)[::-1])
        if not decoded or self._printable_ratio(decoded) <= 0.75:
            return None
        return self._get_url(self._unmix(decoded))

    def _get_base64_candidates_from_html(self, html):
        candidates = []
        self._add_direct_array_values(html, candidates)
        self._add_quoted_base64_values(html, candidates)
        unpacked = self._unpack_first_eval(html)
        if unpacked:
            self._add_direct_array_values(unpacked, candidates)
            self._add_quoted_base64_values(unpacked, candidates)
        self._add_packed_array_values(html, candidates)
        result = []
        for candidate in candidates:
            candidate = (candidate or "").replace("\\/", "/").strip()
            if self._is_likely_encrypted_payload(candidate) and candidate not in result:
                result.append(candidate)
        return result

    def _add_direct_array_values(self, html, candidates):
        array_pattern = re.compile(
            r"\b\w+\s*\(\s*(\[\s*(?:\"[^\"]*\"|'[^']*')\s*(?:,\s*(?:\"[^\"]*\"|'[^']*')\s*)*\])\s*\)",
            re.S,
        )
        for match in array_pattern.finditer(html or ""):
            array_text = match.group(1)
            parsed = self._parse_string_array(array_text)
            if parsed:
                candidates.append(parsed)
            else:
                parts = re.findall(r"""["']([^"']+)["']""", array_text)
                candidates.append("".join(parts))

    def _add_quoted_base64_values(self, html, candidates):
        pattern = re.compile(r"""["'](?P<value>(?:={0,2})[A-Za-z0-9+/]{80,}={0,2})["']""", re.S)
        for match in pattern.finditer(html or ""):
            candidates.append(match.group("value"))

    def _add_packed_array_values(self, html, candidates):
        eval_pattern = re.compile(r"eval\(function\(p,a,c,k,e,d\).*?\.split\(['\"]\|['\"]\),\d+,\{\}\)\)", re.S)
        for eval_match in eval_pattern.finditer(html or ""):
            body = eval_match.group(0)
            dict_match = re.search(r"""['"]([^'"]*)['"]\.split""", body, re.S)
            if not dict_match:
                continue
            dictionary = dict_match.group(1).split("|")
            lookup = string.digits + string.ascii_lowercase + string.ascii_uppercase
            for array_match in re.finditer(r"""\[\s*(["'].*?["']\s*,?\s*)+\s*\]""", body, re.S):
                parts = []
                for part_match in re.finditer(r"""["'](?P<val>.*?)["']""", array_match.group(0), re.S):
                    part = re.sub(
                        r"\w+",
                        lambda m: self._base62_lookup(m.group(0), lookup, dictionary),
                        part_match.group("val"),
                    )
                    parts.append(part)
                candidates.append("".join(parts))

    def _parse_string_array(self, array_text):
        normalized = re.sub(
            r"'([^'\\]*(?:\\.[^'\\]*)*)'",
            lambda m: json.dumps(m.group(1)),
            array_text,
        )
        try:
            return "".join(json.loads(normalized))
        except (TypeError, ValueError):
            return ""

    def _base62_lookup(self, value, lookup, dictionary):
        index = 0
        multiplier = 1
        for char in reversed(value):
            char_index = lookup.find(char)
            if char_index == -1:
                return value
            index += char_index * multiplier
            multiplier *= 62
        if index < len(dictionary) and dictionary[index]:
            return dictionary[index]
        return value

    def _base64_decode_js(self, value):
        if not value:
            return ""
        try:
            if not isinstance(value, bytes):
                value = value.encode("latin-1")
            value += b"=" * ((4 - len(value) % 4) % 4)
            return base64.b64decode(value).decode("latin-1")
        except (TypeError, binascii.Error, UnicodeError):
            return ""

    def _is_likely_encrypted_payload(self, value):
        if len(value) < 40:
            return False
        count = sum(1 for char in value if char.isalnum() or char in "+/=")
        return float(count) / len(value) > 0.85

    def _unmix(self, value):
        chars = []
        for idx, char in enumerate(value):
            code = (ord(char) - (399756995 % (idx + 5)) + 256) % 256
            chars.append(chr(code))
        return "".join(chars)

    def _printable_ratio(self, value):
        if not value:
            return 0
        printable = sum(1 for char in value if char in "\r\n\t" or " " <= char <= "~")
        return float(printable) / len(value)

    def _get_url(self, value):
        value = (value or "").replace("\\/", "/").replace("\\u0026", "&").replace("u0026", "&")
        match = re.search(r"""https?://[^\s"'|<>]+""", value)
        return match.group(0) if match else None

    def _direct_video_link(self, html):
        unpacked = self._unpack_first_eval(html)
        for source in (unpacked, html):
            match = re.search(r"""https?:\\?/\\?/[^"'\s<>]+?\.m3u8[^"'\s<>]*""", source or "", re.I)
            if match:
                return match.group(0).replace("\\/", "/")
        return None

    @staticmethod
    def _first(pattern, text, flags=0):
        match = re.search(pattern, text or "", flags | re.I)
        return match.group(1) if match else ""
