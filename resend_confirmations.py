"""Admin helper: resend confirmation emails for registrations.
Usage examples:
  python resend_confirmations.py --email tester+webhook@example.com
  python resend_confirmations.py --workshop 1 --limit 50
"""
import argparse
import os
from db import get_session, Event, Registration
from mailer import send_email_smtp

def build_attachments(workshop):
    attachments = []
    if workshop and workshop.organizer_pdf:
        p = os.path.join('organizer_pdfs', workshop.organizer_pdf)
        if os.path.exists(p):
            attachments.append(p)
    return attachments


def resend_for_email(email):
    sess = get_session()
    regs = sess.query(Registration).filter(Registration.email==email).all()
    if not regs:
        print('No registrations found for', email)
        return
    smtp = None
    # load smtp config same way webhook_server does
    import json
    if os.environ.get('SMTP_CONFIG'):
        smtp = json.loads(os.environ.get('SMTP_CONFIG'))
    elif os.path.exists('smtp_config.json'):
        with open('smtp_config.json','r') as f:
            smtp = json.load(f)
    else:
        print('No SMTP configuration found')
        return

    for r in regs:
        w = sess.query(Event).filter(Event.id==r.workshop_id).first()
        attachments = build_attachments(w)
        subject = f"Registration confirmed: {w.title if w else 'Event'}"
        body = f"Hi {r.name},\n\nThanks for registering. Attached is the schedule and details."
        try:
            send_email_smtp(smtp, r.email, subject, body, attachments=attachments)
            print('Sent to', r.email, 'for workshop', r.workshop_id)
        except Exception as e:
            print('Failed to send to', r.email, 'error:', e)


def resend_for_workshop(workshop_id, limit=100):
    sess = get_session()
    regs = sess.query(Registration).filter(Registration.workshop_id==workshop_id).order_by(Registration.id.desc()).limit(limit).all()
    if not regs:
        print('No registrations found for workshop', workshop_id)
        return
    import json
    if os.environ.get('SMTP_CONFIG'):
        smtp = json.loads(os.environ.get('SMTP_CONFIG'))
    elif os.path.exists('smtp_config.json'):
        with open('smtp_config.json','r') as f:
            smtp = json.load(f)
    else:
        print('No SMTP configuration found')
        return
    w = sess.query(Event).filter(Event.id==workshop_id).first()
    attachments = build_attachments(w)
    subject = f"Registration confirmed: {w.title if w else 'Event'}"
    for r in regs:
        body = f"Hi {r.name},\n\nThanks for registering. Attached is the schedule and details."
        try:
            send_email_smtp(smtp, r.email, subject, body, attachments=attachments)
            print('Sent to', r.email)
        except Exception as e:
            print('Failed to send to', r.email, 'error:', e)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--email', help='Resend confirmation to this email')
    p.add_argument('--workshop', type=int, help='Resend confirmations for this workshop id')
    p.add_argument('--limit', type=int, default=100, help='Limit number of registrations to resend for workshop')
    args = p.parse_args()
    if args.email:
        resend_for_email(args.email)
    elif args.workshop:
        resend_for_workshop(args.workshop, args.limit)
    else:
        print('Specify --email or --workshop')
