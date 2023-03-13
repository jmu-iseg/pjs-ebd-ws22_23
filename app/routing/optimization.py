from app import app, flash_errors, create_file_object, get_config, get_graph_params, db
from app.models import Termin
from app.api.errors import bad_request
from flask_login import login_required
import flask_login
from flask import request, render_template, redirect, flash, session, url_for, jsonify
from app.forms import SendMailForm, OptimizationForm
from pathlib import Path
import os
import json
from app.forms import *
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime, timedelta
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import requests

config = get_config(app.root_path)

termine = {}
# optimization route
@app.route('/optimization', methods=['GET', 'POST'])
@login_required
def optimization():
    [session.pop(key) for key in list(session.keys()) if key == str(flask_login.current_user.id)]
    form = OptimizationForm()
    if form.validate_on_submit():
        if 'addline' in request.form:
            form.update_self()
        elif 'optimize' in request.form:
            startdate = form.startdate.data.strftime("%Y-%m-%d 00:00:00")
            enddate = form.enddate.data.strftime("%Y-%m-%d 23:59:59")
            termin = form.termine.__getitem__(0)
            return optimization_table(start_date=startdate, end_date=enddate, termin=termin, api=False)
        else:
            for termin in form.data['termine']:
                if termin['delete'] == True:
                    form.delete_termin(termin)
        return render_template("/pages/optimization.html", form=form)
    elif request.method == "POST" and 'optimization_identifier' in request.form:
        flash_errors(form)
        return render_template("/pages/optimization.html", form=form)
    return render_template("/pages/optimization.html", form=form)

def optimization_table(start_date, end_date, termin, api=False, sessiontoken=None):
    config = get_config(app.root_path)
    graph_start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    graph_end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    # transform input date 
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

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
    
    # merge cloud data into solar data 
    df = pd.merge(solar_data, clouds, how='left', left_on=['dateTime'], right_on=['dateTime'])    

    # select planing period
    df = df[(df['dateTime'] >= start_date) & (df['dateTime'] <= end_date)]

    # new column with equation pv_output = ((MAX-MIN)*sun) + MIN
    df['output_prediction'] = ((df['max'] - df['min']) * df['sun']) + df['min']

    # get energy consumption of planned appointments 
    consumption_data = Termin.query.filter(Termin.dateTime > start_date).filter(Termin.dateTime < end_date).all()
    termin_data_df = pd.DataFrame(columns=['dateTime', 'appointment_energy'])
    for t in consumption_data:
        for i in range(0,int(t.duration)):
            termin_data_df.loc[len(termin_data_df.index)] = [pd.to_datetime(t.dateTime + timedelta(hours=i)), t.energyconsumption / t.duration]
    
    # set dummy data if no appointments are planned in future 
    if termin_data_df.empty: 
        termin_data_df.loc[len(termin_data_df.index)] = [start_date, 0.0]

    # group on dateTimes 
    termin_data_df = termin_data_df.groupby('dateTime').sum()    

    # merge energy consumption data of planned appointments with other energy data
    df = pd.merge(df, termin_data_df, how='left', left_on=['dateTime'], right_on=['dateTime'])
    df['appointment_energy'] = df['appointment_energy'].fillna(0) 

    # calculate grid energy
    basicConsumption = float(config['machines']['basicConsumption']) # hourly in kWh
    df['balance'] = (basicConsumption + df['appointment_energy']) - df['output_prediction']
    netzbezug = df.drop(['appointment_energy'], axis=1)

    # take termin input data
    termine = {}
    if api:
        termine['0'] = termin
    else:
        termine['0'] = {'bezeichnung': termin.terminbeschreibung.data, 'dauer': termin.duration.data, 'maschinen': termin.machines.data, 'complexity': termin.product.data, 'mitarbeiter': termin.mitarbeiter.data}
    termine_df_neu = pd.DataFrame.from_dict(termine, orient='index', columns=['bezeichnung', 'dauer', 'maschinen', 'complexity', 'mitarbeiter', 'energieverbrauch', 'complexity_percent'])
    termine_df_neu = termine_df_neu.reset_index().rename(columns={'index': 'termin_id'})

    # API call for calendar data 
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()

    # transform machines for output
    machines_string = ""
    for machine in termine_df_neu['maschinen'].to_list()[0]:
        displayName = ''
        for user in resp['value']:
            if machine==user['id']:
                displayName = user['displayName']
                break
        if machine == termine_df_neu['maschinen'].to_list()[0][-1]:
            machines_string += displayName 
        else: 
            machines_string += displayName + ", "
    termine_df_neu['maschinen_string'] = machines_string

    # transform employees for output
    mitarbeiter_string = ""
    for mitarbeiter in termine_df_neu['mitarbeiter'].to_list()[0]:
        displayName = ''
        for user in resp['value']:
            if mitarbeiter==user['id']:
                displayName = user['displayName']
                break
        if mitarbeiter == termine_df_neu['mitarbeiter'].to_list()[0][-1]:
            mitarbeiter_string += displayName 
        else: 
            mitarbeiter_string += displayName + ", "
    termine_df_neu['mitarbeiter_string'] = mitarbeiter_string

    # get machine type 
    machine_types = []
    machine_types_dict = {}
    for machine in termine_df_neu['maschinen'].to_list()[0]:
        vorname = ''
        for user in resp['value']:
            if machine==user['id']:
                vorname = user['givenName']
                break
        machine_types.append(vorname)
        machine_types_dict[machine] = vorname
    termine_df_neu['machine_types'] = [machine_types]    

    # define energy consumption per machine based on config file 
    machine_consumption = {
        config['machines']['typ_m1']: float(config['machines']['consumption_m1']), 
        config['machines']['typ_m2']: float(config['machines']['consumption_m2']), 
        config['machines']['typ_m3']: float(config['machines']['consumption_m3'])
        }
    
    # define heating energy consumption per machine based on config file
    machine_heating = {
        config['machines']['typ_m1']: float(config['machines']['heating_m1']), 
        config['machines']['typ_m2']: float(config['machines']['heating_m2']), 
        config['machines']['typ_m3']: float(config['machines']['heating_m3'])
        }

    # set product complexity 
    complexity = 1.0
    if str(termine_df_neu['complexity'][0]) == 'Komplex':
        complexity = float(config['machines']['complexity_high'])
    elif str(termine_df_neu['complexity'][0]) == 'Normal':
        complexity = float(config['machines']['complexity_medium'])
    elif str(termine_df_neu['complexity'][0]) == 'Einfach':
        complexity = float(config['machines']['complexity_low'])

    # calculate energy consumption for each termin based on product complexity
    energie = 0
    for maschine in termine_df_neu['machine_types'].to_list()[0]: 
        energie += machine_consumption[maschine] * complexity * float(termine_df_neu['dauer'])
    termine_df_neu['energieverbrauch'] = energie

    # get availability of machines via calendar access
    machine_appointments = {}
    mitarbeiter_appointments = {}
    for machine in termine_df_neu['maschinen'].to_list()[0]:
        cal_url = f"https://graph.microsoft.com/v1.0/users/{machine}/calendarView?startDateTime={graph_start_date+timedelta(days=-1)}&endDateTime={graph_end_date}&$select=start,end"
        resp = requests.get(cal_url, headers=head).json()
        appointments = []
        for appointment in resp['value']:
            start =  datetime.strptime(appointment['start']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")+timedelta(hours=1)
            end = datetime.strptime(appointment['end']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")+timedelta(hours=1)
            start = start.strftime("%Y-%m-%d %H:%M:%S")
            end = end.strftime("%Y-%m-%d %H:%M:%S")
            appointments.append({
                'start': start,
                'end': end
            })
        machine_appointments[machine] = appointments

    # get availability of employees via calendar access
    for mitarbeiter in termine_df_neu['mitarbeiter'].to_list()[0]:
        cal_url = f"https://graph.microsoft.com/v1.0/users/{mitarbeiter}/calendarView?startDateTime={graph_start_date}&endDateTime={graph_end_date}&$select=start,end"
        resp = requests.get(cal_url, headers=head).json()
        appointments = []
        for appointment in resp['value']:
            start =  datetime.strptime(appointment['start']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")+timedelta(hours=1)
            end = datetime.strptime(appointment['end']['dateTime'].rsplit('.', 1)[0], "%Y-%m-%dT%H:%M:%S")+timedelta(hours=1)
            start = start.strftime("%Y-%m-%d %H:%M:%S")
            end = end.strftime("%Y-%m-%d %H:%M:%S")
            appointments.append({
                'start': start,
                'end': end
            })
        mitarbeiter_appointments[mitarbeiter] = appointments
    
    # set amount of appointment suggestions via config file 
    app_amount = int(config['machines']['appointment_amount'])
    termine_df_neu = pd.concat([termine_df_neu] * app_amount,ignore_index=True)
    termine_df_neu = termine_df_neu.reset_index().rename(columns={'index': 'termin_id', 'termin_id': 'del'}).drop('del',axis=1)
    termine_df_neu['termin_id'] = termine_df_neu['termin_id'] + 1
    
    # generate dicts of appointment data 
    termine_energy = dict(termine_df_neu[['termin_id','energieverbrauch']].values) 
    termine_machines = dict(termine_df_neu[['termin_id','maschinen']].values) 
    termine_length = dict(termine_df_neu[['termin_id','dauer']].values)

    # change float key to int
    for k in termine_energy.keys():
        int_key = int(k)
        termine_energy[int_key] = termine_energy.pop(k)
    
    for k in termine_length.keys():
        int_key = int(k)
        termine_length[int_key] = termine_length.pop(k)

    for k in termine_machines.keys():
        int_key = int(k)
        termine_machines[int_key] = termine_machines.pop(k)
    
    # start optimization
    for i in range(1,app_amount+2):
        # throw error if model is infeasible
        if i==app_amount+1:
            flash("Es konnte kein möglicher Terminvorschlag im Planungshorizont gefunden werden.")
            return redirect(url_for("optimization"))

        # try to optimize the appointment with 1 suggestion less 
        if 1 < i < app_amount+1:
            termine_energy.popitem()
            termine_length.popitem()

        # function for testing if machine is used in appointment before on this datetime
        def machine_used_before(dateTime, machine):
           # filter on dateTime (if start == same date like 'dateTime')
            for termin in machine_appointments[machine]:
                date1 = pd.to_datetime(termin['end'])
                date2 = pd.to_datetime(dateTime)
                # machine is used on the same day 
                if (date1.date() == date2.date()) & (date1.time() <= date2.time()):
                    return True
                # machine was used one day before 
                if date1.date() == date2.date()+timedelta(days=-1):
                    return True
            
            return False

        # init gurobi model
        with gp.Env(empty=True) as env:
            env.start()
            
            with gp.Model(env=env) as model:

                # create model 
                model = gp.Model("energy based scheduling")

                # create variables 
                # energy consumption per appointment
                consumption = model.addVars(df['dateTime'],termine_energy,vtype=GRB.CONTINUOUS,name="consumption")
                consumption_without_heating = model.addVars(df['dateTime'],termine_energy,vtype=GRB.CONTINUOUS,name="consumption_wth_heating")

                # planned start of appointment 
                start = model.addVars(consumption, vtype=GRB.BINARY, name="start")
                end = model.addVars(consumption, vtype=GRB.BINARY, name="end")

                # save start day und hour as numerical value
                start_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_hour")
                start_day = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_day")

                # save end hour as numerical value 
                end_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="end_hour")

                # calculate possible grid energy of appointment
                for termin in termine_energy:
                    for dateTime in df['dateTime']:
                        if dateTime.hour < 24-termine_length[termin]:
                            for i in range(0,termine_length[termin]):
                                # calculate energy consumption
                                if float(netzbezug['balance'][netzbezug['dateTime'] == dateTime + pd.Timedelta(hours=i)]) < 0:
                                    consumption[dateTime,termin] = consumption[dateTime,termin] + netzbezug['balance'][netzbezug['dateTime'] == dateTime + pd.Timedelta(hours=i)] + (termine_energy[termin]/termine_length[termin])
                                    consumption_without_heating[dateTime,termin] = consumption_without_heating[dateTime,termin] + netzbezug['balance'][netzbezug['dateTime'] == dateTime + pd.Timedelta(hours=i)] + (termine_energy[termin]/termine_length[termin])
                                else: 
                                    consumption[dateTime,termin] = consumption[dateTime,termin] + termine_energy[termin]/termine_length[termin]
                                    consumption_without_heating[dateTime,termin] = consumption_without_heating[dateTime,termin] + termine_energy[termin]/termine_length[termin]
                                # add possible heating consumption
                                for machine in termine_machines[1]:
                                    if machine_used_before(dateTime, machine) == False:
                                        machine_type = machine_types_dict[machine]
                                        consumption[dateTime,termin] += machine_heating[machine_type]

                # define objective function: minimize grid energy
                obj = sum((consumption[dateTime,termin]*start[dateTime,termin])
                            for dateTime in df['dateTime'] for termin in termine_energy)

                model.setObjective(obj, GRB.MINIMIZE)

                # constraints 
                # weekend constraint
                for termin in termine_energy:
                    for dateTime in df['dateTime']:
                        if dateTime.weekday() in [5,6]:
                            model.addConstr((start[dateTime,termin])==0)
                                
                # generate 3 possible apppointments
                for termin in termine_energy: 
                    model.addConstr(gp.quicksum(start[dateTime,termin] 
                                    for dateTime in df['dateTime']) == 1)

                # no overlap constraint                
                for dateTime in df['dateTime']:
                    if dateTime.hour < 24-termine_length[termin]:
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
                
                # get list of all appointments of involved machines
                prohibited_times_machines = []
                for machine in machine_appointments:
                    for termin in machine_appointments[machine]:
                        prohibited_times_machines.append(termin)

                duration = int(termine_length[1])

                # machines availability constraint
                for prohibited_time in prohibited_times_machines:
                    start_time = datetime.strptime(prohibited_time['start'], '%Y-%m-%d %H:%M:%S') - timedelta(hours=duration)
                    end_time = datetime.strptime(prohibited_time['end'], '%Y-%m-%d %H:%M:%S')
                    for termin in termine_energy:
                        for dateTime in df['dateTime']:
                            if start_time < dateTime < end_time:
                                model.addConstr((start[dateTime,termin])==0)
    
                # get list of all appointments of involved employees
                prohibited_times_mitarbeiter = []
                for mitarbeiter in mitarbeiter_appointments:
                    for termin in mitarbeiter_appointments[mitarbeiter]:
                        prohibited_times_mitarbeiter.append(termin)

                # employees availability constraint
                for prohibited_time in prohibited_times_mitarbeiter:
                    start_time = datetime.strptime(prohibited_time['start'], '%Y-%m-%d %H:%M:%S') - timedelta(hours=duration)
                    end_time = datetime.strptime(prohibited_time['end'], '%Y-%m-%d %H:%M:%S')
                    for termin in termine_energy:
                        for dateTime in df['dateTime']:
                            if start_time < dateTime < end_time:
                                model.addConstr((start[dateTime,termin])==0)

                # optimize 
                model.optimize()

                # generate output
                # save planned appointments
                appointments = pd.DataFrame(columns=['Termin'])

                # catch errors 
                try:
                    for v in model.getVars():
                        if v.X >= 1:
                            if v.VarName.startswith("start["): 
                                appointments = appointments.append({'Termin':v.VarName}, ignore_index=True)                
                except AttributeError:
                    continue

                # reformat dataframe
                appointments['Termin'] = appointments['Termin'].map(lambda x: x.lstrip('start_hourday[').rstrip(']'))
                appointments = appointments.groupby(by="Termin").sum().reset_index()
                appointments[['DateTime', 'TerminID']] = appointments['Termin'].str.split(',', 1, expand=True)
                appointments[['Date', 'Time']] = appointments['DateTime'].str.split(' ', 1, expand=True)
                appointments['TerminID'] = appointments['TerminID'].astype(int)

                # calculate grid energy (objective value) for every appointment
                appointments['netzbezug'] = 0
                for i in range(0,len(appointments)):
                    date = pd.to_datetime(appointments['DateTime'][i])
                    termin_id = int(appointments['TerminID'][i])
                    appointments['netzbezug'][i] = round(consumption_without_heating[date,termin_id].getValue(),1)

                # change negative grid energy of appointments to 0 
                appointments['netzbezug'][appointments['netzbezug'] < 0] = 0 
                appointments['netzbezug'] = appointments['netzbezug'].round(1)
                
                # generate new appointment id based on ordered grid energy
                appointments = appointments.rename(columns={'level_0': 'del'})
                appointments = appointments.sort_values(by="netzbezug")
                appointments = appointments.reset_index().reset_index()
                appointments = appointments.rename(columns={'level_0': 'Termin_ID'})
                appointments['Termin_ID'] = appointments['Termin_ID'] + 1

                # drop unecessary columns
                appointments = appointments.drop('Termin', axis=1)
                appointments = appointments.drop('DateTime', axis=1)

                # join appointments with termine_df_neu
                appointments_output = pd.merge(appointments, termine_df_neu, how='left', left_on=['TerminID'], right_on=['termin_id'])

                # parse to datetime format
                appointments_output['Date'] = pd.to_datetime(appointments_output['Date'], format="%Y.%m.%d")
                appointments_output['Time'] = pd.to_datetime(appointments_output['Time'], format="%H:%M:%S")

                # change format of date and time 
                appointments_output['Date'] = appointments_output.Date.dt.strftime('%d.%m.%Y')
                appointments_output['Time'] = appointments_output.Time.dt.strftime('%H:%M')

                # df to dict as output for render template 
                appointments_dict = appointments_output.to_dict('records')

                # get energy consumption of appointment
                energy_consumption = int(termine_df_neu['energieverbrauch'][0])

                # get list of grid energy of appointment suggestions
                netzbezug_termine = appointments['netzbezug'].to_list()
                
                # calculate pv energy in percent for every appointment suggestion
                appointments['percent'] = 1 - (appointments_output['netzbezug'] / appointments_output['energieverbrauch']) 
                appointments['percent'] = appointments['percent'] * 100
                appointments['percent'] = appointments['percent'].astype(float)
                appointments['percent'] = appointments['percent'].round(2).astype(int)
                appointments['pv_consumption'] = (appointments['percent'] / 100) * energy_consumption
                appointments = appointments.sort_values(by="percent",ascending=False)

                # calculate saved co2 per appointment suggestion
                appointments['saved_co2'] = round(((appointments['pv_consumption'] + appointments['netzbezug']) - appointments['netzbezug']) * 0.412,1)
                netzbezug_termine_percent = appointments.to_dict('records')

                # output prediction visualization 
                output_prediction = netzbezug.set_index('dateTime')
                output_prediction = output_prediction.resample("D").sum().reset_index()
                output_prediction['dateTime'] = pd.to_datetime(output_prediction.dateTime)

                # sum output prediction in time horizon
                output_prediction_sum = int(sum(output_prediction['output_prediction'].to_list()))

                break
    
    # optimization via api 
    if api:
        optimierungszeitpunkt = (datetime.utcnow()+ timedelta(hours=1)).strftime("%d.%m.%Y %H:%M")
        session[sessiontoken] = appointments_dict
        return {
            'Optimierungszeitpunkt': optimierungszeitpunkt,
            'Termine': appointments_dict
        }
    else:
        session[str(flask_login.current_user.id)] = {
            'appointments_dict': appointments_dict,
            'energy_consumption': energy_consumption,
            'netzbezug_termine': netzbezug_termine,
            'netzbezug_termine_percent': netzbezug_termine_percent,
            'output_prediction_list': output_prediction['output_prediction'].round(1).to_list(),
            'output_prediction_dates': output_prediction['dateTime'].dt.strftime("%d.%m.%Y").to_list(),
            'output_prediction_sum': output_prediction_sum,
        }

        return redirect(url_for('appointment_list'))

# return of all appointment data after optimization
@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointment_list():
    user_id = str(flask_login.current_user.id)
    if session.get(user_id) is None:
        return redirect(url_for('optimization'))
    appointments_dict = session.get(user_id).get('appointments_dict')
    energy_consumption = session.get(user_id).get('energy_consumption')
    netzbezug_termine = session.get(user_id).get('netzbezug_termine')
    netzbezug_termine_percent = session.get(user_id).get('netzbezug_termine_percent')
    output_prediction_list = session.get(user_id).get('output_prediction_list')
    output_prediction_dates = session.get(user_id).get('output_prediction_dates')
    output_prediction_sum = session.get(user_id).get('output_prediction_sum')

    # implementation of mail functionality to send optimized appointments
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
        
        # set up connection to the SMTP server
        with smtplib.SMTP(config['mail']['mail_server'], config['mail']['mail_port']) as server:
            server.login(user, password)
            server.sendmail(sender, receiver, msg.as_string())
            flash("Mail erfolgreich verschickt")

        terminID = sendMailForm.terminID.data
        return save_to_calendar(terminID)
 
    elif request.method == "POST" and 'sendMailForm' in request.form:
        flash_errors(sendMailForm)
        return render_template("/pages/optimization_table.html", my_list=appointments_dict, energy_consumption=energy_consumption, netzbezug_termine=netzbezug_termine, netzbezug_termine_percent=netzbezug_termine_percent, output_prediction_list=output_prediction_list, output_prediction_dates=output_prediction_dates, sendMailForm=sendMailForm, output_prediction_sum=output_prediction_sum)

    return render_template("/pages/optimization_table.html", my_list=appointments_dict, energy_consumption=energy_consumption, netzbezug_termine=netzbezug_termine, netzbezug_termine_percent=netzbezug_termine_percent, output_prediction_list=output_prediction_list, output_prediction_dates=output_prediction_dates, sendMailForm=sendMailForm, output_prediction_sum=output_prediction_sum)

# route to save selected appointment in database 
@app.route('/save-optimization', methods=['GET'])
@login_required
def save_termin():
    # get the termin dict
    terminId = request.args.get('id')
    if terminId is None:
        flash("Invalid")
        return redirect(url_for('optimization'))
    return save_to_calendar(terminId=terminId)

# function to save selected appointment in outlook calendar and database
def save_to_calendar(terminId, api=False, sessiontoken=None, flashmessage=True):
    if api:
        appointments_dict = session.get(sessiontoken)
    else:
        appointments_dict = session.get(str(flask_login.current_user.id)).get('appointments_dict')
    if appointments_dict is None:
        if api:
            return bad_request('Es wurden keine Termine geplant!')
        else:
            flash('Es wurden keine Termine geplant!')
            return redirect(url_for('optimization'))
    termin_db = {}
    for trm in appointments_dict:
        if trm["Termin_ID"] == int(terminId):
            termin_db = trm
            break
    if len(termin_db) < 1:
        if api:
            return bad_request('Die Termin ID existiert nicht!')
        else:
            flash('Die Termin ID existiert nicht')
            return redirect(url_for('optimization'))
    dt_str = f"{termin_db['Date']}T{termin_db['Time']}"
    termin_dt = datetime.strptime(dt_str, "%d.%m.%YT%H:%M")

    # save termin to database
    new_termin = Termin(
        dateTime=termin_dt,
        description=termin_db['bezeichnung'],
        duration=termin_db['dauer'],
        energyconsumption=termin_db['energieverbrauch'],
        gridenergy=termin_db['netzbezug'],
        machines=termin_db['maschinen_string'],
        employees=termin_db['mitarbeiter_string'],
        creationTimeUTC = datetime.utcnow()
        )
    db.session.add(new_termin)
    db.session.commit()

    # create caledar event for all employees and machines in their calendar
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token'],
        'Content-type': 'application/json'
    }

    calendars = termin_db['maschinen'] + termin_db['mitarbeiter']

    for calendar in calendars:
        url = f"https://graph.microsoft.com/v1.0/users/{calendar}/calendar/events"
        graph_start_dt = termin_dt.strftime("%Y-%m-%dT%H:%M")
        graph_end_dt = (termin_dt + timedelta(hours=termin_db['dauer'])).strftime("%Y-%m-%dT%H:%M")

        payload = {
            "subject": termin_db['bezeichnung'],
            "body": {
                "contentType": "HTML",
                "content": "Dieser Termin wurde von https://ebt-pjs.de generiert und blockiert die Maschine / den Mitarbeiter für einen Kundentermin"
            },
            "start": {
                "dateTime": graph_start_dt,
                "timeZone": "Europe/Berlin"
            },
            "end": {
                "dateTime": graph_end_dt,
                "timeZone": "Europe/Berlin"
            },
            "location":{
                "displayName":f"Seho Systems GmbH Showroom, Maschinen: {termin_db['maschinen_string']}"
            }
        }

        requests.post(url=url, headers=head, data=json.dumps(payload))
    if api:
        [session.pop(key) for key in list(session.keys()) if key == sessiontoken]
        return jsonify({'Information': 'Der Termin wurde gespeichert'})
    else:
        [session.pop(key) for key in list(session.keys()) if key == str(flask_login.current_user.id)]
        if flashmessage:
            flash("Ihr Termin wurde im Outlook-Kalender für die involvierten Maschinen & Mitarbeiter gespeichert!")
        return redirect(url_for('optimization'))