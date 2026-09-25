import json
import re
import pdfplumber
import requests
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger('pdfplumber').setLevel(logging.WARNING)
logging.getLogger('pdfminer').setLevel(logging.WARNING)

PHONE_RE = re.compile(r'^\d[\d\-() ]+$')

URL = "https://www.pzu.com.ua/admin/upload/2024/upload/spysok-sto.pdf"
PDF_FILE = "sto.pdf"

def is_new_record(word):
    return (
            word['x0'] < 210 and
            word['top'] > 170 and
            word['text'][0].isupper() and
            '@' not in word['text']
    )

def clean_address(raw_address):
    if not raw_address:
        return ""

    raw_address = raw_address.replace('\n', ' ').strip()

    if any(m in raw_address for m in ['м.', 'м. ', 'м ']):
        street_markers = [
            'вул.', 'в.', 'вулиця ', 'пров.', 'просп.', 'пр.', 'пр-кт.',
            'бульв.', 'шосе ', 'площа ', 'Проспект', 'ул.'
        ]

        best_idx = -1
        for marker in street_markers:
            idx = raw_address.find(marker)
            if idx > 0 and raw_address[idx - 1] in (' ', ','):
                if best_idx == -1 or idx < best_idx:
                    best_idx = idx

        if best_idx != -1:
            return raw_address[best_idx:].strip()

        comma_idx = raw_address.find(',')
        if comma_idx != -1:
            return raw_address[comma_idx + 1:].strip()

    return raw_address

def download_pdf(url, output_path):
    response = requests.get(url)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)


def parse_pdf(pdf_path):
    results = []
    current_city = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            table = page.extract_table()

            if not table:
                continue

            for row in table:
                if not row or not any(row):
                    continue

                row = [str(cell).strip() if cell else "" for cell in row]

                if "Найменування" in row or "СТО" in row or "Фактична" in row:
                    continue

                try:
                    city = row[0]
                    name = row[1]
                    address = row[3] if len(row) > 3 else ""
                    phone = row[4] if len(row) > 4 else ""

                    if city and ('Для' in city or 'місто' in city or len(city) > 50):
                        continue

                    if not name:
                        continue

                    if city:
                        current_city = city


                    name_lower = name.lower()

                    if "найменування" in name_lower or "фактична адреса" in name_lower or "сто" == name_lower:
                        continue

                    sto_item = {
                        "city": current_city,
                        "name": name,
                        "street": clean_address(address)
                    }

                    sto_item['name'] = sto_item['name'].replace('\n', ' ').strip()
                    sto_item['city'] = sto_item['city'].replace('\n', '').strip()

                    phone = re.sub(r'[^\d\-() ]', '', phone).strip()

                    if phone and PHONE_RE.match(phone):
                        sto_item["phoneNumber"] = phone

                    results.append(sto_item)

                except IndexError:
                    continue

    return results

if __name__ == '__main__':
    download_pdf(URL, PDF_FILE)

    parsed_data = parse_pdf(PDF_FILE)

    with open('results_pzu.json', 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=2)

    logger.debug(f"Успішно завершено! Оброблено записів СТО: {len(parsed_data)}")