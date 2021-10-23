import http.client
import os
import time
import json
import requests
from bs4 import BeautifulSoup
# Telegram imports
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging


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
                    image_link = 'No photo'

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

    def parsing(self) -> list:

        new_info = []

        self.save_link_data(self.main_url)

        # Current INFO
        if os.stat(self.main_filename).st_size > 0:
            with open(self.main_filename, 'r') as file:
                current_info = json.load(file)
                last_link = current_info[len(current_info) - 1].get('Link')
                file.close()
        else:
            last_link = None
            current_info = []

        # Parsing
        link_data = self.read_link_data()
        data = self.get_data(link_data)
        data.reverse()
        last_link_found = False or last_link is None
        for info in data:
            current_link = info.get('Link')
            if current_link == last_link:
                last_link_found = True
            elif last_link_found:
                current_info.append(info)
                new_info.append(info)

        # Adding info into file
        with open(self.main_filename, 'w') as file:
            json.dump(current_info, file, indent=4, ensure_ascii=False)

        return new_info


class TelegramBot:

    def __init__(self):

        # Reading file and getting settings
        with open('settings.json', 'r') as file:
            file_data = json.load(file)
            self.bot_data_filename = file_data.get('bot_data_filename')
            self.bot_token = file_data.get('bot_token')
            file.close()

        # Initializing current user info
        if not os.path.isfile(self.bot_data_filename):
            with open(self.bot_data_filename, 'x') as file:
                self.current_ids = []
        else:
            with open(self.bot_data_filename, 'r') as file:
                self.current_ids = json.load(file)
                file.close()

        # Main telegram UPDATER
        self.updater = Updater(token=self.bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Handlers
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CommandHandler('stop', self.stop))
        self.dispatcher.add_handler(MessageHandler(Filters.command, self.unknown))

        # Starting the bot
        self.updater.start_polling()

        print('Telegram bot initialized!')

    def add_user(self, user_data: dict):

        key_found = False
        for item in self.current_ids:
            if item.get('user_id') == user_data.get('user_id'):
                key_found = True
                break
        if not key_found:
            self.current_ids.append(user_data)
            # Updating user info file
            with open(self.bot_data_filename, 'w') as file:
                json.dump(self.current_ids, file, indent=4, ensure_ascii=False)

    def remove_user(self, user_id: str):

        for i in range(self.current_ids.count()):
            if self.current_ids[i].get('user_id') == user_id:
                self.current_ids.remove(i)
                break

        # Updating user info file
        with open(self.bot_data_filename, 'w') as file:
            json.dump(self.current_ids, file, indent=4, ensure_ascii=False)

    def start(self, update, context):

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Hi! I will send you all new ads of the cars from 999.md")

        # Saving user ID
        for key in context.dispatcher.chat_data.keys():
            user_data = {"user_id": key,
                         "filters:": "bmw, mercedes"}
            self.add_user(user_data)

    def stop(self, update, context):

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='To start receiving new adds - write /start and choose filters')

        self.remove_user(update.effective_chat.id)

    def unknown(self, update, context):

        context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


def main():

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    parser = Parser()

    telegram_bot = TelegramBot()

    while True:
        new_info = parser.parsing()
        for info in new_info:
            for user_info in telegram_bot.current_ids:
                chat_id = user_info.get('user_id')
                title = info.get('Title')
                telegram_bot.updater.bot.send_message(chat_id=chat_id, text=f'<b>{title}</b>', parse_mode='HTML')
            time.sleep(1)

    telegram_bot.updater.idle()


if __name__ == '__main__':
    main()
