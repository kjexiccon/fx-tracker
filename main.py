from flask import Flask, render_template, request, redirect, url_for
from replit import db
from datetime import datetime

app = Flask(__name__)

# Login credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        # fetch and process form fields
        client = request.form.get('client')
        currency = request.form.get('currency').upper()
        amount = float(request.form.get('amount'))
        booking_rate = float(request.form.get('booking_rate'))
        hedge_status = request.form.get('hedge')
        notes = request.form.get('notes')
        booking_type = request.form.get('type')
        date = datetime.now().strftime('%Y-%m-%d')

        try:
            import requests
            res = requests.get(f'https://api.exchangerate.host/latest?base={currency}&symbols=INR')
            live_rate = res.json()['rates']['INR']
        except:
            live_rate = 0.0

        mtm = round((live_rate - booking_rate) * amount, 2)

        data = {
            "client": client,
            "currency": currency,
            "amount": amount,
            "booking_rate": booking_rate,
            "live_rate": round(live_rate, 4),
            "mtm": mtm,
            "hedge": hedge_status,
            "type": booking_type,
            "date": date,
            "notes": notes
        }

        db[email_key(client, currency)] = data
        return redirect(url_for('dashboard'))

    bookings = [db[key] for key in db.keys() if db[key]]
    return render_template('index.html', bookings=bookings)

@app.route('/reset', methods=['POST'])
def reset():
    for key in list(db.keys()):
        del db[key]
    return redirect(url_for('dashboard'))

def email_key(client, currency):
    return f"{client}_{currency}"

if __name__ == '__main__':
    app.run(debug=True)
