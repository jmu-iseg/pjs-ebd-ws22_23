from app import app, get_graph_params
from flask_login import login_required
import requests
from flask import render_template
from datetime import datetime, timedelta, date
from app.models import *
import pandas as pd


@app.route('/calendar')
@login_required
def calendar():
    # old part when microsoft graph was still used for the calendar events
    """
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    users = {}
    machines = {}
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    for user in resp['value']:
        if user['jobTitle'] == 'pjs_machine':
            machines[user['displayName']] = {
                'id': user['id'],
                'title': user['jobTitle'],
                'mail': user['mail']
                }
        else:
            users[user['displayName']] = {
                'id': user['id'],
                'title': user['jobTitle'],
                'mail': user['mail']
                }
    """
     # get all saved appointments from the database
    termine = Termin.query.all()
    termin_daten = {}
    wochentage_kuerzel = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    # save information for each appointment in a dictionary
    for termin in termine: 
        endtime = termin.dateTime + timedelta(hours=termin.duration)
        termin_daten[termin.id] = {
            'creationTime': pd.to_datetime(termin.creationTimeUTC),
            'dateTime': pd.to_datetime(termin.dateTime),
            'machines': termin.machines,
            'employees': termin.employees,
            'date': termin.dateTime.date().strftime('%d.%m.'),
            'weekday': wochentage_kuerzel[termin.dateTime.weekday()],
            'starttime': termin.dateTime.time().strftime('%H:%M'),
            'endtime': endtime.time().strftime('%H:%M'),
            'duration': termin.duration, 
            'description': termin.description,
            'energy_consumption': termin.energyconsumption,
            'gridenergy': termin.gridenergy,
            'pv_energy': termin.energyconsumption - termin.gridenergy,
            'pv_energy_prcnt': round((1-(termin.gridenergy/termin.energyconsumption)) * 100,1),
            'saved_co2': round((termin.energyconsumption - termin.gridenergy) * 0.412,1), # kg co2 pro kWh
            'previous': 0,
            'before': 0
            } 
    
    # order by date 
    termin_daten = {k: v for k, v in sorted(termin_daten.items(), key=lambda item: item[1]['dateTime'], reverse=False)}
    
    # reset id/index
    termin_daten = {i: v for i, v in enumerate(termin_daten.values())}
    
    # filter by appointments that are in the future
    today = date.today()  
    for termin in list(termin_daten.keys()):
       if termin_daten[termin]['dateTime'].date() < today:
            del termin_daten[termin]

    # loop termin_daten and pass it to the template render function
    if len(termin_daten) < 1: 
        return render_template('/pages/calendar.html', termin_daten={})
    else:
        for termin in range(list(termin_daten.keys())[0],list(termin_daten.keys())[-1]): 
            # check if two appointments are at the same date, in order to display them together
            if termin_daten[termin]['date'] == termin_daten[termin+1]['date']: 
                termin_daten[termin]['after'] = 1
                termin_daten[termin+1]['before'] = 1
        return render_template('/pages/calendar.html', termin_daten=termin_daten)

# old function when microsoft graph was still used for the calendar route
"""
@app.route('/calendar/<id>')
@login_required
def show_calendar(id):
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    start_datetime = datetime.utcnow()
    end_datetime = start_datetime + timedelta(days=7)
    cal_url = f"https://graph.microsoft.com/v1.0/users/{id}/calendarView?startDateTime={start_datetime}&endDateTime={end_datetime}&$select=subject,bodyPreview,start,end,location"
    resp = requests.get(cal_url, headers=head).json()
    events = []
    for entry in resp['value']:
        startdate = datetime.strptime(entry['start']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
        enddate = datetime.strptime(entry['end']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
        event = {
            'subject': entry['subject'],
            'body': entry['bodyPreview'],
            'location': entry['location']['displayName'],
            'day': startdate.strftime("%d"),
            'month': startdate.strftime("%b"),
            'day_text': startdate.strftime("%A"),
            'starttime': startdate.strftime("%H:%M"),
            'endtime': enddate.strftime("%H:%M"),
            'date': startdate.strftime("%d.%m.%Y")
        }
        events.append(event)


    return render_template('/pages/display_calendar.html', events=events)
"""