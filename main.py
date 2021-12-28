import logging
import time
# Modules
from parser import Parser
from telegram_bot import TelegramBot
from database import Database


def main():

    # Logging (TODO: check out if it works)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    database = Database()

    parser = Parser(database.db_all_data)

    telegram_bot = TelegramBot(database.db_user_info)

    while True:
        time.sleep(10)
        links_count = database.db_all_data.count()
        if links_count > 200:
            ids_to_delete = []
            for i in range(100):
                ids_to_delete.append(database.db_all_data.find()[i].get('_id'))
            database.db_all_data.delete_many({'_id': {'$in': ids_to_delete}})
        new_info = parser.start_parsing()
        for info in new_info:
            current_link = info.get('Link')
            database.db_all_data.update({'Link': current_link}, info, upsert=True)
            telegram_bot.user_manager.send_message(info, database.db_user_info)

    telegram_bot.updater.idle()


if __name__ == '__main__':
    main()
