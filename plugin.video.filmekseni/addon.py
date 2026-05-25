# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re
import sys

import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode

from resources.lib.extractor import VideoExtractor
from resources.lib.site import FilmEkseniSite


ADDON_ID = "plugin.video.filmekseni"
ADDON = xbmcaddon.Addon(id=ADDON_ID)
HANDLE = int(sys.argv[1])
BASE_URL = ADDON.getSetting("base_url") or "https://filmekseni.cc"
UA = ADDON.getSetting("user_agent") or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

site = FilmEkseniSite(BASE_URL, UA)
extractor = VideoExtractor(UA, BASE_URL)


def build_url(query):
    return sys.argv[0] + "?" + urlencode(query)


def add_directory(title, action, url="", image="", plot=""):
    li = xbmcgui.ListItem(label=title)
    li.setArt({"thumb": image, "icon": image, "poster": image, "fanart": image})
    li.setInfo("video", {"title": title, "plot": plot})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({"action": action, "url": url}), li, True)


def add_video(title, action, url, image="", plot="", extra=None):
    query = {"action": action, "url": url}
    if extra:
        query.update(extra)
    li = xbmcgui.ListItem(label=title)
    li.setArt({"thumb": image, "icon": image, "poster": image, "fanart": image})
    li.setInfo("video", {"title": title, "plot": plot})
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, False)


def main_menu():
    for title, url in site.categories():
        add_directory(title, "list", url)
    add_directory("Ara", "search")
    xbmcplugin.setContent(HANDLE, "videos")


def list_page(url, page_number=1):
    items = site.get_page_items(url, page_number)
    for item in items:
        add_directory(item["title"], "detail", item["url"], item["image"], item["plot"])
    if items:
        li = xbmcgui.ListItem(label="Sonraki Sayfa")
        xbmcplugin.addDirectoryItem(
            HANDLE,
            build_url({"action": "list", "url": url, "page": str(int(page_number) + 1)}),
            li,
            True,
        )
    xbmcplugin.setContent(HANDLE, "movies")


def search():
    query = xbmcgui.Dialog().input("FilmEkseni Ara")
    if query:
        for item in site.search(query):
            add_directory(item["title"], "detail", item["url"], item["image"], item.get("plot", ""))
        xbmcplugin.setContent(HANDLE, "movies")


def detail(url):
    page = site.get(url)
    info = site.parse_detail(page, url)
    for source in info.get("sources", []):
        add_video(
            source["label"],
            "play_iframe" if source.get("is_trailer") else "play_source",
            source["url"],
            info["image"],
            info["plot"],
            {"referer": source.get("referer") or url, "label": source["label"]},
        )
    if not info.get("sources"):
        xbmcgui.Dialog().notification("FilmEkseni", "Video kaynagi bulunamadi", xbmcgui.NOTIFICATION_WARNING, 3000)


def play_source(url, referer=None, label=""):
    iframe = site.fetch_iframe(url, referer)
    play_iframe(iframe, url, label)


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


def play_iframe(url, referer=None, label=""):
    if youtube_plugin_url(url):
        play_youtube(url)
        return
    stream, subtitles = extractor.resolve(url, referer, label)
    if not stream:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    li = xbmcgui.ListItem(path=stream)
    if subtitles:
        li.setSubtitles(subtitles)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


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
    elif action == "play_iframe":
        play_iframe(url, params.get("referer"), params.get("label", ""))
    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    run()
