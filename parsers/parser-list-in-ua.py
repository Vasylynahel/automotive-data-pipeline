import logging
import json, time
from bs4 import BeautifulSoup
from curl_cffi import requests
from parsers.config import Config
from urllib.parse import unquote, urlparse, parse_qs

logger = logging.getLogger('list.in.ua')
logger.setLevel(Config.LOG_LEVEL)
logger.addHandler(logging.StreamHandler())

session = requests.Session()

START_URL = 'https://list.in.ua/Львів/СТО'
CATEGORY_NAME = unquote(START_URL.rstrip('/').split('/')[-1])


def collect_categories(cities):
    category_ids = set()

    for city_url in cities:
        retries = 3

        while retries > 0:
            try:
                city = unquote(city_url.split('/')[3])
                logger.debug(f'Місто: {city}')

                clean_city_url = city_url.split('?')[0].rstrip('/')

                if clean_city_url.endswith(f'/{CATEGORY_NAME}'):
                    category_url = clean_city_url
                else:
                    category_url = f'{clean_city_url}/{CATEGORY_NAME}'

                response_category = session.get(
                    category_url,
                    impersonate='chrome120',
                    timeout=60
                )

                soup = BeautifulSoup(response_category.text, 'html.parser')
                query_string = soup.find_all('a', class_='cat-filter__link')

                logger.debug(f'Категорій: {len(query_string)}')

                time.sleep(0.3)

                for a in query_string:
                    category_params = a['href']
                    params = parse_qs(urlparse(category_params).query)

                    if 'category' in params:
                        category_id = params['category'][0]
                        category_ids.add(category_id)

                break

            except Exception as e:
                retries -= 1
                logger.exception(f'Помилка для {city_url}: {e}')
                time.sleep(15)
                continue

    return category_ids


def get_cities(url):
    try:
        time.sleep(0.2)
        response = session.get(url, impersonate='chrome120', timeout=60)

        soup = BeautifulSoup(response.text, 'html.parser')
        cities = soup.find('div', class_='geo-cities-new')

        if cities is None:
            logger.info('City is empty')
            return []

        city = cities.find_all('a', href=True)
        results = []

        for item in city:
            url = item['href'].split('?')[0].rstrip('/')

            parts = url.split('/')

            if len(parts) >= 4:
                clean_url = f"{parts[0]}//{parts[2]}/{parts[3]}"
                results.append(clean_url)

        logger.debug(f'Знайдено міст: {len(results)}')

    except Exception as e:
        logger.exception(f'Помилка get_cities для {url}: {e}')
        return []

    return results


def get_items(url, category_id, page):
    try:
        response = session.get(url, impersonate='chrome120', timeout=15)

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='item-search')

        logger.debug(f'Категорія: {category_id}, сторінка: {page}, items: {len(items)}')

    except Exception as e:
        logger.exception(f'Помилка get_items для {url}: {e}')
        return []

    return items


def parse_item(item, city):
    name_tag = item.select_one('h2.item-search__title a')
    phone_tag = item.select_one('a[href^="tel:"]')
    phoneNumber = phone_tag.get('href', '').replace('tel:', '') if phone_tag else ''
    address_div = item.select_one("div.company-address")

    street = (
        (
            address_div.select_one("span.mobile-hide")
            or address_div.select_one("a.mobile-only-show-i")
            or address_div
        ).get_text(" ", strip=True)
        if address_div else ''
    )

    street = ' '.join(street.split())

    name = name_tag.get_text(strip=True) if name_tag else ''

    return {
        'name': name,
        'city': city,
        'street': street,
        'phoneNumber': phoneNumber
    }


cities = get_cities(START_URL)
categories = collect_categories(cities)

with open('category.json', 'w', encoding='utf_8') as f:
    json.dump(list(categories), f, ensure_ascii=False)

results = []

for city_url in cities:
    city = unquote(city_url.split('/')[3])
    logger.info(f'Місто: {city}')
    logger.info(f'URL: {city_url}')

    clean_city_url = city_url.split('?')[0].rstrip('/')

    for category_id in categories:
        page = 1

        while True:

            base_url = (
                clean_city_url
                if clean_city_url.endswith(f'/{CATEGORY_NAME}')
                else f'{clean_city_url}/{CATEGORY_NAME}'
            )

            url = f'{base_url}/page/{page}?category={category_id}'

            items = get_items(url, category_id, page)

            if not items:
                break

            for item in items:
                data = parse_item(item, city)

                if data['name']:
                    results.append(data)

            page += 1
            time.sleep(0.2)

with open('results_list_in_ua.json', 'w', encoding='utf_8') as f:
    json.dump(results, f, ensure_ascii=False)