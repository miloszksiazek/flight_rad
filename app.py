from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, FavouriteFlight, FlightAlert
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajnyklucz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create the database
with app.app_context():
    db.create_all()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    flights = []
    if request.method == 'POST':
        url = 'https://opensky-network.org/api/states/all'
        try:
            response = requests.get(url, timeout=10)
            data = response.json() if response.status_code == 200 else {}
        except Exception as e:
            print("Error fetching data from OpenSky:", e)
            data = {}

        for flight_data in data.get('states', [])[:30]:
            flight_number = flight_data[1].strip() if flight_data[1] else "N/A"
            origin_country = flight_data[2] or "N/A"
            altitude = flight_data[13] if flight_data[13] else "N/A"
            speed = flight_data[9] if flight_data[9] else "N/A"
            on_ground = "Yes" if flight_data[8] else "No"

            flight = {
                'flight_number': flight_number,
                'origin_country': origin_country,
                'altitude': altitude,
                'speed': speed,
                'on_ground': on_ground
            }
            flights.append(flight)

    from models import FlightAlert
    pending_alerts = FlightAlert.query.filter_by(user_id=current_user.id, triggered=False).all()

    return render_template('home.html', flights=flights, pending_alerts=pending_alerts)

@app.route('/add_favourite', methods=['POST'])
@login_required
def add_favourite():
    flight_number = request.form['flight_number']
    airline = request.form['airline']
    aircraft_type = request.form['aircraft_type']
    departure_airport = request.form['departure_airport']
    arrival_airport = request.form['arrival_airport']

    favourite = FavouriteFlight(
        user_id=current_user.id,
        flight_number=flight_number,
        airline=airline,
        aircraft_type=aircraft_type,
        departure_airport=departure_airport,
        arrival_airport=arrival_airport
    )
    db.session.add(favourite)
    db.session.commit()

    return redirect(url_for('home'))

@app.route('/favourites', methods=['GET', 'POST'])
@login_required
def favourites():
    favs = FavouriteFlight.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        url = 'https://opensky-network.org/api/states/all'
        response = requests.get(url).json()

        for favourite in favs:
            for flight_data in response.get('states', []):
                if flight_data[1] and flight_data[1].strip() == favourite.flight_number:
                    favourite.aircraft_type = flight_data[13] if flight_data[13] else "N/A"  # Altitude
                    favourite.departure_airport = flight_data[9] if flight_data[9] else "N/A"  # Speed
                    favourite.arrival_airport = "Yes" if flight_data[8] else "No"  # On Ground
                    break

        db.session.commit()
        favs = FavouriteFlight.query.filter_by(user_id=current_user.id).all()

    return render_template('favourites.html', favourites=favs)

@app.route('/remove_favourite', methods=['POST'])
@login_required
def remove_favourite():
    flight_number = request.form['flight_number']

    favourite = FavouriteFlight.query.filter_by(
        user_id=current_user.id,
        flight_number=flight_number
    ).first()

    if favourite:
        db.session.delete(favourite)
        db.session.commit()

    return redirect(url_for('home'))

@app.route('/alerts', methods=['GET', 'POST'])
@login_required
def alerts():
    # Handle alert creation
    if request.method == 'POST':
        flight_number = request.form['flight_number']
        condition_type = request.form['condition_type']
        threshold = request.form['threshold']

        new_alert = FlightAlert(
            user_id=current_user.id,
            flight_number=flight_number,
            condition_type=condition_type,
            threshold=threshold,
            triggered=False
        )
        db.session.add(new_alert)
        db.session.commit()

        return redirect(url_for('alerts'))

    # Get all user's alerts
    user_alerts = FlightAlert.query.filter_by(user_id=current_user.id).all()

    # Fetch live data from OpenSky API
    url = 'https://opensky-network.org/api/states/all'
    response = requests.get(url).json()
    flights = response.get('states', [])

    for alert in user_alerts:
        if alert.triggered:
            continue

        for flight_data in flights:
            callsign = flight_data[1].strip() if flight_data[1] else None
            if callsign == alert.flight_number:
                if alert.condition_type == "altitude_below":
                    altitude = flight_data[13]
                    if altitude is not None and float(altitude) < float(alert.threshold):
                        alert.triggered = True
                elif alert.condition_type == "on_ground":
                    if flight_data[8]:  # On ground is True
                        alert.triggered = True
                break  # No need to check more flights once matched

    db.session.commit()
    return render_template('alerts.html', alerts=user_alerts)


if __name__ == '__main__':
    app.run(debug=True)