import logging
import asyncio
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from apscheduler.triggers.cron import CronTrigger
from aiogram.fsm.storage.memory import MemoryStorage
from config import token
from tgbot import router
from PatientRegistration import router1
from CancelRegistration import router2
from DataBase import test_connection
from reminder import send_reminder, send_main_email


logging.basicConfig(level=logging.INFO)
bot = Bot(token=token)
scheduler =  AsyncIOScheduler() 
pool = None


async def main_runner():
    # Инициализация бота
    global bot
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router2)
    dp.include_router(router1)
    dp.include_router(router)
    reminder_trigger = CronTrigger(hour=12, minute=30)
    scheduler.add_job(send_reminder,reminder_trigger)
    email_trigger = CronTrigger(hour=12, minute=30) 
    scheduler.add_job(send_main_email, email_trigger) 
    scheduler.start()
    await test_connection()  # Проверяем подключение
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main_runner())
    except KeyboardInterrupt:
        print('Exit')

