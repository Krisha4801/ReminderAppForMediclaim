# scheduler.py
from datetime import datetime, timedelta
import sqlite3
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# ---- UltraMSG Config ----
ULTRAMSG_INSTANCE = "instance154956"
ULTRAMSG_TOKEN = "mcmdpxw3e8sj7bpu"


# ------------------------------------------------------
# Send WhatsApp Message
# ------------------------------------------------------
def send_whatsapp(phone, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": phone,
        "body": message
    }

    try:
        res = requests.post(url, data=payload).json()
        print("UltraMSG Response:", res)
        return res
    except Exception as e:
        print("Error sending WhatsApp:", e)
        return {}


# ------------------------------------------------------
# Main Policy Check Function (runs every minute)
# ------------------------------------------------------
def check_policies():
    print("Running check_policies()...")
    conn = sqlite3.connect("policy.db")
    cur = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT id, phone, message 
        FROM reminders
        WHERE status='pending' AND next_try <= ?
    """, (now,))

    rows = cur.fetchall()

    for rid, phone, message in rows:
        result = send_whatsapp(phone, message)

        # UltraMSG success conditions
        success = (
            result.get("sent") == "true" or 
            result.get("queue") == "added"
        )

        if success:
            cur.execute("UPDATE reminders SET status='sent' WHERE id=?", (rid,))
        else:
            # Retry after 1 min
            retry_time = datetime.now() + timedelta(minutes=1)
            cur.execute(
                "UPDATE reminders SET next_try=? WHERE id=?",
                (retry_time.strftime("%Y-%m-%d %H:%M:%S"), rid)
            )

    conn.commit()
    conn.close()


# ------------------------------------------------------
# Scheduler Starter (ONLY runs when invoked)
# ------------------------------------------------------
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_policies, "interval", minutes=1)
    scheduler.start()
    print("Scheduler started (running every 1 minute).")
