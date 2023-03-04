from pytz import utc
from app import app, create_file_object, flash_errors
from flask import render_template, request, redirect, send_file
from app.models import *
from app.forms import *
from app.routing.auth import *
from app.routing.optimization import *
from app.routing.settings import *
from app.routing.calendar import *
from app.routing.weather import *
import subprocess
import pandas as pd
import mysql.connector as sql
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta, date
import subprocess
from flask_login import login_required

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
     # read 2023 energy data
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'sensor_2023.csv'), mode='r', encoding='utf-8') as sensor:
        df = pd.read_csv(sensor)
    df['dateTime'] = pd.to_datetime(df.dateTime)  

    # read 2023 solar data 
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'solar_data.csv'), mode='r', encoding='utf-8') as solar:
        solar_data = pd.read_csv(solar)
    solar_data['dateTime'] = pd.to_datetime(solar_data.dateTime)

    # merge solar data with df 
    df = pd.merge(df, solar_data, how='left', left_on=['dateTime'], right_on=['dateTime'])
    #df = df.drop('datetime', axis=1)

    # get cloud data
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'streaming_data_platform/weather_forecast.json'), mode='r', encoding='utf-8') as openfile:
        data = json.load(openfile)
    timestamp = []
    clouds = []
    for day in data['list']:
        timestamp.append(datetime.utcfromtimestamp(day['dt']).strftime("%Y-%m-%d"))
        clouds.append(day['clouds'])
    cloud_dict = {
        'dateTime': timestamp,
        'clouds': clouds
    }
    clouds = pd.DataFrame.from_dict(cloud_dict, orient='index').T
    clouds['dateTime'] = pd.to_datetime(clouds.dateTime)
    clouds['clouds'] = clouds['clouds'].astype(int)

    # interpolate cloud data from daily to hourly for next 30 days
    clouds = clouds.set_index('dateTime')
    clouds = clouds.resample("H").interpolate().reset_index()
    clouds['dateTime'] = pd.to_datetime(clouds.dateTime)
    clouds['clouds'] = clouds['clouds'] / 100
    clouds['sun'] = 1 - clouds['clouds']
    
    # merge cloud data into energy data 
    df = pd.merge(df, clouds, how='left', left_on=['dateTime'], right_on=['dateTime'])    

    # select time period
    start_date = pd.to_datetime(datetime.utcnow()+timedelta(hours=1))
    end_date = pd.to_datetime(datetime.utcnow()+timedelta(days=14, hours=1))
    df = df[(df['dateTime'] >= start_date.replace(hour=0)) & (df['dateTime'] <= end_date.replace(hour=23))]

    # neue Spalte mit Formel pv output = ((MAX-MIN)*sun) + MIN
    df['output_prediction'] = ((df['max'] - df['min']) * df['sun']) + df['min']

    # calculate netzbezug
    df['balance'] = (df['basicConsumption'] + df['managementConsumption'] + df['productionConsumption']) - df['output_prediction']
    netzbezug = df.drop(['basicConsumption', 'managementConsumption', 'productionConsumption', 'output'], axis=1)

    # generate outputs for visualisation
    pv_prediction = netzbezug.set_index('dateTime')
    pv_prediction = pv_prediction.resample("D").sum().reset_index()
    pv_prediction_labels = pv_prediction['dateTime'].dt.strftime("%d.%m.%Y").to_list()
    pv_prediction['output_prediction'] = round(pv_prediction['output_prediction'],1)
    pv_prediction = pv_prediction['output_prediction'].to_list()

    # uhrzeit & datum 
    tag = date.today()   
    tag = tag.strftime("%d.%m.%Y")
    uhrzeit = datetime.now()
    uhrzeit = uhrzeit.strftime("%H:%M")

    # auslastung pv-anlage
    df_today = df.set_index('dateTime')
    df_today = df_today.resample("D").sum().reset_index()
    today = date.today().strftime("%Y-%m-%d")
    df_today = df_today[df_today['dateTime'] == today] 
    todays_pv_energy = float(df_today['output_prediction'])
    max_pv_energy = float(df_today['max'])
    auslastung_pv = todays_pv_energy / max_pv_energy
    auslastung_pv = int(round(auslastung_pv*100,0)) 

    # gespeicherte historische termine abfragen
    termine = Termin.query.all()
    termin_daten = {}
    wochentage_kuerzel = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
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
            'saved_co2': round((termin.energyconsumption - termin.gridenergy) * 0.412,1) # kg co2 pro kWh
            } 
    
    # order by date 
    termin_daten = {k: v for k, v in sorted(termin_daten.items(), key=lambda item: item[1]['dateTime'], reverse=False)}
    
    # reset id/index
    termin_daten = {i: v for i, v in enumerate(termin_daten.values())}

    # next 2 termine
    termin_daten_list = {k: termin_daten[k] for k in list(termin_daten.keys())[:2]}

    # timer for next termin 
    next_termin = termin_daten[0]['dateTime']
    print(next_termin)
    print(datetime.now())
    duration = next_termin - datetime.now()
    duration_in_s = duration.total_seconds()    
    days = divmod(duration_in_s, 86400)        
    hours = divmod(days[1], 3600)               
    minutes = divmod(hours[1], 60)  
    days = int(days[0])
    hours = int(hours[0])
    minutes = int(minutes[0])
    timer = [days,hours,minutes]

    # sum of saved co2 (insgesamt)
    saved_co2 = 0
    for termin in termin_daten: 
        saved_co2 += termin_daten[termin]['saved_co2']
        saved_co2 = round(saved_co2,1)

    # sum of saved co2 (heute)
    saved_co2_today = 0
    for termin in termin_daten:
        if termin_daten[termin]['dateTime'].date() == datetime.today().date():
            saved_co2_today += termin_daten[termin]['saved_co2']
            saved_co2_today = round(saved_co2_today,1)

    # weather 
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'streaming_data_platform/weather_forecast.json'), mode='r', encoding='utf-8') as openfile:
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

    return render_template("/pages/home.html", pv_prediction=pv_prediction, pv_prediction_labels=pv_prediction_labels, termin_daten=termin_daten, termin_daten_list=termin_daten_list, records=records, informations=informations, cityname=name, saved_co2=saved_co2, tag=tag, uhrzeit=uhrzeit, auslastung_pv=auslastung_pv, timer=timer)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg'}

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