# script.module.tlsclient

[Turkce dokumantasyon](README_tr.md)

Kodi Python module add-on that wraps the native [`bogdanfinn/tls-client`](https://github.com/bogdanfinn/tls-client) shared libraries through `ctypes`.

The module loads the correct native library from `resources/bin` at runtime and exposes a small Python API for Kodi add-ons.

## Usage

```python
from tlsclient import Session

session = Session(
    headers={"User-Agent": "Kodi"},
    client_identifier="chrome_146",
)

response = session.get("https://example.com")

if response.ok:
    print(response.text)
```

Shortcut functions are also available:

```python
import tlsclient

response = tlsclient.post(
    "https://httpbin.org/post",
    json={"hello": "world"},
)

print(response.json())
```

## Supported Platforms

Bundled native libraries from upstream `v1.14.0`:

- macOS amd64 / arm64
- Linux amd64 / arm64 / armv7
- Windows 32-bit / 64-bit

Android ABI folders are prepared for:

- `arm64-v8a`
- `armeabi-v7a`
- `x86_64`

Place Android libraries here:

```text
resources/bin/android/arm64-v8a/libtlsclient.so
resources/bin/android/armeabi-v7a/libtlsclient.so
resources/bin/android/x86_64/libtlsclient.so
```

## API Notes

`Session` supports common request options:

- `headers`
- `timeout`
- `verify`
- `proxy`
- `client_identifier`
- `random_tls_extension_order`
- `force_http1`
- `disable_http3`
- `with_protocol_racing`

Each request returns a `Response` object with:

- `status_code`
- `headers`
- `content`
- `text`
- `json()`
- `ok`
- `raise_for_status()`

## Import Compatibility

Both import styles are supported:

```python
import tlsclient
import tls_client
```

## Native Library Layout

The runtime loader searches for platform libraries under:

```text
resources/bin/<platform>/...
resources/bin/android/<abi>/...
```

The downloaded native asset hashes are recorded in:

```text
resources/bin/MANIFEST.json
```
