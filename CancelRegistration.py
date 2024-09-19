import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton
from config import admin_email, email_password
from tgbot import submenu_keyboard


logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
router2 = Router()


class CancelRegistrationStates(StatesGroup):
    waiting_for_fio = State()
    waiting_for_med_profile = State()
    waiting_for_additional_info = State()
    waiting_for_confirmation = State()

STOP_REGISTRATION_BUTTON = '🛑 Остановить процесс'

med_profile_options = [
    'Акушер-Гинеколог', 'Гастроэнтеролог', 'Гематолог',
    'Дерматовенеролог', 'Кардиолог', 'Невролог',
    'Нейрохирург', 'Оториноларинголог', 'Офтальмолог',
    'Пульмонолог', 'Сердечно-сосудистый хирург',
    'Торакальный хирург', 'Травматолог', 'Уролог',
    'Хирург', 'Челюстно-лицевой хирург', 'Эндокринолог'
]
last_answer_options = ['Да', 'Нет']

def create_keyboard(buttons):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text=STOP_REGISTRATION_BUTTON))
    for button in buttons:
        keyboard.add(KeyboardButton(text=button))
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def is_valid_type(message):
    return message.content_type == 'text'


@router2.message(F.text == 'Отменить запись к врачу')
async def cancel_registration(message: types.Message, state: FSMContext):
    """Начинает процесс отмены регистрации."""
    await message.answer('Для отмены регистрации, пожалуйста, напишите полностью фамилию, имя, отчество и дату рождения.', reply_markup=create_keyboard([]))
    await state.set_state(CancelRegistrationStates.waiting_for_fio)

@router2.message(CancelRegistrationStates.waiting_for_fio)
async def get_fio(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        await stop_registration(message, state)
        return
    if not is_valid_type(message):
        await message.answer("Ошибка: сообщение должно быть текстовым, повторите ввод.")
        return
    await state.update_data(fio=message.text)  # Сохраняем ФИО
    await message.answer('Выберите профиль врача из списка.', reply_markup=create_keyboard(med_profile_options))
    await state.set_state(CancelRegistrationStates.waiting_for_med_profile)

@router2.message(CancelRegistrationStates.waiting_for_med_profile)
async def get_med_profile(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        await stop_registration(message, state)
        return
    if message.text not in med_profile_options or not is_valid_type(message):
        await message.answer('Пожалуйста, выберите профиль из списка.')
        return
    await state.update_data(med_profile_selected=message.text)  # Сохраняем профиль
    await message.answer('Напишите, пожалуйста, дополнительную информацию при необходимости. Если такой нет, проставьте 0.', reply_markup=create_keyboard([]))
    await state.set_state(CancelRegistrationStates.waiting_for_additional_info)

@router2.message(CancelRegistrationStates.waiting_for_additional_info)
async def add_information(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        await stop_registration(message, state)
        return
    if not is_valid_type(message):
        await message.answer("Ошибка: сообщение должно быть текстовым, повторите ввод.")
        return
    await state.update_data(additional_info=message.text if message.text != "0" else "Не указано")  # Сохраняем дополнительную информацию
    await message.answer('Вы подтверждаете отмену записи?', reply_markup=create_keyboard(last_answer_options))
    await state.set_state(CancelRegistrationStates.waiting_for_confirmation)

@router2.message(CancelRegistrationStates.waiting_for_confirmation)
async def get_confirmation(message: types.Message, state: FSMContext):
    if message.text == STOP_REGISTRATION_BUTTON:
        await stop_registration(message, state)
        return
    if message.text not in last_answer_options or not is_valid_type(message):
        await message.answer('Пожалуйста, выберите ответ из списка.')
        return
    if message.text == 'Да':
        await finalize_cancellation(message.chat.id, message, state)
    else:
        await message.answer('Операция отменена, вы вернулись в меню.', reply_markup=submenu_keyboard())
        await state.clear()

async def finalize_cancellation(user_id, message: types.Message, state: FSMContext):
    await message.answer('Спасибо за заявку, Ваша запись будет отменена.', reply_markup=submenu_keyboard())
    user_data = await state.get_data()  # Получаем данные пользователя из состояния
    fio = user_data.get('fio')
    med_profile_selected = user_data.get('med_profile_selected')
    additional_info = user_data.get('additional_info')
    await send_email(fio, med_profile_selected, additional_info, user_id)
    await state.clear()  # очищаем состояние после обработки


async def stop_registration(message: types.Message, state: FSMContext):
    await message.answer("Процесс отмены записи остановлен. Вы вернулись в меню.", reply_markup=submenu_keyboard())
    await state.clear()

async def send_email(fio, med_profile_selected, additional_info, user_id):
    """Отправляет уведомление об отмене записи на почту администратора."""
    subject = "Отмена записи на прием врача через телеграм"
    body = await create_email_body(fio, med_profile_selected, additional_info, user_id)
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

async def create_email_body(fio, med_profile_selected, additional_info, user_id):
    """Создает HTML-содержимое письма."""
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
            <h2>Новая заявка на отмену записи на прием врача:</h2>
            <ul>
                <li><strong>ФИО и дата рождения:</strong> {fio}</li>
                <li><strong>Медицинская специальность:</strong> {med_profile_selected}</li>
                <li><strong>Дополнительная информация:</strong> {additional_info}</li>
                <li><strong>ID пациента:</strong> {user_id}</li>
            </ul>
            <div class="divider"></div>
            <p>Спасибо за использование нашего сервиса!</p>
        </body>
    </html>
    """