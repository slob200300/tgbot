import logging
import re
from aiogram import types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, FSInputFile
from tgbot import submenu_keyboard, main_menu_keyboard
from sqlalchemy import select, desc
from DataBase import User, Access, get_session, get_user_data, add_multiple_records, update_multiple_records
from datetime import date



# Инициализация логирования и состояния
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
router1 = Router()

class DiseaseMonitoringStates(StatesGroup):
    waiting_for_type_of_diabetes = State()
    waiting_for_choose_time = State()
    waiting_for_continuation = State()
    action_type = State()

class TimeIndicatorsStates(StatesGroup):
    waiting_for_blood_sugar = State()
    waiting_for_insulin_units = State()


continuation = ['Продолжить']
sugar_type = ['Инсулинозависимый СД', 'ИнсулиноНЕзависимый СД']
period = ['Завтрак', 'Обед', 'Ужин']

STOP_MONITORING_BUTTON = '🛑 Остановить мониторинг'

def is_valid_insulin(insulin):
    return bool(re.match(r"^[1-9]\d*$", insulin))

def is_valid_glucose(glucose):
    return bool(re.match(r"^(?!0)\d+(\.\d+)?$", glucose))

def create_keyboard(buttons):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text=STOP_MONITORING_BUTTON))
    for button in buttons:
        keyboard.add(KeyboardButton(text=button))
    return keyboard.adjust(1).as_markup(resize_keyboard=True)

def sugar_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Внести данные глюкозы крови')], [KeyboardButton(text = 'Посмотреть внесенные показатели глюкозы крови')],
    [KeyboardButton(text='⬅️ Выйти из раздела мониторинга сахара')]])
    return keyboard

def show_data_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Редактировать')],
    [KeyboardButton(text='⬅️ Выйти из просмотра данных')]])
    return keyboard


@router1.message(F.text == "Раздел мониторинга СД")
async def start_monitoring(message: types.Message):
    this_user_id = message.chat.id
    if await check_legality(message):
        await message.answer('Доступ разрешен, Выберите нужный пункт:', reply_markup=sugar_menu_keyboard())


@router1.message(F.text == "Внести данные глюкозы крови")
async def input_sugar_data(message: types.Message, state : FSMContext):
    if message.content_type != 'text':
        await message.answer('Сообщение должно быть текстовым!')
        return
    if not await full_data_check(message):
        if await check_legality(message):
            if not await check_type_of_deabetes(message):
                await message.answer('Выберите тип СД', reply_markup = create_keyboard(sugar_type))
                await state.update_data(action_status = "in_process")
                await state.set_state(DiseaseMonitoringStates.waiting_for_type_of_diabetes)
            else:
                await message.answer('Пожалуйста, выберите период, за который хотите внести данные:', reply_markup=create_keyboard(period))
                await state.set_state(DiseaseMonitoringStates.waiting_for_choose_time)
    else:
        await message.answer('Вы уже введи все необходимые данные! Просмотреть их и отредактировать вы можете в разделе "Посмотреть внесенные показатели глюкозы крови"', reply_markup=sugar_menu_keyboard())


@router1.message(DiseaseMonitoringStates.waiting_for_type_of_diabetes)
async def get_diabetes_type(message: types.Message, state: FSMContext):
    if message.text == STOP_MONITORING_BUTTON:
        return await stop_monitoring(message, state)
    if message.text not in sugar_type:
        await message.answer('Пожалуйста, выберите тип диабета из списка')
        return
    await state.update_data(type_of_diabetes=message.text)
    data = await state.get_data()
    this_type_of_diabetes = data.get('type_of_diabetes')
    this_user_id = message.chat.id
    async with get_session() as session:
        # Получаем или создаем запись пользователя
        user_record = await session.execute(select(User).where(User.user_id == this_user_id, User.record_date == date.today()))
        user_data = user_record.scalar()
        # Если запись не найдена, создаем новую
        if user_data is None:
            user_data = User(user_id=this_user_id, record_date = date.today(), type_of_diabetes = this_type_of_diabetes)
            session.add(user_data)  # Добавляем новую запись
        else:
            user_data.type_of_diabetes = this_type_of_diabetes
        await session.commit()
    await message.answer('Пожалуйста, выберите период, за который хотите внести данные:', reply_markup=create_keyboard(period))
    await state.set_state(DiseaseMonitoringStates.waiting_for_choose_time)


@router1.message(DiseaseMonitoringStates.waiting_for_choose_time)
async def get_period(message: types.Message, state: FSMContext):
    if message.text == STOP_MONITORING_BUTTON:
        return await stop_monitoring(message, state)
    if message.text not in period:
        await message.answer('Пожалуйста, выберите период дня из списка')
        return
    await state.update_data(selected_period=message.text)
    await message.answer("Введите значение глюкозы крови:", reply_markup=create_keyboard([]))
    await state.set_state(TimeIndicatorsStates.waiting_for_blood_sugar)


@router1.message(TimeIndicatorsStates.waiting_for_blood_sugar)
async def get_blood_sugar_value(message: types.Message, state: FSMContext):
    if message.text == STOP_MONITORING_BUTTON:
        return await stop_monitoring(message, state)

    if message.content_type != 'text' or not is_valid_glucose(message.text):
        await message.answer('Показания сахара не могут быть ровны нулю и должны состоять только из цифр и точки, пример : 4.3 , 3 . Повторите ввод:')
        return

    blood_sugar_value = message.text  # Сохраняем значение сахара
    await state.update_data(blood_sugar = blood_sugar_value)
    data = await state.get_data()
    selected_period = data['selected_period']
    this_blood_sugar = float(blood_sugar_value)
    if this_blood_sugar > 15:
        await message.answer('☠Ваш уровень сахара превышает норму, рекомендуем вызвать скорую!☠')
    elif this_blood_sugar < 4:
        await message.answer('☠Ваш уровень сахара находится ниже нормы, рекомендуем вызвать скорую!☠')
    else:
        await message.answer('Ваш уровень сахара в норме.')

    await message.answer(f"Уровень глюкозы крови {selected_period}: {blood_sugar_value} ммоль/л. Сколько единиц инсулина вы ввели?", reply_markup=create_keyboard([]))
    await state.set_state(TimeIndicatorsStates.waiting_for_insulin_units)


@router1.message(TimeIndicatorsStates.waiting_for_insulin_units)
async def get_insulin_units(message: types.Message, state: FSMContext):
    if message.text == STOP_MONITORING_BUTTON:
        return await stop_monitoring(message, state)

    if message.content_type != 'text' or not is_valid_insulin(message.text):
        await message.answer('Показания инсулина не могут быть ровны нулю и должны состоять только из цифр, повторите ввод:')
        return

    this_insulin_units_value = message.text  # Сохраняем значение инсулина
    await state.update_data(insulin_units = this_insulin_units_value)
    data = await state.get_data()
    selected_period = data['selected_period']
    this_blood_sugar = data['blood_sugar']
    this_user_id = message.chat.id

#############################################
    async with get_session() as session:
        # Получаем или создаем запись пользователя
        result = await session.execute(
        select(User.type_of_diabetes)
        .where(User.user_id == this_user_id)
        .order_by(desc(User.record_date))  # Сортируем по дате в порядке убывания
        .limit(1)  # Ограничиваем результат одной записью
        )
        this_type_of_diabetes = result.scalar()  
        user_record = await session.execute(select(User).where(User.user_id == this_user_id, User.record_date == date.today()))
        user_data = user_record.scalar()
        # Если запись не найдена, создаем новую
        if user_data is None:
            user_data = User(user_id=this_user_id, record_date = date.today())
            session.add(user_data)  # Добавляем новую запись
        else:
        # Обновляем значения, в зависимости от выбранного периода
            if selected_period == 'Завтрак':
                user_data.breakfast_glucose = this_blood_sugar
                user_data.breakfast_insulin = this_insulin_units_value
            elif selected_period == 'Обед':
                user_data.lunch_glucose = this_blood_sugar
                user_data.lunch_insulin = this_insulin_units_value
            else:  # Ужин
                user_data.dinner_glucose = this_blood_sugar
                user_data.dinner_insulin = this_insulin_units_value
        # Сохраняем изменения в базе данных
        await session.commit()
##################################################################
    await message.answer(f"Записано: \nТип сахарного диабета: {this_type_of_diabetes}\nПериод: {selected_period}\nСахар: {this_blood_sugar} ммоль/л\nИнсулин: {this_insulin_units_value} ЕД.")

    action_status = data.get('action_status')
    print(action_status)
    if action_status == "done":
        await message.answer('Данные успешно обновлены! Хотите продолжить редактировать данные за другой период или остановить процесс мониторинга?', reply_markup=create_keyboard(continuation))
        await state.set_state(DiseaseMonitoringStates.waiting_for_continuation)
    else:
        if await full_data_check(message):
            await message.answer(f"Вы успешно заполнили все данные! 🎉\n"
            f"Данные автоматически отправятся на почту доктору в 20:00.", reply_markup=sugar_menu_keyboard())
            await state.clear()
            await state.update_data(action_status = "done")
        else:
            await message.answer('Хотите продолжить вносить данные за другой период или остановить процесс мониторинга до следующего приема пищи?', reply_markup=create_keyboard(continuation))
            await state.set_state(DiseaseMonitoringStates.waiting_for_continuation)


@router1.message(DiseaseMonitoringStates.waiting_for_continuation)
async def get_continuation(message: types.Message, state: FSMContext):
    if message.text == STOP_MONITORING_BUTTON:
        return await stop_monitoring(message, state)
    if message.content_type != 'text':
        await message.answer('Сообщение должно быть текстовым, повторите ввод:')
        return
    if message.text == 'Продолжить':
        await message.answer('Пожалуйста, выберите период, за который хотите внести данные:', reply_markup=create_keyboard(period))
        await state.set_state(DiseaseMonitoringStates.waiting_for_choose_time)
    else:
        await message.answer("Пожалуйста, выберите 'Продолжить' или остановите процесс.")


async def stop_monitoring(message: types.Message, state: FSMContext):
    await message.answer("Мониторинг остановлен. Вы вернулись в меню.", reply_markup=sugar_menu_keyboard())
    data = await state.get_data()
    currently_action_status=data.get('action_status')
    await state.clear()
    await state.update_data(action_status = currently_action_status)


async def check_legality(message: types.Message):
    this_user_id = message.chat.id
    async with get_session() as session:
        result = await session.execute(select(Access).where(Access.user_id == this_user_id))
        user_exists = result.scalar()   # Проверяем, есть ли пользователь в базе
    if user_exists:
        return True
    else:
        await message.answer("Доступ запрещен", reply_markup=main_menu_keyboard())
        return False

    
async def check_type_of_deabetes(message: types.Message):
    this_user_id = message.chat.id
    async with get_session() as session:
        result = await session.execute(select(User.type_of_diabetes).where(User.user_id == this_user_id, User.record_date == date.today()))
        type_of_diabetes_passed = result.scalar()   # Проверяем, есть ли пользователь в базе
        if type_of_diabetes_passed:
            return True
        else:
            return False


async def check_user_data(message: types.Message, check_empty: bool = False) -> bool:
    async with get_session() as session:
        # Получаем или создаем запись пользователя
        this_user_id = message.chat.id
        user_data = await get_user_data(this_user_id, date.today())
        if user_data is None:
            return False 
        fields_to_check = [
        user_data['breakfast_glucose'],
        user_data['breakfast_insulin'],
        user_data['lunch_glucose'],
        user_data['lunch_insulin'],
        user_data['dinner_glucose'],
        user_data['dinner_insulin']
        ]
        if check_empty:
            return all(field is None or field == 0 for field in fields_to_check)
        else:
            return all(field is not None and field > 0 for field in fields_to_check)


async def full_data_check(message: types.Message) -> bool:
    return await check_user_data(message, check_empty=False) 


async def empty_data_check(message: types.Message) -> bool:
    async with get_session() as session:
        this_user_id = message.chat.id
        user_data = await get_user_data(this_user_id, date.today())
        if user_data is None:
            return True
        else:
            return await check_user_data(message, check_empty=True)
    

@router1.message(F.text == "Посмотреть внесенные показатели глюкозы крови")
async def show_data(message: Message, state: FSMContext):
    if await check_legality(message):
        user_id = message.chat.id
        user_data = await get_user_data(user_id, date.today())
        if user_data and (
            user_data['breakfast_glucose'] or user_data['breakfast_insulin'] or 
            user_data['lunch_glucose'] or user_data['lunch_insulin'] or 
            user_data['dinner_glucose'] or user_data['dinner_insulin']
            ):
            response = (
                f"Ваш идентификатор: {user_data['user_id']}\n"
                f"Ваш тип СД: {user_data['type_of_diabetes']}\n"
                f"Показатели глюкозы крови за утренний период: {user_data.get('breakfast_glucose', 0) or 0}\n"
                f"Показатели введенного инсулина за утренний период: {user_data.get('breakfast_insulin', 0) or 0}\n"
                f"Показатели глюкозы крови за обеденный период: {user_data.get('lunch_glucose', 0) or 0}\n"
                f"Показатели введенного инсулина за обеденный период: {user_data.get('lunch_insulin', 0) or 0}\n"
                f"Показатели глюкозы крови за вечерний период: {user_data.get('dinner_glucose', 0) or 0}\n"
                f"Показатели введенного инсулина за вечерний период: {user_data.get('dinner_insulin', 0) or 0}\n"
                f"Дата: {user_data['record_date']}"
            )
        else:
            response = "Произошла ошибка или вы еще не вносили никаких показаний"
        await message.answer(response, reply_markup=show_data_keyboard())


@router1.message(F.text == "Редактировать")
async def edit_sugar(message: Message, state: FSMContext):
    if await check_legality(message):
        if await empty_data_check(message):  # Проверяем, пустые ли данные
            await message.answer('Отсутствуют данные для редактирования или пользователь не существует', reply_markup=show_data_keyboard())
        else:
            await message.answer('Пожалуйста, выберите период, за который хотите внести данные:', reply_markup=create_keyboard(period))
            await state.set_state(DiseaseMonitoringStates.waiting_for_choose_time)

@router1.message(F.text == "⬅️ Выйти из просмотра данных")
async def back_to_sugar(message: Message, state: FSMContext):
    if await check_legality(message):
        await message.answer("Вы вырнулись в меню. Выберите действие:", reply_markup=sugar_menu_keyboard())


@router1.message(F.text == "⬅️ Выйти из раздела мониторинга сахара")
async def exit_to_sugar(message: Message):
    await message.answer("Вы вырнулись в меню. Выберите действие:", reply_markup=main_menu_keyboard())

    


    