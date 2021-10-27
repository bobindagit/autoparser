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
            self.main_filename = file_data.get('main_filename')
            self.bot_data_filename = file_data.get('bot_data_filename')
            file.close()

        # Checking that service file exists
        if not os.path.isfile(self.main_filename):
            with open(self.main_filename, 'x') as file:
                pass

        print('Parser initialized!')

    def save_link_data(self, link: str):

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

    def get_data(self, link_data: BeautifulSoup) -> list:

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

    def parse(self) -> list:

        new_info = []

        self.save_link_data(self.main_url)

        # Current INFO
        if os.stat(self.main_filename).st_size > 0:
            with open(self.main_filename, 'r') as file:
                current_info = json.load(file)
                len_current_info = len(current_info)
                last_links = []
                # Saving last 19 links, cuz last ad could be deleted and parser will stop working
                for i in range(len_current_info - 1, len_current_info - 20, -1):
                    last_links.append(current_info[i].get('Link'))
                file.close()
        else:
            last_links = []
            current_info = []

        # Parsing
        link_data = self.read_link_data()
        data = self.get_data(link_data)
        data.reverse()

        last_link_found = False or len(last_links) == 0
        for info in data:
            current_link = info.get('Link')
            if current_link in last_links:
                last_link_found = True
            elif last_link_found:
                current_info.append(info)
                new_info.append(info)
        # Safe control if last link wasn't found
        if len(last_links) != 0 and not last_link_found:
            new_info.extend(data)

        # Adding info into file
        with open(self.main_filename, 'w') as file:
            json.dump(current_info, file, indent=4, ensure_ascii=False)

        return new_info


if __name__ == '__main__':
    print('Only for import!')
