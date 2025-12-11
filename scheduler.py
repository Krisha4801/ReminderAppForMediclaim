from apscheduler.schedulers.blocking import BlockingScheduler
import datetime
from database import get_db
import requests

API_KEY = "YOUR_SMS_OR_WHATSAPP_API_KEY"

def check_policies():
    today = str(datetime.date.today())
    conn = get_db()
    
    cursor = conn.execute("SELECT * FROM policy WHERE end_date=? AND status='Pending'", (today,))
    data = cursor.fetchall()

    for row in data:
        name = row["name"]
        contact = row["contact"]

        # ---- Example: SMS using Fast2SMS ----
        msg = f"Dear {name}, your policy is due for renewal today. Please renew soon."

        print("Sending SMS to:", contact)

        # Send SMS (Fast2SMS example)
        requests.get(f"https://www.fast2sms.com/dev/bulkV2?authorization={API_KEY}&message={msg}&language=english&route=q&numbers={contact}")

        # Mark as done
        conn.execute("UPDATE policy SET status='Notified' WHERE id=?", (row["id"],))
        conn.commit()

    conn.close()

scheduler = BlockingScheduler()
scheduler.add_job(check_policies, "interval", hours=24)

print("Scheduler running...")

scheduler.start()
