#from crypt import methods
from lib2to3.pgen2.pgen import DFAState
from flask import Flask, jsonify, render_template, request, url_for, flash, redirect, send_file
import pandas as pd
import numpy as np
import mysql.connector as sql
import gurobipy as gp
from gurobipy import GRB
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
import subprocess
from icalendar import Calendar, Event, vCalAddress, vText
import io

# Create the Webserver
template_dir = os.path.abspath('templates')
app = Flask(__name__, template_folder=template_dir)
   
# home route 
@app.route('/')
def home():
    return render_template("/pages/home.html")

# dashboard route   
@app.route('/dashboard')
def dashboard():
    #Executing SQL Statements
    db_connection = sql.connect(host='localhost', database='energy', user='energy', password='PJS2022', port=3306)
    query = "SELECT dateTime, output, basicConsumption, managementConsumption, productionConsumption FROM sensor"
    df = pd.read_sql(query,db_connection)
    db_connection.close()
    
    
    # filter time (todo: dynamic with user input)
    df = df[(df['dateTime'] >= '2022-07-04 00:00:00') & (df['dateTime'] <= '2022-07-06 23:00:00')]

    return render_template("templates/pages/dashboard.html", labels=df['dateTime'].tolist(), output=df['output'].tolist(), bConsum=df['basicConsumption'].tolist(), mConsum=df['managementConsumption'].tolist(), pConsum=df['productionConsumption'].tolist())

# optimization route
@app.route('/optimization')
def optimization():
    # input: Start & End DateTime (Zeitraum der Planung)
    

    return render_template("templates/pages/optimization.html")
    
@app.route('/reload_webapp')
def reload():
    subprocess.run('/var/www/PJS/update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    return redirect('/')

# take input of start & end date of optimization 
@app.route('/optimization', methods=['POST'])
def get_date():
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    return optimization_table(start_date, end_date)


termine = {}
@app.route('/add_termin', methods=['GET', 'POST'])
def add_termin():
    id = request.form['id']
    bezeichnung = request.form['bezeichnung']
    dauer = request.form['dauer']
    termine[id] = {'bezeichnung': bezeichnung, 'dauer': int(dauer)}
    return print("")
    

@app.route('/delete_termin', methods=['GET', 'POST'])
def delete_termin():
    id = request.form['id']
    termine.pop(id, None)
    return print('termin_deleted')


# optimization route
@app.route('/optimization_table', methods=('GET', 'POST'))
def optimization_table(start_date, end_date):
    # input date range
    start_date = pd.to_datetime(start_date, format="%d.%m.%Y")
    end_date = pd.to_datetime(end_date, format="%d.%m.%Y").replace(hour=23, minute=00) # set hour of end date to 23:00
    
    # db query
    db_connection = sql.connect(host='localhost', database='energy', user='energy', password='PJS2022', port=3306)
    query = "SELECT dateTime, output, basicConsumption, managementConsumption, productionConsumption FROM sensor"
    df = pd.read_sql(query,db_connection)
    db_connection.close()
    df['dateTime'] = pd.to_datetime(df.dateTime)  

    # select planing period
    df = df[(df['dateTime'] >= start_date) & (df['dateTime'] <= end_date)]
    print(df)

    # calculate netzbezug
    df['balance'] = (df['basicConsumption'] + df['managementConsumption'] + df['productionConsumption']) - df['output']
    netzbezug = df.drop(['basicConsumption', 'managementConsumption', 'productionConsumption', 'output'], axis=1)

    # take termin input data 
    termine_df_neu = pd.DataFrame.from_dict(termine, orient='index', columns=['bezeichnung', 'dauer'])
    termine_df_neu = termine_df_neu.reset_index().rename(columns={'index': 'termin_id'})
    termine_df_neu['energieverbrauch'] = termine_df_neu['dauer'] * 20
    
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

            # calculate netzbezug while appointment
            for termin in termine_energy:
                for datetime in df['dateTime']:
                    if datetime.hour < 18:
                        consumption[datetime,termin] = gp.quicksum(netzbezug['balance'][netzbezug['dateTime'] == datetime + pd.Timedelta(hours=i)] + (termine_energy[termin]/termine_length[termin]) 
                                                            for i in range(0,termine_length[termin]))

            # minimize netzbezug
            obj = sum((consumption[datetime,termin]*start[datetime,termin])
                        for datetime in df['dateTime'] for termin in termine_energy)

            # objective 
            model.setObjective(obj, GRB.MINIMIZE)

            # constraints 
            # weekend constraint
            for termin in termine_energy:
                for datetime in df['dateTime']:
                    if datetime.weekday() in [5,6]:
                        model.addConstr((start[datetime,termin])==0)
                            
            # only 1 start time per appointment
            for termin in termine_energy: 
                model.addConstr(gp.quicksum(start[datetime,termin] 
                                for datetime in df['dateTime']) == 1)

            # no overlap constraint                
            for datetime in df['dateTime']:
                if datetime.hour < 18:
                        for t1 in termine_length: 
                            model.addConstr((start[datetime,t1] == 1) >> (gp.quicksum(start[datetime + pd.Timedelta(hours=i),t2] 
                                                                            for i in range(1,termine_length[t1])
                                                                            for t2 in termine_length)==0))                

            # no overlap of start times 
            for datetime in df['dateTime']:
                model.addConstr(gp.quicksum(start[datetime,termin] for termin in termine_energy) <= 1)
                        
            # save start hour and day of appointment 
            for termin in termine_energy: 
                for datetime in df['dateTime']:
                    model.addConstr((start[datetime,termin]==1) >> (start_day[termin]==datetime.day))
                    model.addConstr((start[datetime,termin]==1) >> (start_hour[termin]==datetime.hour))

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
            appointments = appointments.drop('Termin', axis=1)
            appointments = appointments.drop('DateTime', axis=1)
            appointments = appointments.sort_values(by="TerminID")

            # join appointments with termine_df_neu
            appointments_output = pd.merge(appointments, termine_df_neu, how='left', left_on=['TerminID'], right_on=['termin_id'])
            appointments_output.drop(['termin_id','energieverbrauch'], axis=1)

            # parse to datetime format
            appointments_output['Date'] = pd.to_datetime(appointments_output['Date'], format="%Y.%m.%d")
            appointments_output['Time'] = pd.to_datetime(appointments_output['Time'], format="%H:%M:%S")

            # change format of date and time 
            appointments_output['Date'] = appointments_output.Date.dt.strftime('%d.%m.%Y')
            appointments_output['Time'] = appointments_output.Time.dt.strftime('%H:%M')
            
            # to do: die optimierten Termine in DB speichern

            # df to dict as output for render template 
            appointments_dict = appointments_output.to_dict('records')

            return render_template("templates/pages/optimization_table.html", my_list=appointments_dict)

@app.route('/return-files')
def return_files_calendar():
    starttime = "{} {}".format(request.args.get('datum'), request.args.get('uhrzeit'))
    starttime_formatted = datetime.strptime(starttime, '%d.%m.%Y %H:%M')
    endtime_formatted = starttime_formatted + timedelta(hours=float(request.args.get('dauer')))
    filename = "Termineinladung {}.ics".format(request.args.get('id'))
    cal = Calendar()
    event = Event()
    event.add('summary', request.args.get('bezeichnung'))
    event.add('dtstart', starttime_formatted)
    event.add('dtend', endtime_formatted)
    organizer = vCalAddress('MAILTO:hannes.metz@stud-mail.uni-wuerzburg.de')
    organizer.params['cn'] = vText('Hannes Metz')
    organizer.params['role'] = vText('CEO of Uni Wuerzburg')
    event['organizer'] = organizer
    event['location'] = vText('Würzburg, DE')
    cal.add_component(event)
    buf = io.BytesIO()
    buf.write(cal.to_ical())
    buf.seek(0)
    return send_file(buf, download_name=filename)
            
if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)
