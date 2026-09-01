from db import get_session, QuizSubmission

sess = get_session()
rows = sess.query(QuizSubmission).order_by(QuizSubmission.submitted_at.desc()).limit(20).all()
print('Found', len(rows))
for r in rows:
    print(r.id, r.workshop_id, r.email, r.score, r.submitted_at)
