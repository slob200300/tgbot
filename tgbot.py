import telebot
from config import token, link2, answer, med_price_info, add_price_message, med_profile
from telebot import types
from PatientRegistration import user_registrations, PatientRegistration as PR
from CancelRegistration import user_cancelation, CancelRegistration as CR


#telebot.apihelper.proxy = {'https': 'socks5h://127.0.0.1:10808'}
bot = telebot.TeleBot(token)
img_array = []


def submenu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    online_reception_button = types.KeyboardButton('Записаться на прием врача')
    info_button = types.KeyboardButton('Как записаться на прием к специалисту?')
    price_list_button = types.KeyboardButton('Платные услуги')
    specialist = types.KeyboardButton('Специалисты')
    cancel_reseption_button = types.KeyboardButton('Отменить запись к врачу')
    keyboard.add(online_reception_button)
    keyboard.add(info_button)
    keyboard.add(price_list_button, specialist)
    keyboard.add(cancel_reseption_button)
    return keyboard

def med_profile_keyboard(buttons=[]):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_price_button = types.KeyboardButton('⬅️ Вернуться в меню платных услуг')
    keyboard.add(back_price_button)
    for button in buttons: 
        keyboard.add(types.KeyboardButton(button))
    return keyboard

def price_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_button = types.KeyboardButton('⬅️ Назад в меню')
    price_button = types.KeyboardButton('Стоимость консультативного приема')
    payment_instruct = types.KeyboardButton('Как проходит оплата?')
    keyboard.add(price_button)
    keyboard.add(payment_instruct)
    keyboard.add(back_button)
    return keyboard


def is_valid_type(message):
    return message.content_type == 'text'
       

@bot.message_handler(commands=['start'])
def send_welcome(message):
    with open('/home/sou-3.2-2/chatbot/vokb_logotip2.png', 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption="Добрый день! Вы обратились в контактно-информационный центр Волгоградской областной клинической больницы №1.  Выберите интересующий Вас вопрос.", reply_markup=submenu_keyboard())


@bot.message_handler(func=lambda message: message.text == "Записаться на прием врача")
def reception(message):
    bot.send_message(message.chat.id, "Начало регистрации")
    print("Начало процесса регистрации.")  # Отладочная строка
    user_registrations[message.from_user.id] = PR(bot, submenu_keyboard)
    user_registrations[message.from_user.id].start_registration(message)


@bot.message_handler(func=lambda message: message.text == "Отменить запись к врачу")
def cancel_reception(message):
    bot.send_message(message.chat.id, "Отмена регистрации")
    print("Начало отмены регистрации.")  # Отладочная строка
    user_cancelation[message.from_user.id] = CR(bot, submenu_keyboard)
    user_cancelation[message.from_user.id].cancel_registration(message)


@bot.message_handler(func=lambda message: message.text == "Как записаться на прием к специалисту?")
def send_info(message):
    bot.send_message(message.chat.id, answer , reply_markup=submenu_keyboard())


@bot.message_handler(func=lambda message: message.text == "Платные услуги")
def paid_services(message):
    bot.send_message(message.chat.id, "Выберите, пожалуйста, интересующий Вас вопрос." , reply_markup=price_keyboard())


@bot.message_handler(func=lambda message: message.text == "Стоимость консультативного приема")
def send_price(message):
    bot.send_message(message.chat.id, "Выберите, пожалуйста, желаемый профиль." , reply_markup=med_profile_keyboard(med_profile))
    bot.register_next_step_handler(message, price_filter)


def price_filter(message):
    if not is_valid_type(message):
        bot.send_message(message.chat.id, "Отправьте текстовое сообщение")
        return bot.register_next_step_handler(message,price_filter)
    if message.text == '⬅️ Вернуться в меню платных услуг':
        return back_to_price(message)
    profile = message.text
    if profile in med_price_info:
        price = med_price_info[profile]
        print(price)
        price_message = ''
        for procedure, price in med_price_info[profile].items():
            price_message += f"{procedure}: {price}₽\n"
        bot.send_message(message.chat.id, price_message + '(повторное обращение к одному и тому же специалисту в течение месяца)', reply_markup=med_profile_keyboard(med_profile))
        return bot.register_next_step_handler(message,price_filter)
    else:
        bot.send_message(message.chat.id, "Нет информации по этому профилю.", reply_markup=med_profile_keyboard(med_profile))
        return bot.register_next_step_handler(message,price_filter)


@bot.message_handler(func=lambda message: message.text == "Как проходит оплата?")
def payment_instruct(message):
    bot.send_message(message.chat.id, add_price_message, reply_markup=price_keyboard())

@bot.message_handler(func=lambda message: message.text == "Специалисты")
def specialist(message):
    bot.send_message(message.chat.id, 'Подробная информация о каждом специалисте представлена на официальном сайте ГБУЗ «ВОКБ №1 »' + link2, reply_markup=submenu_keyboard())

@bot.message_handler(func=lambda message: message.text == "⬅️ Назад в меню")
def one_step_back(message):
    bot.send_message(message.chat.id, 'Вы вернулись в меню' ,reply_markup=submenu_keyboard())

@bot.message_handler(func=lambda message: message.text == "⬅️ Вернуться в меню платных услуг")
def back_to_price(message):
    bot.send_message(message.chat.id, 'Вы вернулись в меню платных услуг' ,reply_markup=price_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_random_messages(message):
    bot.send_message(message.chat.id, "Пожалуйста, используйте кнопки для навигации.", reply_markup=submenu_keyboard())

@bot.message_handler(content_types=['video', 'audio', 'document', 'photo', 'animation', 'voice', 'video_note', 'contact', 'location', 'poll'])
def handle_multimedia(message):
    bot.send_message(message.chat.id, "Пожалуйста, используйте кнопки для навигации.", reply_markup=submenu_keyboard())


bot.polling(none_stop=True, interval=0)