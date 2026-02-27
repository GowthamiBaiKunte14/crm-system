from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pandas as pd
import requests
from datetime import datetime, date, timezone
from dotenv import load_dotenv

load_dotenv()
FACEBOOK_PAGE_TOKEN = os.getenv("EAATFHK5PY1wBQ6TJQNASpwZBoi3Ev8BvbBx1TS7uvxXIZB30T8zrrQBJYv9z2MQw1rJX5ZAaC75HEZChbuvTnmEJYavQ0ZCr4dZAledueQZBWZB5NO9YxNhPUqCDZB50LUoQqvmdQqFSxtenf3j39r2eBgQhUgRUaYNPL5ZA0TzeNvVZB32jyF1clRjsUpCXaZAygbbe1NR5nAZDZD")

def init_db():
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

# ================= ENV VARIABLES =================


def send_whatsapp_message(phone, name="Customer"):

    url = f"https://graph.facebook.com/v22.0/{os.getenv('PHONE_NUMBER_ID')}/messages"

    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "campaign_offer",   # ✅ NEW TEMPLATE
            "language": {
                "code": "en"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": name
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, json=data, headers=headers)

    print(response.json())   # debugging
    return response.json()

import sqlite3

def send_bulk_whatsapp():

    leads = Lead.query.all()   # ✅ using SQLAlchemy

    total_sent = 0

    for lead in leads:
        if lead.phone:
            name = lead.name if lead.name else "Customer"
            send_whatsapp_message(lead.phone, name)
            total_sent += 1

    return total_sent

# ========================
# APP CONFIG
# ========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "crm.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ========================
# MODELS
# ========================
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    is_approved = db.Column(db.Boolean, default=False)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default="New")
    assigned_to = db.Column(db.Integer, db.ForeignKey("employee.id"))
    notes = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    source = db.Column(db.String(50), default="Manual")
    platform = db.Column(db.String(20), default="WhatsApp")
    facebook_psid = db.Column(db.String(100))
    instagram_id = db.Column(db.String(100))

class MessageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer)
    employee_id = db.Column(db.Integer)
    message = db.Column(db.String(500))
    status = db.Column(db.String(50))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

FACEBOOK_PAGE_TOKEN = "EAAWM2lvTXGQBQp5GdyyiKfE7Q4wC8i4zfeTXYZBcaj0QyJQN842ZBxxcEAqAAYnRgUaoImZApZA7l1lR2ZBRHJ5QzgVfp4SqhCrQZAuWVBq8ZA9VWZAGsQIhhLxNZBrZC4pnh2KRJ2v6zoU0jJTgRTCNZBce5MVD7S4dWdIXfkUtdxw3sJoZBc8sk062yWhVjyTxA96iZAfdpdLfMsbwS1in1RvED45LnF4vPfLhyuQWUNb9zWUhEeJ6F2gZAXnM7uT0R4XAl1rh5DAN22ZCw9sFZBZAEimUyZAwsZD"

def send_facebook_message(psid, message):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FACEBOOK_PAGE_TOKEN}"

    data = {
        "recipient": {"id": psid},
        "message": {"text": message}
    }

    res = requests.post(url, json=data)
    print("Facebook response:", res.text)
    return res.json()

def send_instagram_message(ig_id, message):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FACEBOOK_PAGE_TOKEN}"

    data = {
        "recipient": {"id": ig_id},
        "message": {"text": message}
    }

    res = requests.post(url, json=data)
    print("Instagram response:", res.text)
    return res.json()


# ========================
# HOME
# ========================
@app.route("/")
def home():
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))
    if "employee_id" in session:
        return redirect(url_for("employee_dashboard"))
    return render_template("index.html")

@app.route("/test_whatsapp")
def test_whatsapp():

    result = send_whatsapp_message("918688598058")

    return str(result)

# ========================
# ADMIN LOGIN
# ========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session["admin_id"] = admin.id
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials")

    return render_template("admin/admin_login.html")


# ========================
# ADMIN DASHBOARD
# ========================
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    total_leads = Lead.query.count()
    converted_leads = Lead.query.filter_by(status="Converted").count()
    total_messages = MessageLog.query.count()

    employees = Employee.query.filter_by(is_approved=True).all()

    emp_names = []
    emp_counts = []

    for emp in employees:
        count = Lead.query.filter_by(
            assigned_to=emp.id,
            status="Converted"
        ).count()
        emp_names.append(emp.name)
        emp_counts.append(count)

    statuses = ["New", "Contacted", "Follow-up", "Converted", "Lost"]
    status_counts = [
        Lead.query.filter_by(status=s).count() for s in statuses
    ]

    pending_employees = Employee.query.filter_by(is_approved=False).all()

    return render_template(
        "admin/admin_dashboard.html",
        total_leads=total_leads,
        converted_leads=converted_leads,
        total_messages=total_messages,
        employees=pending_employees,
        emp_names=emp_names,
        emp_counts=emp_counts,
        statuses=statuses,
        status_counts=status_counts
    )

@app.route("/admin/employees")
def admin_employees():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    employees = Employee.query.all()
    data = []

    for emp in employees:
        total = Lead.query.filter_by(assigned_to=emp.id).count()
        converted = Lead.query.filter_by(
            assigned_to=emp.id,
            status="Converted"
        ).count()

        data.append({
            "id": emp.id,
            "name": emp.name,
            "email": emp.email,
            "approved": emp.is_approved,
            "total": total,
            "converted": converted
        })

    return render_template("admin/admin_employees.html", data=data)

@app.route("/admin/performance")
def admin_performance():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    employees = Employee.query.filter_by(is_approved=True).all()
    data = []

    for emp in employees:
        total = Lead.query.filter_by(assigned_to=emp.id).count()
        converted = Lead.query.filter_by(
            assigned_to=emp.id,
            status="Converted"
        ).count()

        rate = (converted / total * 100) if total > 0 else 0

        data.append({
            "name": emp.name,
            "total": total,
            "converted": converted,
            "rate": round(rate, 1)
        })

    return render_template("admin/admin_performance.html", data=data)

@app.route("/admin/source-report")
def source_report():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    sources = ["Manual", "Excel", "Facebook", "Instagram"]
    report = []

    for src in sources:
        count = Lead.query.filter_by(source=src).count()
        report.append({
            "source": src,
            "count": count
        })

    return render_template("source_report.html", report=report)

@app.route("/admin/send_campaign", methods=["POST"])
def send_campaign():

    total_sent = send_bulk_whatsapp()
    flash(f"{total_sent} WhatsApp messages sent!")
    return redirect(url_for("admin_dashboard"))

# ========================
# EMPLOYEE APPROVAL
# ========================
@app.route("/approve/<int:emp_id>")
def approve_employee(emp_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    emp = Employee.query.get(emp_id)
    if emp:
        emp.is_approved = True
        db.session.commit()

    return redirect(url_for("admin_dashboard"))


# ========================
# EMPLOYEE SIGNUP
# ========================
@app.route("/employee/signup", methods=["GET", "POST"])
def employee_signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        if Employee.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("employee_login"))

        emp = Employee(name=name, email=email, password=password)
        db.session.add(emp)
        db.session.commit()

        flash("Signup successful. Wait for approval.")
        return redirect(url_for("employee_login"))

    return render_template("employee/employee_signup.html")


# ========================
# EMPLOYEE LOGIN
# ========================
@app.route("/employee/login", methods=["GET", "POST"])
def employee_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        emp = Employee.query.filter_by(email=email).first()

        if emp and check_password_hash(emp.password, password):
            if not emp.is_approved:
                flash("Not approved yet")
                return redirect(url_for("employee_login"))

            session["employee_id"] = emp.id
            return redirect(url_for("employee_dashboard"))
        else:
            flash("Invalid credentials")

    return render_template("employee/employee_login.html")


# ========================
# EMPLOYEE DASHBOARD
# ========================
@app.route("/employee/dashboard")
def employee_dashboard():
    if "employee_id" not in session:
        return redirect(url_for("employee_login"))

    emp_id = session["employee_id"]
    today = date.today()

    followups = Lead.query.filter_by(
        assigned_to=emp_id,
        follow_up_date=today
    ).all()

    return render_template("employee/employee_dashboard.html", followups=followups)

# ========================
# EMPLOYEE LEADS
# ========================
@app.route("/employee/leads")
def employee_leads():
    if "employee_id" not in session:
        return redirect(url_for("employee_login"))

    emp_id = session["employee_id"]
    leads = Lead.query.filter_by(assigned_to=emp_id).all()

    return render_template("employee/employee_leads.html", leads=leads)


@app.route("/employee/update_lead/<int:lead_id>", methods=["POST"])
def update_lead(lead_id):
    if "employee_id" not in session:
        return redirect(url_for("employee_login"))

    lead = Lead.query.get(lead_id)
    if lead:
        lead.status = request.form["status"]
        db.session.commit()

    return redirect(url_for("employee_leads"))


# ========================
# EMPLOYEE SEND MESSAGE
# ========================
@app.route("/employee/send_message", methods=["POST"])
def employee_send_message():
    if "employee_id" not in session:
        return redirect(url_for("employee_login"))

    emp_id = session["employee_id"]
    lead_ids = request.form.getlist("lead_ids")
    message = request.form["message"]

    print("Selected leads:", lead_ids)  # debug line

    for lead_id in lead_ids:
        lead = Lead.query.get(int(lead_id))
        if lead:
            status = "Failed"   # default status

            if lead.platform == "WhatsApp":
                result = send_whatsapp_message(lead.phone, message)
                status = result.get("status", "Sent")

            elif lead.platform == "Facebook":
                result = send_facebook_message(lead.phone, message)
                status = result.get("status", "Sent")

            elif lead.platform == "Instagram":
                result = send_instagram_message(lead.phone, message)
                status = result.get("status", "Sent")

            log = MessageLog(
                lead_id=lead.id,
                employee_id=emp_id,
                message=message,
                status=status,
                sent_at=datetime.utcnow()
            )
            db.session.add(log)

    db.session.commit()
    flash("Bulk message process completed")
    return redirect(url_for("employee_leads"))

@app.route("/employee/messages")
def employee_messages():
    if "employee_id" not in session:
        return redirect(url_for("employee_login"))

    emp_id = session["employee_id"]

    logs = MessageLog.query.filter_by(
        employee_id=emp_id
    ).order_by(MessageLog.sent_at.desc()).all()

    return render_template("employee/employee_messages.html", logs=logs)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    VERIFY_TOKEN = "crm_verify"

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed"

    data = request.json
    print("Incoming:", data)

    return "EVENT_RECEIVED", 200
# ========================
# ADMIN LEADS
# ========================
@app.route("/admin/leads")
def view_leads():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    leads = Lead.query.all()
    employees = Employee.query.filter_by(is_approved=True).all()

    return render_template(
        "admin/admin_leads.html",
        leads=leads,
        employees=employees
    )


@app.route("/admin/add_lead", methods=["GET", "POST"])
def add_lead():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    employees = Employee.query.filter_by(is_approved=True).all()

    if request.method == "POST":
        lead = Lead(
            name=request.form["name"],
            phone=request.form["phone"],
            assigned_to=request.form.get("assigned_to"),
            source=request.form.get("source", "Manual")
        )
        db.session.add(lead)
        db.session.commit()
        return redirect(url_for("view_leads"))

    return render_template("admin/add_lead.html", employees=employees)

@app.route("/admin/delete_lead/<int:lead_id>")
def delete_lead(lead_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    lead = db.session.get(Lead, lead_id)

    if lead:
        db.session.delete(lead)
        db.session.commit()
        flash("Lead deleted successfully")

    return redirect(url_for("view_leads"))

@app.route("/admin/assign_leads", methods=["POST"])
def assign_leads():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    lead_ids = request.form.getlist("lead_ids")
    employee_id = request.form.get("employee_id")

    if not lead_ids:
        flash("No leads selected")
        return redirect(url_for("view_leads"))

    if not employee_id:
        flash("Please select an employee")
        return redirect(url_for("view_leads"))

    for lid in lead_ids:
        lead = db.session.get(Lead, int(lid))
        if lead:
            lead.assigned_to = int(employee_id)

    db.session.commit()
    flash("Leads assigned successfully")

    return redirect(url_for("view_leads"))

@app.route("/admin/delete_selected", methods=["POST"])
def delete_selected():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    lead_ids = request.form.getlist("lead_ids")

    if not lead_ids:
        flash("No leads selected")
        return redirect(url_for("view_leads"))

    for lid in lead_ids:
        lead = db.session.get(Lead, int(lid))
        if lead:
            db.session.delete(lead)

    db.session.commit()
    flash("Selected leads deleted successfully")

    return redirect(url_for("view_leads"))

# ========================
# EXCEL UPLOAD
# ========================
@app.route("/admin/upload", methods=["GET", "POST"])
def upload_leads():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        file = request.files["file"]
        if file:
            df = pd.read_excel(file)

            # clean column names
            df.columns = df.columns.str.strip().str.lower()

            # possible column variations
            name_col = None
            phone_col = None

            for col in df.columns:
                if "name" in col:
                    name_col = col
                if "phone" in col or "mobile" in col:
                    phone_col = col

            if not name_col or not phone_col:
                flash("Excel must contain Name and Phone columns")
                return redirect(url_for("upload_leads"))

            for _, row in df.iterrows():
                lead = Lead(
                    name=str(row[name_col]),
                    phone=str(row[phone_col]),
                    source="Excel"
                )
                db.session.add(lead)

            db.session.commit()
            flash("Leads uploaded successfully")

    return render_template("admin/upload.html")

@app.route("/check_tables")
def check_tables():
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    conn.close()
    return str(tables)

@app.route("/check_columns")
def check_columns():
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()

    columns = cursor.execute("PRAGMA table_info(leads);").fetchall()

    conn.close()
    return str(columns)

# ========================
# LOGOUT
# ========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ========================
# INIT DB
# ========================
init_db()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not Admin.query.first():
            admin = Admin(
                username="admin",
                password=generate_password_hash("admin123")
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)


