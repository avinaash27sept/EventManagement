import streamlit as st
import requests
import os
import io
import csv
from urllib.parse import urlparse
from db import init_db, get_session, Event, Registration
from db import Feedback
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io as _io

init_db()

def is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


st.title("Admin — Event Manager")

st.header("Create or update an event")
with st.form("upload_form"):
    workshop_title = st.text_input("Event title")
    pdf_file = st.file_uploader("Organizer PDF", type=["pdf"])
    organizing_department = st.text_input("Organizing department (optional)")
    organizer_name = st.text_input("Organizer name (optional)")
    registration_link = st.text_input("Google Form registration link (full URL)")
    submitted = st.form_submit_button("Create / Update Event")
    if submitted:
        if not workshop_title:
            st.error("Provide an event title")
        else:
            if registration_link and not is_valid_url(registration_link):
                st.error("Registration link is not a valid URL (must start with http:// or https://)")
            else:
                os.makedirs("organizer_pdfs", exist_ok=True)
                filename = None
                if pdf_file:
                    filename = f"{workshop_title.replace(' ','_')}.pdf"
                    path = os.path.join("organizer_pdfs", filename)
                    with open(path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                # save or update event in DB
                sess = get_session()
                w = sess.query(Event).filter(Event.title==workshop_title).first()
                if not w:
                    w = Event(title=workshop_title, organizer_pdf=filename, registration_form=registration_link, organizing_department=organizing_department, organizer_name=organizer_name)
                    sess.add(w)
                else:
                    if filename:
                        w.organizer_pdf = filename
                    w.registration_form = registration_link
                    w.organizing_department = organizing_department
                    w.organizer_name = organizer_name
                sess.commit()
                st.success(f"Event '{workshop_title}' saved")

# (Edit existing workshop section removed)

st.markdown("---")
st.subheader("Registrations")
sess = get_session()
registrations = sess.query(Registration).order_by(Registration.registered_at.desc()).limit(1000).all()
for a in registrations:
    st.write(f"{a.name} — {a.email} — Event ID {a.workshop_id} — Score: {a.score}")

# CSV export of registrations
if registrations:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id","name","email","institute","department","contact_no","event_id","registered_at","score","certificate_sent"])
    for a in registrations:
        writer.writerow([a.id, a.name, a.email, a.institute, a.department, a.contact_no, a.workshop_id, a.registered_at, a.score, a.certificate_sent])
    st.download_button(label="Download registrations CSV", data=buffer.getvalue(), file_name="registrations.csv", mime="text/csv")
else:
    st.info("No registrations yet.")

st.header("Registrations")
sess = get_session()
registrations_short = sess.query(Registration).order_by(Registration.registered_at.desc()).limit(200).all()
for a in registrations_short:
    st.write(f"{a.name} — {a.email} — Event ID {a.workshop_id} — Score: {a.score}")

st.markdown("---")
st.header("Feedback control")
sess = get_session()
workshops = sess.query(Event).order_by(Event.id.desc()).all()
if not workshops:
    st.info("No events available to control feedback for.")
else:
    for w in workshops:
        col1, col2 = st.columns([6,1])
        with col1:
            st.write(f"{w.id}: {w.title}")
        with col2:
            enabled = st.checkbox("Show feedback", value=bool(w.feedback_enabled), key=f"fb_{w.id}")
            if enabled != bool(w.feedback_enabled):
                w.feedback_enabled = bool(enabled)
                sess.add(w)
                sess.commit()
                if enabled:
                    st.success("Feedback enabled for this workshop")
                else:
                    st.info("Feedback disabled for this workshop")
        # Feedback report button
        if st.button("Generate feedback PDF", key=f"pdf_{w.id}"):
            # generate PDF in memory
            sess = get_session()
            rows = sess.query(Feedback).filter(Feedback.workshop_id==w.id).order_by(Feedback.submitted_at.desc()).all()
            buf = _io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            width, height = A4
            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            c.drawString(40, y, f"Feedback report — {w.title}")
            y -= 30
            c.setFont("Helvetica", 12)
            total = len(rows)
            if total == 0:
                c.drawString(40, y, "No feedback submitted yet.")
            else:
                # compute averages
                avg = [0,0,0,0,0]
                for r in rows:
                    avg[0] += (r.q1 or 0)
                    avg[1] += (r.q2 or 0)
                    avg[2] += (r.q3 or 0)
                    avg[3] += (r.q4 or 0)
                    avg[4] += (r.q5 or 0)
                avg = [round(v/total,2) for v in avg]
                c.drawString(40, y, f"Total responses: {total}")
                y -= 20
                c.drawString(40, y, f"Average scores: Q1={avg[0]}  Q2={avg[1]}  Q3={avg[2]}  Q4={avg[3]}  Q5={avg[4]}")
                y -= 30
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, "Recent responses:")
                y -= 20
                c.setFont("Helvetica", 10)
                for r in rows[:50]:
                    line = f"{r.submitted_at.strftime('%Y-%m-%d %H:%M')} — {r.email or 'N/A'} — {r.q1},{r.q2},{r.q3},{r.q4},{r.q5}"
                    if y < 60:
                        c.showPage()
                        y = height - 50
                        c.setFont("Helvetica", 10)
                    c.drawString(40, y, line)
                    y -= 14
                y -= 10
                if any(r.comments for r in rows):
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(40, y, "Comments:")
                    y -= 20
                    c.setFont("Helvetica", 10)
                    for r in rows:
                        if not r.comments:
                            continue
                        txt = f"{r.submitted_at.strftime('%Y-%m-%d')} {r.email or 'N/A'}: {r.comments}"
                        # wrap long comments
                        maxlen = 90
                        parts = [txt[i:i+maxlen] for i in range(0, len(txt), maxlen)]
                        for p in parts:
                            if y < 60:
                                c.showPage()
                                y = height - 50
                                c.setFont("Helvetica", 10)
                            c.drawString(40, y, p)
                            y -= 12
                        y -= 6
            c.save()
            buf.seek(0)
            st.download_button(label="Download PDF", data=buf.read(), file_name=f"feedback_{w.id}.pdf", mime="application/pdf")

st.header("Webhook test")
st.write("Use this to POST a test registration or quiz to the webhook server.")
with st.form("test_webhook"):
    evt = st.selectbox("Event type", ["registration", "quiz"])
    name = st.text_input("Name")
    email = st.text_input("Email")
    event_id = st.text_input("Event ID", value="1")
    score = st.number_input("Score (for quiz)", min_value=0, max_value=100, value=80)
    submit = st.form_submit_button("Send test")
    if submit:
        payload = {"type": evt, "name": name, "email": email, "event_id": int(event_id), "score": int(score)}
        try:
            r = requests.post("http://127.0.0.1:8000/webhook", json=payload, timeout=5)
            st.write("Response:", r.status_code, r.text)
        except Exception as e:
            st.error(f"Failed to call webhook: {e}")
