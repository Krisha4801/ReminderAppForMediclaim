from datetime import datetime, timedelta
import sqlite3
import requests
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import sqlite3
import smtplib
from email.message import EmailMessage

load_dotenv()
# -------------------------------
# Send WhatsApp Message
# -------------------------------

# -------------------------------
# Email config
# -------------------------------
EMAIL_USER = "krisha4801@gmail.com"
EMAIL_PASS = "dnox eysp qwot seru"  # Use Gmail App Password here
EMAIL_TO = "202512064@dau.ac.in"

def send_alert_email(phone, message):
    try:
        msg = EmailMessage()
        msg["Subject"] = "WhatsApp Reminder Failed"
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.set_content(
            f"Failed to send WhatsApp message after 3 attempts.\n\n"
            f"Phone: {phone}\nMessage:\n{message}"
        )
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("Alert email sent successfully.")
    except Exception as e:
        print("Failed to send alert email:", e)

# -------------------------------
# WhatsApp sending
# -------------------------------
WA_SERVER_URL = os.getenv("WA_SERVER_URL", "http://127.0.0.1:3001/send")
WA_API_KEY = os.getenv("WA_API_KEY", "change_this_to_secret")

def send_whatsapp(phone, message, attempt):
    try:
        payload = {"number": phone, "message": message}
        headers = {
          "x-api-key": WA_API_KEY,
          "Content-Type": "application/json"
        }
        # very short timeout because server is local
        r = requests.post(WA_SERVER_URL, json=payload, headers=headers, timeout=(3, 10))
        # timeout tuple: (connect_timeout, read_timeout)
        if r.status_code == 200:
            return True
        else:
            print("WhatsApp server error:", r.status_code, r.text)
            return False
    except requests.exceptions.RequestException as e:
        print("WhatsApp request error:", e)
        return False
# -------------------------------
# Check & send reminders
# -------------------------------
def check_policies():
    conn = sqlite3.connect("policy.db")
    cur = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        SELECT id, phone, message, retries
        FROM reminders
        WHERE status='pending' AND next_try <= ?
    """, (now,))

    for rid, phone, message, retries in cur.fetchall():
        success = send_whatsapp(phone, message,  retries + 1)

        if success:
            cur.execute("UPDATE reminders SET status='sent' WHERE id=?", (rid,))
        else:
            retries += 1

            next_try = (datetime.now() + timedelta(minutes=1)).strftime(
             "%Y-%m-%d %H:%M:%S"
            )

            if retries >= 3:
             cur.execute(
              "UPDATE reminders SET status='failed', retries=? WHERE id=?",
              (retries, rid)
              )
             send_alert_email(phone, message)
            else:
             cur.execute(
              "UPDATE reminders SET retries=?, next_try=? WHERE id=?",
              (retries, next_try, rid)
            )

    conn.commit()
    conn.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_policies,
        "interval",
        minutes=2,
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    print("Scheduler started (runs every 1 minute)")

    

