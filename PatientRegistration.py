import re
import logging
import numpy as np
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, Message, FSInputFile
from PIL import Image
import cv2
from config import admin_email, email_password, example_path
from tgbot import submenu_keyboard
from TextRecognition import image_to_text as ITT
from SendMail import send_email


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
# user_photo_path = '/home/sou-3.2-2/chatbot/user_photo.jpg'

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
            user_photo_path = f'user_photo{user_id}.jpg'
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
    await state.update_data(additional_info= message.text if message.text != "0" else "Не указано")
    user_data = await state.get_data()
    info = (f"ФИО: {user_data['fio']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"Медицинский профиль: {user_data['med_profile_selected']}\n"
            f"Тип приема: {user_data['type_of_reception_selected']}\n"
            f"Дополнительная информация: {user_data['additional_info']}")
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

async def finale(chat_id, message: types.Message, state: FSMContext):
    await message.answer("Спасибо за заявку! Ожидайте звонка специалиста!", reply_markup=submenu_keyboard())
    user_data = await state.get_data()  # Получаем данные пользователя из состояния
    fio = user_data.get('fio')
    phone = user_data.get('phone')
    med_profile_selected = user_data.get('med_profile_selected')
    type_of_reception_selected = user_data.get('type_of_reception_selected')
    additional_info = user_data.get('additional_info')
    user_id = message.from_user.id
    user_photo_path = f'user_photo{user_id}.jpg'
    await send_email(admin_email, email_password, fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, user_photo_path)


async def stop_registration(message: types.Message, state: FSMContext):
    await message.answer("Регистрация остановлена. Вы вернулись в меню.", reply_markup=submenu_keyboard())
    await state.clear()

