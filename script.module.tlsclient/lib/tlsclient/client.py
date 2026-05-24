import base64
import json as json_module
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union
from urllib.parse import urlencode

from .native import NativeLibraryError, call


HeaderValue = Union[str, int, float]
Headers = Mapping[str, HeaderValue]
Params = Union[Mapping[str, Any], Iterable[Tuple[str, Any]]]
Body = Union[bytes, bytearray, str]


class RequestError(Exception):
    """Raised when a request cannot be completed."""


class HTTPError(RequestError):
    """Raised by Response.raise_for_status for non-success HTTP responses."""

    def __init__(self, response: "Response") -> None:
        super().__init__("HTTP %s for %s" % (response.status_code, response.url))
        self.response = response


@dataclass
class Response:
    status_code: int
    url: str
    headers: Dict[str, str]
    content: bytes
    reason: str = ""
    cookies: Optional[Dict[str, str]] = None
    session_id: str = ""
    used_protocol: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding, errors="replace")

    @property
    def encoding(self) -> str:
        content_type = self.headers.get("content-type", "")
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                return part.split("=", 1)[1].strip() or "utf-8"
        return "utf-8"

    def json(self) -> Any:
        return json_module.loads(self.text)

    def raise_for_status(self) -> None:
        if not self.ok:
            raise HTTPError(self)


class Session:
    def __init__(
        self,
        headers: Optional[Headers] = None,
        timeout: float = 30.0,
        verify: bool = True,
        session_id: Optional[str] = None,
        client_identifier: str = "",
        random_tls_extension_order: bool = False,
        force_http1: bool = False,
        disable_http3: bool = False,
        with_protocol_racing: bool = False,
        proxy: Optional[str] = None,
    ) -> None:
        self.headers = _normalize_headers(headers or {})
        self.timeout = timeout
        self.verify = verify
        self.session_id = session_id or str(uuid.uuid4())
        self.client_identifier = client_identifier
        self.random_tls_extension_order = random_tls_extension_order
        self.force_http1 = force_http1
        self.disable_http3 = disable_http3
        self.with_protocol_racing = with_protocol_racing
        self.proxy = proxy

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Params] = None,
        data: Optional[Union[Body, Mapping[str, Any], Iterable[Tuple[str, Any]]]] = None,
        json: Any = None,
        headers: Optional[Headers] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        header_order: Optional[Iterable[str]] = None,
        request_host_override: Optional[str] = None,
        proxy: Optional[str] = None,
        is_byte_response: bool = False,
        **kwargs: Any,
    ) -> Response:
        if params:
            url = _append_query(url, params)

        body, content_type, is_byte_request = _prepare_body(data=data, json=json)
        request_headers = dict(self.headers)
        request_headers.update(_normalize_headers(headers or {}))
        if content_type and "content-type" not in request_headers:
            request_headers["content-type"] = content_type

        request_timeout = timeout if timeout is not None else self.timeout
        payload = {
            "requestMethod": method.upper(),
            "requestUrl": url,
            "headers": request_headers,
            "headerOrder": list(header_order or request_headers.keys()),
            "requestBody": body,
            "sessionId": self.session_id,
            "timeoutMilliseconds": int(request_timeout * 1000),
            "followRedirects": bool(allow_redirects),
            "insecureSkipVerify": not self.verify,
            "tlsClientIdentifier": kwargs.pop("tls_client_identifier", self.client_identifier),
            "withRandomTLSExtensionOrder": kwargs.pop(
                "with_random_tls_extension_order",
                self.random_tls_extension_order,
            ),
            "forceHttp1": kwargs.pop("force_http1", self.force_http1),
            "disableHttp3": kwargs.pop("disable_http3", self.disable_http3),
            "withProtocolRacing": kwargs.pop("with_protocol_racing", self.with_protocol_racing),
            "isByteRequest": is_byte_request,
            "isByteResponse": is_byte_response,
            "withoutCookieJar": False,
        }

        active_proxy = proxy if proxy is not None else self.proxy
        if active_proxy:
            payload["proxyUrl"] = active_proxy
        if request_host_override:
            payload["requestHostOverride"] = request_host_override

        payload.update(_known_native_options(kwargs))

        try:
            native_response = call("request", payload)
        except NativeLibraryError as exc:
            raise RequestError(str(exc)) from exc

        return _response_from_native(native_response, is_byte_response=is_byte_response)

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> Response:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def close(self) -> None:
        call("destroySession", {"sessionId": self.session_id})


def request(method: str, url: str, **kwargs: Any) -> Response:
    return Session().request(method, url, **kwargs)


def get(url: str, **kwargs: Any) -> Response:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any) -> Response:
    return request("POST", url, **kwargs)


def put(url: str, **kwargs: Any) -> Response:
    return request("PUT", url, **kwargs)


def patch(url: str, **kwargs: Any) -> Response:
    return request("PATCH", url, **kwargs)


def delete(url: str, **kwargs: Any) -> Response:
    return request("DELETE", url, **kwargs)


def head(url: str, **kwargs: Any) -> Response:
    return request("HEAD", url, **kwargs)


def options(url: str, **kwargs: Any) -> Response:
    return request("OPTIONS", url, **kwargs)


def _normalize_headers(headers: Headers) -> Dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _append_query(url: str, params: Params) -> str:
    separator = "&" if "?" in url else "?"
    return url + separator + urlencode(params, doseq=True)


def _prepare_body(
    data: Optional[Union[Body, Mapping[str, Any], Iterable[Tuple[str, Any]]]],
    json: Any,
) -> Tuple[Optional[str], Optional[str], bool]:
    if json is not None:
        return json_module.dumps(json, separators=(",", ":")), "application/json; charset=utf-8", False
    if data is None:
        return None, None, False
    if isinstance(data, bytes):
        return base64.b64encode(data).decode("ascii"), None, True
    if isinstance(data, bytearray):
        return base64.b64encode(bytes(data)).decode("ascii"), None, True
    if isinstance(data, str):
        return data, "text/plain; charset=utf-8", False
    return urlencode(data, doseq=True), "application/x-www-form-urlencoded", False


def _response_from_native(native_response: Dict[str, Any], is_byte_response: bool) -> Response:
    status = int(native_response.get("status") or 0)
    body = native_response.get("body") or ""
    if status == 0:
        raise RequestError(body)

    if is_byte_response and body.startswith("data:") and ";base64," in body:
        content = base64.b64decode(body.split(";base64,", 1)[1])
    else:
        content = body.encode("utf-8")

    return Response(
        status_code=status,
        url=native_response.get("target") or "",
        headers=_flatten_headers(native_response.get("headers") or {}),
        content=content,
        cookies=native_response.get("cookies") or {},
        session_id=native_response.get("sessionId") or "",
        used_protocol=native_response.get("usedProtocol") or "",
    )


def _flatten_headers(headers: Mapping[str, Any]) -> Dict[str, str]:
    flattened = {}
    for key, value in headers.items():
        if isinstance(value, list):
            flattened[str(key).lower()] = ", ".join(str(item) for item in value)
        else:
            flattened[str(key).lower()] = str(value)
    return flattened


def _known_native_options(values: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {
        "local_address": "localAddress",
        "server_name_overwrite": "serverNameOverwrite",
        "catch_panics": "catchPanics",
        "disable_ipv6": "disableIPV6",
        "disable_ipv4": "disableIPV4",
        "with_debug": "withDebug",
        "with_custom_cookie_jar": "withCustomCookieJar",
        "without_cookie_jar": "withoutCookieJar",
        "is_rotating_proxy": "isRotatingProxy",
        "certificate_pinning_hosts": "certificatePinningHosts",
        "custom_tls_client": "customTlsClient",
        "transport_options": "transportOptions",
        "default_headers": "defaultHeaders",
        "connect_headers": "connectHeaders",
    }
    return {native_key: values[key] for key, native_key in mapping.items() if key in values}
