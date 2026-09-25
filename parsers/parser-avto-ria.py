import logging
import json
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://auto.ria.com/uk/autoservice/sto/'
URL_FOR_PHONE = 'https://auto.ria.com'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

def get_phone(service_url):
    response = session.get(f'{URL_FOR_PHONE}{service_url}', headers=headers, timeout=10)
    service_soup = BeautifulSoup(response.text, 'html.parser')

    phone_tag = service_soup.find_all('label', class_='button--green')
    phones = [tag.get('data-phone', '') for tag in phone_tag]
    phones.sort()
    return phones

def get_cities():
    response = session.get(BASE_URL, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')

    cities = []
    for link in soup.select('.seo-catalog-main a[href]'):
        href = link.get('href', '')
        slug = href.strip('/').split('/')[-1]
        if slug.startswith('city-'):
            cities.append(slug)

    return cities


def get_items(city):
    items = []
    page = 1

    while True:
        url = f'{BASE_URL}{city}/?page={page}'
        response = session.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.find_all('div', class_='proposition')

        logger.debug(f'{city} - {url}: на сторінці {page}, знайдено {len(cards)} карток.')

        if not cards:
            break

        for card in cards:

            name_tag = card.find('div', class_='proposition_name')

            if not name_tag:
                logger.exception("Не знайдено proposition_name")
                continue

            name = name_tag.text.strip()

            address_tag = card.select_one('span.link:has(svg.i16_pin)')
            if not address_tag:
                continue
            address = address_tag.text.strip()

            street = ''

            if ',' in address:
                city_tag, street_tag = address.split(',', 1)
                city_name = city_tag.strip()
                street = street_tag.strip()
            else:
                city_name = address.strip()

            link = card.find('a', class_='proposition_link')

            if not link:
                continue

            service_url = link.get('href', '')

            if not service_url:
                continue

            phone = get_phone(service_url)

            items.append ({
                 'name': name,
                 'city': city_name,
                 'street': street,
                 'phoneNumber': phone
                })

        page += 1
    return items

def run():
    cities = get_cities()

    with open('avto-ria-cities.json', 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)

    all_items = []

    for city in cities:
        all_items.extend(get_items(city))

    with open('results_avto_ria.json', 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False)

    logger.debug(f'Збережено {len(all_items)} записів')

if __name__ == '__main__':
    run()