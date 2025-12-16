from flask import Flask, render_template, request, redirect
from datetime import datetime, timedelta
import sqlite3
from scheduler import check_policies, start_scheduler
from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
import secrets
import os


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or token != request.form.get("csrf_token"):
            return "CSRF blocked", 403

@app.before_request
def set_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrap

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "kaushik" and request.form["password"] == "kaushik123":
            session["logged_in"] = True
            return redirect("/")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required
def form():
    return render_template("add_policy.html")

@app.route("/policies")
@login_required
def view_policies():
    conn = sqlite3.connect("policy.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, customer_no, policy_number, vehicle_number, type, expiry_date FROM policy")
    policies = cur.fetchall()
    conn.close()
    return render_template("view_policies.html", policies=policies)


@app.route("/delete_policy/<int:pid>")
@login_required
def delete_policy(pid):
    conn = sqlite3.connect("policy.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM policy WHERE id=?", (pid,))
    cur.execute("DELETE FROM reminders WHERE phone NOT NULL")  # optional safety

    conn.commit()
    conn.close()
    return redirect("/policies")


@app.route("/add_policy", methods=["POST"])
@login_required
def add_policy():
    name = request.form["name"]
    customer_no = request.form["customer_no"]
    holder_no = "917069098000"
    policy_type = request.form["type"]
    vehicle_number = request.form.get("vehicle_number")
    expiry_date = request.form["expiry_date"]
    policy_number = request.form["policy_number"]
    
    # vehicle number only for vehicle policies
    if policy_type in ("Term Plan", "Mediclaim"):
     vehicle_number = None
    else:
     vehicle_number = vehicle_number.strip()


    # normalize
    customer_no = customer_no.strip()

    # basic validation
    if not customer_no.isdigit() or len(customer_no) < 10:
        return "Invalid customer mobile number"

    # auto add country code
    if len(customer_no) == 10:
        customer_no = "91" + customer_no

    # final validation
    if len(customer_no) != 12:
        return "Invalid customer mobile number"

    conn = sqlite3.connect("policy.db", timeout=10)
    cur = conn.cursor()
    # -------------------------------
    # Create tables if not exists
    # -------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            customer_no TEXT,
            holder_no TEXT,
            policy_number TEXT,
            type TEXT,
            vehicle_number TEXT,
            expiry_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            message TEXT,
            next_try TEXT,
            status TEXT,
            retries INTEGER DEFAULT 0
        )
    """)

    # -------------------------------
    # Insert policy
    # -------------------------------
    cur.execute("""
        INSERT INTO policy
        (name, holder_no, customer_no, policy_number, type, vehicle_number, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, holder_no, customer_no, policy_number, policy_type, vehicle_number, expiry_date))

    # -------------------------------
    # Build WhatsApp message
    # -------------------------------
    dt = datetime.strptime(expiry_date, "%Y-%m-%d")
    formatted_date = dt.strftime("%d-%m-%Y")

    ending_text = "Please pay premium." if policy_type == "Term Plan" else "Please renew."
    vehicle_part = f" ({vehicle_number})" if vehicle_number else ""

    message = (
    "*Reminder:*\n"
    f"Hello {name}\n"
    f"Policy Number: {policy_number} for {policy_type}{vehicle_part} "
    f"expires on {formatted_date}. "
    f"{ending_text} Thank you! \n"
    "*Arihant Jewellers.*"
    )

    # First attempt after 1 minute (testing)
    next_try = (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")

    # -------------------------------
    # Insert reminders
    # -------------------------------
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


# -------------------------------
# Start scheduler ONCE
# -------------------------------
# if __name__ == "__main__":
#     start_scheduler()
#     app.run(debug=False, use_reloader=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False,use_reloader=False,host="0.0.0.0", port=port)


