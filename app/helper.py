from flask import flash
import os
import requests
import json
from datetime import datetime, timedelta
import configparser
from icalendar import Calendar, Event, vCalAddress, vText
import io
from asyncua import Client

# Helper function to get config values
def get_config(root_path):
    config = configparser.ConfigParser()
    config.read(os.path.join(root_path,'settings.cfg'), encoding='utf-8')
    return config

# Helper function to get config values
def write_config(root_path, config):
    with open(os.path.join(root_path,'settings.cfg'), 'w', encoding='utf-8') as configfile:
        config.write(configfile)

# Flash all available errors for every given form
def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Fehler im Feld '%s' - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

# Return the day abbreviations for every day-int
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

# function to return the microsoft graph token from the graph_settings.json. if the token is no longer valid, a new token gets generated
def get_graph_params(root_path):
    with open(os.path.join(root_path, 'graph_settings.json'), 'r') as openfile:
        params = json.load(openfile)

    # retrieve new token, if no token existent or expired
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
        # send request
        resp = requests.post(f"https://login.microsoftonline.com/{params['tenant']}/oauth2/v2.0/token", headers=headers, data=body).json()
        # save new token to the params dictionary
        params['token'] = f"Bearer {resp['access_token']}"
        params['expiry'] = (datetime.utcnow() + timedelta(seconds=(resp['expires_in']) - 120)).strftime("%m/%d/%Y, %H:%M:%S")
        # overwrite the graph_settings.json
        with open(os.path.join(root_path, 'graph_settings.json'), 'w') as outfile:
            json.dump(params, outfile)

    return params

def create_file_object(start, end, summary):
    # create calendar object using icalendar python library
    cal = Calendar()
    event = Event()
    # construct event
    event.add('summary', summary)
    event.add('dtstart', start)
    event.add('dtend', end)
    organizer = vCalAddress('MAILTO:termine@pjs-termine.de')
    organizer.params['cn'] = vText('EBT-PJS')
    organizer.params['role'] = vText('EBT-PJS TN')
    event['organizer'] = organizer
    event['location'] = vText('Würzburg, DE')
    cal.add_component(event)
    # write calendar content in ICS Format to an io.BytesIO array. Has to bee io.BytesIO, because the flask send_file function uses this format.
    buf = io.BytesIO()
    buf.write(cal.to_ical())
    buf.seek(0)
    return buf

"""
OPC UA Sender
    Start the given machine via OPC UA when the time is right
    Validations:
        right time
        connection test
"""
def opc_ua_sender(machineIDs, state, root_path, terminDateTime):
    # Read settings
    config = get_config(root_path)

    # Get terminDateTime and nowtime
    termin_date_time = datetime(terminDateTime)
    now_time = datetime.now()

    # Empty string
    return_notification = []

    # Check for every given machine
    for machine in machineIDs:
        # what type of machine?
        if machine == "Wellenlöt":
            machineType = 1
        elif machine == "Lötbad3/4":
            machineType = 2
        elif machine == "Lötbad5":
            machineType = 3

        # Specify the OPC-UA config
        value_on = config['opcua']['value_on']
        value_off = config['opcua']['value_off']
        client_url = config['opcua']['url' + machineType]
        object_var = config['opcua']['var' + machineType]
        machine_offset = config['opcua']['offset' + machineType]

        # Get the timedelta
        time_diff = now_time - termin_date_time - machine_offset
        time_diff_mins = time_diff.total_minutes()

        # Is it time to start/stop the machine?
        if time_diff_mins <= 0:
            # Connect to the OPC-UA server
            client = Client(client_url)

            # Check connection to client
            try:
                # Connect to the OPC UA server
                client.connect()

                # Browse the address space and find the node you want to write to
                root = client.get_root_node()
                myvar = root.get_child([object_var, "2:MyObject", "2:MyVariable"])

                # Write data to the node
                if state == "on":
                    # Start the machine
                    myvar.set_value(value_on)

                    # Check if client is connected
                    if client.is_connected():
                        client_status = machineType + " started"
                else:
                    # Stop the machine
                    myvar.set_value(value_off)

                    # Check if client is connected
                    if client.is_connected():
                        client_status = machineType + " stopped"
            except:
                # Give the error code
                client_status = "Connection refused from " + machineType
            finally:
                # Disconnect from the server
                client.disconnect()
            return_notification.append(client_status + " | ")
        return_notification.append("Too early to start machine " + machineType + " | ")
    
    return return_notification