import streamlit as st
import os
import json
from db import init_db, get_session, Event, Registration, Feedback, EmailQueue, QuizSubmission
from mailer import send_email_smtp

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

def load_smtp_config():
    cfg = os.environ.get("SMTP_CONFIG")
    if cfg:
        return json.loads(cfg)
    if os.path.exists("smtp_config.json"):
        with open("smtp_config.json","r") as f:
            return json.load(f)
    return {"host":"smtp.gmail.com","port":587,"starttls":True}

if not workshops:
    st.info("No events available yet. Please check back later or contact the organisers.")
else:
    options = [f"{w.id}: {w.title}" for w in workshops]
    sel = st.selectbox("Select workshop to register", options)
    if sel:
        selected_id = int(sel.split(":")[0])
        w = next((x for x in workshops if x.id == selected_id), None)
        if w:
            st.subheader(w.title)
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

            st.markdown("---")
            st.write("Please fill the registration form below:")
            with st.form("local_reg_form"):
                name = st.text_input("Full name")
                email = st.text_input("Email")
                institute = st.text_input("Institute / Organization")
                department = st.text_input("Department")
                contact_no = st.text_input("Contact number")
                submit = st.form_submit_button("Register")
                if submit:
                    if not name or not email:
                        st.error("Please provide name and email.")
                    else:
                        # basic email validation
                        if "@" not in email or "." not in email:
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

                                # send confirmation email
                                smtp = load_smtp_config()
                                attachments = []
                                if w.organizer_pdf:
                                    p = os.path.join("organizer_pdfs", w.organizer_pdf)
                                    if os.path.exists(p):
                                        attachments.append(p)
                                subject = f"Registration confirmed: {w.title}"
                                body = f"Hi {name},\n\nThanks for registering for {w.title}. Attached is the schedule and details."
                                try:
                                    send_email_smtp(smtp, email, subject, body, attachments=attachments)
                                    a.confirmation_sent = True
                                    sess.commit()
                                    st.success("Registration received — confirmation email sent.")
                                except Exception as e:
                                    # enqueue behavior handled by webhook worker; here just inform user
                                    st.success("Registration received — we will email you the schedule shortly.")
                                    # Do not crash on email failure; leave confirmation_sent false

                                if attachments:
                                    with open(attachments[0], "rb") as f:
                                        data = f.read()
                                    st.download_button(label="Download schedule (PDF)", data=data, file_name=os.path.basename(attachments[0]), mime="application/pdf")

            # Feedback form (shown when admin enables it)
            if getattr(w, 'feedback_enabled', False):
                st.markdown("---")
                st.subheader("Workshop Feedback")
                st.write("Please rate the following from 1 (lowest) to 10 (highest).")
                with st.form("feedback_form"):
                    email_fb = st.text_input("Email (required)")
                    q1 = st.slider("1) How satisfied were you with the workshop content?", 1, 10, 8)
                    q2 = st.slider("2) How well paced was the workshop?", 1, 10, 8)
                    q3 = st.slider("3) How useful were the materials provided?", 1, 10, 8)
                    q4 = st.slider("4) How likely are you to recommend this workshop?", 1, 10, 8)
                    q5 = st.slider("5) Overall experience rating", 1, 10, 8)
                    comments = st.text_area("Any additional comments (optional)")
                    fb_submit = st.form_submit_button("Submit feedback")
                    if fb_submit:
                        if not email_fb or "@" not in email_fb:
                            st.error("Please provide a valid email for feedback.")
                        else:
                            sess = get_session()
                            fb = Feedback(workshop_id=w.id, email=email_fb, q1=q1, q2=q2, q3=q3, q4=q4, q5=q5, comments=comments or None)
                            sess.add(fb)
                            sess.commit()
                            st.success("Thank you for your feedback!")
                            # after feedback submission, show quiz immediately
                            st.info("You can now take the workshop quiz below.")
                            # continue to quiz UI below (page reload will show it)

            # Show quiz only if user (email) has submitted feedback for this workshop
            show_quiz = False
            user_email_for_quiz = None
            # check query param or previous submission: try to use email_fb from current session
            if 'email_fb' in locals() and email_fb:
                user_email_for_quiz = email_fb
            # alternatively, allow the user to enter email to check
            if not user_email_for_quiz:
                user_email_for_quiz = st.text_input("Enter your email to check if you can take the quiz (must have submitted feedback)")
            if user_email_for_quiz:
                sess = get_session()
                fb_exists = sess.query(Feedback).filter(Feedback.workshop_id==w.id, Feedback.email==user_email_for_quiz).first()
                # enable quiz when feedback record exists for this workshop+email
                show_quiz = bool(fb_exists)
                if show_quiz:
                    st.markdown("---")
                    st.subheader("Workshop Quiz")
                    st.write("Answer the 20 multiple-choice questions about Streamlit. Each correct answer is worth 5 marks (total 100). Email is required — certificate will be sent to this email.")
                    # Define 20 Streamlit-focused multiple-choice questions and answer key
                    questions = [
                        {"q": "1) Which Streamlit command displays text or data (accepts many types)?", "opts": ["A) st.display", "B) st.write", "C) st.show", "D) st.print"], "ans": "B"},
                        {"q": "2) Which widget lets the user pick a single option from a dropdown?", "opts": ["A) st.radio", "B) st.checkbox", "C) st.selectbox", "D) st.multiselect"], "ans": "C"},
                        {"q": "3) Which Streamlit function uploads files from the user?", "opts": ["A) st.file_upload", "B) st.upload", "C) st.file_uploader", "D) st.uploader"], "ans": "C"},
                        {"q": "4) Which method creates columns for layout?", "opts": ["A) st.columns", "B) st.grid", "C) st.split", "D) st.layout"], "ans": "A"},
                        {"q": "5) Which Streamlit feature allows grouping inputs and deferring execution until submit?", "opts": ["A) st.container", "B) st.form", "C) st.expander", "D) st.session_state"], "ans": "B"},
                        {"q": "6) Which function lets you add a download button for files?", "opts": ["A) st.download", "B) st.save_button", "C) st.download_button", "D) st.file_button"], "ans": "C"},
                        {"q": "7) How do you create a sidebar area?", "opts": ["A) st.sidebar", "B) st.left_panel", "C) st.aside", "D) st.panel"], "ans": "A"},
                        {"q": "8) Which decorator is recommended for caching computational results in recent Streamlit versions?", "opts": ["A) @st.cache", "B) @st.memo", "C) @st.cache_data", "D) @st.cache_resource"], "ans": "C"},
                        {"q": "9) Which Streamlit call reruns the script from the top?", "opts": ["A) st.rerun", "B) st.experimental_rerun", "C) st.refresh", "D) st.run"], "ans": "B"},
                        {"q": "10) Which widget is appropriate for selecting multiple items?", "opts": ["A) st.selectbox", "B) st.radio", "C) st.multiselect", "D) st.slider"], "ans": "C"},
                        {"q": "11) Which function shows a matplotlib figure in Streamlit?", "opts": ["A) st.figure", "B) st.pyplot", "C) st.showplot", "D) st.plot"], "ans": "B"},
                        {"q": "12) Where can you store short-lived per-session values?", "opts": ["A) st.cache", "B) st.session_state", "C) st.global_state", "D) st.temp"], "ans": "B"},
                        {"q": "13) Which control is used for numeric ranges?", "opts": ["A) st.slider", "B) st.selectbox", "C) st.text_input", "D) st.radio"], "ans": "A"},
                        {"q": "14) Which function writes Markdown?", "opts": ["A) st.markdown", "B) st.text", "C) st.html", "D) st.md"], "ans": "A"},
                        {"q": "15) Which option is used to provide a long-running cache for expensive objects (like DB connections)?", "opts": ["A) @st.cache_data", "B) @st.cache_resource", "C) @st.cache", "D) @st.experimental_memo"], "ans": "B"},
                        {"q": "16) How do you show an image file?", "opts": ["A) st.img", "B) st.image", "C) st.show_image", "D) st.display_image"], "ans": "B"},
                        {"q": "17) Which function adds a progress bar?", "opts": ["A) st.progress_bar", "B) st.loading", "C) st.spinner", "D) st.progress"], "ans": "D"},
                        {"q": "18) Which widget is best for free-form multi-line input?", "opts": ["A) st.text_input", "B) st.text_area", "C) st.input", "D) st.multiline"], "ans": "B"},
                        {"q": "19) To show raw HTML you should use which argument?", "opts": ["A) st.markdown(..., unsafe_allow_html=True)", "B) st.html(...)", "C) st.raw_html(...)", "D) st.markdown_html(...)"], "ans": "A"},
                        {"q": "20) Which function returns query parameters from the URL?", "opts": ["A) st.get_query_params", "B) st.experimental_get_query_params", "C) st.query_params", "D) st.get_params"], "ans": "B"}
                    ]

                    with st.form("quiz_form"):
                        quiz_email = st.text_input("Email (required for certificate)", value=user_email_for_quiz)
                        selected_answers = []
                        for i, item in enumerate(questions, start=1):
                            opts = ["Select..."] + item['opts']
                            choice = st.selectbox(f"{item['q']}", opts, key=f"q{i}")
                            if choice == "Select...":
                                selected_answers.append(None)
                            else:
                                # extract letter (A/B/C/D) from choice string
                                selected_answers.append(choice.split(')')[0].strip())
                        submit_quiz = st.form_submit_button("Submit Quiz")
                        if submit_quiz:
                            if not quiz_email or "@" not in quiz_email:
                                st.error("Please provide a valid email for the quiz.")
                            elif any(a is None for a in selected_answers):
                                st.error("Please answer all questions before submitting the quiz.")
                            else:
                                # compute marks: 5 marks per correct answer
                                correct = 0
                                for ans, item in zip(selected_answers, questions):
                                    if ans == item['ans']:
                                        correct += 1
                                marks = correct * 5
                                # store quiz submission
                                import json as _json, os as _os
                                sess = get_session()
                                qb = QuizSubmission(workshop_id=w.id, email=quiz_email, answers=_json.dumps(selected_answers), score=marks)
                                sess.add(qb)
                                # also update or create registration
                                reg = sess.query(Registration).filter(Registration.email==quiz_email, Registration.workshop_id==w.id).first()
                                if not reg:
                                    reg = Registration(name=quiz_email.split('@')[0], email=quiz_email, workshop_id=w.id)
                                    sess.add(reg)
                                    sess.commit()
                                reg.score = marks
                                sess.commit()

                                # generate certificate PDF
                                cert_dir = 'certificates'
                                _os.makedirs(cert_dir, exist_ok=True)
                                cert_path = _os.path.join(cert_dir, f'certificate_{reg.id}.pdf')
                                try:
                                    from mailer import generate_certificate
                                    # pass institute and date for certificate
                                    generate_certificate(reg.name, "AI/ML Application Development with Streamlit", marks, cert_path, institute=reg.institute, date_str="2nd September 2026")
                                    # send certificate via email
                                    smtp = load_smtp_config()
                                    subj = f"Your certificate: {w.title} — Score {marks}/100"
                                    body = f"Hi {reg.name},\n\nThanks for completing the quiz. Your score: {marks}/100. Attached is your certificate."
                                    try:
                                        send_email_smtp(smtp, quiz_email, subj, body, attachments=[cert_path])
                                        reg.certificate_sent = True
                                        sess.commit()
                                        st.success(f"Quiz submitted — certificate emailed to {quiz_email} (score: {marks}/100).")
                                    except Exception as e:
                                        # enqueue certificate for retry
                                        try:
                                            sess2 = get_session()
                                            import datetime as _dt
                                            q = EmailQueue(
                                                to_email=quiz_email,
                                                subject=subj,
                                                body=body,
                                                attachments=json.dumps([cert_path]),
                                                registration_id=reg.id,
                                                attempts=0,
                                                next_attempt=_dt.datetime.utcnow(),
                                                last_error=str(e)
                                            )
                                            sess2.add(q)
                                            sess2.commit()
                                            sess2.close()
                                            st.success(f"Quiz submitted (score: {marks}/100). Certificate generated and queued for retry.")
                                        except Exception as ee:
                                            st.error(f"Quiz submitted (score: {marks}/100). Failed to enqueue certificate: {ee}")
                                except Exception as e:
                                    st.error(f"Failed to generate certificate: {e}")
