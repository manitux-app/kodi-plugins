# Paketleme Scriptleri

Bu klasordeki scriptler Kodi eklentilerini repository yapisina paketler.

Scriptler sunlari yapar:

- `addon.xml` surumunu istege bagli gunceller.
- `repository.manitux/addons.xml` icindeki ilgili addon kaydini gunceller.
- `repository.manitux/<addon-id>/<addon-id>-<version>.zip` dosyasini uretir.
- `repository.manitux/addons.xml.md5` dosyasini yeniler.

## Windows / PowerShell

Mevcut surumle paketle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-addon.ps1 -AddonId plugin.video.dizibox
```

Patch surumunu artirip paketle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-addon.ps1 -AddonId plugin.video.dizibox -BumpPatch
```

Belirli surume cekip paketle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-addon.ps1 -AddonId plugin.video.dizibox -Version 1.0.2
```

## Linux / macOS

Mevcut surumle paketle:

```bash
bash scripts/package-addon.sh --addon-id plugin.video.dizibox
```

Patch surumunu artirip paketle:

```bash
bash scripts/package-addon.sh --addon-id plugin.video.dizibox --bump-patch
```

Belirli surume cekip paketle:

```bash
bash scripts/package-addon.sh --addon-id plugin.video.dizibox --version 1.0.2
```

Calistirmadan once executable yapmak istersen:

```bash
chmod +x scripts/package-addon.sh
./scripts/package-addon.sh --addon-id plugin.video.dizibox
```

## Parametreler

- `AddonId` / `--addon-id`: Paketlenecek eklenti klasoru. Varsayilan: `plugin.video.dizibox`.
- `Version` / `--version`: Eklentiyi belirtilen surume ceker.
- `BumpPatch` / `--bump-patch`: `major.minor.patch` formatindaki patch degerini 1 artirir.
- `RepositoryId` / `--repository-id`: Repository klasoru. Varsayilan: `repository.manitux`.

`--version` ve `--bump-patch` birlikte kullanilmaz.
