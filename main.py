import aiogram
import asyncio
from aiogram import Bot, Dispatcher
import logging
from database import setup_database
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
from handlers.commands import router


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    setup_database() #создание БД
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot stopped')
