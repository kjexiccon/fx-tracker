from flask import Flask, render_template, request, redirect, session
from flask import send_file
from datetime import datetime
from io import StringIO
import csv
import requests

app = Flask(__name__)
app.secret_key = "secure-key"
db = {}

# Static login for simplicity
users = {"admin@example.com": "admin123"}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if email in users and users[email] == password:
            session["user"] = email
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    bookings = list(db.values())
    return render_template("index.html", bookings=bookings, user=session["user"])

@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return redirect("/")
    
    try:
        client = request.form["client"]
        currency = request.form["currency"].upper()
        amount = float(request.form["amount"])
        booked_rate = float(request.form["booking_rate"])
        hedge = request.form["hedge"]
        tx_type = request.form["type"]
        notes = request.form["notes"]
        date = datetime.now().strftime("%Y-%m-%d")

        # Fetch live FX rate from exchangerate.host
        fx_url = f"https://api.exchangerate.host/latest?base={currency}&symbols=USD"
        response = requests.get(fx_url)
        data = response.json()

        if not data.get("success", True):
            return "Failed to fetch live rate"

        live_rate = data["rates"]["USD"]
        mtm = round((live_rate - booked_rate) * amount, 2)

        entry = {
            "client": client,
            "currency": currency,
            "amount": amount,
            "booked_rate": booked_rate,
            "live_rate": live_rate,
            "mtm": mtm,
            "hedge": hedge,
            "type": tx_type,
            "date": date,
            "notes": notes
        }

        db[len(db)] = entry
        return redirect("/dashboard")

    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/reset")
def reset():
    db.clear()
    return redirect("/dashboard")

@app.route("/download")
def download():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Client", "Currency", "Amount", "Booked Rate", "Live Rate", "MTM", "Hedge", "Type", "Date", "Notes"])
    for entry in db.values():
        cw.writerow([
            entry["client"],
            entry["currency"],
            entry["amount"],
            entry["booked_rate"],
            entry["live_rate"],
            entry["mtm"],
            entry["hedge"],
            entry["type"],
            entry["date"],
            entry["notes"]
        ])
    si.seek(0)
    return send_file(StringIO(si.getvalue()), mimetype="text/csv", download_name="bookings.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
