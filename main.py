from flask import Flask, render_template, request, redirect, url_for, session
import requests
import sqlite3
from datetime import datetime
import csv
from io import StringIO
from flask import make_response

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ----------------- Database Setup -----------------
def init_db():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT,
                    currency TEXT,
                    amount REAL,
                    booked_rate REAL,
                    live_rate REAL,
                    mtm REAL,
                    hedge TEXT,
                    type TEXT,
                    date TEXT,
                    notes TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# ----------------- Helper: Get Live Rate -----------------
def get_live_rate(base_currency, target_currency):
    url = f"https://api.exchangerate.host/latest?base={base_currency}&symbols={target_currency}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['rates'].get(target_currency)
    return None

# ----------------- Routes -----------------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['email'] == 'admin@example.com' and request.form['password'] == 'password':
            session['user'] = request.form['email']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()
    return render_template('index.html', bookings=bookings)

@app.route('/add', methods=['POST'])
def add_booking():
    if 'user' not in session:
        return redirect(url_for('login'))

    client = request.form['client']
    currency = request.form['currency']
    amount = float(request.form['amount'])
    booked_rate = float(request.form['booked_rate'])
    hedge = request.form['hedge']
    fx_type = request.form['type']
    notes = request.form['notes']

    base_currency = currency
    target_currency = 'USD' if currency != 'USD' else 'EUR'
    live_rate = get_live_rate(base_currency, target_currency)
    if live_rate is None:
        return "Failed to fetch live rate"

    mtm = round((live_rate - booked_rate) * amount, 2)
    today = datetime.today().strftime('%Y-%m-%d')

    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO bookings (client, currency, amount, booked_rate, live_rate, mtm, hedge, type, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (client, currency, amount, booked_rate, live_rate, mtm, hedge, fx_type, today, notes))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reset')
def reset():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("DELETE FROM bookings")
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/download')
def download():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Client', 'Currency', 'Amount', 'Booked Rate', 'Live Rate', 'MTM', 'Hedge', 'Type', 'Date', 'Notes'])
    for b in bookings:
        cw.writerow(b[1:])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=bookings.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT currency, SUM(mtm) FROM bookings GROUP BY currency")
    data = c.fetchall()
    conn.close()
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    return render_template('charts.html', labels=labels, values=values)

if __name__ == '__main__':
    app.run(debug=True)
