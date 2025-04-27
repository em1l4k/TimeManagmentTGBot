import sqlite3
from datetime import datetime

def create_connection():
    "Создаёт и возвращает соединение с БД."
    return sqlite3.connect('my_database.db')

def setup_database():
    "Инициализирует базу данных и все таблицы."
    conn = create_connection()
    cursor = conn.cursor()

    # Таблица типов задач
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
                CHECK(name IN ('task','action','interrupt'))
        );
    ''')

    # Вставляем стандартные типы, если их ещё нет
    cursor.executemany(
        "INSERT OR IGNORE INTO Type (name) VALUES (?)",
        [('task',), ('action',), ('interrupt',)]
    )

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY NOT NULL,
            name TEXT NOT NULL
        );
    ''')

    # Таблица задач (Object)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Object (
            object_id INTEGER PRIMARY KEY AUTOINCREMENT,
            type INTEGER NOT NULL,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            start_time TEXT,
            pause_time TEXT,
            stop_time TEXT,
            duration_seconds INTEGER DEFAULT 0,
            status TEXT DEFAULT 'новая',
            FOREIGN KEY(type) REFERENCES Type(id),
            FOREIGN KEY(user_id) REFERENCES Users(user_id)
        );
    ''')

    conn.commit()
    conn.close()

def format_time(time_str, with_date=False):
    if not time_str:
        return "Не завершено"

    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    if with_date:
        return dt.strftime('%d.%m.%Y %H:%M')
    else:
        return dt.strftime('%H:%M')


def format_duration(seconds):
    """Форматирует длительность в 'часы:минуты'."""
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}"



def add_user(user_id: int, name: str):
    """Регистрация пользователя (если ещё не был добавлен)."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO Users (user_id, name)
        VALUES (?, ?)
    ''', (user_id, name))
    conn.commit()
    conn.close()

def add_task(user_id: int, task_name: str, type_name: str) -> int:
    """
    Создаёт новую задачу и возвращает её object_id.
    type_name должно быть 'task', 'action' или 'interrupt'.
    """
    conn = create_connection()
    cursor = conn.cursor()

    # Находим id типа
    cursor.execute("SELECT id FROM Type WHERE name = ?", (type_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise Exception("Неизвестный тип задачи.")
    type_id = row[0]

    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO Object (type, name, user_id, created_at)
        VALUES (?, ?, ?, ?)
    ''', (type_id, task_name, user_id, created_at))

    object_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return object_id

def get_tasks(user_id: int):
    """Возвращает список всех задач пользователя: [(object_id, name, status), ...]."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.object_id, o.name, o.status
        FROM Object o
        WHERE o.user_id = ?
        ORDER BY o.object_id
    ''', (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def start_task(user_id: int, object_id: int):
    """
    Ставит на паузу текущую выполняемую задачу (если есть),
    и запускает новую (object_id).
    """
    conn = create_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1) Пауза предыдущей активной
    cursor.execute('''
        SELECT object_id, start_time, duration_seconds
        FROM Object
        WHERE user_id = ? AND status = 'выполняется' AND object_id != ?
    ''', (user_id, object_id))
    row = cursor.fetchone()
    if row:
        old_id, old_start, old_dur = row
        total = int(old_dur or 0)
        if old_start:
            dt = datetime.strptime(old_start, '%Y-%m-%d %H:%M:%S')
            total += int((datetime.now() - dt).total_seconds())
        cursor.execute('''
            UPDATE Object
            SET status = 'приостановлена',
                pause_time = ?,
                duration_seconds = ?
            WHERE object_id = ?
        ''', (now, total, old_id))

    # 2) Старт новой
    cursor.execute('''
        UPDATE Object
        SET status = 'выполняется',
            start_time = ?,
            pause_time = NULL
        WHERE object_id = ?
    ''', (now, object_id))

    conn.commit()
    conn.close()

def stop_task(user_id: int, object_id: int):
    conn = create_connection()
    cursor = conn.cursor()
    now = datetime.now()

    # Получаем статус, время старта и длительность
    cursor.execute('''
        SELECT status, start_time, duration_seconds
        FROM Object
        WHERE user_id = ? AND object_id = ?
    ''', (user_id, object_id))
    row = cursor.fetchone()

    if not row or not row[1]:
        conn.close()
        return

    status, start_time, duration = row
    duration = int(duration or 0)

    # Если задача в статусе "выполняется", считаем текущее время
    if status == 'выполняется':
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        delta = (now - start_dt).total_seconds()
        duration += int(delta)

    cursor.execute('''
        UPDATE Object
        SET status = 'завершена',
            stop_time = ?,
            duration_seconds = ?
        WHERE user_id = ? AND object_id = ?
    ''', (now.strftime('%Y-%m-%d %H:%M:%S'), duration, user_id, object_id))

    conn.commit()
    conn.close()


def resume_last_task(user_id: int) -> bool:
    """
    Возобновляет последнюю приостановленную задачу типа 'task'.
    Возвращает True, если такая найдена и запущена.
    """
    conn = create_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        SELECT o.object_id
        FROM Object o
        JOIN Type t ON o.type = t.id
        WHERE o.user_id = ?
          AND t.name = 'task'
          AND o.status = 'приостановлена'
        ORDER BY o.pause_time DESC
        LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    oid = row[0]
    cursor.execute('''
        UPDATE Object
        SET status = 'выполняется',
            start_time = ?,
            pause_time = NULL
        WHERE object_id = ?
    ''', (now, oid))

    conn.commit()
    conn.close()
    return True

def get_report_for_day(user_id: int, date: str):
    """
    Возвращает отчет по задачам для пользователя за указанный день.
    Сравнивает только дату, игнорируя время.
    """
    conn = create_connection()
    cursor = conn.cursor()

    # Преобразуем created_at в дату и сравниваем только дату
    cursor.execute('''
        SELECT Object.name, Type.name, Object.start_time, Object.stop_time, Object.duration_seconds
        FROM Object
        JOIN Type ON Object.type = Type.id
        WHERE Object.user_id = ? AND DATE(Object.created_at) = ?
    ''', (user_id, date))

    tasks = cursor.fetchall()
    conn.close()

    return tasks



def complete_active_task(user_id: int) -> int:

    conn = create_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Находим активную задачу любого типа
    cursor.execute('''
        SELECT object_id, start_time, duration_seconds
        FROM Object
        WHERE user_id = ? AND status = 'выполняется'
        LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    oid, st, dur = row
    total = int(dur or 0)
    if st:
        start_dt = datetime.strptime(st, '%Y-%m-%d %H:%M:%S')
        total += int((datetime.now() - start_dt).total_seconds())

    # Завершаем её
    cursor.execute('''
        UPDATE Object
        SET status = 'завершена',
            stop_time = ?,
            duration_seconds = ?
        WHERE object_id = ?
    ''', (now, total, oid))

    conn.commit()
    conn.close()
    return oid


if __name__ == '__main__':
    setup_database()
    print("БД создана.")
