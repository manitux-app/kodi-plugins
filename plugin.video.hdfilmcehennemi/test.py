# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import argparse
import json
import os
import sys

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HTTP_LIB = os.path.join(ROOT_DIR, "script.module.manituxhttp", "lib")
if HTTP_LIB not in sys.path:
    sys.path.insert(0, HTTP_LIB)

ADDON_DIR = os.path.dirname(__file__)
if ADDON_DIR not in sys.path:
    sys.path.insert(0, ADDON_DIR)

from resources.lib.extractor import VideoExtractor
from resources.lib.site import HDFilmCehennemiSite


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def base_url_from(url):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "https://www.hdfilmcehennemi.nl"
    return parsed.scheme + "://" + parsed.netloc


def public_media_info(info):
    keys = (
        "title",
        "url",
        "image",
        "backdrop",
        "plot",
        "tags",
        "rating",
        "year",
        "country",
        "actors",
        "duration",
    )
    return dict((key, info.get(key, "")) for key in keys)


def resolve_source(site, extractor, page_url, source):
    result = {
        "label": source.get("label", ""),
        "video_id": source.get("video_id", ""),
        "play_url": source.get("url", ""),
        "is_trailer": bool(source.get("is_trailer")),
        "iframe": "",
        "stream": "",
        "subtitles": [],
        "error": "",
    }

    try:
        if source.get("is_trailer"):
            stream, subtitles = extractor.resolve(source.get("url", ""), page_url)
            result["stream"] = stream or ""
            result["subtitles"] = subtitles or []
            return result

        iframe = site.fetch_source_iframe(source.get("video_id", ""), page_url)
        result["iframe"] = iframe or ""
        if iframe:
            stream, subtitles = extractor.resolve(iframe, page_url)
            result["stream"] = stream or ""
            result["subtitles"] = subtitles or []
    except Exception as exc:
        result["error"] = repr(exc)

    return result


def inspect_url(url, user_agent):
    site = HDFilmCehennemiSite(base_url_from(url), user_agent)
    extractor = VideoExtractor(user_agent)

    page = site.get(url, ajax=True)
    print(page)

    info = site.parse_detail(page, url)
    episodes = info.get("episodes") or []
    sources = info.get("sources") or []

    output = {
        "input_url": url,
        "base_url": site.base_url,
        "type": "series" if episodes else "movie_or_episode",
        "media_info": public_media_info(info),
        "episodes": episodes,
        "play_links": sources,
        "resolved_sources": [],
    }

    if episodes:
        first_episode = episodes[0]
        episode_page = site.get(first_episode["url"])
        episode_info = site.parse_detail(episode_page, first_episode["url"])
        episode_sources = episode_info.get("sources") or []
        output["first_episode"] = {
            "media_info": public_media_info(episode_info),
            "episode": first_episode,
            "play_links": episode_sources,
            "resolved_sources": [
                resolve_source(site, extractor, first_episode["url"], source)
                for source in episode_sources
                if not source.get("is_trailer")
            ],
        }
    else:
        output["resolved_sources"] = [
            resolve_source(site, extractor, url, source)
            for source in sources
            if not source.get("is_trailer")
        ]

    return output

def page_items(url, user_agent):
    site = HDFilmCehennemiSite(base_url_from(url), user_agent)
    page = site.get_page_items(url)
    print(page)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="HDFilmCehennemi media info, play link ve gercek video kaynaklarini test eder."
    )
    parser.add_argument("url", help="Film, dizi veya bolum URL'si")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="Isteklerde kullanilacak User-Agent")
    args = parser.parse_args(argv)

    page_items(args.url, args.user_agent)

    # data = inspect_url(args.url, args.user_agent)
    # print(data)
    # print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
