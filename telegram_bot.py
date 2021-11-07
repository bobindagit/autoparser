import json
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# Filter names
FILTER_BRAND = 'filter_brand'
FILTER_YEAR = 'filter_year'
FILTER_REGISTRATION = 'filter_registration'
FILTER_PRICE = 'filter_price'

# Main menu
MAIN_MENU = [
            [InlineKeyboardButton('Марка', callback_data='m1')],
            [InlineKeyboardButton('Год выпуска', callback_data='m2')],
            [InlineKeyboardButton('Регистрация', callback_data='m3')],
            [InlineKeyboardButton('Цена', callback_data='m4')]
        ]
# Secondary menu
SECONDARY_MENU = [
            [InlineKeyboardButton('✅ Установленные', callback_data='filter_list')],
            [InlineKeyboardButton('❌ Очистить', callback_data='filter_clear')],
            [InlineKeyboardButton('◀️ Главное меню', callback_data='back')]
        ]


class TelegramBot:

    def __init__(self, db_user_info):

        # Reading file and getting settings
        with open('settings.json', 'r') as file:
            file_data = json.load(file)
            bot_token = file_data.get('bot_token')
            file.close()

        # Main telegram UPDATER
        self.updater = Updater(token=bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Connecting to the DB
        self.user_manager = UserManager(db_user_info, self.updater)

        # Initializing Menu object
        menu = TelegramMenu(self.user_manager)
        secondary_menu = TelegramSecondaryMenu(self.user_manager)

        # Initializing Handler object
        handlers = TelegramHandlers(self.user_manager, menu)

        # Handlers
        self.dispatcher.add_handler(CommandHandler('start', handlers.start))
        self.dispatcher.add_handler(CommandHandler('stop', handlers.stop))
        self.dispatcher.add_handler(MessageHandler(Filters.text, menu.menu_message))
        self.dispatcher.add_handler(MessageHandler(Filters.command, handlers.unknown))
        # Menu handlers
        self.dispatcher.add_handler(CallbackQueryHandler(menu.brand_button, pattern='m1'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.year_button, pattern='m2'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.registration_button, pattern='m3'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.price_button, pattern='m4'))
        # Secondary menu handlers
        self.dispatcher.add_handler(CallbackQueryHandler(secondary_menu.all_filters_button, pattern='filter_list'))
        self.dispatcher.add_handler(CallbackQueryHandler(secondary_menu.clear_button, pattern='filter_clear'))
        self.dispatcher.add_handler(CallbackQueryHandler(secondary_menu.back_button, pattern='back'))

        # Starting the bot
        self.updater.start_polling()

        print('Telegram bot initialized!')


class UserManager:

    def __init__(self, db_user_info, updater: Updater):
        self.db_user_info = db_user_info
        self.updater = updater

    def add_user(self, user_info: dict) -> None:
        user_id = user_info.get('user_id')
        self.db_user_info.update({'user_id': user_id}, user_info, upsert=True)

    def remove_user(self, user_id: str) -> None:
        self.db_user_info.remove({'user_id': user_id})

    def set_current_step(self, current_step: str, user_id: str) -> None:
        value_to_update = {"$set": {"current_step": current_step}}
        self.db_user_info.update({'user_id': user_id}, value_to_update)

    def get_current_step(self, user_id: str) -> str:
        return self.db_user_info.find({'user_id': user_id})[0].get('current_step')

    def set_filter(self, user_id: str, filter_name: str, new_value: list) -> None:
        value_to_update = {"$set": {filter_name: new_value}}
        self.db_user_info.update({'user_id': user_id}, value_to_update)

    def get_filter(self, user_id: str, filter_name: str) -> list:
        return self.db_user_info.find({'user_id': user_id})[0].get(filter_name)

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

    def send_message(self, info: dict, db_user_info) -> None:

        message_info = self.generate_html_message(info)
        img = message_info.get('img')
        img_caption = message_info.get('message')

        for user_info in db_user_info.find():
            # Check if user has filters and current info matches user filters
            if (len(user_info.get(FILTER_BRAND)) != 0
                or len(user_info.get(FILTER_REGISTRATION)) != 0
                or len(user_info.get(FILTER_YEAR)) != 0
                or len(user_info.get(FILTER_PRICE)) != 0) \
                    and self.info_matches_filters(info, user_info):
                chat_id = user_info.get('user_id')
                self.updater.bot.send_photo(chat_id=chat_id,
                                            photo=img,
                                            caption=img_caption,
                                            parse_mode='HTML')

    def info_matches_filters(self, info: dict, user_info: dict) -> bool:

        user_id = user_info.get('user_id')

        # BRANDS
        current_filter = self.get_filter(user_id, FILTER_BRAND)
        title = info.get('Title').upper()
        if len(current_filter) != 0:
            title_found = False
            for title_filter in current_filter:
                if title.find(title_filter) != -1:
                    title_found = True
                    break
            if not title_found:
                return False

        # YEARS
        current_filter = self.get_filter(user_id, FILTER_YEAR)
        if len(current_filter) != 0 and info.get('Year') not in current_filter:
            return False

        # # REGISTRATION
        # current_filter = self.get_filter(user_id, FILTER_REGISTRATION)
        # if current_filter.count() != 0 and info.get('Title') not in current_filter:
        #     return False

        # PRICES
        current_filter = self.get_filter(user_id, FILTER_PRICE)
        price = info.get('Price').replace(' ', '').replace('€', '').replace('$', '')
        if len(current_filter) != 0 and price.isdigit():
            price_range_match_found = False
            for price_range in current_filter:
                price_range_list = price_range.split('-')
                if len(price_range_list) > 1:
                    price_from = price_range_list[0]
                    price_to = price_range_list[1]
                    if price_from <= price <= price_to:
                        price_range_match_found = True
                        break
            if not price_range_match_found:
                return False

        return True


class TelegramMenu:

    def __init__(self, user_manager: UserManager):

        self.user_manager = user_manager

        # Main menu buttons
        main_keyboard = [[KeyboardButton(text='Фильтры'), KeyboardButton(text='Контакты')]]
        self.reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, one_time_keyboard=False)

    def menu_message(self, update, context) -> None:

        user_message = update.message.text.upper()
        user_id = update.effective_chat.id

        current_step = self.user_manager.get_current_step(user_id)

        if user_message == 'ФИЛЬТРЫ':
            update.message.reply_text('Выберите фильтр для настройки', reply_markup=InlineKeyboardMarkup(MAIN_MENU))
        elif user_message == 'КОНТАКТЫ':
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Создатель бота - @bobtb")
        elif len(current_step) != 0:
            self.message_handler(user_id, user_message, current_step)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Я не знаю такой команды")

    def brand_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(
            text='Вводите марки автомобиля (как на сайте), чтобы добавить фильтр по ним (Пример: BMW 5 series)',
            reply_markup=InlineKeyboardMarkup(SECONDARY_MENU))
        self.user_manager.set_current_step(FILTER_BRAND, update.effective_chat.id)

    def year_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(text='Введите год или интервал (Пример: 2010 ИЛИ 1990-2010)',
                                reply_markup=InlineKeyboardMarkup(SECONDARY_MENU))
        self.user_manager.set_current_step(FILTER_YEAR, update.effective_chat.id)

    def registration_button(self, update, context) -> None:

        if update.callback_query.data == 'm3_1':
            self.user_manager.set_filter(update.effective_chat.id, FILTER_REGISTRATION, ['Республика Молдова'])
        elif update.callback_query.data == 'm3_2':
            self.user_manager.set_filter(update.effective_chat.id, FILTER_REGISTRATION, ['Приднестровье'])
        elif update.callback_query.data == 'm3_3':
            self.user_manager.set_filter(update.effective_chat.id, FILTER_REGISTRATION, ['Другое'])

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите фильтр по регистрации автомобиля:',
                                reply_markup=self.generate_registration_buttons(update.effective_chat.id))
        self.user_manager.set_current_step(FILTER_REGISTRATION, update.effective_chat.id)

    def generate_registration_buttons(self, user_id: str) -> InlineKeyboardMarkup:

        keyboard = [
            InlineKeyboardButton('Молдова', callback_data='m3_1'),
            InlineKeyboardButton('ПМР', callback_data='m3_2'),
            InlineKeyboardButton('Другое', callback_data='m3_3')
        ]

        current_filters = self.user_manager.get_filter(user_id, FILTER_REGISTRATION)
        for key in keyboard:
            if key.text in current_filters:
                keyboard.remove(key)

        return InlineKeyboardMarkup([keyboard, SECONDARY_MENU[0], SECONDARY_MENU[1], SECONDARY_MENU[2]])

    def price_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(text='Введите диапазон цен в € (Пример: 10000-15000)',
                                reply_markup=InlineKeyboardMarkup(SECONDARY_MENU))
        self.user_manager.set_current_step(FILTER_PRICE, update.effective_chat.id)

    def message_handler(self, user_id: str, user_message: str, current_step: str) -> None:

        if current_step == FILTER_BRAND:
            filters_brand = self.user_manager.get_filter(user_id, FILTER_BRAND)
            if filters_brand is None:
                filters_brand = [user_message]
            elif user_message not in filters_brand:
                filters_brand.append(user_message)
            self.user_manager.set_filter(user_id, FILTER_BRAND, filters_brand)
        elif current_step == FILTER_YEAR:
            filters_year = self.user_manager.get_filter(user_id, FILTER_YEAR)
            current_filter = user_message.replace(' ', '')
            # Checking if user introduced interval
            if current_filter.find('-') != -1:
                current_filters = current_filter.split('-')
                first_year = current_filters[0]
                second_year = current_filters[1]
                years_interval = []
                if first_year.isdigit() and second_year.isdigit():
                    for i in range(int(first_year), int(second_year) + 1):
                        years_interval.append(str(i))
                    for year in years_interval:
                        if year not in filters_year:
                            filters_year.append(year)
            else:
                filters_year.append(user_message)
            self.user_manager.set_filter(user_id, FILTER_YEAR, filters_year)
        elif current_step == FILTER_PRICE:
            filters_price = self.user_manager.get_filter(user_id, FILTER_PRICE)
            current_filter = user_message.replace(' ', '')
            if current_filter.find('-') != -1 and current_filter not in filters_price:
                filters_price.append(current_filter)
                self.user_manager.set_filter(user_id, FILTER_PRICE, filters_price)


class TelegramSecondaryMenu:

    def __init__(self, user_manager: UserManager):

        self.user_manager = user_manager

    def all_filters_button(self, update, context) -> None:

        user_id = update.effective_chat.id
        current_step = self.user_manager.get_current_step(user_id)

        current_filters = self.user_manager.get_filter(user_id, current_step)
        if current_filters is None:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Нет установленных фильтров")
        else:
            all_filters = ''
            for current_filter in current_filters:
                all_filters = f'{all_filters} {current_filter} |'
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=all_filters)

    def clear_button(self, update, context) -> None:

        user_id = update.effective_chat.id
        current_step = self.user_manager.get_current_step(user_id)
        empty_filter = []
        self.user_manager.set_filter(user_id, current_step, empty_filter)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Фильтр очищен")

    def back_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите фильтр для настройки',
                                reply_markup=InlineKeyboardMarkup(MAIN_MENU))
        self.user_manager.set_current_step('', update.effective_chat.id)


class TelegramHandlers:

    def __init__(self, user_manager: UserManager, menu: TelegramMenu):

        # Initializing menu
        self.menu = menu
        self.user_manager = user_manager

    def start(self, update, context) -> None:

        # Adding user ID
        current_user = update.effective_chat
        user_info = {"user_id": current_user.id,
                     "full_name": current_user.full_name,
                     "link": current_user.link,
                     "current_step": "",
                     FILTER_BRAND: [],
                     FILTER_YEAR: [],
                     FILTER_REGISTRATION: [],
                     FILTER_PRICE: []}
        self.user_manager.add_user(user_info)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Привет! Настрой фильтры и я буду присылать тебе все новые объявления о продаже автомобилей с 999.md",
                                 reply_markup=self.menu.reply_markup)

    def stop(self, update, context) -> None:

        self.user_manager.remove_user(update.effective_chat.id)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Чтобы опять получать уведомления - введи /start и настрой фильтры')

    def unknown(self, update, context) -> None:

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Я не знаю такой команды")


if __name__ == '__main__':
    print('Only for import!')
