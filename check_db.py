import sqlite3
db = 'workshop_manager.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
email = 'tester+webhook@example.com'
cur.execute('SELECT id, name, email, workshop_id, registered_at FROM registrations WHERE email=? ORDER BY id DESC LIMIT 5', (email,))
rows = cur.fetchall()
print('FOUND', len(rows))
for r in rows:
    print(r)
cur.close()
conn.close()
