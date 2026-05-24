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
BASE_URL = ADDON.getSetting("base_url") or "https://www.hdfilmcehennemi.nl"
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
    add_directory("Yeni Eklenenler", "list", BASE_URL)
    add_directory("Filmler", "list", BASE_URL + "/category/film-izle-2/")
    add_directory("Diziler", "list", BASE_URL + "/yabancidiziizle-5/")
    add_directory("Türkçe Dublaj", "list", BASE_URL + "/turkce-dublaj-film-izle/")
    add_directory("Türkçe Altyazılı", "list", BASE_URL + "/turkce-altyazili-film-izle/")
    add_directory("IMDb 7+", "list", BASE_URL + "/imdb-7-puan-uzeri-filmler-2/")
    add_directory("Ara", "search")
    xbmcplugin.setContent(HANDLE, "videos")


def list_page(url):
    page = site.get(url)
    items = site.parse_movies(page)
    for item in items:
        add_directory(item["title"], "detail", item["url"], item["image"], item["plot"])
    next_page = site.parse_next_page(page, url)
    if next_page:
        add_directory("Sonraki Sayfa", "list", next_page)
    xbmcplugin.setContent(HANDLE, "movies")


def search():
    query = xbmcgui.Dialog().input("HDFilmCehennemi Ara")
    if query:
        list_page(site.search_url(query))


def detail(url):
    page = site.get(url)
    info = site.parse_detail(page, url)
    if info["sources"]:
        for source in info["sources"]:
            add_video(
                source["label"],
                "play_source",
                url,
                info["image"],
                info["plot"],
                {"video_id": source["video_id"]},
            )
    elif info["iframe"]:
        add_video(info["title"] or "Oynat", "play_iframe", info["iframe"], info["image"], info["plot"], {"referer": url})
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
    if not action:
        main_menu()
    elif action == "list":
        list_page(url)
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
