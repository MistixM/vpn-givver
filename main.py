# Import dependencies
import config # Config with all bot data
import logging
import asyncio
import sqlite3 # Database
import datetime
import os
import payment # Payment API

# Bot lib
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

# StateFilter
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import CallbackQuery

from aiogram.types.message import ContentType

# For debugging
logging.basicConfig(level=logging.INFO)

# Create bot object with TOKEN
bot = Bot(token=config.TOKEN,
          parse_mode='HTML')

# Create dispatcher, database and initialise database cursor
dp = Dispatcher()
db = sqlite3.connect('user-data.db') # Connect database
c = db.cursor()

# Buttons
buy = config.BUY
subscriptions = config.SUBSCRIPTIONS
reviews = config.REVIEWS
support = config.SUPPORT
any_country = config.ANY_COUNTRY
countries = config.COUNTRIES

# Personal user data
class UserData():
    def __init__(self, user_id):
        self.subscriped = []
        self.user_id = user_id
        self.question_message = None
        self.country = None
        self.title = None

    def save_subscription_to_db(self):
        c.execute("DELETE FROM subscriptions WHERE user_id=?", (self.user_id,))
        for sub in self.subscriped:
            c.execute('INSERT INTO subscriptions (user_id, offer, key) VALUES (?, ?, ?)',
                      (self.user_id, sub["offer"], sub["key"]))
            db.commit()

    @staticmethod
    def load_subscription_from_db(user_id):
        c.execute("SELECT offer, key FROM subscriptions WHERE user_id=?", (user_id,))
        subscriped = [{"offer": row[0], "key": row[1]} for row in c.fetchall()]
        return subscriped
    
# For storing user id
user_data_list = {}

# Initialise '/start' command
@dp.message(Command(commands=['start']))
async def start_handler(msg: types.Message):

    # If user id not in list, append
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
        user_data_list[user_id].subscriped = UserData.load_subscription_from_db(user_id)

        # Check, if value in this table already exists
        c.execute("SELECT * FROM potential_customers WHERE username=?", (msg.from_user.username,))
        data = c.fetchone()

        if data is None:
            # Append user into SQL table
            c.execute("INSERT INTO potential_customers VALUES(?, ?)", (msg.from_user.username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            db.commit()

    # Get bot info
    bot_info = await bot.get_me()

    # Prepare buttons
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=buy), KeyboardButton(text=subscriptions)], 
                                       [KeyboardButton(text=reviews), KeyboardButton(text=support)]],
                             resize_keyboard=True)
    
    # Greetings to user with keyboard
    await bot.send_message(msg.chat.id, 
                           f"👋 Добро пожаловать в бота {bot_info.full_name}\n\n🚀 Здесь ты можешь оформить и пользоваться нашим VPN 24/7 без ограничений",
                           reply_markup=kb)

# Buy button handler
@dp.message(lambda msg: msg.text == buy)
async def buy_clicked(msg: types.Message):
    # If user id not in list, append
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)

    # Prepare new interaction keyboard
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=any_country), KeyboardButton(text=countries)]],
                             resize_keyboard=True)
    
    # Send question about country
    await bot.send_message(msg.chat.id,
                           config.WHICH_COUNTRY,
                           reply_markup=kb)

# Any countries handler
@dp.message(lambda msg: msg.text == any_country)
async def any_country_clicked(msg: types.Message):
    # If not in list, append
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
        user_data_list[user_id].subscriped = UserData.load_subscription_from_db(user_id)
    
    # Get personal info using personal user class
    user_data = user_data_list[msg.chat.id]

    # Set country as any and propose the plan
    user_data.country = 'any_country'
    await propose_plan(msg)

# Countries handler
@dp.message(lambda msg: msg.text == countries)
async def countries_clicked(msg: types.Message):
    # If user not in the list, append id
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
        user_data_list[user_id].subscriped = UserData.load_subscription_from_db(user_id)
        
    # Prepare new interaction keyboard with available countries
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Германия 🇩🇪', callback_data='germany')], 
                                                [InlineKeyboardButton(text='Финляндия 🇫🇮', callback_data='finland')],
                                                [InlineKeyboardButton(text='Швейцария 🇨🇭', callback_data='switz')],
                                                [InlineKeyboardButton(text='Турция 🇹🇷', callback_data='turkey')]])    
    
    # Propose this countries
    await bot.send_message(msg.chat.id,
                           config.WHICH_COUNTRY,
                           reply_markup=kb)
    
# Other buttons handlers   
@dp.message(lambda msg: msg.text == subscriptions)
async def subs_clicked(msg: types.Message):
    # If user not in the list, append
    if msg.chat.id not in user_data_list:
        user_data_list[msg.chat.id] = UserData(msg.chat.id)
        user_data_list[msg.chat.id].subscriped = UserData.load_subscription_from_db(msg.chat.id)

    # Get personal user data
    user_data = user_data_list[msg.chat.id] 

    # If user don't have any subscriptions send warning message
    if not user_data.subscriped:
        await bot.send_message(msg.chat.id, config.SUB_ERR)

    # Otherwise get all subscription list
    else:
        text = '\n'.join([f'<b>{sub["offer"]}</b> - <code>{sub["key"]}</code>' for sub in user_data.subscriped])
        await bot.send_message(msg.chat.id,
                               f'<b>Текущие подписки:</b>\n\n{text}')

# Reviews button handler      
@dp.message(lambda msg: msg.text == reviews)
async def review_clicked(msg: types.Message):
    # If user not in the list, append
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)

    # Get bot info
    bot_info = await bot.get_me()

    # Send user information about reviews
    await bot.send_message(msg.chat.id,
                           f'⭐️ Отзывы {bot_info.full_name}: https://t.me/kvpnchat')

# Support button handler
@dp.message(lambda msg: msg.text == support)
async def support_clicked(msg: types.Message):
    # Send message about support
    await bot.send_message(msg.chat.id,
                           config.SUPPORT_INFO)

# Callbacks handler
@dp.callback_query(lambda d: d.data)
async def callbacks_handler(callback: CallbackQuery):
    # If user id not in the list, append
    user_id = callback.message.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)

    # Get user data
    user_data = user_data_list[callback.message.chat.id]

    # If subscription callback with term, send offer using function below the code
    if callback.data == "one_day":
        if await check_files(callback.message):

            pay_url, pay_id = payment.create(config.ONE_DAY,
                                            user_id, 
                                            f"Покупка VPN на 1 день (до {get_term_info(1)})")

            user_data.title = 'VPN на 1 день'

            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Перейти к оплате', url=pay_url, callback_data=''), InlineKeyboardButton(text='Подтвердить оплату', callback_data=f'success_payment_{pay_id}')]])
            
            await bot.send_message(user_id, 
                                f"Ваш номер заказа: <b>{pay_id.strip()}</b>",
                                reply_markup=kb)

        else:
            await bot.send_message(callback.message.chat.id,
                        config.PAYMENT_ERROR)

    elif callback.data == "one_month":
        if await check_files(callback.message):
            pay_url, pay_id = payment.create(config.ONE_MONTH,
                                            user_id, 
                                            f"Покупка VPN на 1 месяц (до {get_term_info(30)})")
            
            user_data.title = 'VPN на 1 месяц'
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Перейти к оплате', url=pay_url, callback_data=''), InlineKeyboardButton(text='Подтвердить оплату', callback_data=f'success_payment_{pay_id}')]])
            
            await bot.send_message(user_id, 
                                f"Ваш номер заказа: <b>{pay_id.strip()}</b>",
                                reply_markup=kb)
            
        else:
            await bot.send_message(callback.message.chat.id,
                        config.PAYMENT_ERROR)

    elif callback.data == "three_month":
        if await check_files(callback.message):

            pay_url, pay_id = payment.create(config.THREE_MONTH,
                                        user_id, 
                                        f"Покупка VPN на 3 месяца (до {get_term_info(90)})")
            
            user_data.title = 'VPN на 3 месяца'
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Перейти к оплате', url=pay_url, callback_data=''), InlineKeyboardButton(text='Подтвердить оплату', callback_data=f'success_payment_{pay_id}')]])
            
            await bot.send_message(user_id, 
                                f"Ваш номер заказа: <b>{pay_id.strip()}</b>",
                                reply_markup=kb)
            
        else:
            await bot.send_message(callback.message.chat.id,
                        config.PAYMENT_ERROR)

    elif callback.data == "six_month":
        if await check_files(callback.message):

            pay_url, pay_id = payment.create(config.SIX_MONTH,
                                        user_id, 
                                        f"Покупка VPN на 6 месяцев (до {get_term_info(180)})")
            
            user_data.title = 'VPN на 6 месяцев'
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Перейти к оплате', url=pay_url, callback_data=''), InlineKeyboardButton(text='Подтвердить оплату', callback_data=f'success_payment_{pay_id}')]])
            
            await bot.send_message(user_id, 
                                f"Ваш номер заказа: <b>{pay_id.strip()}</b>",
                                reply_markup=kb)
            
        else:
            await bot.send_message(callback.message.chat.id,
                                   config.PAYMENT_ERROR)
            
    elif callback.data == "year":
        if await check_files(callback.message):
            pay_url, pay_id = payment.create(config.YEAR,
                                        user_id, 
                                        f"Покупка VPN на 12 месяцев (до {get_term_info(360)})")
            
            user_data.title = 'VPN на 12 месяцев'
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Перейти к оплате', url=pay_url, callback_data=''), InlineKeyboardButton(text='Подтвердить оплату', callback_data=f'success_payment_{pay_id}')]])
            
            await bot.send_message(user_id, 
                                f"Ваш номер заказа: <b>{pay_id.strip()}</b>",
                                reply_markup=kb)
            
        else:
            await bot.send_message(callback.message.chat.id,
                                   config.PAYMENT_ERROR)

    elif "success_payment" in callback.data:
        result = payment.check(callback.data.split('_')[-1])

        if result:
            if user_data.country == "germany":
                await invoice_handler(callback, user_data, "germany", "used_germany")
            elif user_data.country == "finland":
                await invoice_handler(callback, user_data, "finland", "used_finland")
            elif user_data.country == "switz":
                await invoice_handler(callback, user_data, "switz", "used_switz")
            elif user_data.country == "turkey":
                await invoice_handler(callback, user_data, "turkey", "used_turkey")
            else:
                await invoice_handler(callback, user_data, "any_country", "used_any_country")

        else:
            await callback.message.answer('Оплата не прошла. Попробуйте ещё раз! 😕')
                
    # If callback is menu, create new keyboard and go to the menu 
    elif callback.data == "menu":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=buy), KeyboardButton(text=subscriptions)], 
                                    [KeyboardButton(text=reviews), KeyboardButton(text=support)]],
                            resize_keyboard=True)

        sent_msg = await bot.send_message(callback.message.chat.id,
                                    config.BACK_TO_MENU,
                                    reply_markup=kb)
    
    # Callbacks for countries
    # Each country will be stored in user data class
    elif callback.data == "germany":
        user_data.country = callback.data
        await propose_plan(callback.message)
    elif callback.data == "finland":
        user_data.country = callback.data  
        await propose_plan(callback.message)
    elif callback.data == "switz":
        user_data.country = callback.data
        await propose_plan(callback.message)  
    elif callback.data == "turkey":
        user_data.country = callback.data  
        await propose_plan(callback.message)

    # Callbacks for reminder
    elif callback.data == "yes":
        # If user have problems send support contact
        await support_clicked(callback.message)
        await bot.delete_message(callback.message.chat.id, user_data.question_message)
    elif callback.data == "no":
        # If everything okay, just delete the message
        await bot.delete_message(callback.message.chat.id, user_data.question_message)

# Checkout (must be here)
# It checks if text file with keys exists
@dp.pre_checkout_query(lambda query: True)
async def pre_check(precheck_q: types.PreCheckoutQuery):
    # Get user info
    user_id = precheck_q.from_user.id
    user_data = user_data_list.get(user_id, None)

    # Check if there's available txt files with keys
    if user_data:
        country = user_data.country
        if country in ['germany', 'finland', 'switz', 'turkey', 'any_country']:
            filename = f"keys/{country}.txt"
            # If not txt file exists or it's empty, decline payment and notify about error
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                await bot.answer_pre_checkout_query(precheck_q.id, ok=False, error_message=config.PAYMENT_ERROR)
    
    # If there's available txt files, approve invoice
    await bot.answer_pre_checkout_query(precheck_q.id, ok=True)

async def check_files(msg):
    user_id = msg.chat.id
    user_data = user_data_list.get(user_id, None)

    if user_data:
        country = user_data.country
        if country in ['germany', 'finland', 'switz', 'turkey', 'any_country']:
            filename = f"keys/{country}.txt"
            # If not txt file exists or it's empty, decline payment and notify about error
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                return False
            
    return True


# Create a new table if its exist
def create_sqltable(cursor, name, execution):
    if not table_exists(cursor, name):
        cursor.execute(execution)

# Function that will check if table exists using sqlite_master
def table_exists(cursor, table_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def get_term_info(days) -> str:
    # Current date
    current_date = datetime.datetime.now()

    # Term
    end_date = current_date + datetime.timedelta(days=days)

    # Form date str
    end_date_str = end_date.strftime("%d.%m.%y")

    return end_date_str

# Scraping each txt file and send it to the user
async def invoice_handler(callback, user_data, filename, used_filename):
    # Find specific file to scrap
    with open(f"keys/{filename}.txt", 'r') as file:
        lines = file.readlines()

    # Delete file from the main file and put it into the txt file that contains used keys
    if lines:
        with open(f"keys/{used_filename}.txt", "a") as used_file:
            used_file.write(lines[0])

        with open(f"keys/{filename}.txt", "w") as file:
            file.writelines(lines[1:])

        # Divide key info
        key = lines[0].strip()

        # Prepare keyboard
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=buy), KeyboardButton(text=subscriptions)], 
                                            [KeyboardButton(text=reviews), KeyboardButton(text=support)]],
                                    resize_keyboard=True)

        # Notify about success payment
        await bot.send_message(callback.message.chat.id,
                               text=f'✅ Успешная оплата!\n\nВаш ключ: <code>{key}</code>',
                               reply_markup=kb)
        
        # Then send tutorial explanation
        await bot.send_message(callback.message.chat.id,
                               text=config.TUTORIAL)
        
        # Fill out subscription info to the personal user class
        user_data.subscriped.append({"offer": user_data.title,
                                "key": key})

        user_data.save_subscription_to_db()

        # Execute values into the SQL database
        c.execute("INSERT INTO customers VALUES(?, ?, ?, ?)", (callback.from_user.username, 
                                                               datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                               key,
                                                               user_data.title))
        # Commit changes
        db.commit()

# Plan proposition
async def propose_plan(msg):
    # Send inline list with plans
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⭐ 1 день - 10 руб.", callback_data="one_day")], [InlineKeyboardButton(text="⭐ 1 месяц - 179 руб.", callback_data="one_month")],
                                       [InlineKeyboardButton(text="⭐ 3 месяца - 460 руб. (-14%)", callback_data="three_month")], [InlineKeyboardButton(text="⭐ 6 месяц - 900 руб. (-16%)", callback_data="six_month")],
                                       [InlineKeyboardButton(text="⭐ 12 месяцев - 1700 руб. (-20%)", callback_data="year")], [InlineKeyboardButton(text="👈 Меню", callback_data='menu')]])

    # Remove previous keyboard
    sent_msg = await bot.send_message(msg.chat.id,
                           config.PROPOSE_PLAN,
                           reply_markup=ReplyKeyboardRemove())
    
    await bot.delete_message(msg.chat.id, sent_msg.message_id)
    
    # And apply new one
    await bot.send_message(msg.chat.id,
                           config.PROPOSE_PLAN,
                           reply_markup=kb)


async def main():
    # Create to sqltables if they exists
    # - potential_customers: for storing information about potential customers that has already started communication with bot
    # - customers: for storing information about customers that has already bought the plan
    create_sqltable(c, "potential_customers", "CREATE TABLE potential_customers(username text, date text)")
    create_sqltable(c, "customers", "CREATE TABLE customers(username text, date_purchase text, key text, term text)")
    create_sqltable(c, "subscriptions", "CREATE TABLE subscriptions(user_id integer, offer text, key text)")

    # Start bot life
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def load_user_data():
    c.execute("SELECT DISTINCT user_id FROM subscriptions")
    user_ids = [row[0] for row in c.fetchall()]
    for user_id in user_ids:
        user_data = UserData(user_id)
        user_data.subscriped = UserData.load_subscription_from_db(user_id)
        user_data_list[user_id] = user_data

# Using asyncio run main func
if __name__ == "__main__":
    asyncio.run(main())