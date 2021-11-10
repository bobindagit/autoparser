import json
from bs4 import BeautifulSoup
import asyncio
import aiohttp


def get_value(soup: BeautifulSoup, value_title: str) -> str:

    # Find by key
    key = soup.find('span', class_='adPage__content__features__key', string=value_title)
    if key is None:
        return ''
    else:
        return key.parent.find('span', class_='adPage__content__features__value').text.strip()


def link_exists(link: str, db_all_data) -> bool:

    return db_all_data.find({'Link': link}).retrieved > 0


async def get_link_data(session, link: str) -> dict:

    async with session.get(link, ssl=False) as response:

        soup = BeautifulSoup(await response.text(), 'lxml')

        # Title
        title = soup.find('h1').text
        # Year
        year = get_value(soup, ' Год выпуска ')
        # Engine
        engine = get_value(soup, ' Объем двигателя ').replace('   ', ' ')
        # Mileage
        mileage = get_value(soup, ' Пробег ').replace('   ', ' ')
        # Transmission
        transmission = get_value(soup, ' КПП ')
        # Fuel type
        fuel_type = get_value(soup, ' Тип топлива ')
        # Drive type
        drive_type = get_value(soup, ' Привод ')
        # Price
        prices = soup.find('ul', class_='adPage__content__price-feature__prices')
        if prices.find('li', class_='adPage__content__price-feature__prices__price is-negotiable') is None:
            # Finding price in EURO
            for price_row in soup.find('ul', class_='adPage__content__price-feature__prices').find_all('li'):
                if price_row.find('span',
                                  class_='adPage__content__price-feature__prices__price__currency').text == ' € ':
                    price = price_row.find('span',
                                           class_='adPage__content__price-feature__prices__price__value').text.replace(' ', '')
                    break
        else:
            price = 'Договорная'
        # Locality
        locality = soup.find('meta', itemprop='addressLocality').get('content')
        # Contacts
        contacts = []
        all_contacts = soup.find('dl', class_='adPage__content__phone grid_18').find_all('a')
        for current_contact in all_contacts:
            contacts.append(current_contact.get('href').replace('tel:+373', ''))
        # Image
        try:
            image_link = soup.find('div', id='js-ad-photos', class_='slick-cont-full grid_18').find('div', class_='slick-cont-full-item js-item').find('img').get('src')
        except Exception:
            image_link = 'https://www.carfitexperts.com/car-models/wp-content/uploads/2019/01/zen-1.jpg'

        return {
            'Link': link,
            'Title': title,
            'Year': year,
            'Engine': engine,
            'Mileage': mileage,
            'Transmission': transmission,
            'Fuel_type': fuel_type,
            'Drive_type': drive_type,
            'Price': price,
            'Locality': locality,
            'Contacts': contacts,
            'Image': image_link
        }


class Parser:

    def __init__(self, db_all_data):

        self.db_all_data = db_all_data

        self.headers = {
            "Accept": "*/*",
            "User-Agent": "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2"
        }

        # Reading file and getting settings
        with open('settings.json', 'r') as file:
            file_data = json.load(file)
            self.main_url = file_data.get('main_url')
            file.close()

        print('Parser initialized!')

    async def gather_data(self) -> list:

        async with aiohttp.ClientSession(headers=self.headers) as session:
            response = await session.get(self.main_url, ssl=False)
            soup = BeautifulSoup(await response.text(), 'lxml')

            tasks = []

            # Getting all links
            table_rows = soup.find('table', class_='ads-list-table').find_all('tr')
            for row in table_rows:
                link = 'https://999.md' + row.find('td', class_='ads-list-table-title').find('a').get('href')
                if link.find('booster') == -1 and not link_exists(link, self.db_all_data):
                    tasks.append(asyncio.create_task(get_link_data(session, link)))

            # Parsing
            return await asyncio.gather(*tasks)

    def start_parsing(self) -> list:

        return asyncio.run(self.gather_data())


if __name__ == '__main__':
    print('Only for import!')
