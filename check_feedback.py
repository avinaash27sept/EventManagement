from db import get_session, Feedback

sess = get_session()
rows = sess.query(Feedback).order_by(Feedback.submitted_at.desc()).limit(20).all()
print('Found', len(rows))
for r in rows:
    print(r.id, r.workshop_id, r.q1, r.q2, r.q3, r.q4, r.q5, r.comments, r.submitted_at)
