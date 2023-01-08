from flask import Flask, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import flask_login
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.init_app(app)
login.login_view = 'login'
bcrypt = Bcrypt(app)

@app.context_processor
def inject_userdata():
    values = {}
    if flask_login.current_user.is_authenticated != True:
        values['username'] = "NotLoggedIn"
        values['userrole'] = "NoRole"
        values['userid'] = "NoID"
        values['profilepic'] = 'img/img1234.jpg'
        return values
    else:
        values['username'] = flask_login.current_user.username
        values['userrole'] = flask_login.current_user.role
        values['userid'] = flask_login.current_user.id
        if flask_login.current_user.profilepic is None:
            values['profilepic'] = 'img/img1234.jpg'
        else:
            values['profilepic'] = flask_login.current_user.profilepic
        return values

def flash_errors(form):
    """Flashes form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Fehler im '%s' Feld - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

from app import routes, models, errors