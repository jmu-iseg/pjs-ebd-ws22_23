from pytz import utc
from app import app, create_file_object, flash_errors
from flask import render_template, request, redirect, send_file
from app.models import *
from app.forms import *
# importieren aller Sub-Routen
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
    # read 2023 solar data 
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'solar_data.csv'), mode='r', encoding='utf-8') as solar:
        solar_data = pd.read_csv(solar)
    solar_data['dateTime'] = pd.to_datetime(solar_data.dateTime)

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
    df = pd.merge(solar_data, clouds, how='left', left_on=['dateTime'], right_on=['dateTime'])    

    # select time period of 14 days
    start_date = pd.to_datetime(datetime.utcnow()+timedelta(hours=1))
    end_date = pd.to_datetime(datetime.utcnow()+timedelta(days=14, hours=1))
    df = df[(df['dateTime'] >= start_date.replace(hour=0)) & (df['dateTime'] <= end_date.replace(hour=23))]

    # calculation of pv output
    df['output_prediction'] = ((df['max'] - df['min']) * df['sun']) + df['min']

    # generate outputs for visualisation
    pv_prediction = df.set_index('dateTime')
    pv_prediction = pv_prediction.resample("D").sum().reset_index()
    pv_prediction_labels = pv_prediction['dateTime'].dt.strftime("%d.%m.%Y").to_list()
    pv_prediction['output_prediction'] = round(pv_prediction['output_prediction'],1)
    pv_prediction = pv_prediction['output_prediction'].to_list()

    # date & time 
    tag = date.today()   
    tag = tag.strftime("%d.%m.%Y")
    uhrzeit = datetime.now()
    uhrzeit = uhrzeit.strftime("%H:%M")

    # calculate the ratio of actual pv energy and maximum possible pv energy
    df_today = df.set_index('dateTime')
    df_today = df_today.resample("D").sum().reset_index()
    today = date.today().strftime("%Y-%m-%d")
    df_today = df_today[df_today['dateTime'] == today] 
    todays_pv_energy = float(df_today['output_prediction'])
    max_pv_energy = float(df_today['max'])
    auslastung_pv = todays_pv_energy / max_pv_energy
    auslastung_pv = int(round(auslastung_pv*100,0)) 

    # get all saved appointments
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
    
    # order appointments by date 
    termin_daten = {k: v for k, v in sorted(termin_daten.items(), key=lambda item: item[1]['dateTime'], reverse=False)}
    
    # reset id/index
    termin_daten = {i: v for i, v in enumerate(termin_daten.values())}

    # filter appointments in future
    termin_daten_future = termin_daten.copy()
    today = date.today()  
    for termin in list(termin_daten_future.keys()):
       if termin_daten_future[termin]['dateTime'] + timedelta(hours=termin_daten_future[termin]['duration']) < datetime.now():
            del termin_daten_future[termin]

    # next 2 appointments 
    termin_daten_list = {k: termin_daten_future[k] for k in list(termin_daten_future.keys())[:2]}

    # timer for next termin 
    termin_timer = termin_daten_future.copy()
    for termin in list(termin_timer.keys()):
       if termin_timer[termin]['dateTime'] < datetime.now():
            del termin_timer[termin]
    if len(termin_timer) < 1: 
        timer = "0000"
    else:
        next_termin = termin_timer[list(termin_timer.keys())[0]]['dateTime']
        duration = next_termin - datetime.now()
        duration_in_s = duration.total_seconds()    
        days = divmod(duration_in_s, 86400)        
        hours = divmod(days[1], 3600)               
        minutes = divmod(hours[1], 60)  
        days = int(days[0])
        hours = int(hours[0])
        minutes = int(minutes[0])
        timer = [days,hours,minutes]

    # sum of saved co2 (total)
    saved_co2 = 0
    for termin in termin_daten: 
        saved_co2 += termin_daten[termin]['saved_co2']
        saved_co2 = round(saved_co2,1)

    # sum of saved co2 (today)
    saved_co2_today = 0
    for termin in termin_daten:
        if termin_daten[termin]['dateTime'].date() == datetime.today().date():
            saved_co2_today += termin_daten[termin]['saved_co2']
            saved_co2_today = round(saved_co2_today,1)

    # appointment data for co2 visualisation 
    temp_df = pd.DataFrame(termin_daten).T
    temp_df = temp_df.sort_values(by='dateTime')
    temp_df['day'] = temp_df['dateTime'].dt.date
    temp_df = temp_df.groupby('day', as_index=False).sum()    
    temp_df = temp_df[['day', 'saved_co2']]
    temp_df['saved_co2'] = round(temp_df['saved_co2'],1)
    temp_df['day'] = pd.to_datetime(temp_df['day'])
    temp_df['day'] = temp_df['day'].dt.strftime("%d.%m.%Y")
    co2_termine = temp_df.to_dict()    

    # sum of predicted pv energy in next 2 weeks
    pv_prediction_sum = int(sum(pv_prediction))

    # get weather data 
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

    # return data to home 
    return render_template("/pages/home.html", pv_prediction=pv_prediction, pv_prediction_labels=pv_prediction_labels, termin_daten=termin_daten, termin_daten_list=termin_daten_list, records=records, informations=informations, cityname=name, saved_co2=saved_co2, saved_co2_today=saved_co2_today, tag=tag, uhrzeit=uhrzeit, auslastung_pv=auslastung_pv, timer=timer, co2_termine=co2_termine, pv_prediction_sum=pv_prediction_sum)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg'}

# reload route
@app.route('/reload_webapp')
@login_required
def reload():
    """Führt auf der Maschine ein Skript aus, um den neuesten Stand vom Github zu laden
    und den Apache-Webserver neuzustarten.

    Returns:
        redirect('/'): Nachdem erfolgreich neu geladen wurde, wird auf die Home-Seite verwiesen
    """
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
    save_to_calendar(request.args.get('id'), flashmessage=False)
    return send_file(buf, download_name=filename)

