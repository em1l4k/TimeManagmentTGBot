from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Меню выбора типа задачи
task_type_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Задача')],
        [KeyboardButton(text='Действие')],
        [KeyboardButton(text='Прерывание')],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите тип задачи"
)

main_type_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Задача')],
        [KeyboardButton(text='Действие')],
        [KeyboardButton(text='Прерывание')],
        [KeyboardButton(text='📋 Открыть основное меню')]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите тип задачи"
)

classic_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Список задач'),KeyboardButton(text='✅ Завершить всё')],
        [KeyboardButton(text='Отчёт📝')],
        [KeyboardButton(text='↩️ Назад к добавлению'), KeyboardButton(text='🔄 Возобновить задачу')]
    ],
    resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню'
)


SpisZd = []

async def reply_spiszd():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='Вернуться в меню'))
    for zd in SpisZd:
        keyboard.add(KeyboardButton(text = zd))

    return keyboard.adjust(1).as_markup()