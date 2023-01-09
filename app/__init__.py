from flask import Flask, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import flask_login
from flask_bcrypt import Bcrypt
import json
import requests
from datetime import datetime, timedelta
import os

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
            flash(u"Fehler im Feld '%s' - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

def get_graph_params():
    with open(os.path.join(app.root_path, 'graph_settings.json'), 'r') as openfile:
        params = json.load(openfile)

    if not ('token' in params and 'expiry' in params and datetime.utcnow() < datetime.strptime(params['expiry'], "%m/%d/%Y, %H:%M:%S")):
        headers = {
            'Host': 'login.microsoftonline.com',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = {
            'client_id': params['client'],
            'scope': 'https://graph.microsoft.com/.default',
            'client_secret': params['secret'],
            'grant_type': 'client_credentials'
        }
        resp = requests.post(f"https://login.microsoftonline.com/{params['tenant']}/oauth2/v2.0/token", headers=headers, data=body).json()
        params['token'] = f"Bearer {resp['access_token']}"
        params['expiry'] = (datetime.utcnow() + timedelta(seconds=(resp['expires_in']) - 120)).strftime("%m/%d/%Y, %H:%M:%S")
        with open(os.path.join(app.root_path, 'graph_settings.json'), 'w') as outfile:
            json.dump(params, outfile)

    return params

from app import routes, models, errors