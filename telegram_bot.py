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

    def create_user(self, current_user: telegram.Chat) -> None:
        user_info = {'user_id': current_user.id,
                     'full_name': current_user.full_name,
                     'link': current_user.link,
                     'current_step': '',
                     'active': False,
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

        title = f'<b>{info.get("Title")} {info.get("Year")}</b> ({info.get("Price")} €)'
        contacts = ''
        for contact in info.get('Contacts'):
            contacts += contact + '; '
        link = f'<i><a href="{info.get("Link")}"> *** ССЫЛКА *** </a></i>'
        html_message = f'{title}' \
                       f'\n┌ Мотор: {info.get("Engine")}; {info.get("Fuel_type")}' \
                       f'\n├ Пробег: {info.get("Mileage")}; КПП: {info.get("Transmission")}' \
                       f'\n├ {info.get("Locality")}' \
                       f'\n└ Контакты: {contacts.strip()}' \
                       f'\n{link}'

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
            [KeyboardButton(text='Фильтры'),
             KeyboardButton(text='Включить / Выключить'),
             KeyboardButton(text='Очистить все фильтры'),
             KeyboardButton(text='Контакты')]
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

        if user_message == 'ФИЛЬТРЫ':
            update.message.reply_text('Выберите фильтр для настройки',
                                      reply_markup=InlineKeyboardMarkup(MAIN_MENU))
        elif user_message == 'ВКЛЮЧИТЬ / ВЫКЛЮЧИТЬ':
            user_active = not self.user_manager.get_field(user_id, 'active')
            self.user_manager.set_field(user_id, 'active', user_active)
            # Info message
            if user_active:
                message_text = '✅ Получение объявлений включено'
            else:
                message_text = '⛔️ Получение объявлений приостановлено'
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=message_text)
        elif user_message == 'ОЧИСТИТЬ ВСЕ ФИЛЬТРЫ':
            self.user_manager.reset_user(update.effective_chat)
            # Info message
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='Все фильтры очищены')
        elif user_message == 'КОНТАКТЫ':
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Создатель бота - @bobtb")
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
        query.edit_message_text(text=f'Вводите марки автомобиля (как на сайте), чтобы добавить фильтр по ним (<b>Пример: BMW 5 series</b>)',
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
        current_filters = self.user_manager.get_field(user_id, FILTER_REGISTRATION)

        if update.callback_query.data == 'm3_1':
            current_filters.append('Республика Молдова')
        elif update.callback_query.data == 'm3_2':
            current_filters.append('Приднестровье')
        elif update.callback_query.data == 'm3_3':
            current_filters.append('Другое')

        self.user_manager.set_filter(user_id, FILTER_REGISTRATION, current_filters)

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
        current_filters = self.user_manager.get_field(user_id, FILTER_FUEL_TYPE)

        if update.callback_query.data == 'm5_1':
            current_filters.append('Бензин')
        elif update.callback_query.data == 'm5_2':
            current_filters.append('Дизель')
        elif update.callback_query.data == 'm5_3':
            current_filters.append('Газ / Бензин (пропан)')
        elif update.callback_query.data == 'm5_4':
            current_filters.append('Газ / Бензин (метан)')
        elif update.callback_query.data == 'm5_5':
            current_filters.append('Гибрид')
        elif update.callback_query.data == 'm5_6':
            current_filters.append('Плагин-гибрид')
        elif update.callback_query.data == 'm5_7':
            current_filters.append('Электричество')
        elif update.callback_query.data == 'm5_8':
            current_filters.append('Газ')

        self.user_manager.set_filter(user_id, FILTER_FUEL_TYPE, current_filters)

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
        current_filters = self.user_manager.get_field(user_id, FILTER_TRANSMISSION)

        if update.callback_query.data == 'm6_1':
            current_filters.append('Механическая')
        elif update.callback_query.data == 'm6_2':
            current_filters.append('Роботизированная')
        elif update.callback_query.data == 'm6_3':
            current_filters.append('Автоматическая')
        elif update.callback_query.data == 'm6_4':
            current_filters.append('Вариатор')

        self.user_manager.set_filter(user_id, FILTER_TRANSMISSION, current_filters)

        keyboard = [
            InlineKeyboardButton('Механическая', callback_data='m6_1'),
            InlineKeyboardButton('Роботизированная', callback_data='m6_2'),
            InlineKeyboardButton('Автоматическая', callback_data='m6_3'),
            InlineKeyboardButton('Вариатор', callback_data='m6_4')
        ]

        query = update.callback_query
        query.answer()

        query.edit_message_text(text='Выберите фильтр по регистрации автомобиля:',
                                reply_markup=self.generate_buttons(keyboard, user_id, FILTER_TRANSMISSION))
        self.user_manager.set_field(update.effective_chat.id, 'current_step', FILTER_TRANSMISSION)

    def condition_button(self, update, context) -> None:

        user_id = update.effective_chat.id
        current_filters = self.user_manager.get_field(user_id, FILTER_CONDITION)

        if update.callback_query.data == 'm7_1':
            current_filters.append('Новый')
        elif update.callback_query.data == 'm7_2':
            current_filters.append('С пробегом')
        elif update.callback_query.data == 'm7_3':
            current_filters.append('Требует ремонта')

        self.user_manager.set_filter(user_id, FILTER_CONDITION, current_filters)

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
        current_filters = self.user_manager.get_field(user_id, FILTER_AUTHOR_TYPE)

        if update.callback_query.data == 'm8_1':
            current_filters.append('Частное лицо')
        elif update.callback_query.data == 'm8_2':
            current_filters.append('Автодилер')

        self.user_manager.set_filter(user_id, FILTER_AUTHOR_TYPE, current_filters)

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
        current_filters = self.user_manager.get_field(user_id, FILTER_WHEEL)

        if update.callback_query.data == 'm9_1':
            current_filters.append('Левый')
        elif update.callback_query.data == 'm9_2':
            current_filters.append('Правый')

        self.user_manager.set_filter(user_id, FILTER_WHEEL, current_filters)

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
                                 text="Привет! Настрой фильтры и я буду присылать тебе все новые объявления о продаже автомобилей с 999.md",
                                 reply_markup=self.menu.reply_markup)

    def stop(self, update, context) -> None:

        self.user_manager.delete_user(update.effective_chat.id)

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Чтобы опять получать уведомления - введи /start и настрой фильтры')

    def unknown(self, update, context) -> None:

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Я не знаю такой команды")


if __name__ == '__main__':
    print('Only for import!')
