# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json
import os
import zipfile

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen


ADDON = xbmcaddon.Addon()
TITLE = ADDON.getAddonInfo("name")
DEFAULT_SERVICE = "https://tinyurl.com/"
USER_AGENT = "Mozilla/5.0 (Kodi; Manitux Repo Installer)"


def text(string_id):
    return ADDON.getLocalizedString(string_id)


def main():
    dialog = xbmcgui.Dialog()
    mode = dialog.select(TITLE, [text(30016), text(30017)])
    if mode == -1:
        return

    is_repository = mode == 0
    value = dialog.input(text(30000), defaultt="mntxrepo" if is_repository else "")
    if not value:
        return

    short_url = normalize_short_url(value)
    try:
        zip_url = resolve_url(short_url)
    except Exception as exc:
        notify(text(30006), str(exc), xbmcgui.NOTIFICATION_ERROR)
        return

    found_message = text(30003) if is_repository else text(30020)
    if not zip_url.lower().endswith(".zip"):
        if not dialog.yesno(TITLE, text(30001), zip_url, text(30002)):
            return
    elif not dialog.yesno(TITLE, found_message, zip_url, text(30004)):
        return

    try:
        zip_path = download(zip_url)
        addon_id = install_addon_zip(zip_path, is_repository)
        enable_addon(addon_id)
        xbmc.executebuiltin("UpdateLocalAddons")
        if is_repository:
            xbmc.executebuiltin("UpdateAddonRepos")
        notify(text(30008) if is_repository else text(30021), addon_id, xbmcgui.NOTIFICATION_INFO)
    except Exception as exc:
        notify(text(30009) if is_repository else text(30022), str(exc), xbmcgui.NOTIFICATION_ERROR)


def normalize_short_url(value):
    value = (value or "").strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return DEFAULT_SERVICE + value.lstrip("/")


def resolve_url(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        request = Request(url, headers=headers, method="HEAD")
        response = urlopen(request, timeout=20)
        return response.geturl()
    except TypeError:
        request = Request(url, headers=headers)
        response = urlopen(request, timeout=20)
        return response.geturl()
    except Exception:
        request = Request(url, headers=headers)
        response = urlopen(request, timeout=20)
        return response.geturl()


def download(url):
    temp_dir = translate_path("special://temp")
    target = os.path.join(temp_dir, "manitux-addon.zip")
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, text(30005))
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        response = urlopen(request, timeout=30)
        total = int(response.headers.get("content-length") or 0)
        received = 0
        with open(target, "wb") as handle:
            while True:
                if progress.iscanceled():
                    raise RuntimeError(text(30007))
                chunk = response.read(1024 * 64)
                if not chunk:
                    break
                handle.write(chunk)
                received += len(chunk)
                percent = int((received * 100) / total) if total else 0
                progress.update(percent, text(30005))
        return target
    finally:
        progress.close()


def install_addon_zip(zip_path, is_repository):
    addons_dir = translate_path("special://home/addons")
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = [name for name in archive.namelist() if name and not name.endswith("/")]
        root = find_zip_root(names)
        if not root:
            raise RuntimeError(text(30010))
        addon_xml = root + "/addon.xml"
        if addon_xml not in names:
            raise RuntimeError(text(30011))
        addon_id = read_addon_id(archive.read(addon_xml).decode("utf-8", "replace"))
        if is_repository and not addon_id.startswith("repository."):
            raise RuntimeError(text(30012).format(addon_id))
        if not is_repository and not addon_id.startswith("plugin."):
            raise RuntimeError(text(30023).format(addon_id))
        extract_safe(archive, addons_dir)
    return addon_id


def find_zip_root(names):
    roots = set()
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if parts:
            roots.add(parts[0])
    return roots.pop() if len(roots) == 1 else ""


def read_addon_id(addon_xml):
    marker = 'id="'
    start = addon_xml.find(marker)
    if start == -1:
        raise RuntimeError(text(30013))
    start += len(marker)
    end = addon_xml.find('"', start)
    if end == -1:
        raise RuntimeError(text(30014))
    return addon_xml[start:end]


def extract_safe(archive, target_dir):
    target_dir = os.path.abspath(target_dir)
    for member in archive.infolist():
        destination = os.path.abspath(os.path.join(target_dir, member.filename))
        if not destination.startswith(target_dir + os.sep):
            raise RuntimeError(text(30015).format(member.filename))
    archive.extractall(target_dir)


def enable_addon(addon_id):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Addons.SetAddonEnabled",
        "params": {"addonid": addon_id, "enabled": True},
    }
    xbmc.executeJSONRPC(json.dumps(payload))


def translate_path(path):
    if hasattr(xbmcvfs, "translatePath"):
        return xbmcvfs.translatePath(path)
    return xbmc.translatePath(path).decode("utf-8")


def notify(heading, message, icon):
    xbmcgui.Dialog().notification(heading, message, icon, 5000)


if __name__ == "__main__":
    main()
