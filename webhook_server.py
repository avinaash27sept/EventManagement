from fastapi import FastAPI, Request
import uvicorn
from db import init_db, get_session, Registration, Event
from mailer import send_email_smtp, generate_certificate
import os
import json

init_db()

app = FastAPI()

# Expect SMTP config in env var SMTP_CONFIG as JSON or use a local file `smtp_config.json`.
def load_smtp_config():
    cfg = os.environ.get("SMTP_CONFIG")
    if cfg:
        return json.loads(cfg)
    if os.path.exists("smtp_config.json"):
        with open("smtp_config.json","r") as f:
            return json.load(f)
    return {"host":"smtp.gmail.com","port":587,"starttls":True}


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    typ = data.get("type")
    sess = get_session()
    smtp = load_smtp_config()

    if typ == "registration":
        name = data.get("name")
        email = data.get("email")
        # accept either event_id or workshop_id in payload
        workshop_id = data.get("event_id") if data.get("event_id") is not None else data.get("workshop_id")
        workshop_id = int(workshop_id)
        # store registration
        a = Registration(name=name, email=email, workshop_id=workshop_id)
        sess.add(a)
        sess.commit()

        # find event PDF
        w = sess.query(Event).filter(Event.id==workshop_id).first()
        attachments = []
        if w and w.organizer_pdf:
            p = os.path.join("organizer_pdfs", w.organizer_pdf)
            if os.path.exists(p):
                attachments.append(p)

        # send confirmation email
        subject = f"Registration confirmed: {w.title if w else 'Event'}"
        body = f"Hi {name},\n\nThanks for registering. Attached is the schedule and details."
        try:
            send_email_smtp(smtp, email, subject, body, attachments=attachments)
        except Exception as e:
            return {"status":"stored_but_email_failed","error":str(e)}

        return {"status":"ok"}

    if typ == "quiz":
        name = data.get("name")
        email = data.get("email")
        workshop_id = data.get("event_id") if data.get("event_id") is not None else data.get("workshop_id")
        workshop_id = int(workshop_id)
        score = int(data.get("score",0))
        # find registration record
        a = sess.query(Registration).filter(Registration.email==email, Registration.workshop_id==workshop_id).first()
        if not a:
            # create registration if missing
            a = Registration(name=name, email=email, workshop_id=workshop_id, score=score)
            sess.add(a)
        else:
            a.score = score
        sess.commit()

        # generate certificate
        os.makedirs("certificates", exist_ok=True)
        workshop = sess.query(Event).filter(Event.id==workshop_id).first()
        title = workshop.title if workshop else "Event"
        cert_path = os.path.join("certificates", f"certificate_{a.id}.pdf")
        generate_certificate(name, title, score, cert_path)

        # send certificate
        subject = f"Your certificate: {title}"
        body = f"Hi {name},\n\nAttached is your certificate. Your quiz score: {score}."
        try:
            send_email_smtp(smtp, email, subject, body, attachments=[cert_path])
            a.certificate_sent = True
            sess.commit()
        except Exception as e:
            return {"status":"stored_but_email_failed","error":str(e)}

        return {"status":"ok"}

    return {"status":"ignored","reason":"unknown type"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
