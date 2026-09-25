from bs4 import BeautifulSoup
from curl_cffi import requests
import re
import json

session = requests.Session()

BASE_URL = 'https://ua.motul.store/partners/'

def get_phone(item):
    info_tel_tag = item.find('div', class_='info__tel')

    phone_numbers = []

    if info_tel_tag:
        for phone_link in info_tel_tag.find_all('a', href=re.compile(r'^tel:')):
            phone = phone_link.get('href').replace('tel:', '').strip()
            for p in phone.split(','):
                p = p.strip()
                if p:
                    phone_numbers.append(p)
    phone_numbers.sort()
    return phone_numbers

def get_data():
    motul_items = []
    response = session.get(BASE_URL, timeout = 10)
    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.find_all('div', class_='partners__item')
    for item in items:
        item_name = item.find('div', class_='h2-h2').text

        city_name = item.get('data-city')

        info_col = item.find('div', class_='info__col')
        street = info_col.find_all('div')[1].text

        phone_numbers = get_phone(item)

        item_data = {
            'name': item_name,
            'city': city_name,
            'street': street,
            'phoneNumber': phone_numbers
        }

        motul_items.append(item_data)
    return motul_items

def run():
    results = get_data()

    with open('results_motul_store.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False)

if __name__ == '__main__':
    run()