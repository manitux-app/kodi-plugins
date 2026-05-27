# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import client

# import  cloudscraper
# scraper = cloudscraper.create_scraper()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://hdfilmcehennemi.nl",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "X-Requested-With": "fetch"
}

url = "https://hdfilmcehennemi.nl/load/page/2/genres/bilim-kurgu-filmlerini-izleyin-5/"

#response = scraper.get(url, headers=headers)
# session = client.Session(headers=headers, use_cloudscraper=False)
session = client.Session()
response = session.get(url, headers=headers)

print(response.status_code)
print(response.text)
