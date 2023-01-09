from app import *
from flask import render_template, request, redirect, send_file
from app.models import *
from app.forms import *
from app.routing.auth import *
from app.routing.optimization import *
from app.routing.settings import *
import subprocess
import pandas as pd
import mysql.connector as sql
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
import subprocess
from icalendar import Calendar, Event, vCalAddress, vText
import io
import os
import configparser
from flask_login import login_required
import requests
import json
from pathlib import Path

ALLOWED_EXTENSIONS = {'png', 'jpg'}

config = configparser.ConfigParser()
config.read(os.path.join(app.root_path,'settings.cfg'))

@app.route('/')
@login_required
def home():
    return render_template("/pages/home.html")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# dashboard route   
@app.route('/dashboard')
@login_required
def dashboard():
    #Executing SQL Statements
    db_connection = sql.connect(host='localhost', database='energy', user='energy', password='PJS2022', port=3306)
    query = "SELECT dateTime, output, basicConsumption, managementConsumption, productionConsumption FROM sensor"
    df = pd.read_sql(query,db_connection)
    db_connection.close()

    # filter time (todo: dynamic with user input)
    df = df[(df['dateTime'] >= '2022-07-04 00:00:00') & (df['dateTime'] <= '2022-07-06 23:00:00')]

    return render_template("/pages/dashboard.html", labels=df['dateTime'].tolist(), output=df['output'].tolist(), bConsum=df['basicConsumption'].tolist(), mConsum=df['managementConsumption'].tolist(), pConsum=df['productionConsumption'].tolist())
    
@app.route('/weather')
@login_required
def weather():
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'streaming_data_platform/data.json'), mode='r', encoding='utf-8') as openfile:
        data = json.load(openfile)
    timestamp = []
    clouds = []
    rain = []
    speed = []
    sunrise = []
    sunset = []
    feel_temp = []
    temps = []
    weather = []
    weather_code = []
    pressure = []
    humidity = []
    night = []
    wochentag = []
    records = data['cnt']
    name = data['city']['name']
    for day in data['list']:
        timestamp.append(datetime.utcfromtimestamp(day['dt']).strftime("%d.%m.%Y"))
        temps.append(round(day['temp']['max'], 1))
        weather.append(day['weather'][0]['description'])
        weather_code.append(day['weather'][0]['id'])
        pressure.append(day['pressure'])
        humidity.append(day['humidity'])
        clouds.append(day['clouds'])
        night.append(round(day['temp']['min'], 1))
        wochentag.append(get_weekday(datetime.utcfromtimestamp(day['dt']).strftime("%w")))
        if 'rain' in day:
            rain.append(day['rain'])
        else:
            rain.append(0)
        speed.append(day['speed'])
        sunrise.append(datetime.utcfromtimestamp(day['sunrise']).strftime("%H:%M"))
        sunset.append(datetime.utcfromtimestamp(day['sunset']).strftime("%H:%M"))
        feel_temp.append(round(day['feels_like']['day'], 1))
    informations = {
        'Tag': timestamp,
        'Sonnenaufgang': sunrise,
        'Sonnenuntergang': sunset,
        'Temp': temps,
        'Wetter': weather,
        'Wettercode': weather_code,
        'Druck': pressure,
        'Feuchtigkeit': humidity,
        'Wolken': clouds,
        'Regen': rain,
        'Wind': speed,
        'Feelslike': feel_temp,
        'Nacht': night,
        'Wochentag': wochentag
    }
    return render_template('/pages/weather.html', records=records, informations=informations, cityname=name)

@app.route('/calendar')
@login_required
def calendar():
    params = get_graph_params()
    head = {
        'Authorization': params['token']
    }
    users = {}
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    for user in resp['value']:
        users[user['displayName']] = {
            'id': user['id'],
            'title': user['jobTitle'],
            'mail': user['mail']
            }
    return render_template('/pages/calendar.html', users=users)

@app.route('/calendar/<id>')
@login_required
def show_calendar(id):
    params = get_graph_params()
    head = {
        'Authorization': params['token']
    }
    start_datetime = datetime.utcnow()
    end_datetime = start_datetime + timedelta(days=7)
    cal_url = f"https://graph.microsoft.com/v1.0/users/{id}/calendarView?startDateTime={start_datetime}&endDateTime={end_datetime}&$select=subject,bodyPreview,start,end,location"
    resp = requests.get(cal_url, headers=head).json()
    events = []
    for entry in resp['value']:
        startdate = datetime.strptime(entry['start']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")
        enddate = datetime.strptime(entry['end']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")
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

# reload route
@app.route('/reload_webapp')
@login_required
def reload():
    subprocess.run('sudo chmod 777 update_files.sh', shell=True, check=True, text=True, cwd=app.root_path)
    subprocess.run('./update_files.sh', shell=True, check=True, text=True, cwd=app.root_path)
    return redirect('/')

@app.route('/return-files')
@login_required
def return_files_calendar():
    starttime = "{} {}".format(request.args.get('datum'), request.args.get('uhrzeit'))
    starttime_formatted = datetime.strptime(starttime, '%d.%m.%Y %H:%M')
    endtime_formatted = starttime_formatted + timedelta(hours=float(request.args.get('dauer')))
    filename = "Termineinladung {}.ics".format(request.args.get('id'))
    buf = create_file_object(starttime_formatted, endtime_formatted, request.args.get('bezeichnung'))
    return send_file(buf, download_name=filename)

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