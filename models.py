from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class FavouriteFlight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    flight_number = db.Column(db.String(50))
    airline = db.Column(db.String(100))
    aircraft_type = db.Column(db.String(50))
    departure_airport = db.Column(db.String(50))
    arrival_airport = db.Column(db.String(50))



    
def __repr__(self):
        return f"{self.flight_number} ({self.airline}) from {self.departure_airport} to {self.arrival_airport}"