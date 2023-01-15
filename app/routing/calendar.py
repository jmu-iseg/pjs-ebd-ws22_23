from app import app, get_graph_params
from flask_login import login_required
import requests
from flask import render_template
from datetime import datetime, timedelta

@app.route('/calendar')
@login_required
def calendar():
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
    return render_template('/pages/calendar.html', users=users, machines=machines)

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