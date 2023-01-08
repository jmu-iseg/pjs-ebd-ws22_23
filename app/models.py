from app import db, login
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    role = db.Column(db.String(20))
    password = db.Column(db.String(80), nullable=False)
    profilepic = db.Column(db.String(100))

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))