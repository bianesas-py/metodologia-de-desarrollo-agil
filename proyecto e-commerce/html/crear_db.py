
import sqlite3

def inicializar_db():
    with open('schema.sql', 'r', encoding='utf-8') as f:
        script = f.read()

    conn = sqlite3.connect('tienda.db')
    cursor = conn.cursor()
    cursor.executescript(script)
    conn.commit()
    conn.close()
    print("¡Base de datos tienda.db creada y poblada con éxito!")

if __name__ == '__main__':
    inicializar_db()