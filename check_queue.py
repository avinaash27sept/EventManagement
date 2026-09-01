import sqlite3
conn = sqlite3.connect('workshop_manager.db')
cur = conn.cursor()
cur.execute("SELECT id, to_email, subject, attempts, next_attempt, last_error FROM email_queue ORDER BY id DESC LIMIT 10")
rows = cur.fetchall()
print('FOUND', len(rows))
for r in rows:
    print(r)
cur.close()
conn.close()
