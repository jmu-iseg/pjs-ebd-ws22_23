from flask import flash
from datetime import datetime, timedelta
import requests
import json
import os
from app import app

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

def get_weekday(day):
    if day == 0:
        return "So"
    elif day == 1:
        return "Mo"
    elif day == 2:
        return "Di"
    elif day == 3:
        return "Mi"
    elif day == 4:
        return "Do"
    elif day == 5:
        return "Fr"
    elif day == 6:
        return "Sa"
    else:
        return "Error"