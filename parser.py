import os
import json
import requests
from bs4 import BeautifulSoup


class Parser:

    def __init__(self):

        # Reading file and getting settings
        with open('settings.json', 'r') as file:
            file_data = json.load(file)
            self.main_url = file_data.get('main_url')
            self.temp_filename = file_data.get('temp_filename')
            file.close()

        print('Parser initialized!')

    def save_link_data(self, link: str) -> None:

        headers = {
            "Accept": "*/*",
            "User-Agent": "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2"
        }

        session = requests.Session()
        html = session.get(url=link, headers=headers).text

        with open(self.temp_filename, "w") as file:
            file.write(html)

    def read_link_data(self) -> BeautifulSoup:

        with open(self.temp_filename, 'r') as file:
            html = file.read()
            file.close()

        # Deleting temp file, because it no more needed
        os.remove(self.temp_filename)

        return BeautifulSoup(html, "lxml")

    def generate_link_info(self, link_data: BeautifulSoup) -> list:

        info = []

        table = link_data.find('table', class_='ads-list-table')
        rows = table.find_all('tr')
        for tr in rows:

            # Link and Title
            link_title = tr.find('td', class_='ads-list-table-title').find('a')
            link = 'https://999.md' + link_title.get('href')

            if link.find('booster') == -1:
                title = link_title.text.strip()
                year = tr.find('td', class_='ads-list-table-col-3 feature-19').text.strip()
                engine = tr.find('td', class_='ads-list-table-col-4 feature-103').text.strip()
                mileage = tr.find('td', class_='ads-list-table-col-4 feature-104').text.strip()
                transmission = tr.find('td', class_='ads-list-table-col-2 feature-101').text.strip()
                # Price could be 'договорная'
                try:
                    price = tr.find('td', class_='ads-list-table-price feature-2').text.strip()
                except Exception:
                    price = tr.find('td', class_='ads-list-table-price feature-2 is-negotiable').text.strip()
                date = tr.find('td', class_='ads-list-table-date').text.strip()
                try:
                    image_link = tr.find('div', class_='photo js-tooltip-photo').get('data-image')
                    image_link = image_link.split('?')[0]
                except Exception:
                    image_link = 'https://www.carfitexperts.com/car-models/wp-content/uploads/2019/01/zen-1.jpg'

                info.append(
                    {'Link': link,
                     'Title': title,
                     'Year': year,
                     'Engine': engine.replace('    ', ' '),
                     'Mileage': mileage.replace('    ', ' '),
                     'Transmission': transmission,
                     'Price': price.replace('\u00A0', ' '),
                     'Date': date,
                     'ImageLink': image_link}
                )

        return info

    def parse(self, db_all_data) -> list:

        new_info = []

        self.save_link_data(self.main_url)

        # Parsing
        link_data = self.read_link_data()
        data = self.generate_link_info(link_data)

        for current_info in data:
            current_link = current_info.get('Link')
            write_result = db_all_data.update({'Link': current_link}, current_info, upsert=True)
            if not write_result.get('updatedExisting'):
                new_info.append(current_info)

        return new_info


if __name__ == '__main__':
    print('Only for import!')
