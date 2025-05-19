from flask import Flask, render_template, request, redirect, session
import requests
import json
import os
from datetime import date

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for session login

DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# --- Login Page ---
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    email = request.form['email']
    password = request.form['password']

    if email == 'admin@example.com' and password == 'admin123':
        session['user'] = email
        return redirect('/dashboard')
    else:
        return render_template('login.html', error='Invalid credentials')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- Dashboard Page ---
@app.route('/dashboard')
def index():
    if 'user' not in session:
        return redirect('/')
    db = load_db()
    bookings = list(db.values())
    return render_template('index.html', bookings=bookings, user=session['user'])

# --- Add Booking ---
@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect('/')
    client = request.form['client']
    currency = request.form['currency'].upper()
    amount = float(request.form['amount'])
    booking_rate = float(request.form['booking_rate'])
    hedge_status = request.form['hedge']
    trade_type = request.form['type']
    notes = request.form.get('notes', '')

    # Get live rate
    try:
        api_url = f"https://api.exchangerate.host/latest?base={currency}&symbols=INR"
        res = requests.get(api_url)
        live_rate = res.json()['rates']['INR']
    except Exception as e:
        print("API error:", e)
        return "Failed to fetch live rate"

    mtm = (live_rate - booking_rate) * amount
    db = load_db()

    data = {
        "client": client,
        "currency": currency,
        "amount": amount,
        "booking_rate": booking_rate,
        "live_rate": round(live_rate, 4),
        "mtm": round(mtm, 2),
        "hedge": hedge_status,
        "type": trade_type,
        "date": str(date.today()),
        "notes": notes
    }

    key = client + "_" + currency + "_" + str(len(db) + 1)
    db[key] = data
    save_db(db)
    return redirect('/dashboard')

# --- Reset DB (Optional utility) ---
@app.route('/reset')
def reset_db():
    save_db({})
    return redirect('/dashboard')

# --- Download CSV ---
@app.route('/download')
def download():
    import csv
    from flask import Response
    db = load_db()
    bookings = list(db.values())

    def generate():
        data = bookings
        header = data[0].keys() if data else []
        yield ','.join(header) + '\n'
        for row in data:
            yield ','.join(str(row[h]) for h in header) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=fx_bookings.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
