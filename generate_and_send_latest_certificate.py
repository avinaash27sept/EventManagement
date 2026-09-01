from db import get_session, QuizSubmission, Registration, Event, EmailQueue
from mailer import generate_certificate, send_email_smtp
import os, json, datetime

sess = get_session()
qs = sess.query(QuizSubmission).order_by(QuizSubmission.submitted_at.desc()).first()
if not qs:
    print('No quiz submissions found.')
    raise SystemExit(0)

reg = sess.query(Registration).filter(Registration.email==qs.email, Registration.workshop_id==qs.workshop_id).first()
if not reg:
    # create a minimal registration record
    reg = Registration(name=qs.email.split('@')[0], email=qs.email, workshop_id=qs.workshop_id)
    sess.add(reg)
    sess.commit()

workshop = sess.query(Event).filter(Event.id==qs.workshop_id).first()
workshop_title = workshop.title if workshop else 'AI/ML application development with Streamlit'

os.makedirs('certificates', exist_ok=True)
cert_path = os.path.join('certificates', f'certificate_{reg.id}.pdf')

print('Generating certificate at', cert_path)
try:
    generate_certificate(reg.name, workshop_title, qs.score or 0, cert_path, institute=reg.institute, date_str='2nd September 2026')
    print('Certificate generated')
except Exception as e:
    print('Failed to generate certificate:', e)
    raise

# load smtp config
smtp_cfg = None
if os.path.exists('smtp_config.json'):
    with open('smtp_config.json','r') as f:
        smtp_cfg = json.load(f)
if not smtp_cfg:
    smtp_cfg = {'host':'smtp.gmail.com','port':587,'starttls':True}

subject = f"Your certificate: {workshop_title} — Score {qs.score or 0}/100"
body = f"Hi {reg.name},\n\nAttached is your workshop certificate. Your score: {qs.score or 0}/100."

print('Attempting to send email to', reg.email)
try:
    send_email_smtp(smtp_cfg, reg.email, subject, body, attachments=[cert_path])
    reg.certificate_sent = True
    sess.commit()
    print('Email sent successfully to', reg.email)
except Exception as e:
    print('Email send failed, enqueuing:', e)
    try:
        q = EmailQueue(
            to_email=reg.email,
            subject=subject,
            body=body,
            attachments=json.dumps([cert_path]),
            registration_id=reg.id,
            attempts=0,
            next_attempt=datetime.datetime.utcnow(),
            last_error=str(e)
        )
        sess.add(q)
        sess.commit()
        print('Enqueued certificate send, queue id', q.id)
    except Exception as ee:
        print('Failed to enqueue email:', ee)

sess.close()
