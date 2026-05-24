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


def main():
    dialog = xbmcgui.Dialog()
    value = dialog.input(TITLE, defaultt="mntxrepo")
    if not value:
        return

    short_url = normalize_short_url(value)
    try:
        repo_url = resolve_url(short_url)
    except Exception as exc:
        notify("Kisa adres cozulmedi", str(exc), xbmcgui.NOTIFICATION_ERROR)
        return

    if not repo_url.lower().endswith(".zip"):
        if not dialog.yesno(TITLE, "Cozulen adres zip gibi gorunmuyor:", repo_url, "Devam edilsin mi?"):
            return
    elif not dialog.yesno(TITLE, "Repository zip adresi bulundu:", repo_url, "Kurulsun mu?"):
        return

    try:
        zip_path = download(repo_url)
        addon_id = install_repository_zip(zip_path)
        enable_addon(addon_id)
        xbmc.executebuiltin("UpdateLocalAddons")
        xbmc.executebuiltin("UpdateAddonRepos")
        notify("Repository kuruldu", addon_id, xbmcgui.NOTIFICATION_INFO)
    except Exception as exc:
        notify("Repository kurulamadi", str(exc), xbmcgui.NOTIFICATION_ERROR)


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
    target = os.path.join(temp_dir, "manitux-repository.zip")
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, "Repository zip indiriliyor")
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        response = urlopen(request, timeout=30)
        total = int(response.headers.get("content-length") or 0)
        received = 0
        with open(target, "wb") as handle:
            while True:
                if progress.iscanceled():
                    raise RuntimeError("Islem iptal edildi")
                chunk = response.read(1024 * 64)
                if not chunk:
                    break
                handle.write(chunk)
                received += len(chunk)
                percent = int((received * 100) / total) if total else 0
                progress.update(percent, "Repository zip indiriliyor")
        return target
    finally:
        progress.close()


def install_repository_zip(zip_path):
    addons_dir = translate_path("special://home/addons")
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = [name for name in archive.namelist() if name and not name.endswith("/")]
        root = find_zip_root(names)
        if not root:
            raise RuntimeError("Zip icinde eklenti klasoru bulunamadi")
        addon_xml = root + "/addon.xml"
        if addon_xml not in names:
            raise RuntimeError("Zip icinde addon.xml bulunamadi")
        addon_id = read_addon_id(archive.read(addon_xml).decode("utf-8", "replace"))
        if not addon_id.startswith("repository."):
            raise RuntimeError("Zip bir repository eklentisi degil: {0}".format(addon_id))
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
        raise RuntimeError("addon.xml icinde id bulunamadi")
    start += len(marker)
    end = addon_xml.find('"', start)
    if end == -1:
        raise RuntimeError("addon.xml icinde id okunamadi")
    return addon_xml[start:end]


def extract_safe(archive, target_dir):
    target_dir = os.path.abspath(target_dir)
    for member in archive.infolist():
        destination = os.path.abspath(os.path.join(target_dir, member.filename))
        if not destination.startswith(target_dir + os.sep):
            raise RuntimeError("Guvenli olmayan zip yolu: {0}".format(member.filename))
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
