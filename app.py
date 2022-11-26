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
    db_connection = sql.connect(host='127.0.0.1', database='energy', user='root', password='root', port=8889)
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
    

# take input of start & end date of optimization 
@app.route('/optimization', methods=['POST'])
def get_date():
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    return optimization_table(start_date, end_date)


# optimization route
@app.route('/optimization_table', methods=('GET', 'POST'))
def optimization_table(start_date, end_date):
    # input: Start & End DateTime (Zeitraum der Planung)
    

    # input: Daten dieses Zeitraums aus MySQL DB

    # read data 
    db_connection = sql.connect(host='127.0.0.1', database='energy', user='root', password='root', port=8889)
    query = "SELECT dateTime, output, basicConsumption, managementConsumption, productionConsumption FROM sensor"
    df = pd.read_sql(query,db_connection)
    db_connection.close()

    # parse dates  
    df['dateTime'] = pd.to_datetime(df.dateTime)  # parse timestamps

    start_datetime = datetime.strptime(start_date, '%d.%m.%Y')
    end_datetime = datetime.strptime(end_date, '%d.%m.%Y')
    
    print(start_datetime)
    print(end_datetime)

    #df['dateTime'] = df['dateTime'].dt.strftime('%d.%m.%Y %H:%M:%S') # use later for better output
    #start_date = start_date.dt.strftime('%Y.%m.%d %H:%M:%S')
    #end_date = end_date.dt.strftime('%Y.%m.%d %H:%M:%S')
    
    #end_date = pd.to_datetime(end_date, format="%Y-%m-%d %H:%M")
    #print(start_date)
    #print(end_date)


    # select planing period of 2 weeks, starting with monday 
    df = df[(df['dateTime'] >= start_date) & (df['dateTime'] <= end_date)]
    
    print(df)

    # calculate netzbezug
    df['balance'] = (df['basicConsumption'] + df['managementConsumption'] + df['productionConsumption']) - df['output']
    df = df.drop(['basicConsumption', 'managementConsumption', 'productionConsumption', 'output'], axis=1)

    # reformat day and hour 
    df['hour'] = df['dateTime'].dt.hour
    n=24
    df['day'] = [int(i/n) for i,x in enumerate(df.index)]
    netzbezug = df

    # set planning times of 2 weeks 
    days = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]
    hours = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
                            
    # read appointment data
    termine_df = pd.read_csv('streaming_data_platform/termine.csv', sep=";")
    termine_energy = dict(termine_df[['Termin','Energieverbrauch']].values) 
    termine_length = dict(termine_df[['Termin','Dauer']].values)
    
    # create model 
    model = gp.Model("energy based scheduling")

    # create variables 
    # energy consumption per appointment
    consumption = model.addVars(days,hours,termine_energy,vtype=GRB.CONTINUOUS,name="consumption")

    # planned start of appointment 
    start = model.addVars(consumption, vtype=GRB.BINARY, name="start")
    end = model.addVars(consumption, vtype=GRB.BINARY, name="end")

    # save start day und hour as numerical value
    start_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_hour")
    start_day = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="start_day")

    # save end hour as numerical value 
    end_hour = model.addVars(termine_energy,vtype=GRB.CONTINUOUS,name="end_hour")

    # hilfsvariable
    p = model.addVars(days,hours,termine_energy,vtype=GRB.BINARY,name="p")

    # calculate netzbezug while appointment
    # calculate netzbezug of appointment
    for termin in termine_energy:
        for day in days: 
            for hour in range(0,18):
                for i in range(0,termine_length[termin]):
                    consumption[day,hour,termin] = consumption[day,hour,termin]+netzbezug['balance'][(netzbezug['day'] == day) & (netzbezug['hour'] == hour+i)]+(termine_energy[termin]/termine_length[termin])              

    # minimize netzbezug
    obj = gp.quicksum((consumption[day,hour,termin]*start[day,hour,termin])
                 for day in days for hour in hours for termin in termine_energy)

    # objective 
    model.setObjective(obj, GRB.MINIMIZE)

    # constraints 
    # weekend constraint
    for termin in termine_energy:
        for hour in hours:
            for day in days:
                if day in [5,6,12,13]: 
                    model.addConstr((start[day,hour,termin])==0)
                    
    # only 1 start time per appointment
    for termin in termine_energy: 
        model.addConstr(gp.quicksum(start[day,hour,termin] 
                        for day in days for hour in hours) == 1)

    # no overlap constraint                
    for day in days: 
        for hour in hours:
            if hour < 18:
                for t1 in termine_length: 
                    model.addConstr((start[day,hour,t1] == 1) >> (gp.quicksum(start[day,hour+i,t2] 
                                                                    for i in range(1,termine_length[t1])
                                                                    for t2 in termine_length)==0))
                    
    # no overlap of start times 
    for day in days:
        for hour in hours:
            model.addConstr(start[day,hour,0]+start[day,hour,1]+start[day,hour,2]<=1)
                
    # save start hour and day of appointment 
    for termin in termine_energy: 
        for day in days: 
            for hour in hours:
                model.addConstr((start[day,hour,termin]==1) >> (start_day[termin]==day))
                model.addConstr((start[day,hour,termin]==1) >> (start_hour[termin]==hour))

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
    appointments = pd.DataFrame(columns=['Termin', 'Start_Day', 'Start_Hour'])
    for v in model.getVars():
        if v.VarName.startswith("start_day"): 
            appointments = appointments.append({'Termin':v.VarName, 'Start_Day':int(v.X)}, ignore_index=True)                
        if v.VarName.startswith("start_hour"):
            appointments = appointments.append({'Termin':v.VarName, 'Start_Hour':int(v.X)}, ignore_index=True)

    # reformat dataframe
    appointments['Termin'] = appointments['Termin'].map(lambda x: x.lstrip('start_hourday[').rstrip(']'))
    appointments = appointments.groupby(by="Termin").sum().reset_index()

    # merge with dataframe with timestamps
    start_times = pd.merge(netzbezug, appointments,  how='left', left_on=['hour','day'], right_on = ['Start_Hour','Start_Day']).dropna()
    start_times = start_times.drop(['balance', 'Start_Day', 'Start_Hour', 'hour', 'day'], axis=1)
    start_times = start_times.rename(columns={'dateTime': 'Start_DateTime'}) # rename column
    start_times = start_times.sort_values(by="Termin")
    #start_times.to_csv('optimized.csv')
    start_times['Start_Date'] = start_times['Start_DateTime'].dt.date
    start_times['Start_Time'] = start_times['Start_DateTime'].dt.time


    
    # output: csv/anderes Format mit optimierten Terminen --> render_template in Tabelle 

    return render_template("optimization_table.html", termin=start_times['Termin'].tolist(), start_date=start_times['Start_Date'].tolist(), start_time=start_times['Start_Time'].tolist())
    
if __name__ == "__main__":
    app.run()
