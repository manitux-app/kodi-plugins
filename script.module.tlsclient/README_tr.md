# script.module.tlsclient

[`bogdanfinn/tls-client`](https://github.com/bogdanfinn/tls-client) native paylasimli kutuphanelerini `ctypes` ile saran Kodi Python module add-on paketi.

Modul, calisma aninda dogru native kutuphaneyi `resources/bin` altindan yukler ve Kodi eklentileri icin kucuk bir Python API sunar.

## Kullanim

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

Kisa yol fonksiyonlari da kullanilabilir:

```python
import tlsclient

response = tlsclient.post(
    "https://httpbin.org/post",
    json={"hello": "world"},
)

print(response.json())
```

## Desteklenen Platformlar

Upstream `v1.14.0` surumunden gelen native kutuphaneler:

- macOS amd64 / arm64
- Linux amd64 / arm64 / armv7
- Windows 32-bit / 64-bit

Android ABI klasorleri hazir:

- `arm64-v8a`
- `armeabi-v7a`
- `x86_64`

Android kutuphanelerini buraya koyun:

```text
resources/bin/android/arm64-v8a/libtlsclient.so
resources/bin/android/armeabi-v7a/libtlsclient.so
resources/bin/android/x86_64/libtlsclient.so
```

## API Notlari

`Session` yaygin istek seceneklerini destekler:

- `headers`
- `timeout`
- `verify`
- `proxy`
- `client_identifier`
- `random_tls_extension_order`
- `force_http1`
- `disable_http3`
- `with_protocol_racing`

Her istek bir `Response` nesnesi dondurur:

- `status_code`
- `headers`
- `content`
- `text`
- `json()`
- `ok`
- `raise_for_status()`

## Import Uyumlulugu

İki import bicimi de desteklenir:

```python
import tlsclient
import tls_client
```

## Native Kutuphane Yerlesimi

Runtime loader platform kutuphanelerini su konumlarda arar:

```text
resources/bin/<platform>/...
resources/bin/android/<abi>/...
```

Indirilen native asset hash bilgileri burada tutulur:

```text
resources/bin/MANIFEST.json
```
