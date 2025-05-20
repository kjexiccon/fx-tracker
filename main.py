from flask import Flask, render_template, request, redirect, session, url_for, make_response
import requests
import sqlite3
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------- Initialize Database ----------
def init_db():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
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
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- Free API: Frankfurter ----------
def get_live_rate(base_currency, target_currency):
    try:
        url = f"https://api.frankfurter.app/latest?from={base_currency}&to={target_currency}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target_currency)
    except Exception as e:
        print("Live rate error:", e)
    return None

# ---------- Routes ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@example.com' and password == 'password':
            session['user'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()
    return render_template('index.html', bookings=bookings)

@app.route('/add', methods=['POST'])
def add_booking():
    if 'user' not in session:
        return redirect('/')

    client = request.form['client']
    currency = request.form['currency']
    amount = float(request.form['amount'])
    booked_rate = float(request.form['booked_rate'])
    hedge = request.form['hedge']
    fx_type = request.form['type']
    notes = request.form['notes']
    today = datetime.today().strftime('%Y-%m-%d')

    # Convert from selected currency to INR
    live_rate = get_live_rate(currency, 'INR')
    if not live_rate:
        return "Failed to fetch live rate"

    mtm = round((live_rate - booked_rate) * amount, 2)

    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("""INSERT INTO bookings 
        (client, currency, amount, booked_rate, live_rate, mtm, hedge, type, date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client, currency, amount, booked_rate, live_rate, mtm, hedge, fx_type, today, notes)
    )
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/reset')
def reset():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("DELETE FROM bookings")
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/download')
def download():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Client', 'Currency', 'Amount', 'Booked Rate', 'Live Rate', 'MTM', 'Hedge', 'Type', 'Date', 'Notes'])
    for b in bookings:
        writer.writerow(b[1:])
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=bookings.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT currency, SUM(mtm) FROM bookings GROUP BY currency")
    result = c.fetchall()
    conn.close()

    labels = [r[0] for r in result]
    values = [r[1] for r in result]
    return render_template('charts.html', labels=labels, values=values)

if __name__ == '__main__':
    app.run(debug=True)
