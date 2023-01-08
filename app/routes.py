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
    lat = config['weather']['lat']
    lon = config['weather']['lon']
    key = config['weather']['openweatherapikey']
    resp = requests.get(f'https://pro.openweathermap.org/data/2.5/forecast/climate?lat={lat}&lon={lon}&appid={key}&units=metric&lang=de').json()
    timestamp = []
    temps = []
    weather = []
    pressure = []
    humidity = []
    records = resp['cnt']
    for day in resp['list']:
        timestamp.append(datetime.utcfromtimestamp(day['dt']).date())
        temps.append(day['temp']['day'])
        weather.append(day['weather'][0]['description'])
        pressure.append(day['pressure'])
        humidity.append(day['humidity'])
    informations = {
        'Tag': timestamp,
        'Temp': temps,
        'Wetter': weather,
        'Druck': pressure,
        'Feuchtigkeit': humidity
    }
    return render_template('/pages/weather.html', records=records, informations=informations)

@app.route('/calendar')
@login_required
def calendar():
    return render_template('/pages/calendar.html')

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