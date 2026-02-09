import os
import time
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

if not os.getenv("BOT_TOKEN"):
    logging.error("BOT_TOKEN не установлен! Добавьте его в Variables на Railway")
    exit(1)

scheduler = AsyncIOScheduler()

class ReminderStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_message = State()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_full_name = message.from_user.full_name
    
    logging.info(f"user_id={user_id} user_full_name={user_full_name} time={time.asctime()}")
    
    await message.reply(
        f"Привет, {user_full_name}!\n\n"
        f"⏰ В какое время напоминать тебе?\n"
        f"Напиши время в формате ЧЧ:ММ (например, 19:30)"
    )
    
    await state.set_state(ReminderStates.waiting_for_time)
    await state.update_data(user_full_name=user_full_name)


@dp.message(ReminderStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    time_text = message.text.strip()
    
    try:
        hour, minute = map(int, time_text.split(':'))
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        await state.update_data(reminder_hour=hour, reminder_minute=minute)
        await state.set_state(ReminderStates.waiting_for_message)
        
        await message.reply(
            f"⏰ Отлично! Время установлено на {hour:02d}:{minute:02d}.\n\n"
            f"✏️ Какой текст напоминания ты хочешь получать?\n"
            f"Напиши любой текст (например: «Займись ботом!»)"
        )
    
    except (ValueError, AttributeError):
        await message.reply(
            "❌ Неправильный формат времени.\n"
            "Пожалуйста, напиши время в формате ЧЧ:ММ (например, 19:30)"
        )


@dp.message(ReminderStates.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    reminder_text = message.text.strip()
    
    data = await state.get_data()
    hour = data.get('reminder_hour')
    minute = data.get('reminder_minute')
    user_full_name = data.get('user_full_name', 'друг')
    
    scheduler.add_job(
        bot.send_message,
        "cron",
        hour=hour,
        minute=minute,
        args=[user_id, reminder_text]
    )
    
    await message.reply(
        f"✅ Готово! Напоминание установлено:\n\n"
        f"⏰ Время: {hour:02d}:{minute:02d} каждый день\n"
        f"📝 Текст: «{reminder_text}»"
    )
    
    await state.clear()
    logging.info(f"Напоминание для {user_full_name} установлено на {hour:02d}:{minute:02d} с текстом: {reminder_text}")


async def main():
    scheduler.start()
    logging.info("Бот запущен")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
