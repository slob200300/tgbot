import telebot
from config import token, admin_email, email_password, link, questions as que, answers, contact_information
from telebot import types
from PatientRegistration import PatientRegistration as PR


#telebot.apihelper.proxy = {'https': 'socks5h://127.0.0.1:10808'}
bot = telebot.TeleBot(token)


def main_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=False)
    main_menu_button = types.KeyboardButton('Главное меню')
    contact_button = types.KeyboardButton('Контактная информация')
    keyboard.add(main_menu_button)
    keyboard.add(contact_button)
    return keyboard

def submenu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    online_reception_button = types.KeyboardButton('Записаться на прием врача')
    back_button = types.KeyboardButton('Назад в главное меню')
    info_button = types.KeyboardButton('Частозадаваемые вопросы')
    keyboard.add(online_reception_button)
    keyboard.add(info_button, back_button)
    return keyboard

def questions_keyboard(questions):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_button = types.KeyboardButton('Назад')
    for question in questions:
        keyboard.add(types.KeyboardButton(question))
    keyboard.add(back_button)
    return keyboard

patient_registration = PR(bot, submenu_keyboard)  # Создаем экземпляр класса


@bot.message_handler(commands=['start'])
def send_welcome(message):
    with open('/home/sou-3.2-2/Рабочий стол/чат-бот/vokb_logotip2.png', 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption="Здравствуйте, вы обратились в РТМЦ, что вас интересует?", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "Главное меню")
def main_menu(message):
    bot.send_message(message.chat.id, "Вы в главном меню. Выберите действие:", reply_markup=submenu_keyboard())

@bot.message_handler(func=lambda message: message.text == "Записаться на прием врача")
def reception(message):
    bot.send_message(message.chat.id, "Пожалуйста, заполните следующие данные: ")
    print("Начало процесса регистрации.")  # Отладочная строка
    patient_registration.start_registration(message)
    print(patient_registration.name)


@bot.message_handler(func=lambda message: message.text == "Контактная информация")
def send_contact(message):
    bot.send_message(message.chat.id, contact_information, reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "Частозадаваемые вопросы")
def send_info(message):
    bot.send_message(message.chat.id, "Выберите интересующий вас вопрос:", reply_markup=questions_keyboard(que))

@bot.message_handler(func=lambda message: message.text in que)
def handle_question(message):
    print(f"Received question: {message.text}") 
    index = que.index(message.text)  # Получаем индекс вопроса
    answer = answers[index]  # Находим соответствующий ответ
    bot.send_message(message.chat.id, answer, reply_markup=questions_keyboard(que))  


@bot.message_handler(func=lambda message: message.text == "Назад")
def one_step_back(message):
    bot.send_message(message.chat.id, 'Вы вернулись в меню' ,reply_markup=submenu_keyboard())

@bot.message_handler(func=lambda message: message.text == "Назад в главное меню")
def back_to_main_menu(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню. Выберите действие:", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_random_messages(message):
    bot.send_message(message.chat.id, "Пожалуйста, используйте кнопки для навигации.", reply_markup=submenu_keyboard())

bot.polling(none_stop=True, interval=0)