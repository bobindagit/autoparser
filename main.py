import time
import logging
# Modules
from parser import Parser
from telegram_bot import TelegramBot
from database import Database


def main():

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    database = Database()

    parser = Parser()

    telegram_bot = TelegramBot(database.db_user_info)

    while True:
        new_info = parser.parse(database.db_all_data)
        for current_info in new_info:
            telegram_bot.send_message(current_info, database.db_user_info)
            time.sleep(0.5)

    telegram_bot.updater.idle()


if __name__ == '__main__':
    main()
