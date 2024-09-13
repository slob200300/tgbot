from telebot import types
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import os
import logging
from config import admin_email, email_password


user_cancelation = {}

logging.basicConfig(level=logging.INFO)

class CancelRegistration:
    STOP_REGISTRATION_BUTTON = '🛑 Остановить процесс'

    def __init__(self, bot, menu_keyboard_func):
        self.bot = bot
        self.menu_keyboard = menu_keyboard_func
        self.fio = ''
        self.med_profile_selected = None
        self.additional_information = "Не указано"
        self.user_id = None
        self.med_profile = [
            'Акушер-Гинеколог', 'Гастроэнтеролог', 'Гематолог', 
            'Дерматовенеролог', 'Кардиолог', 'Невролог', 
            'Нейрохирург', 'Оториноларинголог', 'Офтальмолог', 
            'Пульмонолог', 'Сердечно-сосудистый хирург', 
            'Торакальный хирург', 'Травматолог', 'Уролог', 
            'Хирург', 'Челюстно-лицевой хирург', 'Эндокринолог'
        ]
        self.last_answer = ['Да', 'Нет']

    def create_keyboard(self, buttons):
        """Создает клавиатуру с заданными кнопками."""
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton(self.STOP_REGISTRATION_BUTTON)
        keyboard.add(stop_button)
        for button in buttons:
            keyboard.add(types.KeyboardButton(button))
        return keyboard

    def check_stop_registration(self, message):
        if message.text == self.STOP_REGISTRATION_BUTTON:
            self.stop_registration(message)
            return True
        return False

    def is_valid_type(self, message):
        return message.content_type == 'text'

    def stop_registration(self, message):
        self.bot.send_message(message.chat.id, "Процесс отмены записи остановлен. Вы вернулись в меню.", reply_markup=self.menu_keyboard())

    def cancel_registration(self, message):
        """Начинает процесс отмены регистрации."""
        self.bot.send_message(message.from_user.id, 'Для отмены регистрации, пожалуйста, напишите полностью фамилию, имя, отчество и дату рождения.', reply_markup=self.create_keyboard([]))
        self.bot.register_next_step_handler(message, self.get_fio)

    def get_fio(self, message):
        """Получает ФИО от пользователя."""
        if self.check_stop_registration(message):
            return
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Ошибка: сообщение должно быть текстовым, повторите ввод")
            return self.bot.register_next_step_handler(message, self.get_fio)
        self.user_id = message.from_user.id
        self.fio = message.text
        self.bot.send_message(message.from_user.id, 'Выберите профиль врача из списка.', reply_markup=self.med_profile_keyboard())
        self.bot.register_next_step_handler(message, self.get_med_profile)

    def med_profile_keyboard(self):
        """Создает клавиатуру для выбора медицинского профиля."""
        return self.create_keyboard(self.med_profile)

    def get_med_profile(self, message):
        """Получает медицинский профиль от пользователя."""
        if self.check_stop_registration(message):
            return
        if not self.is_valid_type(message) or message.text not in self.med_profile:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберите профиль из списка.')
            return self.bot.register_next_step_handler(message, self.get_med_profile)
        self.med_profile_selected = message.text
        self.bot.send_message(message.from_user.id, 'Напишите, пожалуйста, дополнительную информацию при необходимости. Если такой нет, проставьте 0.', reply_markup=self.create_keyboard([]))
        self.bot.register_next_step_handler(message, self.add_information)

    def add_information(self, message):
        """Получает дополнительную информацию от пользователя."""
        if self.check_stop_registration(message):
            return
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Ошибка: Сообщение должно быть текстовым, повторите ввод")
            return self.bot.register_next_step_handler(message, self.add_information)
        if message.text == "0":
            self.additional_information = "Не указано"
        else:
            self.additional_information = message.text
        self.bot.send_message(message.from_user.id, 'Вы подтверждаете отмену записи?', reply_markup=self.last_answer_keyboard())
        self.bot.register_next_step_handler(message, self.get_confirmation)

    def last_answer_keyboard(self):
        """Создает клавиатуру для ответа на подтверждение."""
        return self.create_keyboard(self.last_answer)

    def get_confirmation(self, message):
        """Получает подтверждение на отмену записи от пользователя."""
        if self.check_stop_registration(message):
            return
        if not self.is_valid_type(message) or message.text not in self.last_answer:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберите ответ из списка.')
            return self.bot.register_next_step_handler(message, self.get_confirmation)
        if message.text == 'Да':
            self.finalize_cancellation(message.from_user.id)
        else:
            self.bot.send_message(message.from_user.id, 'Операция отменена, вы вернулись в меню.', reply_markup=self.menu_keyboard())

    def finalize_cancellation(self, user_id):
        """Заканчивает отмену записи и отправляет уведомление."""
        self.bot.send_message(user_id, 'Спасибо за заявку, Ваша запись будет отменена.', reply_markup=self.menu_keyboard())
        self.send_email()

    def send_email(self):
        """Отправляет уведомление об отмене записи на почту администратора."""
        subject = "Отмена записи на прием врача через телеграм"
        body = self.create_email_body()
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = admin_email
        msg['To'] = admin_email
        msg.attach(MIMEText(body, 'html'))
        
        try:
            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(admin_email, email_password)
                server.send_message(msg)
            logging.info("Письмо отправлено успешно.")
        except Exception as e:
            logging.error(f"Не удалось отправить письмо: {e}")

    def create_email_body(self):
        """Создает HTML-содержимое письма."""
        return (f"""
        <html>
            <body>
                <h2 style="font-size: 24px;">Отмена записи на прием:</h2>
                <ul style="font-size: 18px;">
                    <li><strong>ФИО:</strong> {self.fio}</li>
                    <li><strong>Медицинская специальность:</strong> {getattr(self, 'med_profile_selected', 'Не выбран')}</li>
                    <li><strong>Дополнительная информация:</strong> {self.additional_information}</li>
                    <li><strong>ID пациента:</strong> {self.user_id}</li>
                </ul>
            </body>
        </html>
        """)



