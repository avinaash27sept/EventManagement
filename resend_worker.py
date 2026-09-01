import time
import json
import datetime
import os
from db import get_session, EmailQueue, Registration, Event
from mailer import send_email_smtp

# Load SMTP config (same behavior as webhook_server)
def load_smtp_config():
    cfg = os.environ.get("SMTP_CONFIG")
    if cfg:
        return json.loads(cfg)
    if os.path.exists("smtp_config.json"):
        with open("smtp_config.json","r") as f:
            return json.load(f)
    return {"host":"smtp.gmail.com","port":587,"starttls":True}

BASE_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 3600
MAX_ATTEMPTS = 6
SLEEP_WHEN_IDLE = 30


def process_queue_once():
    sess = get_session()
    now = datetime.datetime.utcnow()
    rows = sess.query(EmailQueue).filter(EmailQueue.next_attempt <= now).order_by(EmailQueue.next_attempt).limit(20).all()
    if not rows:
        sess.close()
        return 0

    smtp = load_smtp_config()
    processed = 0
    for q in rows:
        processed += 1
        attachments = []
        try:
            if q.attachments:
                attachments = json.loads(q.attachments)
        except Exception:
            attachments = []
        try:
            send_email_smtp(smtp, q.to_email, q.subject, q.body or "", attachments=attachments)
            # mark registration as confirmed or certificate_sent depending on content
            if q.registration_id:
                reg = sess.query(Registration).filter(Registration.id==q.registration_id).first()
                if reg:
                    # determine if this queued email was a certificate (by attachment name or subject)
                    sent_cert = False
                    try:
                        for a in attachments:
                            if 'certificate' in (a or '').lower():
                                reg.certificate_sent = True
                                sent_cert = True
                                break
                    except Exception:
                        sent_cert = False
                    if not sent_cert:
                        if q.subject and 'certificate' in (q.subject or '').lower():
                            reg.certificate_sent = True
                        else:
                            reg.confirmation_sent = True
            # delete queue entry
            sess.delete(q)
            sess.commit()
            print(f"Sent queued email to {q.to_email} (registration {q.registration_id})")
        except Exception as e:
            q.attempts = (q.attempts or 0) + 1
            q.last_error = str(e)
            if q.attempts >= MAX_ATTEMPTS:
                print(f"Giving up on {q.to_email} after {q.attempts} attempts. Error: {e}")
                sess.delete(q)
                sess.commit()
            else:
                delay = min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS * (2 ** (q.attempts - 1)))
                q.next_attempt = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)
                sess.add(q)
                sess.commit()
                print(f"Retry scheduled for {q.to_email} in {delay}s (attempt {q.attempts}). Error: {e}")
    sess.close()
    return processed


if __name__ == '__main__':
    print('Starting resend worker — polling email_queue...')
    try:
        while True:
            count = process_queue_once()
            if count == 0:
                time.sleep(SLEEP_WHEN_IDLE)
            else:
                # short pause between batches
                time.sleep(2)
    except KeyboardInterrupt:
        print('Worker stopped by user')
