from flask import Flask, render_template, request
from datetime import datetime, timedelta
import sqlite3
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler import check_policies,start_scheduler

app = Flask(__name__)

ULTRAMSG_INSTANCE = "instance154956"
ULTRAMSG_TOKEN = "mcmdpxw3e8sj7bpu"


def send_whatsapp(number, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    data = {
        "token": ULTRAMSG_TOKEN,
        "to": number,
        "body": message
    }
    return requests.post(url, data=data).json()


@app.route("/")
def form():
    return render_template("add_policy.html")


@app.route("/add_policy", methods=["POST"])
def add_policy():
    name = request.form["name"]
    customer_no = request.form["customer_no"]
    holder_no = "7069098000"
    policy_type = request.form["type"]
    amount = request.form["amount"]
    expiry_date = request.form["expiry_date"]
    policy_number = request.form["policy_number"]

    conn = sqlite3.connect("policy.db")
    cur = conn.cursor()

    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            customer_no TEXT,
            holder_no TEXT,
            policy_number TEXT,
            type TEXT,
            amount TEXT,
            expiry_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            message TEXT,
            next_try TEXT,
            status TEXT
        )
    """)

    # Insert policy
    cur.execute("""
        INSERT INTO policy (name, holder_no, customer_no, policy_number, type, amount, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, holder_no, customer_no, policy_number, policy_type, amount, expiry_date))

    # Build message
    dt = datetime.strptime(expiry_date, "%Y-%m-%d")
    formatted_date = dt.strftime("%d-%m-%Y")

    if policy_type == "Term Plan":
        ending_text = "Please pay premium."
    else:
        ending_text = "Please renew."

    message = (
        f"Reminder: Policy No. {policy_number} for {name} ({policy_type}) "
        f"for INR {amount} expires on {formatted_date}. {ending_text}"
    )

    # First attempt after 1 minute
    next_time = datetime.now() + timedelta(minutes=1)
    next_try = next_time.strftime("%Y-%m-%d %H:%M:%S")

    # Add reminders
    cur.execute("""
        INSERT INTO reminders (phone, message, next_try, status)
        VALUES (?, ?, ?, 'pending')
    """, (holder_no, message, next_try))

    if customer_no != holder_no:
        cur.execute("""
            INSERT INTO reminders (phone, message, next_try, status)
            VALUES (?, ?, ?, 'pending')
        """, (customer_no, message, next_try))

    conn.commit()
    conn.close()

    return "Policy saved. Reminder scheduled."


# START APSCHEDULER ONLY ONCE
scheduler = BackgroundScheduler()
scheduler.add_job(check_policies, "interval", minutes=1)
scheduler.start()


if __name__ == "__main__":
    start_scheduler()
    app.run(debug=True)
