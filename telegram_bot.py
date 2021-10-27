import os
import json
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup


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

        # Initializing Menu object
        self.menu = TelegramMenu()

        # Main telegram UPDATER
        self.updater = Updater(token=self.bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Handlers
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CommandHandler('stop', self.stop))
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.menu.button_handler))
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

        # Saving user ID
        for key in context.dispatcher.chat_data.keys():
            user_data = {"user_id": key,
                         "filters:": "bmw, mercedes"}
            self.add_user(user_data)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Hi! I will send you all new ads of the cars from 999.md",
                                 reply_markup=self.menu.reply_markup)

    def stop(self, update, context):

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='To start receiving new adds - write /start and choose filters')

        self.remove_user(update.effective_chat.id)

    def unknown(self, update, context):

        context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

    def generate_html_message(self, info: dict) -> dict:

        # Downloading image
        headers = {
            "Accept": "*/*",
            "User-Agent": "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2"
        }
        session = requests.Session()
        html_img = session.get(url=info.get('ImageLink'), headers=headers)

        title = f'<b>{info.get("Title")} {info.get("Year")}</b> ({info.get("Price")})'
        link = f'<i><a href="{info.get("Link")}"> *** ССЫЛКА *** </a></i>'
        html_message = f'{title}\n{info.get("Engine")}; {info.get("Transmission")}\n{info.get("Mileage")}\n{link}'

        return {'img': html_img.content,
                'message': html_message}


class TelegramMenu:

    def __init__(self):

        keyboard = [[KeyboardButton(text='/settings'), KeyboardButton(text='Key 2'), KeyboardButton(text='Регистрация')],
                         [KeyboardButton(text='Key4'), KeyboardButton(text='Key5'), KeyboardButton(text='Key6')],
                         [KeyboardButton(text='Key7'), KeyboardButton(text='Key8'), KeyboardButton(text='Key9')]]

        self.reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    def button_handler(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Hi!")


if __name__ == '__main__':
    print('Only for import!')
