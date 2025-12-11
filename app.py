from flask import Flask, render_template, request
from datetime import datetime, timedelta
import time
import sqlite3
import requests
import threading

app = Flask(__name__)

ULTRAMSG_INSTANCE = "instance154956"
ULTRAMSG_TOKEN = "mcmdpxw3e8sj7bpu"


def send_whatsapp(number, message):
    url = f"https://api.ultramsg.com/instance154956/messages/chat"
    data = {
        "token": ULTRAMSG_TOKEN,
        "to": number,
        "body": message
    }
    res = requests.post(url, data=data)
    return res.json()


def schedule_message(send_date, customer_no, holder_no, message):
    def task():
        now = datetime.now()
        wait_seconds = (send_date - now).total_seconds()
        if wait_seconds > 0:
            threading.Timer(wait_seconds, send_reminders).start()

    def send_reminders():
        # Send to policy holder
        send_whatsapp(holder_no, message)

        # If customer's phone number is different, send to customer
        if customer_no != holder_no:
            send_whatsapp(customer_no, message)

    threading.Thread(target=task).start()


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

    # ----------- CREATE TABLES -----------
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

    # ----------- INSERT POLICY -----------
    cur.execute("""
    INSERT INTO policy (name, holder_no, customer_no, policy_number, type, amount, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, holder_no, customer_no, policy_number, policy_type, amount, expiry_date))



    # ----------- BUILD MESSAGE -----------
    # Convert expiry_date to dd-mm-yyyy
    date_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d-%m-%Y")
    if policy_type == "Term Plan":
     ending_text = "Please pay premium."
    else:
     ending_text = "Please renew."


    message = (
    f"Reminder: Policy No. {policy_number} for {name} ({policy_type}) "
    f"for INR {amount} expires on {expiry_date}. {ending_text}."
    )

    # ----------- SCHEDULE FIRST ATTEMPT (1 MINUTE FROM NOW) -----------
    next_time = datetime.now() + timedelta(minutes=1)
    next_time_str = next_time.strftime("%Y-%m-%d %H:%M:%S")

    # ----------- ADD REMINDER FOR POLICY HOLDER -----------
    cur.execute("""
        INSERT INTO reminders(phone, message, next_try, status)
        VALUES (?, ?, ?, 'pending')
    """, (holder_no, message, next_time_str))

    # ----------- ADD REMINDER FOR CUSTOMER (if NOT the same number) -----------
    if customer_no != holder_no:
        cur.execute("""
            INSERT INTO reminders(phone, message, next_try, status)
            VALUES (?, ?, ?, 'pending')
        """, (customer_no, message, next_time_str))

    conn.commit()
    conn.close()

    return "Policy saved. Reminder scheduled in 1 year. Thank You"

def start_scheduler():
    def scheduler():
        while True:
            conn = sqlite3.connect("policy.db")
            cur = conn.cursor()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute("""
                SELECT id, phone, message FROM reminders
                WHERE status='pending' AND next_try <= ?
            """, (now,))

            rows = cur.fetchall()

            for rid, phone, message in rows:
               result = send_whatsapp(phone, message)

               success = (
                result.get("sent") == "true" or 
                result.get("queue") == "added"
               )

               if success:
                cur.execute("UPDATE reminders SET status='sent' WHERE id=?", (rid,))
               else:
                new_time = datetime.now() + timedelta(minutes=1)
                cur.execute("UPDATE reminders SET next_try=? WHERE id=?",
                    (new_time.strftime("%Y-%m-%d %H:%M:%S"), rid))

            conn.commit()
            conn.close()

            time.sleep(30)  # check every 30 seconds

    thread = threading.Thread(target=scheduler)
    thread.daemon = True
    thread.start()



if __name__ == "__main__":
    from werkzeug.serving import run_simple

    def run_server():
        start_scheduler()
        run_simple("127.0.0.1", 5000, app, use_reloader=False)

    run_server()

