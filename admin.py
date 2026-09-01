import streamlit as st
import requests
import os
import io
import csv
from urllib.parse import urlparse
from db import init_db, get_session, Event, Registration

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
