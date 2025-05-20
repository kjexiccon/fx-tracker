from flask import Flask, render_template, request, redirect, session, url_for
import requests
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
data = []

# Free API (no key needed)
def fetch_live_rate(base, symbol):
    try:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={symbol}"
        res = requests.get(url)
        return res.json()['rates'][symbol]
    except Exception as e:
        print("API error:", e)
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

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('index.html', data=data)

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect('/')

    try:
        client = request.form['client']
        currency = request.form['currency']
        amount = float(request.form['amount'])
        booked_rate = float(request.form['booked_rate'])
        hedge_status = request.form['hedge_status']
        trade_type = request.form['type']
        notes = request.form['notes']
        date = datetime.now().strftime('%Y-%m-%d')

        live_rate = fetch_live_rate(currency, 'INR')
        if live_rate is None:
            return "Failed to fetch live rate"

        mtm = round((live_rate - booked_rate) * amount, 2)
        if hedge_status == "Hedged":
            mtm = -abs(mtm)

        data.append({
            'client': client,
            'currency': currency,
            'amount': amount,
            'booked_rate': booked_rate,
            'live_rate': live_rate,
            'mtm': mtm,
            'hedge': hedge_status,
            'type': trade_type,
            'date': date,
            'notes': notes
        })
        return redirect('/dashboard')

    except Exception as e:
        print("Add Error:", e)
        return "Internal Error Occurred"

@app.route('/reset')
def reset():
    if 'user' not in session:
        return redirect('/')
    data.clear()
    return redirect('/dashboard')

@app.route('/download')
def download():
    if 'user' not in session:
        return redirect('/')
    output = [['Client', 'Currency', 'Amount', 'Booked Rate', 'Live Rate', 'MTM', 'Hedge', 'Type', 'Date', 'Notes']]
    for row in data:
        output.append([row[k] for k in output[0]])
    with open('bookings.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(output)
    return redirect('/dashboard')

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')
    return render_template('charts.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)
