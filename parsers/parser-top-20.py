import time
import json
import uuid
import logging
import random
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from curl_cffi import requests

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SITE_URL = 'https://top20.ua/'
session = requests.Session()
CLIENT_ID = str(uuid.uuid4())

def make_record_id(city, name, street):
    raw = f"{city}|{name}|{street}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def get_cities():
    cities = {}
    response = session.get(SITE_URL, impersonate='chrome120', timeout=60)
    soup = BeautifulSoup(response.text, 'html.parser')
    city_tag = soup.find_all('a', class_='p-4')
    for city in city_tag:
        slug = city.get('href').strip('/')
        name = city.text.strip()
        cities[slug] = name
    logger.debug(cities)
    return cities

def get_phone(slug, address_id, company_url):
    data = {
        'address': address_id,
        'callTracking': 'true',
        'user': CLIENT_ID,
    }
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': company_url
    }

    try:
        response = session.post(f'{SITE_URL}{slug}/company/phone', data=data, headers=headers, impersonate='chrome120')
        if response.status_code != 200:
            return None
        return response.json()
    except Exception as e:
        logger.exception(f'Phone error for {address_id}')
        return None

def get_items(page_url, slug, name, page):
    response = session.get(page_url, impersonate='chrome120', timeout=60)
    soup = BeautifulSoup(response.text, 'html.parser')
    cards = soup.find_all('div', class_='card js-company')
    if page > 1 and response.url != page_url:
        logger.debug(f'Requested: {page_url} | Got: {response.url}')
        return []
    logger.debug(f'Page {page_url} — {len(cards)} cards')
    results = []
    for item in cards:
        results.append(parse_item(item, slug, name))
    return results

def parse_item(card, slug, name):
    title_tag = card.find('div', class_='caption-title')
    title = title_tag.text.strip() if title_tag else None

    link_tag = title_tag.find('a') if title_tag else None
    card_url = link_tag.get('href') if link_tag else None

    street_tag = card.find('a', attrs={'data-address-id': True})
    street = street_tag.text.strip() if street_tag else None
    address_id = street_tag.get('data-address-id') if street_tag else None

    phone = None
    if address_id and card_url:
        phone_data = get_phone(slug, address_id, card_url)
        if phone_data and isinstance(phone_data, list):
            phone = phone_data[0].get('phone')

    record = {
        'name': title,
        'city': name,
        'street': street,
        'phoneNumber': phone,
        'scraped_at': datetime.now(timezone.utc).isoformat(),
    }
    record['record_id'] = make_record_id(record['city'], record['name'], record['street'])
    return record

def run():
    cities = get_cities()

    BASE_URL = SITE_URL + '{city}/avto-moto/page/{page}/'

    all_results = []
    for slug, name in cities.items():
        page = 1

        while True:
            logger.debug(f'City: {name}, page: {page}')
            page_url = BASE_URL.format(city=slug, page=page)

            items = get_items(page_url, slug, name, page)

            if not items:
                break

            all_results.extend(items)

            page += 1
            time.sleep(random.uniform(0.2, 0.5))

    with open('results_top_20.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False)

if __name__ == '__main__':
    run()
