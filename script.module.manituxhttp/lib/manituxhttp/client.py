# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json as json_module
import ssl

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    import certifi  # type: ignore
except Exception:
    certifi = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

try:
    from urllib.parse import urlencode
    from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPCookieProcessor, HTTPSHandler
    from urllib.error import HTTPError as UrlHTTPError, URLError
    import http.cookiejar as cookielib
except ImportError:
    from urllib import urlencode
    from urllib2 import Request, build_opener, HTTPRedirectHandler, HTTPCookieProcessor, HTTPSHandler, HTTPError as UrlHTTPError, URLError
    import cookielib


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class RequestError(RuntimeError):
    pass


class HTTPError(RequestError):
    def __init__(self, response):
        self.response = response
        RequestError.__init__(self, "HTTP %s for %s" % (response.status_code, response.url))


class Response(object):
    def __init__(self, status_code=0, url="", headers=None, content=b""):
        self.status_code = int(status_code or 0)
        self.url = url or ""
        self.headers = headers or {}
        self.content = content or b""

    @property
    def text(self):
        encoding = _encoding_from_headers(self.headers) or "utf-8"
        try:
            return self.content.decode(encoding, "replace")
        except LookupError:
            return self.content.decode("utf-8", "replace")

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return json_module.loads(self.text)

    def raise_for_status(self):
        if not self.ok:
            raise HTTPError(self)


class Session(object):
    def __init__(self, headers=None, verify=True):
        self.headers = headers.copy() if headers else {}
        self.verify = verify
        self._requests_session = requests.Session() if requests is not None else None
        self._cookie_jar = cookielib.CookieJar()

    def request(self, method, url, **kwargs):
        headers = self.headers.copy()
        headers.update(kwargs.pop("headers", None) or {})
        if "User-Agent" not in headers:
            headers["User-Agent"] = DEFAULT_USER_AGENT

        timeout = kwargs.pop("timeout", 25)
        data = kwargs.pop("data", None)
        json_data = kwargs.pop("json", None)
        params = kwargs.pop("params", None)
        allow_redirects = kwargs.pop("allow_redirects", True)
        verify = _verify_value(kwargs.pop("verify", self.verify))
        kwargs.pop("tls_client_identifier", None)
        kwargs.pop("client_identifier", None)

        if json_data is not None:
            data = json_module.dumps(json_data, separators=(",", ":"))
            headers.setdefault("Content-Type", "application/json")

        if params:
            url = _append_query(url, params)

        if self._requests_session is not None:
            return self._request_with_requests(
                method,
                url,
                headers=headers,
                data=data,
                timeout=timeout,
                allow_redirects=allow_redirects,
                verify=verify,
                **kwargs
            )

        return self._request_with_urllib(
            method,
            url,
            headers=headers,
            data=data,
            timeout=timeout,
            allow_redirects=allow_redirects,
            verify=verify,
        )

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def head(self, url, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def options(self, url, **kwargs):
        return self.request("OPTIONS", url, **kwargs)

    def _request_with_requests(self, method, url, headers, data, timeout, allow_redirects, verify, **kwargs):
        try:
            raw = self._requests_session.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=timeout,
                allow_redirects=allow_redirects,
                verify=verify,
                **kwargs
            )
        except Exception as exc:
            raise RequestError(str(exc))

        return Response(
            status_code=raw.status_code,
            url=getattr(raw, "url", url),
            headers=dict(getattr(raw, "headers", {}) or {}),
            content=getattr(raw, "content", b"") or b"",
        )

    def _request_with_urllib(self, method, url, headers, data, timeout, allow_redirects, verify):
        if data is not None and not isinstance(data, bytes):
            if isinstance(data, dict):
                data = urlencode(data)
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            data = data.encode("utf-8")

        context = None
        if not verify:
            try:
                context = ssl._create_unverified_context()
            except Exception:
                context = None

        handlers = [HTTPCookieProcessor(self._cookie_jar)]
        if context is not None:
            handlers.append(HTTPSHandler(context=context))
        if not allow_redirects:
            handlers.append(_NoRedirectHandler())
        opener = build_opener(*handlers)

        req = Request(url, data=data, headers=headers)
        try:
            req.get_method = lambda: method.upper()
            raw = opener.open(req, timeout=timeout)
        except UrlHTTPError as exc:
            return Response(
                status_code=exc.code,
                url=getattr(exc, "url", url),
                headers=dict(exc.headers.items()) if exc.headers else {},
                content=exc.read() or b"",
            )
        except URLError as exc:
            raise RequestError(str(exc))
        except Exception as exc:
            raise RequestError(str(exc))

        try:
            status_code = raw.getcode()
            final_url = raw.geturl()
            headers_out = dict(raw.info().items())
            content = raw.read() or b""
        finally:
            raw.close()

        return Response(status_code=status_code, url=final_url, headers=headers_out, content=content)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(method, url, **kwargs):
    return Session().request(method, url, **kwargs)


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)


def put(url, **kwargs):
    return request("PUT", url, **kwargs)


def patch(url, **kwargs):
    return request("PATCH", url, **kwargs)


def delete(url, **kwargs):
    return request("DELETE", url, **kwargs)


def head(url, **kwargs):
    return request("HEAD", url, **kwargs)


def options(url, **kwargs):
    return request("OPTIONS", url, **kwargs)


def _append_query(url, params):
    query = urlencode(params)
    separator = "&" if "?" in url else "?"
    return url + separator + query


def _encoding_from_headers(headers):
    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = value
            break
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip()
    return None


def _verify_value(verify):
    if verify is True and certifi is not None:
        try:
            return certifi.where()
        except Exception:
            return True
    return verify
