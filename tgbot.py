import logging
from aiogram import F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import StateFilter, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config import link2, reseption_answer, med_price_info, add_price_message, med_profile


logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
router = Router()


# Определение состояний
class RegistrationStatesMain(StatesGroup):
    waiting_for_price_profile = State()  # Ожидание выбора профиля

# Клавиатуры
def submenu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Записаться на прием врача')], [KeyboardButton(text = 'Как записаться на прием к специалисту?')],
    [KeyboardButton(text='Платные услуги'), KeyboardButton(text = 'Специалисты ')], [KeyboardButton(text='Раздел мониторинга СД')], [KeyboardButton(text='Отменить запись к врачу')]])
    return keyboard


def med_profile_keyboard(buttons=None):
    if buttons is None:
        buttons = []
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='⬅️ Вернуться в меню платных услуг'))
    for button in buttons:
        if isinstance(button, str):  # Проверяем, что элемент списка — строка
            keyboard.add(KeyboardButton(text=button))
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def price_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Стоимость консультативного приема')], [KeyboardButton(text = 'Как проходит оплата?')],
    [KeyboardButton(text='⬅️ Назад в меню')]])
    return keyboard

@router.message(CommandStart())
async def send_welcome(message: Message):
    photo = FSInputFile('/home/sou-3.2-2/chatbot/vokb_logotip2.png')
    # Создаём InputFile, передавая файл
    await message.answer_photo(photo, caption="🌟 Добрый день! Вы обратились в контактно-информационный центр Волгоградской областной клинической больницы №1. Пожалуйста, выберите интересующий вас вопрос: 💬", reply_markup=submenu_keyboard())

@router.message(F.text == "Как записаться на прием к специалисту?")
async def send_info(message: Message):
    await message.answer(reseption_answer, reply_markup=submenu_keyboard())

@router.message(F.text == "Платные услуги")
async def paid_services(message: Message):
    await message.answer("Выберите, пожалуйста, интересующий Вас вопрос.", reply_markup=price_keyboard())

@router.message(F.text == "Стоимость консультативного приема")
async def send_price(message: Message, state: FSMContext):
    print("Кнопка нажата!")  # Отладочный вывод
    await message.answer("Выберите, пожалуйста, желаемый профиль.", reply_markup=med_profile_keyboard(med_profile))
    await state.set_state(RegistrationStatesMain.waiting_for_price_profile)

@router.message(StateFilter(RegistrationStatesMain.waiting_for_price_profile))
async def price_filter(message: Message, state: FSMContext):
    if message.content_type != 'text':
        await message.answer("Пожалуйста, отправьте текстовое сообщение с выбором профиля.", reply_markup=med_profile_keyboard(med_profile))
        return
    if message.text == '⬅️ Вернуться в меню платных услуг':
        await state.clear()  # Завершение состояния
        return await back_to_price(message)
    # Ожидание профиля
    profile = message.text
    if profile in med_price_info:
        price_message = '\n'.join(f"{procedure}: {price}₽" for procedure, price in med_price_info[profile].items())
        await message.answer(price_message + '(повторное обращение к одному и тому же специалисту в течение месяца)', reply_markup=med_profile_keyboard(med_profile))
    else:
        await message.answer("Нет информации по этому профилю.", reply_markup=med_profile_keyboard(med_profile))

# Обработчик для инструкций по оплате
@router.message(F.text == "Как проходит оплата?")
async def payment_instruct(message: Message):
    await message.answer(add_price_message, reply_markup=price_keyboard())

@router.message(F.text == "Специалисты")
async def specialist(message: Message):
    await message.answer('Подробная информация о каждом специалисте представлена на официальном сайте ГБУЗ «ВОКБ №1»: ' + link2, reply_markup=submenu_keyboard())

@router.message(F.text == "⬅️ Назад в меню")
async def one_step_back(message: Message):
    await message.answer('Вы вернулись в меню', reply_markup=submenu_keyboard())

@router.message(F.text == "⬅️ Вернуться в меню платных услуг")
async def back_to_price(message: Message):
    await message.answer('Вы вернулись в меню платных услуг', reply_markup=price_keyboard())

@router.message()
async def handle_random_messages(message: Message):
    await message.answer("Пожалуйста, используйте кнопки для навигации.", reply_markup=submenu_keyboard())