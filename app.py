#from crypt import methods
from lib2to3.pgen2.pgen import DFAState
from flask import Flask, jsonify, render_template, request, url_for, flash, redirect
import pandas as pd
import numpy as np
import mysql.connector as sql
import gurobipy as gp
from gurobipy import GRB
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import datetime
from datetime import datetime
import subprocess

# Create the Webserver
app = Flask(__name__)
   
# home route 
@app.route('/')
def home():
    return render_template("home.html")

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

    return render_template("dashboard.html", labels=df['dateTime'].tolist(), output=df['output'].tolist(), bConsum=df['basicConsumption'].tolist(), mConsum=df['managementConsumption'].tolist(), pConsum=df['productionConsumption'].tolist())

# optimization route
@app.route('/optimization')
def optimization():
    # input: Start & End DateTime (Zeitraum der Planung)
    

    return render_template("optimization.html")
    
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

    # read appointment data
    termine_df = pd.read_csv('/var/www/PJS/termine.csv', sep=";")
    termine_energy = dict(termine_df[['Termin','Energieverbrauch']].values) 
    termine_length = dict(termine_df[['Termin','Dauer']].values)
    
    with gp.Env(empty=True) as env:
        env.setParam('WLSACCESSID', '9b407e02-8567-441b-aaab-53e6d5e7bff6')
        env.setParam('WLSSECRET', '35167c90-8a1b-41e4-b736-46a476c67d3d')
        env.setParam('LICENSEID', 905984)
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
            
            # to do: die optimierten Termine in DB speichern

            # parse to datetime format
            appointments['Date'] = pd.to_datetime(appointments['Date'], format="%Y.%m.%d")
            appointments['Time'] = pd.to_datetime(appointments['Time'], format="%H:%M:%S")

            # change format of date and time 
            appointments['Date'] = appointments.Date.dt.strftime('%d.%m.%Y')
            appointments['Time'] = appointments.Time.dt.strftime('%H:%M')

            return render_template("optimization_table.html", termin=appointments['TerminID'].tolist(), start_date=appointments['Date'].tolist(), start_time=appointments['Time'].tolist())
    
if __name__ == "__main__":
    app.run(debug=True)
