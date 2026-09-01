import sqlite3
conn = sqlite3.connect('workshop_manager.db')
cur = conn.cursor()
cur.execute('SELECT id, name, email, workshop_id, confirmation_sent FROM registrations ORDER BY id DESC LIMIT 10')
rows = cur.fetchall()
for r in rows:
    print(r)
cur.close()
conn.close()
