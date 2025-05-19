from flask import Flask, render_template, request, redirect, session
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # required for sessions

# Temporary in-memory database
db = {}

# Hardcoded login credentials
USER_EMAIL = 'admin@example.com'
USER_PASSWORD = 'admin123'

@app.route('/', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/', methods=['POST'])
def do_login():
    email = request.form.get('email')
    password = request.form.get('password')
    if email == USER_EMAIL and password == USER_PASSWORD:
        session['user'] = email
        return redirect('/dashboard')
    else:
        return render_template('login.html', error='Invalid credentials')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user' not in session:
        return redirect('/')
    
    bookings = []
    for key in db.keys():
        bookings.append(db[key])
    
    return render_template('index.html', bookings=bookings)

@app.route('/add', methods=['POST'])
def add_booking():
    if 'user' not in session:
        return redirect('/')
    
    client = request.form['client']
    currency = request.form['currency'].upper()
    amount = float(request.form['amount'])
    booking_rate = float(request.form['booking_rate'])
    type_ = request.form.get('type', 'Export')
    notes = request.form.get('notes', '')
    hedge = request.form.get('hedge', 'Unhedged')

    # Fetch live rate
    api_url = f"https://api.exchangerate.host/latest?base={currency}&symbols=INR"
    try:
        res = requests.get(api_url)
        live_rate = res.json()['rates']['INR']
    except Exception as e:
        print("API error:", e)
        return "Failed to fetch live rate"

    mtm = (live_rate - booking_rate) * amount
    data = {
        "client": client,
        "currency": currency,
        "amount": amount,
        "booking_rate": booking_rate,
        "live_rate": round(live_rate, 4),
        "mtm": round(mtm, 2),
        "type": type_,
        "notes": notes,
        "hedge": hedge,
        "date": str(datetime.now().date())
    }

    key = client + "_" + currency + "_" + str(datetime.now())
    db[key] = data

    return redirect('/dashboard')

@app.route('/reset', methods=['POST'])
def reset():
    if 'user' not in session:
        return redirect('/')
    
    db.clear()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')
    
    bookings = list(db.values())
    return render_template('charts.html', bookings=bookings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
