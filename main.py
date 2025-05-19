
from flask import Flask, render_template, request, redirect, Response, session
import requests
from datetime import datetime
from replit import db
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'fx-secret-key-123'  # Use a secure random key in production

# --- Static user setup ---
users = {
    "admin@example.com": {"password": "admin123", "role": "admin"},
    "client1@example.com": {"password": "client123", "role": "client"}
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and user['password'] == password:
            session['email'] = email
            session['role'] = user['role']
            return redirect('/dashboard')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/')
    current_user = session['email']
    role = session['role']
    bookings = []
    for key in db.keys():
        b = db[key]
        if role == "admin" or b['user'] == current_user:
            bookings.append(b)
    return render_template('index.html', bookings=bookings, user=current_user)

@app.route('/add', methods=['POST'])
def add():
    if 'email' not in session:
        return redirect('/')
    user = session['email']
    client = request.form['client']
    currency = request.form['currency'].upper()
    amount = float(request.form['amount'])
    booking_rate = float(request.form['booking_rate'])
    hedge_status = request.form['hedge_status']
    booking_type = request.form['booking_type']
    notes = request.form.get('notes', '')
    date = datetime.now().strftime("%Y-%m-%d")

    quote_currency = "USD" if currency != "USD" else "INR"
    api_url = f"https://api.frankfurter.app/latest?from={currency}&to={quote_currency}"

    try:
        res = requests.get(api_url)
        live_rate = res.json()['rates'][quote_currency]
    except Exception as e:
        print("API error:", e)
        return "Failed to fetch live rate"

    mtm = (live_rate - booking_rate) * amount
    mtm_color = "green" if mtm >= 0 else "red"

    record = {
        "user": user,
        "client": client,
        "currency": currency,
        "amount": amount,
        "booking_rate": booking_rate,
        "live_rate": round(live_rate, 4),
        "mtm": round(mtm, 2),
        "hedge_status": hedge_status,
        "booking_type": booking_type,
        "notes": notes,
        "date": date,
        "mtm_color": mtm_color,
        "timestamp": datetime.now().isoformat()
    }

    db[user + "_" + client + "_" + currency + "_" + date] = record
    return redirect('/dashboard')

@app.route('/download')
def download_csv():
    if 'email' not in session:
        return redirect('/')
    current_user = session['email']
    role = session['role']
    csv_data = "Client,Currency,Amount,Booking Rate,Live Rate,MTM,Hedge Status,Booking Type,Date,Notes\n"
    for key in db.keys():
        b = db[key]
        if role == "admin" or b["user"] == current_user:
            row = f"{b['client']},{b['currency']},{b['amount']},{b['booking_rate']},{b['live_rate']},{b['mtm']},{b['hedge_status']},{b['booking_type']},{b['date']},{b['notes']}"
            csv_data += row + "\n"
    return Response(csv_data, mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=bookings.csv"})

@app.route('/reset')
def reset_db():
    if 'email' not in session or session['role'] != 'admin':
        return redirect('/')
    for key in list(db.keys()):
        del db[key]
    return redirect('/dashboard')

@app.route('/charts')
def charts():
    if 'email' not in session:
        return redirect('/')
    current_user = session['email']
    role = session['role']
    mtm_by_currency = {}
    exposure_by_currency = {}
    trend_map = defaultdict(float)

    for key in db.keys():
        b = db[key]
        if role == "admin" or b["user"] == current_user:
            cur = b["currency"]
            mtm_by_currency[cur] = mtm_by_currency.get(cur, 0) + b["mtm"]
            exposure_by_currency[cur] = exposure_by_currency.get(cur, 0) + b["amount"]
            trend_map[b["date"]] += b["mtm"]

    mtm_trend = [{"date": d, "mtm": trend_map[d]} for d in sorted(trend_map)]
    return render_template("charts.html",
        mtm_by_currency=mtm_by_currency,
        exposure_by_currency=exposure_by_currency,
        mtm_trend=mtm_trend
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
