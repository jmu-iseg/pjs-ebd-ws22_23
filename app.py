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
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt

# Create the Webserver
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

# home route 
@app.route('/')
def home():
    return render_template("/pages/home.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect('/')
    return render_template('/pages/login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/')

    return render_template('/pages/register.html', form=form)

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

# optimization route
@app.route('/optimization')
@login_required
def optimization():
    return render_template("/pages/optimization.html")
    
@app.route('/reload_webapp')
def reload():
    subprocess.run('sudo chmod 777 update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    subprocess.run('/var/www/PJS/update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    return redirect('/')

# take input of start & end date of optimization 
@app.route('/optimization', methods=['POST'])
@login_required
def get_date():
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    return optimization_table(start_date, end_date)


termine = {}
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

    return print("")
    

@app.route('/delete_termin', methods=['GET', 'POST'])
@login_required
def delete_termin():
    id = request.form['id']
    termine.pop(id, None)
    return print('termin_deleted')


# optimization route
@app.route('/optimization_table', methods=('GET', 'POST'))
@login_required
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
    termine_df_neu['maschine1'].loc[termine_df_neu['maschinen'].str.contains('Maschine1')] = 1
    termine_df_neu['maschine2'].loc[termine_df_neu['maschinen'].str.contains('Maschine2')] = 1
    termine_df_neu['maschine3'].loc[termine_df_neu['maschinen'].str.contains('Maschine3')] = 1
    termine_df_neu['maschine1'].loc[(termine_df_neu['maschine1'].isnull())] = 0
    termine_df_neu['maschine2'].loc[(termine_df_neu['maschine2'].isnull())] = 0
    termine_df_neu['maschine3'].loc[(termine_df_neu['maschine3'].isnull())] = 0

    # define energy consumption per machine (TODO: Later via user input data )    
    consumption_m1 = 50
    consumption_m2 = 30
    consumption_m3 = 20

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

            # transform maschinen for better output 
            appointments_output['maschinen'] = appointments_output['maschinen'].str.replace(",",", ")
            
            # df to dict as output for render template 
            appointments_dict = appointments_output.to_dict('records')

            # TODO: die optimierten Termine in DB speichern


            return render_template("/pages/optimization_table.html", my_list=appointments_dict)

@app.route('/return-files')
@login_required
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
