from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database import (
    setup_database, add_user, add_task, get_tasks,
    start_task, stop_task,format_time,
    get_report_for_day, resume_last_task,complete_active_task,format_duration
)
import handlers.keyboards as kb

router = Router()

# FSM состояния для добавления задачи
class AddTaskFSM(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()



# FSM для ручного выбора задачи (если нужно будет оставить)
class TaskControlState(StatesGroup):
    waiting_for_task_number_to_start = State()
    waiting_for_task_number_to_pause = State()
    waiting_for_task_number_to_stop = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    setup_database()
    await message.answer("Привет! Введи название новой задачи:", reply_markup=kb.main_type_menu)
    await state.set_state(AddTaskFSM.waiting_for_name)

@router.message(AddTaskFSM.waiting_for_name)
async def get_task_name(message: Message, state: FSMContext):
    text = message.text.strip()

    # Кнопка выхода в главное меню
    if text == "📋 Открыть основное меню":
        await state.clear()
        await message.answer("📋 Открываю основное меню:", reply_markup=kb.classic_menu)
        return

    #  Любая другая "системная" кнопка — тоже игнор
    if text in [
         "↩️ Назад к добавлению", "Список задач", "Отчёт📝",
        "Удалить задачу", "Начать задачу ▶",
        "Приостановить ⏸", "Завершить ✅",
        "Задача", "Действие", "Прерывание"
     ]:
        return

    #Обычный ввод — принимаем как название задачи
    await state.update_data(task_name=text)
    await message.answer("Какой тип задачи?", reply_markup=kb.task_type_keyboard)
    await state.set_state(AddTaskFSM.waiting_for_type)

@router.message(AddTaskFSM.waiting_for_type)
async def get_task_type(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == '↩️ Назад к добавлению':
        await state.set_state(AddTaskFSM.waiting_for_name)
        await message.answer("✍️ Введи название новой задачи:", reply_markup=kb.main_type_menu)
        return

    type_map = {
        'задача': 'task',
        'действие': 'action',
        'прерывание': 'interrupt'
    }

    if text.lower() not in type_map:
        await message.answer("❗ Пожалуйста, выбери тип задачи с клавиатуры.")
        return

    data = await state.get_data()
    task_name = data.get('task_name')
    type_name = type_map[text.lower()]

    add_user(message.from_user.id, message.from_user.full_name)
    object_id = add_task(message.from_user.id, task_name, type_name)  #Создаём задачу
    start_task(message.from_user.id, object_id)  #И сразу её стартуем

    await message.answer(
        f"✅ Задача «{task_name}» добавлена и запущена как «{text.title()}».",
        reply_markup=kb.main_type_menu
    )
    await state.set_state(AddTaskFSM.waiting_for_name)


@router.message(F.text == '📋 Открыть основное меню')
async def show_main_menu(message: Message):
    await message.answer("📋 Вот основное меню:", reply_markup=kb.classic_menu)

@router.message(F.text == '↩️ Назад к добавлению')
async def back_to_add_mode(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✍️ Введи название новой задачи:", reply_markup=kb.main_type_menu)
    await state.set_state(AddTaskFSM.waiting_for_name)



@router.message(F.text == 'Список задач')
async def spis_zad(message: Message):
    tasks = get_tasks(message.from_user.id)

    if not tasks:
        await message.answer("📭 У тебя пока нет задач.")
        return

    task_list = "\n".join([
        f"{i + 1}. {name} {'✅' if status == 'завершена' else ''}"
        for i, (_, name, status) in enumerate(tasks)
    ])

    await message.answer(f"📝 Твои задачи:\n{task_list}")


@router.message(F.text == 'Отчёт📝')
async def show_report(message: Message):
    from datetime import datetime

    # Дата для запроса в базу
    today_for_db = datetime.now().strftime('%Y-%m-%d')  # 2025-04-27
    # Дата для красивого отображения
    today_for_user = datetime.now().strftime('%d.%m.%Y')  # 27.04.2025

    # Получаем задачи за сегодня
    tasks = get_report_for_day(message.from_user.id, today_for_db)

    if not tasks:
        await message.answer("📭 У тебя пока нет задач за сегодняшний день.")
        return

    # Формируем шапку отчета
    report = f"📊 *Отчёт по задачам за сегодня ({today_for_user}):*\n\n"

    # Проходим по всем задачам
    for task_name, task_type, start_time, stop_time, duration in tasks:
        start_time_formatted = format_time(start_time)  # часы:минуты
        stop_time_formatted = format_time(stop_time)    # часы:минуты
        formatted_duration = format_duration(duration)  # часы:минуты
        #перевод английских типов на русский
        type_translation = {
            'task': 'Задача',
            'action': 'Действие',
            'interrupt': 'Прерывание'
        }
        # Перевод типа
        task_type_rus = type_translation.get(task_type.lower(), task_type)
        # Формируем строку задачи
        report += (
            f"📝 *{task_type_rus}*: {task_name}\n"
            f"Начало: {start_time_formatted}\n"
            f"Конец: {stop_time_formatted}\n"
            f"Длительность: {formatted_duration}\n\n"
        )

    await message.answer(report, parse_mode='Markdown')



@router.message(F.text == '🔄 Возобновить задачу')
async def resume_previous_task(message: Message):
    # Останавливаем активное действие или прерывание
    stop_task(message.from_user.id)

    # Пытаемся найти последнюю обычную задачу (тип "task") и запустить её
    if resume_last_task(message.from_user.id):
        await message.answer("🔄 Последняя задача успешно возобновлена.", reply_markup=kb.classic_menu)
    else:
        await message.answer("❗ Нет задачи для возобновления.", reply_markup=kb.classic_menu)

@router.message(F.text == '✅ Завершить всё')
async def complete_any_active(message: Message):
    oid = complete_active_task(message.from_user.id)
    if oid:
        await message.answer("✅ Текущая активная задача завершена.", reply_markup=kb.classic_menu)
    else:
        await message.answer("📭 Нет активных задач для завершения.", reply_markup=kb.classic_menu)
