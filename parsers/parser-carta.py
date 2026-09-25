import requests
import logging
import json
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = 'https://carta.ua/sto/'
ITEM_URL = 'https://carta.ua'

session = requests.Session()

def get_item(url):
    items = []
    page = 1

    while True:
        response = session.get(f'{BASE_URL}/?page={page}', timeout = 15)
        soup = BeautifulSoup(response.text, 'html.parser')

        cards = soup.find_all('div', class_='facility-list-card')
        logger.debug(f'{url}: на сторінці {page}, знайдено {len(cards)} карток.')

        if not cards:
            break

        for card in cards:
            name_tag = card.select_one('.card-title a[title]')

            if not name_tag:
                logger.exception("Не знайдено card_name")
                continue

            name = name_tag.text.strip()

            address_div = card.find('div', class_='card-content-row addres')
            address_tag = address_div.find('div', class_='text-wrap')

            if not address_tag:
                logger.exception("Не знайдено card_address")
                continue

            address = address_tag.text.strip()
            address_strip = address.split(',', 1)
            city = address_strip[0].strip()
            street = address_strip[1].strip()

            phone_tag = card.select_one('.card-content-row a[href]')
            phone_url = phone_tag['href']

            phoneNumber = get_phone(phone_url)

            items.append({
                'name': name,
                'city': city,
                'street': street,
                'phoneNumber': phoneNumber
            })

        page += 1
    return items

def get_phone(phone_url):
    response = session.get(f'{ITEM_URL}{phone_url}', timeout = 10)
    soup = BeautifulSoup(response.text, 'html.parser')

    phone_tag = soup.find('script', type='application/ld+json')
    data = json.loads(phone_tag.text)

    if not phone_tag:
        return None

    phones = data.get('telephone', [])

    return phones

def run():
    items = get_item(BASE_URL)

    with open('results_carta_ua.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False)

    logger.debug(f'Збережено {len(items)} записів')

if __name__ == '__main__':
    run()
