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
from datetime import datetime, timedelta
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
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'streaming_data_platform/data.json'), mode='r', encoding='utf-8') as openfile:
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
    pv_prediction = pv_prediction['output_prediction'].to_list()

    # gespeicherte historische termine abfragen
    termine = Termin.query.all()
    for termin in termine:
        print(termin.dateTime)

    return render_template("/pages/home.html", pv_prediction=pv_prediction, pv_prediction_labels=pv_prediction_labels)


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