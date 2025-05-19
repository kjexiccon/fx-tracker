from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import requests
from replit import db

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == 'admin@example.com' and password == 'admin':
            session['user'] = email
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/dashboard')
def index():
    if 'user' not in session:
        return redirect('/')
    bookings = []
    for key in db.keys():
        bookings.append(db[key])
    return render_template('index.html', bookings=bookings, user=session['user'])

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect('/')

    client = request.form.get('client')
    currency = request.form.get('currency')
    amount = float(request.form.get('amount'))
    booking_rate = float(request.form.get('booking_rate'))
    hedge = request.form.get('hedge')
    type_ = request.form.get('type')
    notes = request.form.get('notes')

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
        "hedge": hedge,
        "type": type_,
        "notes": notes,
        "date": str(datetime.now().date())
    }

    db[client + "_" + currency + "_" + str(datetime.now())] = data
    return redirect('/dashboard')

@app.route('/reset')
def reset():
    for key in list(db.keys()):
        del db[key]
    return redirect('/dashboard')

@app.route('/download')
def download():
    from flask import Response
    import csv
    output = "Client,Currency,Amount,Booked Rate,Live Rate,MTM,Hedge,Type,Date,Notes\n"
    for key in db.keys():
        b = db[key]
        row = f"{b['client']},{b['currency']},{b['amount']},{b['booking_rate']},{b['live_rate']},{b['mtm']},{b['hedge']},{b['type']},{b['date']},{b['notes']}"
        output += row + "\n"
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=bookings.csv"})

@app.route('/charts')
def charts():
    if 'user' not in session:
        return redirect('/')
    bookings = list(db.values())
    return render_template('charts.html', bookings=bookings)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
