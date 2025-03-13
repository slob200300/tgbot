import re
import io
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, FSInputFile
from PIL import Image
import numpy as np
import cv2
from config import admin_email, email_password, example_path
from tgbot import submenu_keyboard
from TextRecognition import image_to_text as ITT


logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
router1 = Router()


# Состояния для регистрации пациента
class RegistrationStates(StatesGroup):
    waiting_for_fio = State()
    waiting_for_phone = State()
    waiting_for_type_of_reception = State()
    waiting_for_photo = State()
    waiting_for_med_profile = State()
    waiting_for_additional_info = State()
    waiting_for_confirmation = State()


STOP_REGISTRATION_BUTTON = '🛑 Остановить регистрацию'


med_profile_options = [
    'Акушер-Гинеколог', 'Гастроэнтеролог', 'Гематолог',
    'Дерматовенеролог', 'Кардиолог', 'Невролог',
    'Нейрохирург', 'Оториноларинголог', 'Офтальмолог',
    'Пульмонолог', 'Сердечно-сосудистый хирург', 
    'Торакальный хирург', 'Травматолог', 'Уролог', 
    'Хирург', 'Челюстно-лицевой хирург', 'Эндокринолог'
]
type_of_reception_options = ['OMC (при наличии направления)', 'За счет личных средств', 'ДМС / Договор с организацией']
last_answer_options = ['Да', 'Нет']
user_photo_path = ''



def create_keyboard(buttons):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text=STOP_REGISTRATION_BUTTON))
    for button in buttons:
        keyboard.add(KeyboardButton(text=button))
    return keyboard.adjust(1).as_markup(resize_keyboard=True)


def is_valid_type(message):
    return message.content_type == 'text'

def is_valid_name(name):
    return bool(re.match(r"^[А-Яа-яЁё\s-]+$", name))

# Функция для проверки телефона
def is_valid_phone(phone):
    return bool(re.match(r"^\d+$", phone))


@router1.message(F.text == "Записаться на прием врача")
async def reception(message: Message, state: FSMContext):
    await message.answer("Начало регистрации")
    await state.set_state(RegistrationStates.waiting_for_fio)
    await message.answer('Напишите, пожалуйста, полностью фамилию, имя и отчество пациента.', reply_markup=create_keyboard([]))
    

@router1.message(RegistrationStates.waiting_for_fio)
async def get_fio(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if not is_valid_type(message) or not is_valid_name(message.text):
        await message.answer('Ошибка: ФИО должно состоять только из букв')
        return
    await state.update_data(fio=message.text)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer('Напишите, пожалуйста, Ваш номер телефона.')


@router1.message(RegistrationStates.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if not is_valid_type(message) or not is_valid_phone(message.text):
        await message.answer('Ошибка: Номер должен состоять только из цифр')
        return
    await state.update_data(phone=message.text)
    await message.answer('Выберите тип приема', reply_markup=create_keyboard(type_of_reception_options))
    await state.set_state(RegistrationStates.waiting_for_type_of_reception)


@router1.message(RegistrationStates.waiting_for_type_of_reception)
async def get_type_of_reception(message: types.Message, state: FSMContext): 
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if message.text not in type_of_reception_options or not is_valid_type(message):
        await message.answer('Пожалуйста, выберите тип приема из списка.')
        return
    await state.update_data(type_of_reception_selected=message.text)
    if message.text == 'OMC (при наличии направления)':
        await message.answer('Предоставьте, пожалуйста, фото своего направления. Выделенная зона должна четко просматриваться (как на примере)', reply_markup=create_keyboard([]))
        photo = FSInputFile(example_path)
        # Создаём InputFile, передавая файл
        await message.answer_photo(photo)
        await state.set_state(RegistrationStates.waiting_for_photo)
    else:
        await message.answer('Выберите медицинский профиль', reply_markup=create_keyboard(med_profile_options))
        await state.set_state(RegistrationStates.waiting_for_med_profile)


@router1.message(RegistrationStates.waiting_for_photo)
async def get_photo(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if message.content_type == 'photo':
        global user_photo_path
        from runner import bot
        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        # Загружаем файл в BytesIO
        file_data = await bot.download_file(file_path, destination = None)
        if file_data is not None:
            file_data.seek(0)  # Перемещаем указатель в начало
            image = Image.open(file_data)
            # Преобразуем изображение в массив NumPy
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised_photo = cv2.GaussianBlur(binary, (5, 5), 0)
        else:
            await message.answer('Не удалось загрузить изображение, повторите попытку', reply_markup=create_keyboard(med_profile_options))
            await state.set_state(RegistrationStates.waiting_for_photo)
        if ITT(img_array):
            await message.answer('Фото успешно загружено. Выберите медицинский профиль.', reply_markup=create_keyboard(med_profile_options))
            await state.set_state(RegistrationStates.waiting_for_med_profile)
            user_id = message.from_user.id
            user_photo_path = f'/home/sou-3.2-2/chatbot/user_photo_{user_id}.jpg'
            await bot.download_file(file_path, user_photo_path)
        else:
            await message.answer('Направление не прошло проверку. Пожалуйста, сделайте фото под прямым углом или при лучшем освещении.')
            await state.set_state(RegistrationStates.waiting_for_photo)
    else:
        await message.answer('Пожалуйста, отправьте фото или нажмите кнопку остановить регистрацию для выхода.', reply_markup=create_keyboard([]))
        await state.set_state(RegistrationStates.waiting_for_photo)


@router1.message(RegistrationStates.waiting_for_med_profile)
async def get_med_profile(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if message.text not in med_profile_options or not is_valid_type(message):
        await message.answer('Пожалуйста, выберите медицинский профиль из списка.')
        return
    await state.update_data(med_profile_selected=message.text)
    await message.answer('Напишите, пожалуйста, дополнительную информацию при необходимости. Если такой нет, проставьте 0.', reply_markup=create_keyboard([]))
    await state.set_state(RegistrationStates.waiting_for_additional_info)


@router1.message(RegistrationStates.waiting_for_additional_info)
async def add_information(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if not is_valid_type(message):
        await message.answer('Ошибка: сообщение должно быть текстовым. Повторите ввод.')
        return
    additional_info = message.text if message.text != "0" else "Не указано"
    user_data = await state.get_data()
    info = (f"ФИО: {user_data['fio']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"Медицинский профиль: {user_data['med_profile_selected']}\n"
            f"Тип приема: {user_data['type_of_reception_selected']}\n"
            f"Дополнительная информация: {additional_info}")
    await message.answer(info)
    await message.answer('Указанные вами данные верны?', reply_markup=create_keyboard(last_answer_options))
    await state.set_state(RegistrationStates.waiting_for_confirmation)


@router1.message(RegistrationStates.waiting_for_confirmation)
async def get_type_last_answer(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        return await stop_registration(message, state)
    if not is_valid_type(message):
        await message.answer('Ошибка: сообщение должно быть текстовым. Повторите ввод.')
        return
    if message.text == 'Да':
        await finale(message.chat.id, message, state)
        await state.clear()
    elif message.text == 'Нет':
        await reception(message, state)

async def stop_registration(message: types.Message, state: FSMContext):
    await message.answer("Регистрация остановлена. Вы вернулись в меню.", reply_markup=submenu_keyboard())
    await state.clear()

async def finale(chat_id, message: types.Message, state: FSMContext):
    await message.answer("Спасибо за заявку! Ожидайте звонка специалиста!", reply_markup=submenu_keyboard())
    user_data = await state.get_data()  # Получаем данные пользователя из состояния
    global user_photo_path
    fio = user_data.get('fio', 'Не указано')
    phone = user_data.get('phone', 'Не указано')
    med_profile_selected = user_data.get('med_profile_selected', 'Не указано')
    type_of_reception_selected = user_data.get('type_of_reception_selected', 'Не указано')
    additional_info = user_data.get('additional_information', 'Не указано')
    user_id = message.from_user.id
    await send_email(admin_email, email_password, fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, user_photo_path)

async def send_email(admin_email, email_password, fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path):
    subject = "Новая запись на прием через телеграм"
    body = create_email_body(fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path)
    msg = prepare_email_message(subject, body, attachment_path, admin_email)
    try:
        send_email_message(msg, admin_email, email_password)
        cleanup_attachment(attachment_path)
    except Exception as e:
        logging.error(f"Ошибка при отправке письма: {e}")

def create_email_body(fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path):
    return f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                }}
                h2 {{
                    color: #4CAF50;
                    font-size: 24px;
                    margin-bottom: 10px;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                li {{
                    background: #f4f4f4;
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }}
                strong {{
                    color: #000;
                }}
                .divider {{
                    height: 1px;
                    background: #ddd;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <h2>Новая запись на прием:</h2>
            <ul>
                <li><strong>ФИО:</strong> {fio}</li>
                <li><strong>Телефон:</strong> {phone}</li>
                <li><strong>Медицинская специальность:</strong> {med_profile_selected}</li>
                <li><strong>Тип приема:</strong> {type_of_reception_selected}</li>
                <li><strong>Дополнительная информация:</strong> {additional_info}</li>
                <li><strong>ID пациента:</strong> {user_id}</li>
                <li><strong>Фото направления прикреплено:</strong> {'Да' if os.path.isfile(attachment_path) else 'Нет'}</li>
            </ul>
            <div class="divider"></div>
            <p>Спасибо за использование нашего сервиса!</p>
        </body>
    </html>
    """

def prepare_email_message(subject, body, attachment_path, admin_email):
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
                part.add_header('Content-Disposition',f'attachment; filename="{os.path.basename(attachment_path)}"')
                msg.attach(part)
        except Exception as e:
            logging.error(f'Ошибка при добавлении вложения: {e}')
    else:
        logging.warning(f'Файл "{attachment_path}" не найден, вложение не добавлено.')
    return msg

def send_email_message(msg, admin_email, email_password):
    with smtplib.SMTP('smtp.mail.ru', 587) as server:
        server.starttls()
        server.login(admin_email, email_password)
        server.send_message(msg)
    logging.info("Письмо отправлено успешно.")

def cleanup_attachment(attachment_path):
    try:
        if os.path.isfile(attachment_path):
            os.remove(attachment_path)
            logging.info(f"{attachment_path} успешно удален.")
        else:
            logging.warning(f"{attachment_path} не найден для удаления.")
    except Exception as e:
        logging.error(f"Ошибка при удалении файла {attachment_path}: {e}")