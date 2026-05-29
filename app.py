import os
import functools
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "electricity-portal-secret-2025")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ─── Public Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    db = get_db()
    stats = {
        "customers": db.execute("SELECT COUNT(*) FROM Customer").fetchone()[0],
        "connections": db.execute("SELECT COUNT(*) FROM Connection").fetchone()[0],
        "complaints": db.execute("SELECT COUNT(*) FROM Complaint WHERE Status='Pending'").fetchone()[0],
        "outages": db.execute("SELECT COUNT(*) FROM Power_Outage WHERE Status='Active'").fetchone()[0],
    }
    outages = db.execute("""
        SELECT po.*, a.Area_Name, a.City FROM Power_Outage po
        JOIN Area a ON po.Area_Id = a.Area_Id
        WHERE po.Status = 'Active' ORDER BY po.Start_Time DESC LIMIT 5
    """).fetchall()
    db.close()
    return render_template("index.html", stats=stats, outages=outages)


@app.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    connection_types = db.execute("SELECT * FROM Connection_Type").fetchall()
    areas = db.execute("SELECT * FROM Area ORDER BY City, Area_Name").fetchall()
    meters = db.execute("SELECT * FROM Meter WHERE Status='Active' AND Meter_Id NOT IN (SELECT Meter_Id FROM Connection)").fetchall()

    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            cnic = request.form["cnic"].strip()
            phone = request.form["phone"].strip()
            email = request.form["email"].strip()
            street = request.form["street"].strip()
            city = request.form["city"].strip()
            postal = request.form["postal"].strip()
            conn_type = int(request.form["connection_type"])
            area_id = int(request.form["area"])
            load_kw = int(request.form["load"])
            meter_type = request.form["meter_type"]

            # Insert customer
            cur = db.execute("INSERT INTO Customer (Cust_Name, CNIC) VALUES (?,?)", (name, cnic))
            cust_id = cur.lastrowid

            # Contact
            db.execute("INSERT INTO Customer_Contact (Cust_Id, Phone, Email) VALUES (?,?,?)", (cust_id, phone, email))

            # Address
            cur2 = db.execute("INSERT INTO Address (Street, City, Postal_Code) VALUES (?,?,?)", (street, city, postal))
            addr_id = cur2.lastrowid
            db.execute("INSERT INTO Customer_Address (Cust_Id, Address_Id) VALUES (?,?)", (cust_id, addr_id))

            # New meter
            import random, string
            serial = "MTR" + "".join(random.choices(string.digits, k=6))
            cur3 = db.execute(
                "INSERT INTO Meter (Serial_No, Installation_Date, Meter_Type, Status) VALUES (?,?,?,'Active')",
                (serial, date.today().isoformat(), meter_type)
            )
            meter_id = cur3.lastrowid

            # Connection
            cur4 = db.execute(
                "INSERT INTO Connection (Cust_Id, Meter_Id, Connection_Type_Id, Load, Status) VALUES (?,?,?,?,'Active')",
                (cust_id, meter_id, conn_type, load_kw)
            )
            conn_id = cur4.lastrowid
            db.execute("INSERT INTO Connection_Area (Connection_Id, Area_Id) VALUES (?,?)", (conn_id, area_id))

            db.commit()
            flash(f"Registration successful! Your Customer ID is <strong>{cust_id}</strong> and Meter Serial is <strong>{serial}</strong>.", "success")
            db.close()
            return redirect(url_for("register"))
        except Exception as e:
            db.rollback()
            flash(f"Error: {str(e)}", "danger")

    db.close()
    return render_template("register.html", connection_types=connection_types, areas=areas, meters=meters)


@app.route("/complaint", methods=["GET", "POST"])
def complaint():
    db = get_db()
    if request.method == "POST":
        try:
            cnic = request.form["cnic"].strip()
            description = request.form["description"].strip()

            customer = db.execute("SELECT * FROM Customer WHERE CNIC=?", (cnic,)).fetchone()
            if not customer:
                flash("No customer found with that CNIC.", "danger")
            else:
                db.execute(
                    "INSERT INTO Complaint (Cust_Id, Description, Status, Date_Logged) VALUES (?,?,'Pending',?)",
                    (customer["Cust_Id"], description, date.today().isoformat())
                )
                db.commit()
                flash(f"Complaint submitted for {customer['Cust_Name']}. We will get back to you soon.", "success")
                db.close()
                return redirect(url_for("complaint"))
        except Exception as e:
            db.rollback()
            flash(f"Error: {str(e)}", "danger")

    db.close()
    return render_template("complaint.html")


@app.route("/bill-check", methods=["GET", "POST"])
def bill_check():
    db = get_db()
    bills = None
    customer = None
    if request.method == "POST":
        cnic = request.form["cnic"].strip()
        customer = db.execute("SELECT * FROM Customer WHERE CNIC=?", (cnic,)).fetchone()
        if customer:
            bills = db.execute("""
                SELECT b.*, p.Payment_Status, p.Amount_Paid, p.Payment_Date,
                       ct.Connection_Type_Name
                FROM Billing b
                JOIN Connection c ON b.Connection_Id = c.Connection_Id
                JOIN Connection_Type ct ON c.Connection_Type_Id = ct.Connection_Type_Id
                LEFT JOIN Payment p ON b.Bill_Id = p.Bill_Id
                WHERE c.Cust_Id = ?
                ORDER BY b.Issue_Date DESC
            """, (customer["Cust_Id"],)).fetchall()
        else:
            flash("No customer found with that CNIC.", "danger")
    db.close()
    return render_template("bill_check.html", bills=bills, customer=customer)


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid password.", "danger")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        "customers": db.execute("SELECT COUNT(*) FROM Customer").fetchone()[0],
        "meters": db.execute("SELECT COUNT(*) FROM Meter").fetchone()[0],
        "connections": db.execute("SELECT COUNT(*) FROM Connection").fetchone()[0],
        "bills": db.execute("SELECT COUNT(*) FROM Billing").fetchone()[0],
        "paid": db.execute("SELECT COUNT(*) FROM Payment WHERE Payment_Status='Paid'").fetchone()[0],
        "unpaid": db.execute("SELECT COUNT(*) FROM Payment WHERE Payment_Status='Unpaid'").fetchone()[0],
        "pending_complaints": db.execute("SELECT COUNT(*) FROM Complaint WHERE Status='Pending'").fetchone()[0],
        "revenue": db.execute("SELECT COALESCE(SUM(Amount_Paid),0) FROM Payment WHERE Payment_Status='Paid'").fetchone()[0],
    }
    recent_complaints = db.execute("""
        SELECT c.*, cu.Cust_Name FROM Complaint c
        JOIN Customer cu ON c.Cust_Id = cu.Cust_Id
        ORDER BY c.Date_Logged DESC LIMIT 5
    """).fetchall()
    db.close()
    return render_template("admin_dashboard.html", stats=stats, recent_complaints=recent_complaints)


def admin_table_route(table_name, template, query, *args):
    db = get_db()
    rows = db.execute(query).fetchall()
    db.close()
    return render_template(template, rows=rows)


@app.route("/admin/customers")
@login_required
def admin_customers():
    db = get_db()
    rows = db.execute("""
        SELECT c.*, cc.Phone, cc.Email, a.Street, a.City, a.Postal_Code
        FROM Customer c
        LEFT JOIN Customer_Contact cc ON c.Cust_Id = cc.Cust_Id
        LEFT JOIN Customer_Address ca ON c.Cust_Id = ca.Cust_Id
        LEFT JOIN Address a ON ca.Address_Id = a.Address_Id
        ORDER BY c.Cust_Id
    """).fetchall()
    db.close()
    return render_template("admin_table.html", rows=rows, title="Customers",
        columns=["ID","Name","CNIC","Phone","Email","Street","City","Postal Code"])


@app.route("/admin/meters")
@login_required
def admin_meters():
    db = get_db()
    rows = db.execute("SELECT * FROM Meter ORDER BY Meter_Id").fetchall()
    db.close()
    return render_template("admin_table.html", rows=rows, title="Meters",
        columns=["ID","Serial No","Installation Date","Type","Status"])


@app.route("/admin/connections")
@login_required
def admin_connections():
    db = get_db()
    rows = db.execute("""
        SELECT cn.Connection_Id, cu.Cust_Name, m.Serial_No, ct.Connection_Type_Name,
               cn.Load, cn.Status, ar.Area_Name, ar.City
        FROM Connection cn
        JOIN Customer cu ON cn.Cust_Id = cu.Cust_Id
        JOIN Meter m ON cn.Meter_Id = m.Meter_Id
        JOIN Connection_Type ct ON cn.Connection_Type_Id = ct.Connection_Type_Id
        LEFT JOIN Connection_Area ca ON cn.Connection_Id = ca.Connection_Id
        LEFT JOIN Area ar ON ca.Area_Id = ar.Area_Id
        ORDER BY cn.Connection_Id
    """).fetchall()
    db.close()
    return render_template("admin_table.html", rows=rows, title="Connections",
        columns=["ID","Customer","Meter Serial","Type","Load (kW)","Status","Area","City"])


@app.route("/admin/billing")
@login_required
def admin_billing():
    db = get_db()
    rows = db.execute("""
        SELECT b.Bill_Id, cu.Cust_Name, b.Billing_Month, b.Issue_Date, b.Due_Date,
               b.Units_Consumed, b.Total_Amount, p.Payment_Status, p.Amount_Paid
        FROM Billing b
        JOIN Connection cn ON b.Connection_Id = cn.Connection_Id
        JOIN Customer cu ON cn.Cust_Id = cu.Cust_Id
        LEFT JOIN Payment p ON b.Bill_Id = p.Bill_Id
        ORDER BY b.Issue_Date DESC
    """).fetchall()
    db.close()
    return render_template("admin_table.html", rows=rows, title="Billing & Payments",
        columns=["Bill ID","Customer","Month","Issue Date","Due Date","Units","Amount (PKR)","Payment Status","Amount Paid"])


@app.route("/admin/complaints")
@login_required
def admin_complaints():
    db = get_db()
    rows = db.execute("""
        SELECT c.Complaint_Id, cu.Cust_Name, e.Name AS Employee, c.Description,
               c.Status, c.Date_Logged
        FROM Complaint c
        JOIN Customer cu ON c.Cust_Id = cu.Cust_Id
        LEFT JOIN Employee e ON c.Employee_Id = e.Employee_Id
        ORDER BY c.Date_Logged DESC
    """).fetchall()
    db.close()
    return render_template("admin_complaints.html", rows=rows)


@app.route("/admin/complaints/<int:complaint_id>/resolve", methods=["POST"])
@login_required
def resolve_complaint(complaint_id):
    employee_id = request.form.get("employee_id")
    db = get_db()
    db.execute(
        "UPDATE Complaint SET Status='Resolved', Employee_Id=? WHERE Complaint_Id=?",
        (employee_id or None, complaint_id)
    )
    db.commit()
    db.close()
    flash("Complaint resolved.", "success")
    return redirect(url_for("admin_complaints"))


@app.route("/admin/outages")
@login_required
def admin_outages():
    db = get_db()
    rows = db.execute("""
        SELECT po.*, a.Area_Name, a.City FROM Power_Outage po
        JOIN Area a ON po.Area_Id = a.Area_Id
        ORDER BY po.Start_Time DESC
    """).fetchall()
    areas = db.execute("SELECT * FROM Area ORDER BY City, Area_Name").fetchall()
    db.close()
    return render_template("admin_outages.html", rows=rows, areas=areas)


@app.route("/admin/outages/add", methods=["POST"])
@login_required
def add_outage():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO Power_Outage (Area_Id, Start_Time, End_Time, Reason, Status) VALUES (?,?,?,?,?)",
            (request.form["area_id"], request.form["start_time"],
             request.form.get("end_time") or None, request.form["reason"], request.form["status"])
        )
        db.commit()
        flash("Outage added.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    db.close()
    return redirect(url_for("admin_outages"))


@app.route("/admin/employees")
@login_required
def admin_employees():
    db = get_db()
    rows = db.execute("""
        SELECT e.*, ec.Emp_Phone FROM Employee e
        LEFT JOIN Employee_Contact ec ON e.Employee_Id = ec.Employee_Id
        ORDER BY e.Employee_Id
    """).fetchall()
    db.close()
    return render_template("admin_table.html", rows=rows, title="Employees",
        columns=["ID","Name","Role","Department","Phone"])


@app.route("/admin/meter-readings")
@login_required
def admin_meter_readings():
    db = get_db()
    rows = db.execute("""
        SELECT mr.Reading_Id, m.Serial_No, e.Name AS Employee,
               mr.Reading_Date, mr.Units
        FROM Meter_Reading mr
        JOIN Meter m ON mr.Meter_Id = m.Meter_Id
        JOIN Employee e ON mr.Employee_Id = e.Employee_Id
        ORDER BY mr.Reading_Date DESC
    """).fetchall()
    meters = db.execute("SELECT * FROM Meter WHERE Status='Active'").fetchall()
    employees = db.execute("SELECT * FROM Employee").fetchall()
    db.close()
    return render_template("admin_readings.html", rows=rows, meters=meters, employees=employees)


@app.route("/admin/meter-readings/add", methods=["POST"])
@login_required
def add_reading():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO Meter_Reading (Meter_Id, Employee_Id, Reading_Date, Units) VALUES (?,?,?,?)",
            (request.form["meter_id"], request.form["employee_id"],
             request.form["reading_date"], request.form["units"])
        )
        db.commit()
        flash("Meter reading recorded.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    db.close()
    return redirect(url_for("admin_meter_readings"))


@app.route("/admin/tariffs")
@login_required
def admin_tariffs():
    db = get_db()
    rows = db.execute("""
        SELECT t.*, ct.Connection_Type_Name FROM Tariff t
        JOIN Connection_Type ct ON t.Connection_Type_Id = ct.Connection_Type_Id
    """).fetchall()
    connection_types = db.execute("SELECT * FROM Connection_Type").fetchall()
    db.close()
    return render_template("admin_tariffs.html", rows=rows, connection_types=connection_types)


@app.route("/admin/tariffs/update/<int:tariff_id>", methods=["POST"])
@login_required
def update_tariff(tariff_id):
    db = get_db()
    try:
        db.execute(
            "UPDATE Tariff SET Unit_Rate=?, Fixed_Charges=?, Tax_Percentage=? WHERE Tariff_Id=?",
            (request.form["unit_rate"], request.form["fixed_charges"],
             request.form["tax_percentage"], tariff_id)
        )
        db.commit()
        flash("Tariff updated.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    db.close()
    return redirect(url_for("admin_tariffs"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "false").lower() == "true")
