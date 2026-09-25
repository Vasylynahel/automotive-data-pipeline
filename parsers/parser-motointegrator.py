import logging
from curl_cffi import requests
import time
import json

from parsers.config import Config

logger = logging.getLogger("motointegrator")
logger.setLevel(Config.LOG_LEVEL)
logger.addHandler(logging.StreamHandler())

BASE_URL = "https://motointegrator.com/api/search/v4/workshop"

PARAMS = {
    'locale': 'uk',
    'market': 'UA',
    'perPage': 100
}

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Cookie': 'cf_clearance=A3jkHjBd98XuPI9EImXVeQhUcCFs89ZYsudznXjoMj4-1779955371-1.2.1.1-e4kUGiYvH8IN5clICbr_ZTrmeDswfJOgHZAy0BiUGMRVM6Jbu2dmSg_zYwkMpdtCfeOzN8Z89igEZqoD8amlXuKUGocvIH7j2.55FQem75gLaoaRWNJzyhLe0Ztn8F5f7tcbhKSk0VcPl8XruFVzM8TmXflMLQnLiqrXWZj1hDeov2LixNn6IZi.9XgtTCHZMGlSol0eHqv17RvyjFY1biZ4ow1og4tJEtGrzVbhtF2P5rGlDoS4VvT7wBd0u.AiEISR_tlzk9otuQ3etVKBJooAOv231YTJRffsqn02DPSGlGGsWhlr_dzUx1WtmVF6NYm4MwT2pU51IqoQmUnEeA; _ga_0Q7HBR042X=GS2.1.s1779955370$o1$g0$t1779955636$j60$l0$h0; _ga=GA1.1.604624852.1779955370; CookieScriptConsent={"googleconsentmap":{"ad_storage":"targeting","analytics_storage":"performance","ad_personalization":"targeting","ad_user_data":"targeting","functionality_storage":"functionality","personalization_storage":"functionality","security_storage":"functionality"},"bannershown":1}',
    'Host': 'motointegrator.com',
    'Priority': 'u=0, i',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0',
}

all_results = []
page = 1

session = requests.Session()

while True:
    response = session.get(BASE_URL, impersonate="chrome120", timeout=15, params={**PARAMS, 'page': page}, headers=HEADERS)
    logger.info(f"Page: {page}")
    logger.debug(f"status code: {response.status_code}")

    if response.status_code == 403:
        logger.exception(f"Заблоковано на сторінці {page}, збережено {len(all_results)} записів")
        time.sleep(4)

        continue

    data = response.json()
    logger.debug(f"elements on page: {len(data['results'])}\n")

    if len(data['results']) == 0:
        break

    all_results.extend(data['results'])

    page += 1

    time.sleep(1)

results = [{'name': item['name'], 'city': item['address']['locality'], 'street': item['address']['street'], 'phoneNumber': item['phoneNumber']} for item in all_results]

with open('results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False)

logger.info(f"завершено на сторінці {page}, збережено {len(all_results)} записів")

