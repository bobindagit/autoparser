import time
import logging
# Modules
from parser import Parser
from telegram_bot import TelegramBot
# DB
import pymongo


def main():

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    parser = Parser()

    telegram_bot = TelegramBot()

    while True:
        new_info = parser.parse()
        for info in new_info:
            message_info = telegram_bot.generate_html_message(info)
            message = message_info.get('message')
            img = message_info.get('img')
            for user_info in telegram_bot.current_ids:
                chat_id = user_info.get('user_id')
                # telegram_bot.updater.bot.send_photo(chat_id=chat_id,
                #                                     photo=img,
                #                                     caption=message,
                #                                     parse_mode='HTML')
            time.sleep(0.5)

    telegram_bot.updater.idle()


if __name__ == '__main__':
    main()
