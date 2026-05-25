# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .client import (
    DEFAULT_USER_AGENT,
    BeautifulSoup,
    HTTPError,
    RequestError,
    Response,
    Session,
    delete,
    get,
    head,
    options,
    patch,
    post,
    put,
    request,
)

__all__ = [
    "DEFAULT_USER_AGENT",
    "BeautifulSoup",
    "HTTPError",
    "RequestError",
    "Response",
    "Session",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "request",
]

__version__ = "1.0.0"
