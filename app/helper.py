from flask import flash
import os
import requests
import json
from datetime import datetime, timedelta
import configparser
from icalendar import Calendar, Event, vCalAddress, vText
import io
from asyncua import Client, Node, ua

def get_config(root_path):
    config = configparser.ConfigParser()
    config.read(os.path.join(root_path,'settings.cfg'), encoding='utf-8')
    return config

def write_config(root_path, config):
    with open(os.path.join(root_path,'settings.cfg'), 'w') as configfile:
        config.write(configfile)

def flash_errors(form):
    """Flashes form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Fehler im Feld '%s' - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

def get_weekday(day):
    if day == '0':
        return "So"
    elif day == '1':
        return "Mo"
    elif day == '2':
        return "Di"
    elif day == '3':
        return "Mi"
    elif day == '4':
        return "Do"
    elif day == '5':
        return "Fr"
    elif day == '6':
        return "Sa"
    else:
        return "Error"

def get_graph_params(root_path):
    with open(os.path.join(root_path, 'graph_settings.json'), 'r') as openfile:
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
        with open(os.path.join(root_path, 'graph_settings.json'), 'w') as outfile:
            json.dump(params, outfile)

    return params

def create_file_object(start, end, summary):
    cal = Calendar()
    event = Event()
    event.add('summary', summary)
    event.add('dtstart', start)
    event.add('dtend', end)
    organizer = vCalAddress('MAILTO:termine@pjs-termine.de')
    organizer.params['cn'] = vText('Hannes Metz')
    organizer.params['role'] = vText('CEO of Uni Wuerzburg') # ein Macher
    event['organizer'] = organizer
    event['location'] = vText('Würzburg, DE')
    cal.add_component(event)
    buf = io.BytesIO()
    buf.write(cal.to_ical())
    buf.seek(0)
    return buf

def opc_ua_sender(machine, value: str, root_path: str, terminDate: datetime):
    # get machine
    machine = machine

    """ Get the config values """
    # read settings
    config = get_config(root_path)

    # specify the OPC-UA config
    value_on = config['opcua']['value_on']
    value_off = config['opcua']['value_off']
    url1 = config['opcua']['url1']
    var1 = config['opcua']['var1']

    """ Check the OPC-UA status """
    # Connect to the OPC-UA server
    client = Client(url1)

    # Check connection to client 1
    try:
        # Connect to the OPC UA server
        client.connect()

        # Browse the address space and find the node you want to write to
        root = client.get_root_node()
        myvar = root.get_child(["0:Objects", "2:MyObject", "2:MyVariable"])

        # Write data to the node
        myvar.set_value(value_on)

        # Check if client 1 is connected
        if client.is_connected():
            client_status = 1
    except:
        # Give the error code
        client_status = 2
    finally:
        # Disconnect from the server
        client.disconnect()
    
    return client_status