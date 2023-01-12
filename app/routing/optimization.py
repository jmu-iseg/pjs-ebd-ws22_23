from app import app, flash_errors, create_file_object, get_config
from flask_login import login_required
from flask import request, Response, render_template, redirect, flash
from app.forms import SendMailForm
from pathlib import Path
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime, timedelta
import pandas as pd
import mysql.connector as sql
import gurobipy as gp
from gurobipy import GRB

config = get_config(app.root_path)

termine = {}
# optimization route
@app.route('/optimization')
@login_required
def optimization():
    termine.clear()
    return render_template("/pages/optimization.html")

# add termin to dictionary
@app.route('/add_termin', methods=['GET', 'POST'])
@login_required
def add_termin():
    id = request.form['id']
    bezeichnung = request.form['bezeichnung']
    dauer = request.form['dauer']
    maschinen_string = request.form['maschinen']
    maschinen = maschinen_string.split(",") # split string maschinen into list 
    
    # new termin with user inputs
    termine[id] = {'bezeichnung': bezeichnung, 'dauer': int(dauer), 'maschinen': maschinen}

    return Response(status=204)

# delete termin from dictionary 
@app.route('/delete_termin', methods=['GET', 'POST'])
@login_required
def delete_termin():
    id = request.form['id']
    print(id)
    termine.pop(id, None)
    return Response(status=204)

# take input of start & end date of optimization 
@app.route('/optimization', methods=['POST'])
@login_required
def get_date():
    errors = {}

     # send mail
    sendMailForm = SendMailForm()
    if sendMailForm.validate_on_submit() and 'sendMailForm' in request.form:
        receiver = sendMailForm.mailAddress.data
        sender = config['mail']['mail_user']
        msg = MIMEMultipart()

        msg['Subject'] = 'Termineinladung'
        msg['From'] = formataddr((config['mail']['mail_sender'], config['mail']['mail_user']))
        msg['To'] = receiver

        msgText = MIMEText('<b>%s</b>' % (sendMailForm.mailText.data), 'html')
        msg.attach(msgText)

        starttime = "{} {}".format(sendMailForm.date.data, sendMailForm.time.data)
        starttime_formatted = datetime.strptime(starttime, '%d.%m.%Y %H:%M')
        endtime_formatted = starttime_formatted + timedelta(hours=float(sendMailForm.dauer.data))

        calendar = create_file_object(starttime_formatted, endtime_formatted, sendMailForm.bezeichnung.data)
        attachment = MIMEApplication(calendar.read())
        attachment.add_header('Content-Disposition','attachment',filename='Termineinladung.ics')
        msg.attach(attachment)

        user = config['mail']['mail_user']
        password = config['mail']['mail_pw']

        # Set up connection to the SMTP server
        with smtplib.SMTP(config['mail']['mail_server'], config['mail']['mail_port']) as server:
            server.login(user, password)
            server.sendmail(sender, receiver, msg.as_string())
            flash("Mail erfolgreich verschickt")
        return redirect('/optimization')
    elif request.method == "POST" and 'sendMailForm' in request.form:
        flash_errors(sendMailForm)
        return redirect('/optimization')

    if len(termine) < 1: 
        errors['Terminerror'] = 'Bitte mindestens einen Termin definieren.'
    else:
        for termin in termine:
            d = termine[termin]['maschinen']
            if "null" in d: 
                errors['Terminerror'] = 'In jedem Termin müssen Maschinen gewählt werden.'
                break
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    try:
        start = datetime.strptime(start_date, "%d.%m.%Y")
    except ValueError:
        errors['Startzeiterror'] = 'Bitte das Startdatum angeben.'
    try:
        end = datetime.strptime(end_date, "%d.%m.%Y")
    except ValueError:
        errors['Endzeiterror'] = 'Bitte das Enddatum angeben.'
    if end_date < start_date: 
        errors['Startzeiterror'] = 'Das Startdatum muss vor dem Enddatum liegen.'
    if len(errors) > 0:
        termine.clear()
        return render_template("pages/optimization.html", errors=errors)
    else:    
        return optimization_table(start_date, end_date,sendMailForm)

# optimization route
@app.route('/optimization_table', methods=['GET', 'POST'])
@login_required
def optimization_table(start_date, end_date, sendMailForm):
    # input date range
    start_date = pd.to_datetime(start_date, format="%d.%m.%Y")
    end_date = pd.to_datetime(end_date, format="%d.%m.%Y").replace(hour=23, minute=00) # set hour of end date to 23:00
    
    # db query
    #db_connection = sql.connect(host='localhost', database='energy', user='energy', password='PJS2022', port=3306)
    #query = "SELECT dateTime, output, basicConsumption, managementConsumption, productionConsumption FROM sensor"
    #df = pd.read_sql(query,db_connection)
    #db_connection.close()
    #df['dateTime'] = pd.to_datetime(df.dateTime)  

    # Übergangslösung, bis Daten von SEHO bereitstehen 

    # read 2023 energy data
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'sensor_2023.csv'), mode='r', encoding='utf-8') as sensor:
        df = pd.read_csv(sensor)
    #df = pd.read_csv('sensor_2023.csv')
    df['dateTime'] = pd.to_datetime(df.dateTime)  

    # read 2023 solar data 
    with open(os.path.join(Path(app.root_path).parent.absolute(), 'solar_data.csv'), mode='r', encoding='utf-8') as solar:
        solar_data = pd.read_csv(solar)
    #solar_data = pd.read_csv('solar_data.csv')
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
        timestamp.append(datetime.utcfromtimestamp(day['dt']).strftime("%Y-%m-%d %H:%M:%S"))
        clouds.append(day['clouds'])
    cloud_dict = {
        'dateTime': timestamp,
        'clouds': clouds
    }
    clouds = pd.DataFrame.from_dict(cloud_dict, orient='index', columns=['dateTime', 'clouds'])
    print(clouds)
    clouds['dateTime'] = pd.to_datetime(clouds.dateTime)

    print(clouds)

    # merge cloud data into energy data 
    df = pd.merge(df, clouds, how='left', left_on=['dateTime'], right_on=['dateTime'])

    print(df)
    

    # select planing period
    df = df[(df['dateTime'] >= start_date) & (df['dateTime'] <= end_date)]

    # calculate netzbezug
    df['balance'] = (df['basicConsumption'] + df['managementConsumption'] + df['productionConsumption']) - df['output']
    netzbezug = df.drop(['basicConsumption', 'managementConsumption', 'productionConsumption', 'output'], axis=1)

    # take termin input data 
    termine_df_neu = pd.DataFrame.from_dict(termine, orient='index', columns=['bezeichnung', 'dauer', 'maschinen', 'maschine1', 'maschine2', 'maschine3', 'energieverbrauch'])
    termine_df_neu = termine_df_neu.reset_index().rename(columns={'index': 'termin_id'})

    # energy consumption based on machines 

    # transform strings of machines 
    termine_df_neu['maschinen'] = termine_df_neu['maschinen'].astype('str') 
    termine_df_neu['maschinen'] = termine_df_neu['maschinen'].str.replace("[","")
    termine_df_neu['maschinen'] = termine_df_neu['maschinen'].str.replace("]","")
    termine_df_neu['maschinen'] = termine_df_neu['maschinen'].str.replace("'","")
    termine_df_neu['maschinen'] = termine_df_neu['maschinen'].str.replace(" ","")

    # transform machines columns into binary column 
    termine_df_neu['maschine1'].loc[termine_df_neu['maschinen'].str.contains('Wellenlöt')] = 1
    termine_df_neu['maschine2'].loc[termine_df_neu['maschinen'].str.contains('Lötbad3/4')] = 1
    termine_df_neu['maschine3'].loc[termine_df_neu['maschinen'].str.contains('Lötbad5')] = 1
    termine_df_neu['maschine1'].loc[(termine_df_neu['maschine1'].isnull())] = 0
    termine_df_neu['maschine2'].loc[(termine_df_neu['maschine2'].isnull())] = 0
    termine_df_neu['maschine3'].loc[(termine_df_neu['maschine3'].isnull())] = 0

    # define energy consumption per machine 
    consumption_m1 = int(config['machines']['consumption_m1'])
    consumption_m2 = int(config['machines']['consumption_m2'])
    consumption_m3 = int(config['machines']['consumption_m3'])

    # calculate energy consumption for each termin
    termine_df_neu['energieverbrauch'] = ((termine_df_neu['maschine1'] * consumption_m1) + (termine_df_neu['maschine2'] * consumption_m2) + (termine_df_neu['maschine3'] * consumption_m3)) * termine_df_neu['dauer'] 
    
    # generate dicts of termin data 
    termine_energy = dict(termine_df_neu[['termin_id','energieverbrauch']].values) 
    termine_length = dict(termine_df_neu[['termin_id','dauer']].values)
    
    # gurobi model
    with gp.Env(empty=True) as env:
        env.start()
        
        with gp.Model(env=env) as model:

            # create model 
            model = gp.Model("energy based scheduling")

            # create variables 
            # energy consumption per appointment
            consumption = model.addVars(df['dateTime'],termine_energy,vtype=GRB.CONTINUOUS,name="consumption")

            # planned start of appointment 
            start = model.addVars(consumption, vtype=GRB.BINARY, name="start")
            end = model.addVars(consumption, vtype=GRB.BINARY, name="end")

            # save start day und hour as numerical value
            start_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_hour")
            start_day = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_day")

            # save end hour as numerical value 
            end_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="end_hour")

            # calculate netzbezug of appointment
            for termin in termine_energy:
                for dateTime in df['dateTime']:
                    if dateTime.hour < 18:
                        for i in range(0,termine_length[termin]):
                            if float(netzbezug['balance'][netzbezug['dateTime'] == dateTime + pd.Timedelta(hours=i)]) < 0:
                                consumption[dateTime,termin] = consumption[dateTime,termin] + netzbezug['balance'][netzbezug['dateTime'] == dateTime + pd.Timedelta(hours=i)] + (termine_energy[termin]/termine_length[termin])
                            else: 
                                consumption[dateTime,termin] = consumption[dateTime,termin] + termine_energy[termin]/termine_length[termin]

            # minimize netzbezug
            obj = sum((consumption[dateTime,termin]*start[dateTime,termin])
                        for dateTime in df['dateTime'] for termin in termine_energy)

            # objective 
            model.setObjective(obj, GRB.MINIMIZE)

            # constraints 
            # weekend constraint
            for termin in termine_energy:
                for dateTime in df['dateTime']:
                    if dateTime.weekday() in [5,6]:
                        model.addConstr((start[dateTime,termin])==0)
                            
            # only 1 start time per appointment
            for termin in termine_energy: 
                model.addConstr(gp.quicksum(start[dateTime,termin] 
                                for dateTime in df['dateTime']) == 1)

            # no overlap constraint                
            for dateTime in df['dateTime']:
                if dateTime.hour < 18:
                        for t1 in termine_length: 
                            model.addConstr((start[dateTime,t1] == 1) >> (gp.quicksum(start[dateTime + pd.Timedelta(hours=i),t2] 
                                                                            for i in range(1,termine_length[t1])
                                                                            for t2 in termine_length)==0))                

            # no overlap of start times 
            for dateTime in df['dateTime']:
                model.addConstr(gp.quicksum(start[dateTime,termin] for termin in termine_energy) <= 1)
                        
            # save start hour and day of appointment 
            for termin in termine_energy: 
                for dateTime in df['dateTime']:
                    model.addConstr((start[dateTime,termin]==1) >> (start_day[termin]==dateTime.day))
                    model.addConstr((start[dateTime,termin]==1) >> (start_hour[termin]==dateTime.hour))

            # set end time of appointment 
            for termin in termine_length:            
                model.addConstr(end_hour[termin]==start_hour[termin]+termine_length[termin])      
                
            # end time constraint
            for termin in termine_length:            
                model.addConstr(end_hour[termin] <= 18)      
                
            # start time constraint 
            for termin in termine_length:            
                model.addConstr(start_hour[termin] >= 8)      

            # optimize 
            model.optimize()

            # generate output
            # save planned appointments
            appointments = pd.DataFrame(columns=['Termin'])
            for v in model.getVars():
                if v.X >= 1:
                    if v.VarName.startswith("start["): 
                        appointments = appointments.append({'Termin':v.VarName}, ignore_index=True)                
                
            # reformat dataframe
            appointments['Termin'] = appointments['Termin'].map(lambda x: x.lstrip('start_hourday[').rstrip(']'))
            appointments = appointments.groupby(by="Termin").sum().reset_index()
            appointments[['DateTime', 'TerminID']] = appointments['Termin'].str.split(',', 1, expand=True)
            appointments[['Date', 'Time']] = appointments['DateTime'].str.split(' ', 1, expand=True)

             # calculate netzbezug (objective value) for every appointment
            appointments['netzbezug'] = 0
            for i in range(0,len(appointments)):
                date = pd.to_datetime(appointments['DateTime'][i])
                termin_id = str(appointments['TerminID'][i])
                appointments['netzbezug'][i] = round(consumption[date,termin_id].getValue(),2)
            
            # drop unecessary columns
            appointments = appointments.drop('Termin', axis=1)
            appointments = appointments.drop('DateTime', axis=1)
            appointments = appointments.sort_values(by="TerminID")

            # join appointments with termine_df_neu
            appointments_output = pd.merge(appointments, termine_df_neu, how='left', left_on=['TerminID'], right_on=['termin_id'])
            #appointments_output.drop(['termin_id','energieverbrauch'], axis=1)

            # parse to datetime format
            appointments_output['Date'] = pd.to_datetime(appointments_output['Date'], format="%Y.%m.%d")
            appointments_output['Time'] = pd.to_datetime(appointments_output['Time'], format="%H:%M:%S")

            # change format of date and time 
            appointments_output['Date'] = appointments_output.Date.dt.strftime('%d.%m.%Y')
            appointments_output['Time'] = appointments_output.Time.dt.strftime('%H:%M')

            # transform maschinen for better output 
            appointments_output['maschinen'] = appointments_output['maschinen'].str.replace(",",", ")
            
            # df to dict as output for render template 
            appointments_dict = appointments_output.to_dict('records')

            # TODO: die optimierten Termine in DB speichern


            # save objective value of model
            obj_value = model.getAttr("ObjVal")

            # get sum of energy consumption of all appointments 
            energy_consumption = termine_df_neu['energieverbrauch'].sum()

            # list of energy consumption & termin id of appointments
            energy_consumption_list = termine_df_neu['energieverbrauch'].tolist()
            termin_list = termine_df_neu['termin_id'].astype(int).tolist()

            # percent of renewable energy for appointments
            renewable_percent = (1-(obj_value/energy_consumption)) * 100

            # round output data
            renewable_percent = round(renewable_percent, 2)
            energy_consumption = round(energy_consumption, 2)
            obj_value = round(obj_value, 2)

            # netzbezug für jeden einzelnen termin 
            netzbezug_termine = appointments['netzbezug'].to_list()
            appointments['percent'] = 1 - (appointments_output['netzbezug'] / appointments_output['energieverbrauch']) 
            appointments['percent'] = appointments['percent'] * 100
            appointments['percent'] = appointments['percent'].astype(float)
            appointments['percent'] = appointments['percent'].round(2) 
            netzbezug_termine_percent = appointments.to_dict('records')
    return render_template("/pages/optimization_table.html", my_list=appointments_dict, obj_value=obj_value, renewable_percent=renewable_percent, energy_consumption=energy_consumption, energy_consumption_list=energy_consumption_list, termin_list=termin_list, netzbezug_termine=netzbezug_termine, netzbezug_termine_percent=netzbezug_termine_percent, sendMailForm=sendMailForm)