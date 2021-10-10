import os
import requests
from bs4 import BeautifulSoup
import json

MAIN_URL = 'https://999.md/ru/list/transport/cars?view_type=short'
TEMP_FILENAME = 'tmp_file.html'
MAIN_FILE = 'all_info.json'
MAIN_FILE_URLS = 'all_urls.json'


def save_link_data(link: str):

    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"
    }

    html = requests.get(link, headers=headers).text

    with open(TEMP_FILENAME, "w") as file:
        file.write(html)


def read_link_data() -> BeautifulSoup:

    with open(TEMP_FILENAME) as file:
        html = file.read()

    # Deleting temp file, because it no more needed
    os.remove(TEMP_FILENAME)

    return BeautifulSoup(html, "lxml")


def main():

    save_link_data(MAIN_URL)

    link_data = read_link_data()

    # Current INFO
    if os.stat(MAIN_FILE).st_size > 0:
        with open(MAIN_FILE, 'r') as file:
            current_info = json.load(file)
            file.close()
    else:
        current_info = []

    # Current URLS
    if os.stat(MAIN_FILE_URLS).st_size > 0:
        with open(MAIN_FILE_URLS, 'r') as file:
            current_links = json.load(file)
            last_link = current_links[len(current_links) - 1]
            file.close()
    else:
        current_links = []
        last_link = ''

    # Parsing
    table = link_data.find('table', 'ads-list-table')
    all_tr = table.findAll('tr')
    list(all_tr).reverse()
    #TODO Сформировать новую структуру и работать уже с ней массив можно уже нормально перевернуть
    for tr in all_tr:

        # Link and Title
        link_title = tr.find('td', 'ads-list-table-title').find('a')
        link = 'https://999.md' + link_title.get('href')

        # We should add only new links
        if link == last_link:
            break
        elif link.find('booster') == -1:
            title = link_title.text.strip()
            year = tr.find('td', 'ads-list-table-col-3 feature-19').text.strip()
            engine = tr.find('td', 'ads-list-table-col-4 feature-103').text.strip()
            mileage = tr.find('td', 'ads-list-table-col-4 feature-104').text.strip()
            transmission = tr.find('td', 'ads-list-table-col-2 feature-101').text.strip()
            # Price could be 'договорная'
            try:
                price = tr.find('td', 'ads-list-table-price feature-2').text.strip()
            except Exception:
                price = tr.find('td', 'ads-list-table-price feature-2 is-negotiable').text.strip()
            date = tr.find('td', 'ads-list-table-date').text.strip()

            current_links.append(link)

            current_info.append(
                {'Link': link,
                 'Title': title,
                 'Year': year,
                 'Engine': engine.replace('    ', ' '),
                 'Mileage': mileage.replace('    ', ' '),
                 'Transmission': transmission,
                 'Price': price.replace('\u00A0', ' '),
                 'Date': date}
            )

    # Adding links into file
    with open(MAIN_FILE_URLS, 'w') as file:
        json.dump(current_links, file, indent=4, ensure_ascii=False)

    # Adding info into file
    with open(MAIN_FILE, 'w') as file:
        json.dump(current_info, file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()