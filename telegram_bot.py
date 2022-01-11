import json
import requests
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

# Filter names
FILTER_BRAND = 'filter_brand'
FILTER_YEAR = 'filter_year'
FILTER_REGISTRATION = 'filter_registration'
FILTER_PRICE = 'filter_price'
FILTER_FUEL_TYPE = 'filter_fuel_type'
FILTER_TRANSMISSION = 'filter_transmission'
FILTER_CONDITION = 'filter_condition'
FILTER_AUTHOR_TYPE = 'filter_author_type'
FILTER_WHEEL = 'filter_wheel'

# Main menu
MAIN_MENU = [
    [InlineKeyboardButton('Марка', callback_data='m1')],
    [InlineKeyboardButton('Год выпуска', callback_data='m2')],
    [InlineKeyboardButton('Регистрация', callback_data='m3')],
    [InlineKeyboardButton('Цена', callback_data='m4')],
    [InlineKeyboardButton('Тип топлива', callback_data='m5')],
    [InlineKeyboardButton('Тип КПП', callback_data='m6')],
    [InlineKeyboardButton('Состояние', callback_data='m7')],
    [InlineKeyboardButton('Автор объявления', callback_data='m8')],
    [InlineKeyboardButton('Руль', callback_data='m9')],
]

# Secondary menu
SECONDARY_MENU = [
    [InlineKeyboardButton('✅ Установленные', callback_data='filter_list')],
    [InlineKeyboardButton('❌ Очистить', callback_data='filter_clear')],
    [InlineKeyboardButton('◀️ Назад', callback_data='back')]
]


def generate_current_filters_message(user_manager, user_id: str) -> str:

    all_filters = [{'name': FILTER_BRAND, 'title': '\n▶️<b>МАРКА: </b>'},
                   {'name': FILTER_YEAR, 'title': '\n▶️<b>ГОД ВЫПУСКА: </b>'},
                   {'name': FILTER_REGISTRATION, 'title': '\n▶️<b>РЕГИСТРАЦИЯ: </b>'},
                   {'name': FILTER_PRICE, 'title': '\n▶️<b>ЦЕНА: </b>'},
                   {'name': FILTER_FUEL_TYPE, 'title': '\n▶️<b>ТИП ТОПЛИВА: </b>'},
                   {'name': FILTER_TRANSMISSION, 'title': '\n▶️<b>ТИП КПП: </b>'},
                   {'name': FILTER_CONDITION, 'title': '\n▶️<b>СОСТОЯНИЕ: </b>'},
                   {'name': FILTER_AUTHOR_TYPE, 'title': '\n▶️<b>АВТОР ОБЪЯВЛЕНИЯ: </b>'},
                   {'name': FILTER_WHEEL, 'title': '\n▶️<b>РУЛЬ: </b>'}]

    message = '✅<b>УСТАНОВЛЕННЫЕ ФИЛЬТРЫ</b>✅\n'
    for auto_filter in all_filters:
        current_filters = user_manager.get_field(user_id, auto_filter.get('name'))
        if current_filters is not None and len(current_filters) != 0:
            message += auto_filter.get('title')
            for current_filter in current_filters:
                message += f'{current_filter} | '

    return message


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
        self.dispatcher.add_handler(CallbackQueryHandler(menu.fuel_button, pattern='m5'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.transmission_button, pattern='m6'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.condition_button, pattern='m7'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.author_button, pattern='m8'))
        self.dispatcher.add_handler(CallbackQueryHandler(menu.wheel_button, pattern='m9'))
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

    def user_exists(self, user_id: str) -> bool:
        return self.db_user_info.count_documents({'user_id': user_id}) != 0

    def create_user(self, current_user: telegram.Chat) -> None:
        # User could clear chat and press Start button again
        if not self.user_exists(current_user.id):
            user_info = {'user_id': current_user.id,
                         'full_name': current_user.full_name,
                         'link': current_user.link,
                         'current_step': '',
                         'active': True,
                         FILTER_BRAND: [],
                         FILTER_YEAR: [],
                         FILTER_REGISTRATION: [],
                         FILTER_PRICE: [],
                         FILTER_FUEL_TYPE: [],
                         FILTER_TRANSMISSION: [],
                         FILTER_CONDITION: [],
                         FILTER_AUTHOR_TYPE: [],
                         FILTER_WHEEL: []}
            self.db_user_info.update({'user_id': current_user.id}, user_info, upsert=True)

    def delete_user(self, user_id: str) -> None:
        self.db_user_info.remove({'user_id': user_id})

    def reset_user(self, current_user: telegram.Chat) -> None:
        user_id = current_user.id
        # Saving service fields
        current_step = self.get_field(user_id, 'current_step')
        active = self.get_field(user_id, 'active')
        # Reset of the user
        self.delete_user(user_id)
        self.create_user(current_user)
        # Restore of service fields
        self.set_field(user_id, 'current_step', current_step)
        self.set_field(user_id, 'active', active)

    def get_field(self, user_id: str, field_name: str) -> str | bool | list:
        return self.db_user_info.find({'user_id': user_id})[0].get(field_name)

    def set_field(self, user_id: str, field_name: str, new_value: str) -> None:
        value_to_update = {"$set": {field_name: new_value}}
        self.db_user_info.update({'user_id': user_id}, value_to_update)

    def set_filter(self, user_id: str, filter_name: str, value_to_add: str) -> None:
        current_filter = self.get_field(user_id, filter_name)
        if value_to_add not in current_filter:
            current_filter.append(value_to_add)
            value_to_update = {"$set": {filter_name: current_filter}}
            self.db_user_info.update({'user_id': user_id}, value_to_update)

    def generate_html_message(self, info: dict) -> dict:

        # Downloading image
        headers = {
            "Accept": "*/*",
            "User-Agent": "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2"
        }
        session = requests.Session()
        html_img = session.get(url=info.get('Image'), headers=headers)

        title = f'{info.get("Title")} {info.get("Year")} ({info.get("Price")} €)'
        title_link = f'<i><a href="{info.get("Link")}"><b>{title}</b></a></i>'
        contacts = ''
        for contact in info.get('Contacts'):
            contacts += contact + '; '
        html_message = f'{title_link}' \
                       f'\n┌ <b>Двигатель</b>: {info.get("Engine")}; {info.get("Fuel_type")}' \
                       f'\n├ <b>КПП</b>: {info.get("Transmission")}' \
                       f'\n├ <b>Пробег</b>: {info.get("Mileage")}' \
                       f'\n├ <b>Регион</b>: {info.get("Locality")}' \
                       f'\n└ <b>Контакты</b>: {contacts.strip()}' \

        return {'img': html_img.content,
                'message': html_message}

    def send_message(self, info: dict, db_user_info) -> None:

        message_info = self.generate_html_message(info)
        img = message_info.get('img')
        img_caption = message_info.get('message')

        for user_info in db_user_info.find({'active': True}):

            # User should have installed at least 1 filter
            if (len(user_info.get(FILTER_BRAND)) == 0
                    and len(user_info.get(FILTER_YEAR)) == 0
                    and len(user_info.get(FILTER_REGISTRATION)) == 0
                    and len(user_info.get(FILTER_PRICE)) == 0
                    and len(user_info.get(FILTER_FUEL_TYPE)) == 0
                    and len(user_info.get(FILTER_TRANSMISSION)) == 0
                    and len(user_info.get(FILTER_CONDITION)) == 0
                    and len(user_info.get(FILTER_AUTHOR_TYPE)) == 0
                    and len(user_info.get(FILTER_WHEEL)) == 0):
                continue

            # Check if current info matches user filters
            if self.info_matches_filters(info, user_info):
                self.updater.bot.send_photo(chat_id=user_info.get('user_id'),
                                            photo=img,
                                            caption=img_caption,
                                            parse_mode=ParseMode.HTML)

    def info_matches_filters(self, info: dict, user_info: dict) -> bool:

        user_id = user_info.get('user_id')

        # BRANDS
        current_filter = self.get_field(user_id, FILTER_BRAND)
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
        current_filter = self.get_field(user_id, FILTER_YEAR)
        if len(current_filter) != 0 and info.get('Year') not in current_filter:
            return False

        # REGISTRATION
        current_filter = self.get_field(user_id, FILTER_REGISTRATION)
        if len(current_filter) != 0 and info.get('Title') not in current_filter:
            return False

        # PRICES
        current_filter = self.get_field(user_id, FILTER_PRICE)
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
        main_keyboard = [
            [KeyboardButton(text='📝 Фильтры'),
             KeyboardButton(text='🔔 Уведомлять / 🔕 Не уведомлять'),
             KeyboardButton(text='✅ Мои фильтры'),
             KeyboardButton(text='❌ Очистить все фильтры')]
        ]
        self.reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, one_time_keyboard=False)

    def generate_buttons(self, keyboard: list, user_id: str, filter_name: str) -> InlineKeyboardMarkup:

        current_filters = self.user_manager.get_field(user_id, filter_name)
        for current_filter in current_filters:
            for key in keyboard:
                if current_filter == key.text:
                    keyboard.remove(key)

        keyboard_list = []
        for key in keyboard:
            keyboard_list.append([key])

        return InlineKeyboardMarkup(keyboard_list + SECONDARY_MENU)

    def menu_message(self, update, context) -> None:

        user_message = update.message.text.upper()
        user_id = update.effective_chat.id

        current_step = self.user_manager.get_field(user_id, 'current_step')

        if user_message.find('ОЧИСТИТЬ ВСЕ ФИЛЬТРЫ') != -1:
            self.user_manager.reset_user(update.effective_chat)
            # Info message
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='❌ <b>Все фильтры очищены</b> ❌',
                                     parse_mode=ParseMode.HTML)
        elif user_message.find('МОИ ФИЛЬТРЫ') != -1:
            # Info message
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=generate_current_filters_message(self.user_manager, user_id),
                                     parse_mode=ParseMode.HTML)
        elif user_message.find('ФИЛЬТРЫ') != -1:
            update.message.reply_text('Выберите фильтр для настройки',
                                      reply_markup=InlineKeyboardMarkup(MAIN_MENU))
        elif user_message.find('УВЕДОМЛЯТЬ') != -1 \
                and user_message.find('НЕ УВЕДОМЛЯТЬ') != -1:
            user_active = not self.user_manager.get_field(user_id, 'active')
            self.user_manager.set_field(user_id, 'active', user_active)
            # Info message
            if user_active:
                message_text = '✅ <b>Получение объявлений включено</b> ✅'
            else:
                message_text = '⛔️ <b>Получение объявлений приостановлено</b> ⛔'
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=message_text,
                                     parse_mode=ParseMode.HTML)
        elif len(current_step) != 0:
            self.message_handler(user_id, user_message, current_step)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Я не знаю такой команды")

    def message_handler(self, user_id: str, user_message: str, current_step: str) -> None:

        # Empty message
        if len(user_message) == 0:
            return

        if current_step == FILTER_BRAND:
            self.user_manager.set_filter(user_id, current_step, user_message)
        elif current_step == FILTER_YEAR:
            # Removing all spaces
            year = user_message.replace(' ', '')
            # If user introduced interval
            if year.find('-') != -1:
                years_interval = year.split('-')
                year_from = years_interval[0]
                # If user didn't introduced second year in the interval
                if not years_interval[1]:
                    year_to = '2025'
                else:
                    year_to = years_interval[1]
                if year_from.isdigit() and year_to.isdigit():
                    for i in range(int(year_from), int(year_to) + 1):
                        self.user_manager.set_filter(user_id, current_step, i)
            else:
                self.user_manager.set_filter(user_id, current_step, year)
        elif current_step == FILTER_PRICE:
            # Removing all spaces
            price = user_message.replace(' ', '')
            if price.find('-') != -1:
                price_interval = price.split('-')
                price_from = price_interval[0]
                # If user didn't introduced second price in the interval
                if not price_interval[1]:
                    price_to = '999999'
                else:
                    price_to = price_interval[1]
                if price_from.isdigit() and price_to.isdigit():
                    self.user_manager.set_filter(user_id, current_step, price_from + '-' + price_to)

    def brand_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(
            text=f'Введите марку автомобиля (как на сайте, 1 сообщение - 1 фильтр) (<b>Пример: BMW 5 series</b>)',
            reply_markup=InlineKeyboardMarkup(SECONDARY_MENU),
            parse_mode=ParseMode.HTML)
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_BRAND)

    def year_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(text=f'Введите год или интервал (<b>Пример: 2010 ИЛИ 1990-2010 ИЛИ 2015-</b>)',
                                reply_markup=InlineKeyboardMarkup(SECONDARY_MENU),
                                parse_mode=ParseMode.HTML)
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_YEAR)

    def registration_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm3_1':
            value_to_add = 'Республика Молдова'
        elif update.callback_query.data == 'm3_2':
            value_to_add = 'Приднестровье'
        elif update.callback_query.data == 'm3_3':
            value_to_add = 'Другое'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_REGISTRATION, value_to_add)

        keyboard = [
            InlineKeyboardButton('Республика Молдова', callback_data='m3_1'),
            InlineKeyboardButton('Приднестровье', callback_data='m3_2'),
            InlineKeyboardButton('Другое', callback_data='m3_3')
        ]
        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите варианты регистрации автомобиля:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_REGISTRATION))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_REGISTRATION)

    def price_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()
        query.edit_message_text(text=f'Введите диапазон цен в € (<b>Пример: 10000-15000 ИЛИ 0-5600 ИЛИ 55000-</b>)',
                                reply_markup=InlineKeyboardMarkup(SECONDARY_MENU),
                                parse_mode=ParseMode.HTML)
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_PRICE)

    def fuel_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm5_1':
            value_to_add = 'Бензин'
        elif update.callback_query.data == 'm5_2':
            value_to_add = 'Дизель'
        elif update.callback_query.data == 'm5_3':
            value_to_add = 'Газ / Бензин (пропан)'
        elif update.callback_query.data == 'm5_4':
            value_to_add = 'Газ / Бензин (метан)'
        elif update.callback_query.data == 'm5_5':
            value_to_add = 'Гибрид'
        elif update.callback_query.data == 'm5_6':
            value_to_add = 'Плагин-гибрид'
        elif update.callback_query.data == 'm5_7':
            value_to_add = 'Электричество'
        elif update.callback_query.data == 'm5_8':
            value_to_add = 'Газ'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_FUEL_TYPE, value_to_add)

        keyboard = [
            InlineKeyboardButton('Бензин', callback_data='m5_1'),
            InlineKeyboardButton('Дизель', callback_data='m5_2'),
            InlineKeyboardButton('Газ / Бензин (пропан)', callback_data='m5_3'),
            InlineKeyboardButton('Газ / Бензин (метан)', callback_data='m5_4'),
            InlineKeyboardButton('Гибрид', callback_data='m5_5'),
            InlineKeyboardButton('Плагин-гибрид', callback_data='m5_6'),
            InlineKeyboardButton('Электричество', callback_data='m5_7'),
            InlineKeyboardButton('Газ', callback_data='m5_8')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите типы топлива:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_FUEL_TYPE))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_FUEL_TYPE)

    def transmission_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm6_1':
            value_to_add = 'Механическая'
        elif update.callback_query.data == 'm6_2':
            value_to_add = 'Роботизированная'
        elif update.callback_query.data == 'm6_3':
            value_to_add = 'Автоматическая'
        elif update.callback_query.data == 'm6_4':
            value_to_add = 'Вариатор'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_TRANSMISSION, value_to_add)

        keyboard = [
            InlineKeyboardButton('Механическая', callback_data='m6_1'),
            InlineKeyboardButton('Роботизированная', callback_data='m6_2'),
            InlineKeyboardButton('Автоматическая', callback_data='m6_3'),
            InlineKeyboardButton('Вариатор', callback_data='m6_4')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите типы КПП:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_TRANSMISSION))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_TRANSMISSION)

    def condition_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm7_1':
            value_to_add = 'Новый'
        elif update.callback_query.data == 'm7_2':
            value_to_add = 'С пробегом'
        elif update.callback_query.data == 'm7_3':
            value_to_add = 'Требует ремонта'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_CONDITION, value_to_add)

        keyboard = [
            InlineKeyboardButton('Новый', callback_data='m7_1'),
            InlineKeyboardButton('С пробегом', callback_data='m7_2'),
            InlineKeyboardButton('Требует ремонта', callback_data='m7_3')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите варианты состояния:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_CONDITION))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_CONDITION)

    def author_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm8_1':
            value_to_add = 'Частное лицо'
        elif update.callback_query.data == 'm8_2':
            value_to_add = 'Автодилер'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_AUTHOR_TYPE, value_to_add)

        keyboard = [
            InlineKeyboardButton('Частное лицо', callback_data='m8_1'),
            InlineKeyboardButton('Автодилер', callback_data='m8_2')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите варианты авторов объявлений:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_AUTHOR_TYPE))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_AUTHOR_TYPE)

    def wheel_button(self, update, context) -> None:

        user_id = update.effective_chat.id

        if update.callback_query.data == 'm9_1':
            value_to_add = 'Левый'
        elif update.callback_query.data == 'm9_2':
            value_to_add = 'Правый'
        else:
            value_to_add = ''

        self.user_manager.set_filter(user_id, FILTER_WHEEL, value_to_add)

        keyboard = [
            InlineKeyboardButton('Левый', callback_data='m9_1'),
            InlineKeyboardButton('Правый', callback_data='m9_2')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите вариант расположения руля:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_WHEEL))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_WHEEL)


class TelegramSecondaryMenu:

    def __init__(self, user_manager: UserManager):

        self.user_manager = user_manager

    def all_filters_button(self, update, context) -> None:

        user_id = update.effective_chat.id
        current_step = self.user_manager.get_field(user_id, 'current_step')

        current_filters = self.user_manager.get_field(user_id, current_step)
        if current_filters is None or len(current_filters) == 0:
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
        current_step = self.user_manager.get_field(user_id, 'current_step')
        empty_filter = []
        self.user_manager.set_field(user_id, current_step, empty_filter)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Фильтр очищен")

    def back_button(self, update, context) -> None:

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите фильтр для настройки',
                                reply_markup=InlineKeyboardMarkup(MAIN_MENU))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', '')


class TelegramHandlers:

    def __init__(self, user_manager: UserManager, menu: TelegramMenu):
        # Initializing menu
        self.menu = menu
        self.user_manager = user_manager

    def start(self, update, context) -> None:
        # Creating user with empty filters
        current_user = update.effective_chat
        self.user_manager.create_user(current_user)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'👋 <b>Привет, {current_user.full_name}!</b> 👋\n\n'
                                      f'✳️ Чтобы получать уведомления о продаже автомобилей - настрой фильтры\n'
                                      f'💰 Удачных и выгодных сделок!\n\n'
                                      f'❓ <i>Есть вопрос или предложение? Контакт администратора находится в описании бота</i>',
                                 reply_markup=self.menu.reply_markup,
                                 parse_mode=ParseMode.HTML)

    def stop(self, update, context) -> None:
        self.user_manager.delete_user(update.effective_chat.id)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Чтобы опять получать уведомления - введите <b>/start</b> и выберите фильтры',
                                 parse_mode=ParseMode.HTML)

    def unknown(self, update, context) -> None:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Я не знаю такой команды')


if __name__ == '__main__':
    print('Only for import!')
