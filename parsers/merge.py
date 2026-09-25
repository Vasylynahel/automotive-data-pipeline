import json
import logging
import re
import pandas as pd

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def normalize_single(p):
    p = re.sub(r'\D', '', str(p))
    if len(p) == 10 and p.startswith('0'):
        p = '38' + p
    return p

def normalize_phone(phone):
    if not phone:
        return ''
    if isinstance(phone, list):
        return ', '.join(normalize_single(p) for p in phone)
    return normalize_single(phone)

def load_and_tag(file, source):
    with open(file) as f:
        data = json.load(f)
        for item in data:
            item['source'] = source
    logger.debug(f"[ЗЧИТАНО] Файл {file}: додано {len(data)} записів з джерела '{source}'")
    return data

file_sources = {
    'results.json': 'motointegrator.com',
    'results_list_in_ua.json': 'list_in_ua',
    'results_top_20.json': 'top20.ua',
    'results_avto_ria.json': 'avto-ria.com',
    'results_motul_store.json': 'ua.motul.store',
    'results_pzu.json': 'pzu.com',
    'results_carta_ua.json': 'carta.ua'
}

def run():
    merged_results = []

    for key, value in file_sources.items():
        merged_results.extend(load_and_tag(key, value))

    logger.debug(f"[ОБ'ЄДНАНО] Всього зібрано {len(merged_results)} записів для перевірки на дублікати")

    seen_phones = set()
    results = []

    for item in merged_results:
        phone = normalize_phone(item.get('phoneNumber'))
        item['phoneNumber'] = phone

        if not phone:
            results.append(item)
            continue

        phones = [p.strip() for p in phone.split(',') if p.strip()]

        if any(p in seen_phones for p in phones):
            continue

        seen_phones.update(phones)
        results.append(item)

    with open('merged_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    df = pd.read_json('merged_results.json')
    df.to_excel('merged_results.xlsx', index=False)

    logger.debug(f"[ГОТОВО] Очищення завершено. Збережено {len(results)} унікальних записів в JSON та Excel.")


if __name__ == '__main__':
    run()