# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode

from resources.lib.extractor import VideoExtractor
from resources.lib.site import HDFilmCehennemiSite


ADDON_ID = "plugin.video.hdfilmcehennemi"
ADDON = xbmcaddon.Addon(id=ADDON_ID)
HANDLE = int(sys.argv[1])
BASE_URL = ADDON.getSetting("base_url") or "https://www.hdfilmcehennemi.com"
UA = ADDON.getSetting("user_agent") or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

site = HDFilmCehennemiSite(BASE_URL, UA)
extractor = VideoExtractor(UA)


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
    query = xbmcgui.Dialog().input("HDFilmCehennemi Ara")
    if query:
        for item in site.search(query):
            add_directory(item["title"], "detail", item["url"], item["image"], item.get("plot", ""))
        xbmcplugin.setContent(HANDLE, "movies")


def detail(url):
    page = site.get(url)
    info = site.parse_detail(page, url)
    for episode in info.get("episodes", []):
        add_directory(episode["title"], "detail", episode["url"], info["image"], info["plot"])
    if info["sources"]:
        for source in info["sources"]:
            add_video(
                source["label"],
                "play_iframe" if source.get("is_trailer") else "play_source",
                source["url"] if source.get("is_trailer") else url,
                info["image"],
                info["plot"],
                {"video_id": source.get("video_id", "")},
            )
    else:
        xbmcgui.Dialog().notification("HDFilmCehennemi", "Video kaynagi bulunamadi", xbmcgui.NOTIFICATION_WARNING, 3000)


def play_iframe(url, referer=None):
    stream, subtitles = extractor.resolve(url, referer)
    if not stream:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    li = xbmcgui.ListItem(path=stream)
    if subtitles:
        li.setSubtitles(subtitles)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def play_source(page_url, video_id):
    try:
        iframe = site.fetch_source_iframe(video_id, page_url)
    except Exception:
        page = site.get(page_url)
        iframe = site.parse_detail(page, page_url).get("iframe")
    play_iframe(iframe, page_url)


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
    elif action == "play_iframe":
        play_iframe(url, params.get("referer"))
    elif action == "play_source":
        play_source(url, params.get("video_id"))
    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    run()
