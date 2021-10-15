import os
import time
import json
import requests
from bs4 import BeautifulSoup
# Telegram imports
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging


MAIN_URL = 'https://999.md/ru/list/transport/cars?view_type=short'
TEMP_FILENAME = 'tmp_file.html'
MAIN_FILE = 'all_info.json'
BOT_DATA = 'bot_data.json'


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


def get_data(link_data: BeautifulSoup):

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


def parsing():

    save_link_data(MAIN_URL)

    # Current INFO
    if os.stat(MAIN_FILE).st_size > 0:
        with open(MAIN_FILE, 'r') as file:
            current_info = json.load(file)
            last_link = current_info[len(current_info) - 1].get('Link')
            file.close()
    else:
        last_link = None
        current_info = []

    # Parsing
    link_data = read_link_data()
    data = get_data(link_data)
    data.reverse()
    last_link_found = False or last_link is None
    for info in data:
        current_link = info.get('Link')
        if current_link == last_link:
            last_link_found = True
        elif last_link_found:
            current_info.append(info)

    # Adding info into file
    with open(MAIN_FILE, 'w') as file:
        json.dump(current_info, file, indent=4, ensure_ascii=False)


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! I can send you all new ads of cars from 999.md")


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


def main():

    # Checking that service files exists
    if not os.path.isfile(MAIN_FILE):
        with open(MAIN_FILE, 'x') as file:
            pass
    if not os.path.isfile(BOT_DATA):
        with open(BOT_DATA, 'x') as file:
            pass

    # Telegram bot service code
    updater = Updater(token='1915826120:AAELKWL6xfLbgQT7l0FRmwzYtGLwzOjXkaQ', use_context=True)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    dispatcher = updater.dispatcher

    # Commands
    # START
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    # UNKNOWN COMMAND
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # Starting the bot
    updater.start_polling()

    for i in range(2):
        time.sleep(2)
        parsing()


if __name__ == '__main__':
    main()
