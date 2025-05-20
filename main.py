from flask import Flask, render_template, request, redirect, session, send_file
import csv
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB = []

def get_live_rate(currency):
    try:
        response = requests.get(f"https://api.exchangerate.host/latest?base={currency}&symbols=INR")
        data = response.json()
        return data["rates"]["INR"]
    except Exception as e:
        print("Live rate fetch failed:", e)
        return None

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
    return render_template('login.html', error="Invalid credentials")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('index.html', data=DB)

@app.route('/add', methods=['POST'])
def add_booking():
    if 'user' not in session:
        return redirect('/')
    try:
        client = request.form['client']
        currency = request.form['currency']
        amount = float(request.form['amount'])
        booked_rate = float(request.form['booked_rate'])
        hedge = request.form['hedge']
        trade_type = request.form['type']
        notes = request.form['notes']
        live_rate = get_live_rate(currency)
        if not live_rate:
            return "Failed to fetch live rate"

        mtm = round((live_rate - booked_rate) * amount, 2)
        DB.append({
            "client": client,
            "currency": currency,
            "amount": amount,
            "booked_rate": booked_rate,
            "live_rate": live_rate,
            "mtm": mtm,
            "hedge": hedge,
            "type": trade_type,
            "date": datetime.today().strftime('%Y-%m-%d'),
            "notes": notes
        })
        return redirect('/dashboard')
    except Exception as e:
        return f"Internal Server Error: {e}"

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')
    return render_template('charts.html', data=DB)

@app.route('/reset')
def reset():
    DB.clear()
    return redirect('/dashboard')

@app.route('/download')
def download():
    filename = "bookings.csv"
    keys = ["client", "currency", "amount", "booked_rate", "live_rate", "mtm", "hedge", "type", "date", "notes"]
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(DB)
    return send_file(filename, as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')
