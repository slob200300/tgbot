import telebot
from telebot import types
import re
import smtplib
from email.mime.text import MIMEText
from config import admin_email, email_password

class PatientRegistration:
    def __init__(self, bot, menu_keyboard_func):
        self.bot = bot
        self.menu_keyboard = menu_keyboard_func
        self.name = ''
        self.surname = ''
        self.father_name = ''
        self.phone = None
        self.med_profile_selected = None
        self.type_of_reception_selected = None
        self.med_profile = [
            'Акушер-Гинеколог', 'Гастроэнтеролог', 
            'Гематолог', 'Дерматолог', 'Кардиолог', 
            'Невролог', 'Нейрохирург', 'Оториноларинголог', 
            'Офтальмолог', 'Пульмонолог', 
            'Сердечно-сосудистый хирург', 'Торакальный хирург', 
            'Травматолог-ортопед', 'Уролог', 
            'Хирург', 'Челюстно-лицевой хирург', 
            'Эндокринолог'
        ]
        self.type_of_reception = ['OMC', 'За счет личных средств']
        self.last_answer = ['Да', 'Нет']

    def start_registration(self, message):
        self.bot.send_message(message.from_user.id, 'Как вас зовут?', reply_markup=self.registration_keyboard())
        self.bot.register_next_step_handler(message, self.get_name)

    def registration_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton('🛑 Остановить регистрацию')
        keyboard.add(stop_button)
        return keyboard

    def get_name(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return 
        if not self.is_valid_name(message.text):
            self.bot.send_message(message.from_user.id, "Ошибка: Имя должно содержать только буквы. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_name)  # Повторный запрос
        self.name = message.text
        self.bot.send_message(message.from_user.id, 'Какая у вас фамилия?')
        self.bot.register_next_step_handler(message, self.get_surname)

    def get_surname(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if not self.is_valid_name(message.text):
            self.bot.send_message(message.from_user.id, "Ошибка: Фамилия должно содержать только буквы. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_surname)
        self.surname = message.text
        self.bot.send_message(message.from_user.id, 'Какое у вас отчество?')
        self.bot.register_next_step_handler(message, self.get_father_name)

    def get_father_name(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if not self.is_valid_name(message.text):
            self.bot.send_message(message.from_user.id, "Ошибка: Отчество должно содержать только буквы. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_father_name)
        self.father_name = message.text
        self.bot.send_message(message.from_user.id, 'Напишите ваш номер телефона в формате: 71234567890')
        self.bot.register_next_step_handler(message, self.get_phone)

    def get_phone(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if not self.is_valid_phone(message.text) or len(message.text) != 11:
            self.bot.send_message(message.from_user.id, "Ошибка: Номер телефона должен содержать только цифры и состоять из 11 символов. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_phone)
        self.phone = message.text
        self.bot.send_message(message.from_user.id, 'Выберите медицинский профиль', reply_markup=self.med_profile_keyboard())
        self.bot.register_next_step_handler(message, self.get_med_profile)

    def med_profile_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton('🛑 Остановить регистрацию')
        keyboard.add(stop_button)
        for profile in self.med_profile:
            keyboard.add(types.KeyboardButton(profile))
        return keyboard

    def get_med_profile(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if message.text not in self.med_profile:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберете профиль из списка.')
            return self.bot.register_next_step_handler(message, self.get_med_profile)
        self.med_profile_selected = message.text
        self.bot.send_message(message.from_user.id, 'Выберите тип приема', reply_markup=self.type_of_reception_keyboard())
        self.bot.register_next_step_handler(message, self.get_type_of_reception)

    def type_of_reception_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton('🛑 Остановить регистрацию')
        keyboard.add(stop_button)
        for reception in self.type_of_reception:
            keyboard.add(types.KeyboardButton(reception))
        return keyboard

    def get_type_of_reception(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if message.text not in self.type_of_reception:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберете тип приема из списка.')
            return self.bot.register_next_step_handler(message, self.get_type_of_reception)
        self.type_of_reception_selected = message.text
        info = (f"Имя: {self.name}\nФамилия: {self.surname}\nОтчество: {self.father_name}\n"
        f"Телефон: {self.phone}\nМедицинский профиль: {getattr(self, 'med_profile_selected', 'Не выбран')}\n"
        f"Тип приема: {getattr(self, 'type_of_reception_selected', 'Не выбран')}")
        self.bot.send_message(message.from_user.id, info)
        self.bot.send_message(message.from_user.id, 'Указанные вами данные верны?', reply_markup=self.last_answer_keyboard())
        self.bot.register_next_step_handler(message, self.get_type_last_answer)

    def last_answer_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton('🛑 Остановить регистрацию')
        keyboard.add(stop_button)
        for answer in self.last_answer:
            keyboard.add(types.KeyboardButton(answer))
        return keyboard

    def get_type_last_answer(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if message.text not in self.last_answer:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберете ответ из списка.')
            return self.bot.register_next_step_handler(message, self.get_type_last_answer)
        if message.text == 'Да':
            self.display_patient_info(message.chat.id)
        elif message.text == 'Нет':
            self.start_registration(message)

    def stop_registration(self, message):
        self.bot.send_message(message.chat.id, "Регистрация остановлена. Вы вернулись в меню.", reply_markup=self.menu_keyboard())

    def display_patient_info(self, chat_id):
        #info = (f"Имя: {self.name}\nФамилия: {self.surname}\nОтчество: {self.father_name}\n"
          #      f"Телефон: {self.phone}\nМедицинский профиль: {getattr(self, 'med_profile_selected', 'Не выбран')}\n"
          #      f"Тип приема: {getattr(self, 'type_of_reception_selected', 'Не выбран')}")
      #  self.bot.send_message(chat_id, info)
        self.send_email()
        self.bot.send_message(chat_id, "Вы успешно записаны, ждите обратной связи", reply_markup=self.menu_keyboard())

    def is_valid_name(self, name):
        return bool(re.match("^[А-Яа-яЁё\s-]+$", name))

    def is_valid_phone(self, phone):
        return phone.isdigit()

    def send_email(self):
        subject = "Новая запись на прием через телеграм"
        body = (f"Новая запись на прием:\n"
                f"Имя: {self.name}\n"
                f"Фамилия: {self.surname}\n"
                f"Отчество: {self.father_name}\n"
                f"Телефон: {self.phone}\n"
                f"Медицинская специальность: {getattr(self, 'med_profile_selected', 'Не выбран')}\n"
                f"Тип приема: {getattr(self, 'type_of_reception_selected', 'Не выбран')}")

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = admin_email
        msg['To'] = admin_email

        try:
            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(admin_email, email_password)
                server.send_message(msg)
            print("Письмо отправлено успешно.")
        except Exception as e:
            print(f"Не удалось отправить письмо: {e}")