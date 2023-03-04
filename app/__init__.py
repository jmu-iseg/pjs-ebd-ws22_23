from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import flask_login
from flask_bcrypt import Bcrypt
from app.helper import *

# Eigentliche Applikation mit Config (Datenhaltung)
app = Flask(__name__)
app.config.from_object(Config)
# Datenbankverbindung
db = SQLAlchemy(app)
# Datenbankmigrationen
migrate = Migrate(app, db)
# Login-Konzept
login = LoginManager(app)
login.init_app(app)
login.login_view = 'login'
# Passwortverschlüsselung
bcrypt = Bcrypt(app)

@app.context_processor
def inject_userdata():
    """Nutzerdaten global als Context_processor bereitstellen,
    damit diese auf jeder HTML Seite genutzt werden können.

    Returns:
        values: Dictionary mit Nutzername, Rolle, ID und Profilbild
    """
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

# importieren von API als Blueprint, da abgeschottete Funktionalität
from app.api import bp as api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# importieren von Routen, Models und Errors
from app import routes, models, errors