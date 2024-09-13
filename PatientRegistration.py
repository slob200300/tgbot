from telebot import types
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import numpy as np
import cv2
from PIL import Image
import os
import logging
from config import admin_email, email_password, example_path
from TextRecognition import image_to_text as ITT

user_registrations = {}

class PatientRegistration:
    STOP_REGISTRATION_BUTTON = '🛑 Остановить регистрацию'

    def __init__(self, bot, menu_keyboard_func):
        self.bot = bot
        self.menu_keyboard = menu_keyboard_func
        self.fio = ''
        self.phone = None
        self.med_profile_selected = None
        self.type_of_reception_selected = None
        self.med_profile = [
            'Акушер-Гинеколог', 'Гастроэнтеролог',
            'Гематолог', 'Дерматовенеролог', 'Кардиолог',
            'Невролог', 'Нейрохирург', 'Оториноларинголог',
            'Офтальмолог', 'Пульмонолог',
            'Сердечно-сосудистый хирург', 'Торакальный хирург',
            'Травматолог', 'Уролог',
            'Хирург', 'Челюстно-лицевой хирург',
            'Эндокринолог'
        ]
        self.type_of_reception = ['OMC (при наличии направления)', 'За счет личных средств',
                                  'ДМС / Договор с организацией']
        self.last_answer = ['Да', 'Нет']
        self.additional_information = ''
        self.bot_status = None
        self.ITT_status = 0
        self.photo_path = ''
        self.user_id = []

    def create_keyboard(self, buttons):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        stop_button = types.KeyboardButton(self.STOP_REGISTRATION_BUTTON)
        keyboard.add(stop_button)
        for button in buttons:
            keyboard.add(types.KeyboardButton(button))
        return keyboard

    def registration_keyboard(self):
        return self.create_keyboard([])

    def check_stop_registration(self, message):
        if message.text == self.STOP_REGISTRATION_BUTTON:
            self.stop_registration(message)
            return True
        return False

    def is_valid_type(self, message):
        return message.content_type == 'text'

    def is_valid_input(self, data, pattern):
        return bool(re.match(pattern, data))

    def is_valid_name(self, name):
        return self.is_valid_input(name, r"^[А-Яа-яЁё\s-]+$")

    def is_valid_phone(self, phone):
        return self.is_valid_input(phone, "^\\d+$")

    def start_registration(self, message):
        self.ITT_status = 0
        self.bot.send_message(message.from_user.id, 'Напишите, пожалуйста, полностью фамилию, имя и отчество пациента.', reply_markup=self.registration_keyboard())
        self.bot.register_next_step_handler(message, self.get_fio)

    def get_fio(self, message):
        self.user_id = message.from_user.id
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Ошибка: Отправьте текстовое сообщение")
            return self.bot.register_next_step_handler(message, self.get_fio)
        if self.check_stop_registration(message):
            return
        if not self.is_valid_name(message.text):
            self.bot.send_message(message.from_user.id, "Ошибка: Имя должно содержать только буквы. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_fio)
        self.fio = message.text
        self.bot.send_message(message.from_user.id, 'Напишите ваш номер телефона')
        self.bot.register_next_step_handler(message, self.get_phone)

    def get_phone(self, message):
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Ошибка: Отправьте текстовое сообщение")
            return self.bot.register_next_step_handler(message, self.get_phone)
        if self.check_stop_registration(message):
            return
        if not self.is_valid_phone(message.text):
            self.bot.send_message(message.from_user.id, "Ошибка: Номер телефона должен содержать только цифры. Повторите ввод.")
            return self.bot.register_next_step_handler(message, self.get_phone)
        self.phone = message.text
        self.bot.send_message(message.from_user.id, 'Выберите тип приема',
                              reply_markup=self.type_of_reception_keyboard())
        self.bot.register_next_step_handler(message, self.get_type_of_reception)

    def type_of_reception_keyboard(self):
        return self.create_keyboard(self.type_of_reception)

    def get_type_of_reception(self, message):
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Пожалуйста, выберите тип приема из списка.")
            return self.bot.register_next_step_handler(message, self.get_type_of_reception)
        if self.check_stop_registration(message):
            return
        if message.text not in self.type_of_reception:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберите тип приема из списка.')
            return self.bot.register_next_step_handler(message, self.get_type_of_reception)
        if message.text == 'OMC (при наличии направления)':
            photo_path = example_path
            self.bot.send_message(message.from_user.id,'Предоставьте, пожалуйста, фото своего направления. Выделенная зона должна четко просматриваться (как на примере)', reply_markup=self.registration_keyboard())
            self.bot_status = 'waiting'
            self.type_of_reception_selected = message.text
            with open(photo_path, "rb") as photo:
                self.bot.send_photo(message.chat.id, photo)
                self.bot.register_next_step_handler(message, self.get_photo)
        else:
            self.type_of_reception_selected = message.text
            self.bot.send_message(message.from_user.id, 'Выберите медицинский профиль', reply_markup=self.med_profile_keyboard())
            self.bot.register_next_step_handler(message, self.get_med_profile)

    def get_photo(self, message):
        if message.text == "🛑 Остановить регистрацию":
            self.stop_registration(message)
            return
        if message.content_type == 'photo':
            file_info = self.bot.get_file(message.photo[-1].file_id)
            file_data = self.bot.download_file(file_info.file_path)
            self.photo_path = 'user_photo.jpg'  # Измените имя файла при необходимости
            with open(self.photo_path, 'wb') as new_file:
                new_file.write(file_data)
            image = Image.open(io.BytesIO(file_data))
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Удаляем шум с помощью размытия
            denoised_photo = cv2.GaussianBlur(binary, (5, 5), 0)
            if ITT(img_array):
                self.ITT_status = 1
                self.bot_status = None
                self.bot.send_message(message.from_user.id, 'Фото успешно прошло проверку')
                self.bot.send_message(message.from_user.id, 'Выберите медицинский профиль', reply_markup=self.med_profile_keyboard())
                self.bot.register_next_step_handler(message, self.get_med_profile)
            else:
                self.bot.send_message(message.from_user.id, 'Направление не прошло проверку. Пожалуйста, сделайте фото под прямым углом или при лучшем освещении.',  reply_markup=self.registration_keyboard())
                return self.bot.register_next_step_handler(message, self.get_photo)
        else:
            self.bot.send_message(message.from_user.id,'Пожалуйста отправьте фото или нажмите кнопку остановить регистрацию для выхода', reply_markup=self.registration_keyboard())
            return self.bot.register_next_step_handler(message, self.get_photo)

    def med_profile_keyboard(self):
        return self.create_keyboard(self.med_profile)

    def get_med_profile(self, message):
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Пожалуйста, выберите профиль из списка.")
            return self.bot.register_next_step_handler(message, self.get_med_profile)
        if self.check_stop_registration(message):
            return
        if message.text not in self.med_profile:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберите профиль из списка.')
            return self.bot.register_next_step_handler(message, self.get_med_profile)
        self.med_profile_selected = message.text
        self.bot.send_message(message.from_user.id,'Напишите, пожалуйста, дополнительную информацию при необходимости. Если такой нет, проставьте 0.', reply_markup=self.registration_keyboard())
        self.bot.register_next_step_handler(message, self.add_information)

    def add_information(self, message):
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Пожалуйста, отправьте текстовое сообщение")
            return self.bot.register_next_step_handler(message, self.add_information)
        if self.check_stop_registration(message):
            return
        if message.text == "0":
            self.additional_information = "Не указано"
        else:
            self.additional_information = message.text
        info = (f"ФИО: {self.fio}\n"
                f"Телефон: {self.phone}\n"
                f"Медицинский профиль: {self.med_profile_selected}\n"
                f"Тип приема: {self.type_of_reception_selected}\n"
                f"Дополнительная информация: {self.additional_information}")
        self.bot.send_message(message.from_user.id, info)
        self.bot.send_message(message.from_user.id, 'Указанные вами данные верны?', reply_markup=self.last_answer_keyboard())
        self.bot.register_next_step_handler(message, self.get_type_last_answer)

    def last_answer_keyboard(self):
        return self.create_keyboard(self.last_answer)

    def get_type_last_answer(self, message):
        if not self.is_valid_type(message):
            self.bot.send_message(message.from_user.id, "Пожалуйста, выберите ответ из списка")
            return self.bot.register_next_step_handler(message, self.get_type_last_answer)
        if self.check_stop_registration(message):
            return
        if message.text not in self.last_answer:
            self.bot.send_message(message.from_user.id, 'Пожалуйста, выберите ответ из списка.')
            return self.bot.register_next_step_handler(message, self.get_type_last_answer)
        if message.text == 'Да':
            self.finale(message.chat.id)
        elif message.text == 'Нет':
            self.start_registration(message)

    def stop_registration(self, message):
        self.bot.send_message(message.chat.id, "Регистрация остановлена. Вы вернулись в меню.", reply_markup=self.menu_keyboard())

    def finale(self, chat_id):
        self.bot.send_message(chat_id, "Спасибо за заявку! Ожидайте звонка специалиста!", reply_markup=self.menu_keyboard())
        self.send_email(self.photo_path)
        print(user_registrations)

    def send_email(self, attachment_path):
        subject = "Новая запись на прием через телеграм"
        body = self.create_email_body()
        msg = self.prepare_email_message(subject, body, attachment_path)
        try:
            self.send_email_message(msg)
            self.cleanup_attachment(attachment_path)
        except Exception as e:
            logging.error(f"Ошибка при отправке письма: {e}")

    def create_email_body(self):
        return f"""
        <html>
            <body>
                <h2 style="font-size: 24px;">Новая запись на прием:</h2>
                <ul style="font-size: 18px;">
                    <li><strong>ФИО:</strong> {self.fio}</li>
                    <li><strong>Телефон:</strong> {self.phone}</li>
                    <li><strong>Медицинская специальность:</strong> {self.med_profile_selected}</li>
                    <li><strong>Тип приема:</strong> {self.type_of_reception_selected}</li>
                    <li><strong>Дополнительная информация:</strong> {self.additional_information}</li>
                    <li><strong>ID пациента:</strong> {self.user_id}</li>
                    <li><strong>Фото направления прикреплено:</strong> {'Да' if self.ITT_status == 1 else 'Нет'}</li>
                </ul>
            </body>
        </html>
        """

    def prepare_email_message(self, subject, body, attachment_path):
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = admin_email
        msg['To'] = admin_email
        msg.attach(MIMEText(body, 'html'))

        if os.path.isfile(attachment_path):
            try:
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition',
                                    f'attachment; filename="{os.path.basename(attachment_path)}"')
                    msg.attach(part)
            except Exception as e:
                logging.error(f'Ошибка при добавлении вложения: {e}')
        else:
            logging.warning(f'Файл "{attachment_path}" не найден, вложение не добавлено.')

        return msg

    def send_email_message(self, msg):
        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(admin_email, email_password)
            server.send_message(msg)
        logging.info("Письмо отправлено успешно.")

    def cleanup_attachment(self, attachment_path):
        try:
            if os.path.isfile(attachment_path):
                os.remove(attachment_path)
                logging.info(f"{attachment_path} успешно удален.")
            else:
                logging.warning(f"{attachment_path} не найден для удаления.")
        except Exception as e:
            logging.error(f"Ошибка при удалении файла {attachment_path}: {e}")