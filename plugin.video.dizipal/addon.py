# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re
import sys

import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    from urllib.parse import parse_qsl, quote, urlencode
except ImportError:
    from urlparse import parse_qsl
    from urllib import quote, urlencode

from resources.lib.site import DiziPalSite


ADDON_ID = "plugin.video.dizipal"
ADDON = xbmcaddon.Addon(id=ADDON_ID)
HANDLE = int(sys.argv[1])
BASE_URL = ADDON.getSetting("base_url") or "https://dizipal.im"
UA = ADDON.getSetting("user_agent") or (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)

site = DiziPalSite(BASE_URL, UA)


def build_url(query):
    return sys.argv[0] + "?" + urlencode(query)


def art_url(url, referer=None):
    if not url or "|" in url or not url.startswith(("http://", "https://")):
        return url
    bits = ["User-Agent=" + quote(UA)]
    bits.append("Referer=" + quote(referer or BASE_URL + "/"))
    return url + "|" + "&".join(bits)


def set_art(li, image, referer=None):
    image = art_url(image, referer)
    li.setArt({"thumb": image, "icon": image, "poster": image, "fanart": image})


def add_directory(title, action, url="", image="", plot=""):
    li = xbmcgui.ListItem(label=title)
    set_art(li, image, url or BASE_URL + "/")
    li.setInfo("video", {"title": title, "plot": plot})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({"action": action, "url": url}), li, True)


def add_video(title, action, url, image="", plot="", extra=None):
    query = {"action": action, "url": url}
    if extra:
        query.update(extra)
    li = xbmcgui.ListItem(label=title)
    set_art(li, image, extra.get("referer") if extra else BASE_URL + "/")
    li.setInfo("video", {"title": title, "plot": plot})
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, False)


def main_menu():
    add_directory("Ara", "search")
    for title, url in site.categories():
        add_directory(title, "list", url)
    xbmcplugin.setContent(HANDLE, "tvshows")


def list_page(url, page_number=1):
    items = site.get_page_items(url, page_number)
    for item in items:
        add_directory(item["title"], "detail", item["url"], item["image"], item["plot"])
    if items:
        xbmcplugin.addDirectoryItem(
            HANDLE,
            build_url({"action": "list", "url": url, "page": str(int(page_number) + 1)}),
            xbmcgui.ListItem(label="Sonraki Sayfa"),
            True,
        )
    xbmcplugin.setContent(HANDLE, "tvshows")


def search():
    query = xbmcgui.Dialog().input("DiziPal Ara")
    if query:
        for item in site.search(query):
            add_directory(item["title"], "detail", item["url"], item["image"], item.get("plot", ""))
        xbmcplugin.setContent(HANDLE, "tvshows")


def detail(url):
    info = site.detail(url)
    sources = info.get("sources", [])
    episodes = info.get("episodes", [])
    for source in sources if not episodes else [source for source in sources if source.get("is_trailer")]:
        add_video(
            source["label"],
            "play_youtube" if source.get("is_trailer") else "play_source",
            source["url"],
            info.get("image", ""),
            info.get("plot", ""),
            {"referer": source.get("referer") or url, "label": source["label"]},
        )
    if episodes:
        for episode in episodes:
            add_directory(
                episode.get("title") or "Bolum",
                "detail",
                episode["url"],
                episode.get("image") or info.get("image", ""),
                info.get("plot", ""),
            )
    if not sources and not episodes:
        xbmcgui.Dialog().notification("DiziPal", "Kaynak veya bolum bulunamadi", xbmcgui.NOTIFICATION_WARNING, 3000)
    xbmcplugin.setContent(HANDLE, "tvshows")


def youtube_plugin_url(url):
    video_id = ""
    for pattern in (
        r"(?:youtube\.com/embed/|youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})",
        r"[?&]v=([A-Za-z0-9_-]{6,})",
    ):
        match = re.search(pattern, url or "", re.I)
        if match:
            video_id = match.group(1)
            break
    return "plugin://plugin.video.youtube/play/?video_id=" + video_id if video_id else ""


def play_youtube(url):
    plugin_url = youtube_plugin_url(url)
    if not plugin_url:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    try:
        xbmcaddon.Addon(id="plugin.video.youtube")
    except Exception:
        xbmcgui.Dialog().notification("YouTube", "plugin.video.youtube gerekli", xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    xbmcplugin.setResolvedUrl(HANDLE, True, xbmcgui.ListItem(path=plugin_url))


def play_source(url, referer=None, label=""):
    stream, subtitles = site.resolve_source(url, referer, label)
    if not stream:
        xbmcgui.Dialog().notification("DiziPal", "Kaynak cozumlenemedi", xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    path = clean_stream_url(stream) if is_hls_stream(stream) else stream
    li = xbmcgui.ListItem(path=path)
    if is_hls_stream(stream):
        li.setMimeType("application/vnd.apple.mpegurl")
        li.setContentLookup(False)
        if has_addon("inputstream.adaptive"):
            li.setProperty("inputstream", "inputstream.adaptive")
            li.setProperty("inputstream.adaptive.stream_headers", stream_headers(stream))
            li.setProperty("inputstream.adaptive.manifest_headers", stream_headers(stream))
    if subtitles:
        li.setSubtitles(subtitles)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def is_hls_stream(url):
    clean = (url or "").split("|", 1)[0]
    return bool(re.search(r"(?:\.m3u8|/playlist/[^/?#]+\.json)(?:[?#].*)?$", clean, re.I))


def stream_headers(url):
    if "|" not in (url or ""):
        return ""
    return url.split("|", 1)[1]


def clean_stream_url(url):
    return (url or "").split("|", 1)[0]


def has_addon(addon_id):
    try:
        xbmcaddon.Addon(id=addon_id)
        return True
    except Exception:
        return False


def run():
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get("action")
    url = params.get("url", "")
    page_number = int(params.get("page", "1"))
    if not action:
        main_menu()
    elif action == "list":
        list_page(url, page_number)
    elif action == "search":
        search()
    elif action == "detail":
        detail(url)
    elif action == "play_source":
        play_source(url, params.get("referer"), params.get("label", ""))
    elif action == "play_youtube":
        play_youtube(url)
    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    run()
