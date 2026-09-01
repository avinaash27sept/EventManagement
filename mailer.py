import smtplib
from email.message import EmailMessage
import os
import base64
import requests
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def send_email_smtp(smtp_cfg, to_email, subject, body, attachments=None):
    msg = EmailMessage()
    msg["From"] = smtp_cfg.get("from") or smtp_cfg.get("user")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    for path in (attachments or []):
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            data = f.read()
        maintype = "application"
        subtype = "pdf"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(path))

    with smtplib.SMTP(smtp_cfg.get("host"), smtp_cfg.get("port")) as s:
        if smtp_cfg.get("starttls", True):
            s.starttls()
        if smtp_cfg.get("user") and smtp_cfg.get("password"):
            s.login(smtp_cfg.get("user"), smtp_cfg.get("password"))
        s.send_message(msg)


def send_via_sendgrid(api_key, to_email, subject, body, attachments=None, from_email=None):
    """Send email via SendGrid Web API. attachments is a list of file paths."""
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    from_email = from_email or os.environ.get("SENDGRID_FROM") or "no-reply@example.com"

    personalizations = [{"to": [{"email": to_email}], "subject": subject}]
    content = [{"type": "text/plain", "value": body}]

    data = {
        "personalizations": personalizations,
        "from": {"email": from_email},
        "content": content
    }

    files = []
    if attachments:
        attach_list = []
        for path in attachments:
            if not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                b = base64.b64encode(f.read()).decode("utf-8")
            attach_list.append({
                "content": b,
                "type": "application/pdf",
                "filename": os.path.basename(path)
            })
        if attach_list:
            data["attachments"] = attach_list

    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp


def generate_certificate(name, workshop_title, score, out_path):
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 150, "Certificate of Completion")
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 200, f"This certifies that {name}")
    c.drawCentredString(width / 2, height - 230, f"completed the event: {workshop_title}")
    c.drawCentredString(width / 2, height - 260, f"Quiz score: {score}")
    c.showPage()
    c.save()
