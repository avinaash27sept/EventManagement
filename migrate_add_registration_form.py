import sqlite3
import os

DB_FILE = "workshop_manager.db"

def ensure_column():
    if not os.path.exists(DB_FILE):
        print(f"DB file '{DB_FILE}' not found in current directory: {os.getcwd()}")
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(workshops)")
    cols = [row[1] for row in cur.fetchall()]
    print("Existing columns:", cols)
    if "registration_form" not in cols:
        print("Adding column 'registration_form' to workshops table...")
        cur.execute("ALTER TABLE workshops ADD COLUMN registration_form TEXT")
        conn.commit()
        print("Column added.")
    else:
        print("Column already exists.")
    cur.execute("PRAGMA table_info(workshops)")
    print("Updated columns:", [row[1] for row in cur.fetchall()])
    cur.close()
    conn.close()

if __name__ == '__main__':
    ensure_column()
