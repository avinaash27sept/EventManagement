import smtplib
from email.message import EmailMessage
import os
import base64
import requests
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm


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

    timeout = smtp_cfg.get("timeout", 10)
    with smtplib.SMTP(smtp_cfg.get("host"), smtp_cfg.get("port"), timeout=timeout) as s:
        # optional debug logging for SMTP conversation
        if smtp_cfg.get("debug"):
            s.set_debuglevel(1)
        if smtp_cfg.get("starttls", True):
            s.starttls()
        if smtp_cfg.get("user") and smtp_cfg.get("password"):
            s.login(smtp_cfg.get("user"), smtp_cfg.get("password"))
        s.send_message(msg)
    # provide a simple confirmation when function completes without exception
    if smtp_cfg.get("debug"):
        print(f"Email sent to {to_email} via {smtp_cfg.get('host')}:{smtp_cfg.get('port')}")


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


def generate_certificate(name, workshop_title, score, out_path, institute=None, date_str=None):
    # Create a professional-looking certificate PDF on A3 landscape
    pagesize = landscape(A3)
    c = canvas.Canvas(out_path, pagesize=pagesize)
    width, height = pagesize

    # Optional: register commonly available TTF fonts if present (silently ignore failures)
    try:
        pdfmetrics.registerFont(TTFont('Times-Roman', 'Times.ttf'))
    except Exception:
        pass

    # border
    margin = 30 * mm
    c.setStrokeColor(colors.HexColor('#2C3E50'))
    c.setLineWidth(4)
    c.rect(margin/2, margin/2, width - margin, height - margin)

    # Header / logo
    header_y = height - 80
    # draw logo if present
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, margin/2 + 10, header_y - 40, width=80, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(colors.HexColor('#0B3D91'))
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(width/2, header_y, "Vidya Pratishthan's Kamalnayan Bajaj Institute of Engineering and Technology, Baramati")

    # Organized by line
    c.setFont('Helvetica', 12)
    c.setFillColor(colors.HexColor('#2E4053'))
    c.drawCentredString(width/2, header_y - 30, "Organized by Artificial Intelligence and Data Science Department")

    # Certificate title
    title_y = header_y - 90
    c.setFont('Helvetica-Bold', 48)
    c.setFillColor(colors.HexColor('#1C2833'))
    c.drawCentredString(width/2, title_y, "Certificate of Completion")

    # Main statements
    body_start = title_y - 70
    c.setFont('Times-Roman', 18)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, body_start, "This is to certify that")

    # Name
    c.setFont('Helvetica-Bold', 34)
    c.drawCentredString(width/2, body_start - 40, name)

    # From / institute
    if institute:
        c.setFont('Times-Roman', 16)
        c.drawCentredString(width/2, body_start - 80, "from")
        c.setFont('Times-Roman', 16)
        c.drawCentredString(width/2, body_start - 105, institute)

    # Workshop line
    ws_y = body_start - 150
    c.setFont('Times-Roman', 16)
    c.drawCentredString(width/2, ws_y, "has completed workshop on")

    # Workshop big title
    # Use canonical workshop title formatting
    ws_title = "AI/ML Application Development with Streamlit"
    c.setFont('Helvetica-Bold', 30)
    c.setFillColor(colors.HexColor('#922B21'))
    c.drawCentredString(width/2, ws_y - 40, ws_title)

    # Date
    date_display = date_str or "2nd September 2026"
    c.setFont('Times-Roman', 14)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, ws_y - 80, date_display)

    # Signature lines
    sig_y = margin + 60
    sig_xs = [width*0.12, width*0.36, width*0.64, width*0.88]
    sig_names = [
        "Avinash Koare\n(Trainer)",
        "Shital Kokare\n(Coordinator)",
        "Dr. Chaitnya Kulkarni\n(HOD-AIDS)",
        "Dr. Sudhir Lande\n(Principal)"
    ]

    c.setStrokeColor(colors.HexColor('#566573'))
    c.setLineWidth(1)
    for x in sig_xs:
        c.line(x - 60, sig_y + 18, x + 60, sig_y + 18)

    c.setFont('Times-Roman', 10)
    c.setFillColor(colors.HexColor('#2C3E50'))
    for x, name_txt in zip(sig_xs, sig_names):
        lines = name_txt.split('\n')
        for i, ln in enumerate(lines):
            c.drawCentredString(x, sig_y - (i*12), ln)

    # Footer / seal area (optional decorative circle)
    c.setFillColor(colors.HexColor('#D4AC0D'))
    c.circle(width - margin - 60, margin + 50, 30, stroke=0, fill=1)

    c.showPage()
    c.save()
