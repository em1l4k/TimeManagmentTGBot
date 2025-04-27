import sqlite3

DB_NAME = 'my_database.db'

def check_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверка таблицы Type
    cursor.execute("SELECT * FROM Type")
    print("Type table:", cursor.fetchall())

    # Проверка таблицы Object для задач
    cursor.execute("SELECT object_id, name FROM Object")
    print("Tasks:", cursor.fetchall())

    cursor.execute('''
        SELECT object_id, name, user_id, created_at
        FROM Object
    ''')
    print("\n[All tasks in Object table]")
    for row in cursor.fetchall():
        print(row)



check_db()
