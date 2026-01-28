import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import BOT_TOKEN, MANAGER_CHAT_ID, GOOGLE_SHEET_NAME, CREDENTIALS_FILE

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- Google Sheets ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1


class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()


@dp.message_handler(commands="start")
async def start(message: types.Message):
    await message.answer("Здравствуйте! Как вас зовут?")
    await Form.name.set()


@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    if not message.text.strip():
        await message.answer("Пожалуйста, введите имя.")
        return

    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона:")
    await Form.phone.set()


@dp.message_handler(state=Form.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not message.text.strip():
        await message.answer("Введите корректный номер телефона.")
        return

    await state.update_data(phone=message.text)
    await message.answer("Введите комментарий:")
    await Form.comment.set()


@dp.message_handler(state=Form.comment)
async def get_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()

    name = data["name"]
    phone = data["phone"]
    comment = message.text

    # Сохраняем в таблицу
    sheet.append_row([name, phone, comment])

    # Отправляем менеджеру
    await bot.send_message(
        MANAGER_CHAT_ID,
        f"📩 Новая заявка\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Комментарий: {comment}"
    )

    await message.answer("Спасибо! Мы свяжемся с вами в ближайшее время.")
    await state.finish()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
