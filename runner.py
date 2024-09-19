import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import token
from tgbot import router
from PatientRegistration import router1
from CancelRegistration import router2


logging.basicConfig(level=logging.INFO)
bot = Bot(token=token)


async def main_runner():
    # Инициализация бота
    global bot
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router2)
    dp.include_router(router1)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main_runner())
    except KeyboardInterrupt:
        print('Exit')

