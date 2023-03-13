from app import db, login, bcrypt
from flask_login import UserMixin
import base64
from datetime import datetime, timedelta
import os

# Database model for an appointment
class Termin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dateTime = db.Column(db.DateTime)
    description = db.Column(db.String(2000))
    duration = db.Column(db.Float)
    energyconsumption = db.Column(db.Float)
    gridenergy = db.Column(db.Float)
    machines = db.Column(db.String(2000))
    employees = db.Column(db.String(2000))
    creationTimeUTC = db.Column(db.DateTime)

    # returns the string representation for an appointment
    def __repr__(self):
        return f'<Termin {self.id}>'

# Database model for website users
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    role = db.Column(db.String(20))
    password = db.Column(db.String(80), nullable=False)
    profilepic = db.Column(db.String(100))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # returns the string representation for a user
    def __repr__(self):
        return f'<User {self.username}>'

    # returns the dictionary representation for a user
    def to_dict(self):
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }
        return data

    # set a password for a user
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password)

    # check, if the password is correct
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # set user attributes from dictionary
    def from_dict(self, data, new_user=False):
        for field in ['username', 'role']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    # return token if a valid token exists or generate a token with a standard expiration of 1 hour
    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    # revoke the token
    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    # check, if the token is valid and return the user
    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

# login manager user loader
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))