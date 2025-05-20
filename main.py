
from flask import Flask, render_template, request, redirect, session, url_for, make_response
import requests
import sqlite3
import uuid
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secure_key'

# Initialize or upgrade the database schema
def init_db():
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            client TEXT,
            buy_currency TEXT,
            sell_currency TEXT,
            amount REAL,
            booked_rate REAL,
            forward_rate REAL,
            mtm REAL,
            hedge TEXT,
            type TEXT,
            trade_date TEXT,
            maturity_date TEXT,
            option_start TEXT,
            option_end TEXT,
            notes TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_live_rate(base_currency, target_currency):
    try:
        url = f"https://api.frankfurter.app/latest?from={base_currency}&to={target_currency}"
        res = requests.get(url)
        data = res.json()
        return data['rates'][target_currency]
    except Exception as e:
        print("Live rate fetch error:", e)
        return None

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['email'] == 'admin@example.com' and request.form['password'] == 'password':
            session['user'] = request.form['email']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    rows = c.fetchall()
    conn.close()
    return render_template('index.html', bookings=rows)

@app.route('/add', methods=['POST'])
def add_booking():
    if 'user' not in session:
        return redirect('/')

    try:
        client = request.form['client']
        buy_currency = request.form['buy_currency']
        sell_currency = request.form['sell_currency']
        amount = float(request.form['amount'])
        booked_rate = float(request.form['booked_rate'])
        hedge = request.form['hedge']
        trade_type = request.form['type']
        trade_date = request.form['trade_date']
        maturity_date = request.form['maturity_date']
        option_start = request.form.get('option_start') or ''
        option_end = request.form.get('option_end') or ''
        notes = request.form['notes']
        trade_id = str(uuid.uuid4())
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        live_rate = get_live_rate(buy_currency, sell_currency)
        if live_rate is None:
            return "Failed to fetch live rate."

        forward_rate = round(live_rate * 1.0025, 6)  # Simulated forward rate
        mtm = round((forward_rate - booked_rate) * amount, 2)

        conn = sqlite3.connect('fx_tracker.db')
        c = conn.cursor()
        c.execute('''INSERT INTO bookings (
            id, client, buy_currency, sell_currency, amount, booked_rate,
            forward_rate, mtm, hedge, type, trade_date, maturity_date,
            option_start, option_end, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            trade_id, client, buy_currency, sell_currency, amount, booked_rate,
            forward_rate, mtm, hedge, trade_type, trade_date, maturity_date,
            option_start, option_end, notes, created_at
        ))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    except Exception as e:
        return f"Internal Error: {str(e)}"

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
    rows = c.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Client', 'Buy Currency', 'Sell Currency', 'Amount', 'Booked Rate', 'Forward Rate',
                     'MTM', 'Hedge', 'Type', 'Trade Date', 'Maturity Date', 'Option Start', 'Option End', 'Notes', 'Created At'])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=fx_bookings.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')
    conn = sqlite3.connect('fx_tracker.db')
    c = conn.cursor()
    c.execute("SELECT sell_currency, SUM(mtm) FROM bookings GROUP BY sell_currency")
    data = c.fetchall()
    conn.close()
    labels = [r[0] for r in data]
    values = [r[1] for r in data]
    return render_template('charts.html', labels=labels, values=values)

if __name__ == '__main__':
    app.run(debug=True)
