# CHANGELOG.md

Bu dosya, Codex ile yapilan onemli proje degisikliklerini kisa notlarla takip etmek icin tutulur.

## 2026-05-26

- `plugin.video.dizibox` surumu `1.0.1` olarak yukseltildi ve paketleme icin repo metadata'si guncellendi.
- Kodi eklentilerini surum guncelleyip repo zip'i uretecek `scripts/package-addon.ps1` paketleme scripti eklendi.
- Linux/macOS icin `scripts/package-addon.sh` paketleme scripti ve script kullanimlari icin `scripts/README.md` eklendi.
- Paketleme scriptleri zip'in yanina ilgili eklentinin `icon.png` dosyasini da kopyalayacak sekilde guncellendi.
- PowerShell paketleme scriptinde zip icindeki yollar Kodi uyumlulugu icin `/` ayiraci kullanacak sekilde duzeltildi.
- Kodi'nin bozuk `1.0.1` paket cache'ini asmak icin `plugin.video.dizibox` surumu `1.0.2` olarak paketlendi.
- Proje hafizasi icin `AGENTS.md` eklendi.
- Codex oturumlari arasinda yapilan isleri izlemek icin `CHANGELOG.md` eklendi.
- `plugin.video.dizibox` icinde fragman kaynaklarinin `DiziBox` yerine `Fragman` gorunmesi saglandi.
- `plugin.video.dizibox` player cozumleyicisinde site player iframe'leri, dogrudan medya URL'leri ve percent-escaped iframe kodlari daha toleransli cozuldu.
- Plugin/extractor ornekleri icin `providers\TurkishProviders` altindaki dosyalarin referans alinacagi proje hafizasina not edildi.
- `plugin.video.dizibox` ana menu kategorileri ag istegi olmadan sabit listeden donmeye basladi.
- `plugin.video.dizibox` dizi detayinda tum sezonlari pesin indirmek yerine sezon linkleri klasor olarak gosterilmeye basladi.
- `plugin.video.dizibox` dizi detayinda lazy-load poster alanlari, data tabanli player linkleri ve fragman/player etiketleri daha genis parse edilmeye baslandi.
- `plugin.video.dizibox` poster/art URL'lerine Kodi icin User-Agent ve Referer header suffix'i eklendi.
- Poster 403 sorununda ayni header suffix yaklasiminin diger pluginlere de uygulanmasi gerektigi proje hafizasina not edildi.
- `plugin.video.dizibox` player listesi `data-video`, `data-hash`, `data-id`, `data-type`, `data-player` ve script icindeki player URL'lerini de yakalayacak sekilde genisletildi.
- `plugin.video.dizibox` site ici `/player/...` URL'leri cozumlenemezse raw player sayfasi Kodi'ye gonderilmeyecek sekilde extractor guvenli hale getirildi.
- `plugin.video.dizibox` bolum listesinde genel/logo/player linklerinin bolum gibi gorunmesini engellemek icin episode parser sadece sezon/bolum kalibina uyan linkleri kabul edecek sekilde daraltildi.
- `plugin.video.dizibox` bolum veya sezon listesi olan sayfalarda player kaynaklarinin bolum satiri gibi basilmamasi icin kaynaklar sadece gercek bolum URL'lerinde gosterilecek sekilde ayrildi.
- `plugin.video.dizibox` oynatma kaynaklari TurkishProviders DiziBox modeline uygun olarak `div.video-toolbar option[value]` merkezli parse edilmeye baslandi; gereksiz King/DiziBox satirlari engellendi ve DBXPro, Moly+, Odnok etiketleri normalize edildi.
- `plugin.video.dizibox` oynatma kaynaklari canli DiziBox HTML'ine gore `option[href]` secili DBXPro kaynagini da okuyacak sekilde duzeltildi; DBXPro/Moly+/Odnok canli resolve ile dogrulandi.
- `plugin.video.dizibox` DBXPro/Molystream CryptoJS AES sayfalari ve `/embed/sheila/` HLS playlistleri extractor tarafinda desteklendi.
- `plugin.video.dizibox` dizi ana sayfasindaki YouTube fragmaninin bolum listesiyle birlikte gorunmesi canli sayfada dogrulandi.
- Scrape/extract islerinde tahmin yerine canli HTML/player verisiyle dogrulama yapilmasi gerektigi proje hafizasina not edildi.
- `plugin.video.dizibox` fragman parser'ina `div#trailer-box iframe[src|data-src]` destegi eklendi.
- `plugin.video.dizibox` DBXPro `/embed/sheila/` master playlistleri en yuksek HLS varyantina cozulmeye baslandi; uzantisiz HLS URL'leri icin Kodi ListItem mime type ayarlandi.
- Uzantisiz HLS/master playlist oynatma sorunlari icin DBXPro'da kullanilan varyant secme ve Kodi HLS mime ayari proje hafizasina referans cozum olarak eklendi.
- `plugin.video.dizibox` DBXPro CryptoJS AES cozumlemesi icin `script.module.pycryptodome` bagimliligi eklendi; HLS inputstream ayarlari `inputstream.adaptive` varsa uygulanacak sekilde guvenli hale getirildi.
- Scrape/extract referanslari icin `providers\TurkishProviders` ve alternatif extract referanslari icin `providers\SeyirTurk\parsers.py` proje hafizasina not edildi.
