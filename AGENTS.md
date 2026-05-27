# AGENTS.md

Bu dosya, Codex'in bu repoda yeni oturumlarda baglami hizlica yeniden kurmasi icin tutulur.

## Proje

Bu repo Manitux Kodi eklentilerini ve ilgili repository/script modullerini icerir.

Baslica klasorler:

- `plugin.video.dizibox`: Dizibox video eklentisi.
- `plugin.video.filmekseni`: Filmekseni video eklentisi.
- `plugin.video.filmmakinesi`: Filmmakinesi video eklentisi.
- `plugin.video.filmmodu`: Filmmodu video eklentisi.
- `plugin.video.hdfilmcehennemi`: Hdfilmcehennemi video eklentisi.
- `repository.manitux`: Kodi repository paketi.
- `script.manitux.repoinstaller`: Repo yukleyici script.
- `script.module.manituxhttp`: Paylasilan HTTP yardimci modulu.
- `script.module.tlsclient`: TLS client modulu.

## Calisma Kurallari

- Mevcut eklenti yapisini ve dosya stilini koru.
- Kullanici degisikliklerini geri alma; once mevcut farklari kontrol et.
- Elle dosya duzenlerken `apply_patch` kullan.
- Arama icin once `rg` veya `rg --files` kullan.
- Eklenti davranisini etkileyen degisikliklerde mumkunse ilgili modulu calistirarak veya statik kontrolle dogrula.
- Paket/zip dosyalarini, surum artirimini ve repository metadata paketleme guncellemelerini kullanici acikca paketleme istediginde yap. Kod degisikligi sonrasi kullanici "paketle" demedikce zip uretme veya surum artirma.
- Paketleme yapilirken zip dosyasi `repository.manitux/<addon-id>/` altina atilir ve ilgili eklentinin `icon.png` dosyasi da ayni klasore kopyalanir; mevcut icon varsa uzerine yazilir.

## Hatirlanacaklar

- Onemli kararlar ve tamamlanan isler `CHANGELOG.md` dosyasina kisa not olarak eklenmeli.
- Yeni oturumda once bu dosya, sonra `CHANGELOG.md`, sonra ilgili eklentinin dosyalari okunmali.
- Plugin ve extractor ornekleri icin once `providers\TurkishProviders` altindaki dosyalardan bilgi alinmali. Bu klasor calisma agacinda yoksa kullaniciya belirtilmeli ve mevcut repo baglamiyla devam edilmeli.
- Scrape ve extract ornekleri icin `providers\TurkishProviders`; eski/alternatif extract ornekleri icin `providers\SeyirTurk\parsers.py` dosyasi referans alinabilir.
- Scrape/extract sorunlarinda tahmini duzeltme yapma. Mumkunse once gercek canli HTML/player verisini cek, parser/extractor sonucunu bu veriyle dogrula, sonra kodu degistir. Canli erisim sandbox veya ag izni gerektirirse izin iste.
- Poster/thumb/icon/fanart URL'leri 403 verirse diger pluginlerde de Kodi `setArt` oncesi `|User-Agent=...&Referer=...` header suffix'i uygulanmali. Dizibox icindeki `art_url()` / `set_art()` yaklasimi referans alinabilir.
- Uzantisiz HLS/master playlist URL'leri Kodi'de oynatilamazsa canli playlist icerigi okunup en uygun varyant URL'si secilmeli; Kodi `ListItem` icin `application/vnd.apple.mpegurl` mime type ve `setContentLookup(False)` ayarlanmalidir. Dizibox DBXPro `/embed/sheila/` cozumlemesi referans alinabilir.
- Windows Kodi log dosyasi: `C:\Users\metek\AppData\Roaming\Kodi\kodi.log`. Kullanici Kodi tarafinda test ettigini soylediginde bu dosya saat bilgisine gore kontrol edilmeli; Linux log yolu kullanici tarafindan ayrica verilecek.
