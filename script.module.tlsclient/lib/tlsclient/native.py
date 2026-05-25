import ctypes
import json
import os
import platform
import struct
from typing import Any, Dict, Iterable, Tuple


class NativeLibraryError(RuntimeError):
    pass


_LIB = None


def call(function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    lib = load_library()
    func = getattr(lib, function_name)
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ptr = func(ctypes.c_char_p(raw))
    if not ptr:
        raise NativeLibraryError("%s returned null" % function_name)

    response_bytes = ctypes.string_at(ptr)
    try:
        response = json.loads(response_bytes.decode("utf-8"))
    finally:
        _free_response(lib, response_bytes)
    return response


def load_library():
    global _LIB
    if _LIB is not None:
        return _LIB

    path = library_path()
    try:
        lib = ctypes.CDLL(path)
    except OSError as exc:
        raise NativeLibraryError("Failed to load tls-client native library at %s: %s" % (path, exc))

    for name in (
        "request",
        "destroySession",
        "getCookiesFromSession",
        "addCookiesToSession",
    ):
        func = getattr(lib, name)
        func.argtypes = [ctypes.c_char_p]
        func.restype = ctypes.c_void_p

    lib.destroyAll.argtypes = []
    lib.destroyAll.restype = ctypes.c_void_p
    lib.freeMemory.argtypes = [ctypes.c_char_p]
    lib.freeMemory.restype = None

    _LIB = lib
    return lib


def library_path() -> str:
    system = platform.system().lower()
    arch = _machine()
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources", "bin"))

    if _is_android():
        path = _first_existing(base, _android_candidates(arch))
        if path:
            return path
        raise NativeLibraryError("No Android tls-client native library for ABI %s" % _android_abi(arch))

    candidates = []
    if system == "linux":
        if arch in ("x86_64", "amd64"):
            candidates.append(("linux-amd64", "libtls-client.so"))
        elif arch in ("aarch64", "arm64"):
            candidates.append(("linux-arm64", "libtls-client.so"))
        elif arch.startswith("arm"):
            candidates.append(("linux-armv7", "libtls-client.so"))
    elif system == "darwin":
        if arch in ("x86_64", "amd64"):
            candidates.append(("darwin-amd64", "libtls-client.dylib"))
        elif arch in ("aarch64", "arm64"):
            candidates.append(("darwin-arm64", "libtls-client.dylib"))
    elif system == "windows":
        if struct.calcsize("P") * 8 == 64:
            candidates.append(("windows-amd64", "tls-client.dll"))
        else:
            candidates.append(("windows-x86", "tls-client.dll"))

    for folder, filename in candidates:
        path = os.path.join(base, folder, filename)
        if os.path.exists(path):
            return path

    raise NativeLibraryError("No tls-client native library for %s/%s" % (system, arch))


def destroy_all() -> Dict[str, Any]:
    lib = load_library()
    ptr = lib.destroyAll()
    if not ptr:
        raise NativeLibraryError("destroyAll returned null")
    response_bytes = ctypes.string_at(ptr)
    try:
        response = json.loads(response_bytes.decode("utf-8"))
    finally:
        _free_response(lib, response_bytes)
    return response


def _free_response(lib, response_bytes: bytes) -> None:
    try:
        response = json.loads(response_bytes.decode("utf-8"))
    except ValueError:
        return
    response_id = response.get("id")
    if response_id:
        lib.freeMemory(ctypes.c_char_p(str(response_id).encode("utf-8")))


def _machine() -> str:
    machine = platform.machine().lower()
    if machine in ("i386", "i686", "x86"):
        return "x86"
    return machine


def _is_android() -> bool:
    if "ANDROID_ARGUMENT" in os.environ or "ANDROID_ROOT" in os.environ:
        return True
    try:
        import xbmc  # type: ignore

        return bool(xbmc.getCondVisibility("System.Platform.Android"))
    except Exception:
        return False


def _android_abi(arch: str) -> str:
    bits = struct.calcsize("P") * 8
    if arch in ("aarch64", "arm64"):
        return "arm64-v8a" if bits == 64 else "armeabi-v7a"
    if arch in ("x86_64", "amd64"):
        return "x86_64" if bits == 64 else "x86"
    if arch == "x86":
        return "x86"
    return "armeabi-v7a"


def _android_candidates(arch: str) -> Iterable[Tuple[str, str]]:
    abi = _android_abi(arch)
    aliases = [abi]
    if abi == "x86_64":
        aliases.append("x86-64")

    for alias in aliases:
        yield (os.path.join("android", alias), "libtlsclient.so")
        yield (os.path.join("android", alias), "libtls-client.so")
        yield (alias, "libtlsclient.so")
        yield (alias, "libtls-client.so")

    legacy = {
        "arm64-v8a": "android-arm64",
        "armeabi-v7a": "android-armv7",
        "x86_64": "android-amd64",
        "x86": "android-x86",
    }
    if abi in legacy:
        yield (legacy[abi], "libtlsclient.so")
        yield (legacy[abi], "libtls-client.so")


def _first_existing(base: str, candidates: Iterable[Tuple[str, str]]) -> str:
    for folder, filename in candidates:
        path = os.path.join(base, folder, filename)
        if os.path.exists(path):
            return path
    return ""
