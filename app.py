import streamlit as st
import os
import re
from db import init_db, get_session, Event, Registration

init_db()

# Header: institute title and subtitle
col1, col2 = st.columns([1, 8])
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=96)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=96)
    else:
        st.write("")
with col2:
    st.markdown(
        """
        <div style='line-height:1'>
          <h1 style='margin:0; font-size:22px'>Vidya Pratishthan's Kamalnayan Bajaj Institute of Engineering and Technology, Baramati</h1>
          <div style='color:#444; margin-top:6px; font-size:16px; font-weight:600'>Event Management</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.header("Available Events")
sess = get_session()
workshops = sess.query(Event).order_by(Event.id.desc()).all()
if not workshops:
    st.info("No events available yet. Please check back later or contact the organisers.")
else:
    for w in workshops:
        st.subheader(w.title)
        # show total registrations count
        sess = get_session()
        total = sess.query(Registration).filter(Registration.workshop_id == w.id).count()
        st.write(f"Total registrations: {total}")
        if w.organizer_pdf:
            pdf_path = os.path.join("organizer_pdfs", w.organizer_pdf)
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    data = f.read()
                st.download_button(label="Download schedule (PDF)", data=data, file_name=w.organizer_pdf, mime="application/pdf")
            else:
                st.write("Schedule not available yet.")
        else:
            st.write("Schedule not available yet.")
        # show registration link if available
        if getattr(w, 'registration_form', None):
            link = w.registration_form
            if link:
                st.markdown(f"**Register:** [Open registration form]({link})")

        # Inline registration form (alternative to Google Form)
        with st.expander("Register here"):
            with st.form(f"reg_form_{w.id}"):
                name = st.text_input("Full name")
                email = st.text_input("Email")
                institute = st.text_input("Institute / Organization")
                department = st.text_input("Department")
                contact_no = st.text_input("Contact number")
                submit = st.form_submit_button("Register")
                if submit:
                    # basic validation
                    if not name or not email:
                        st.error("Please provide name and email.")
                    else:
                        email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
                        if not email_re.match(email):
                            st.error("Please provide a valid email address.")
                        else:
                            sess = get_session()
                            exists = sess.query(Registration).filter(Registration.email==email, Registration.workshop_id==w.id).first()
                            if exists:
                                st.info("You are already registered for this event.")
                            else:
                                a = Registration(name=name, email=email, institute=institute or None, department=department or None, contact_no=contact_no or None, workshop_id=w.id)
                                sess.add(a)
                                sess.commit()
                                st.success("Registration received — thank you!")
                                # allow download of schedule if available
                                if w.organizer_pdf:
                                    pdf_path = os.path.join("organizer_pdfs", w.organizer_pdf)
                                    if os.path.exists(pdf_path):
                                        with open(pdf_path, "rb") as f:
                                            data = f.read()
                                        st.download_button(label="Download schedule (PDF)", data=data, file_name=w.organizer_pdf, mime="application/pdf")

st.markdown("---")
st.write("Registrations are handled via Google Form. Please use the form link provided by organisers to register.")
