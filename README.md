# Event Manager (Streamlit + Webhook)

Quick scaffold to manage events, receive registrations/quizzes via webhook, send confirmation emails and certificates.

Setup

1. Create a Python venv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Configure SMTP. Provide credentials in `smtp_config.json` (or set env `SMTP_CONFIG` with JSON):

Example `smtp_config.json`:

```json
{
  "host": "smtp.gmail.com",
  "port": 587,
  "starttls": true,
  "user": "your@gmail.com",
  "password": "app-password",
  "from": "Workshop Team <your@gmail.com>"
}
```

3. Run the webhook server (FastAPI/uvicorn):

```bash
uvicorn webhook_server:app --reload
```

4. Run the Streamlit admin UI:

```bash
streamlit run app.py
```

Apps Script example (send to webhook):

```javascript
function onFormSubmit(e){
  var payload = {
    type: 'registration',
    name: e.values[1],
    email: e.values[2],
    workshop_id: 1
  };
  UrlFetchApp.fetch('https://your-server/webhook', {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  });
}
```

Notes
- The webhook expects JSON with `type` set to `registration` or `quiz`.
- For `quiz`, include `score`.
- Organizer PDFs uploaded via the Streamlit admin are attached to confirmation emails.
- Certificates are auto-generated and emailed after quiz webhook.

SendGrid
-------
You can send mail using SendGrid instead of SMTP. Set the env var `SENDGRID_API_KEY` or create `sendgrid_config.json` with `{"api_key":"SG.xxxxx"}`.

Example (Python):

```py
from mailer import send_via_sendgrid
import os
send_via_sendgrid(os.environ['SENDGRID_API_KEY'], 'attendee@example.com', 'Subject', 'Body', attachments=['certificates/certificate_1.pdf'])
```
