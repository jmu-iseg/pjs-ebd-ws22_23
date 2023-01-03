#from crypt import methods
from lib2to3.pgen2.pgen import DFAState
from flask import Flask, jsonify, render_template, request, url_for, flash, redirect, send_file, session, escape, Response
import subprocess
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
import configparser
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
import flask_login
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

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
    role = db.Column(db.String(20))
    password = db.Column(db.String(80), nullable=False)
    profilepic = db.Column(db.String(100))

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    
    role = SelectField(u'role', choices=[('0', 'Admin'), ('1', 'Standard')])

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

class ProfileForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    
    profilepic = FileField()

    submit = SubmitField('Aktualisieren')

class WeatherForm(FlaskForm):
    apikey = StringField(validators=[
                           InputRequired()])

    lat = StringField(validators=[
                             InputRequired()])
    
    lon = StringField(validators=[
                             InputRequired()])

    submit = SubmitField('Aktualisieren')

    def validate_apikey(self, apikey):
        def is_ascii(s):
            return all(ord(c) < 128 for c in s)
        if not is_ascii(apikey.data):
            raise ValidationError("ASCII - Characters only")

class MachineForm(FlaskForm):
    consumption_m1 = StringField(validators=[
                           InputRequired()])

    consumption_m2 = StringField(validators=[
                             InputRequired()])
    
    consumption_m3 = StringField(validators=[
                             InputRequired()])

    submit = SubmitField('Aktualisieren')

def flash_errors(form):
    """Flashes form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

@app.context_processor
def inject_userdata():
    values = {}
    if flask_login.current_user.is_authenticated != True:
        values['username'] = "NotLoggedIn"
        values['userrole'] = "NoRole"
        values['userid'] = "NoID"
        return values
    else:
        values['username'] = flask_login.current_user.username
        values['userrole'] = flask_login.current_user.role
        values['userid'] = flask_login.current_user.id
        if flask_login.current_user.profilepic is None:
            values['profilepic'] = 'img/img1234.jpg'
        else:
            values['profilepic'] = flask_login.current_user.profilepic
        return values

# read settings
config = configparser.ConfigParser()
config.read(os.path.join(app.root_path,'settings.cfg'))

# home route 
@app.route('/')
@login_required
def home():
    return render_template("/pages/home.html")

# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if User.query.first():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                if bcrypt.check_password_hash(user.password, form.password.data):
                    login_user(user)
                    return redirect('/')
        return render_template('/pages/login.html', form=form)
    else:
        form = RegisterForm()

        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')

        return render_template('/pages/register.html', form=form)

# 404 route
@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('/pages/404.html'), 404

# profle route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profilepage():
    username = flask_login.current_user.username
    form = ProfileForm(username=username)

    if form.validate_on_submit():
        filename = secure_filename(form.profilepic.data.filename)
        form.profilepic.data.save(os.path.join(app.root_path,'static/img/profile',filename))
        filenameDB = os.path.join('img/profile',filename)
        user = User.query.filter_by(id = flask_login.current_user.id).first()
        user.username = form.username.data
        user.password = bcrypt.generate_password_hash(form.password.data)
        user.profilepic = filenameDB

        db.session.commit()
        return redirect('/profile')
    return render_template('/pages/profil.html', form=form)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# logout route
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# settings route
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    role = flask_login.current_user.role
    
    # specify the location
    lat = config['weather']['lat']
    lon = config['weather']['lon']

    # specify the api key
    apikey = config['weather']['openweatherapikey']

    # set the weatherForm
    weatherForm=WeatherForm(apikey=apikey,lat=lat,lon=lon)
    if weatherForm.validate_on_submit():
        config['weather']['lat'] = weatherForm.lat.data
        config['weather']['lon'] = weatherForm.lon.data
        config['weather']['openweatherapikey'] = weatherForm.apikey.data
        with open(os.path.join(app.root_path,'settings.cfg'), 'w') as configfile:
            config.write(configfile)
        return redirect('/settings')
    
     # specify the location
    consumption_m1 = config['machines']['consumption_m1']
    consumption_m2 = config['machines']['consumption_m2']
    consumption_m3 = config['machines']['consumption_m3']

    # set the machineForm
    machineForm=MachineForm(consumption_m1=consumption_m1,consumption_m2=consumption_m2,consumption_m3=consumption_m3)
    if machineForm.validate_on_submit():
        config['machines']['consumption_m1'] = machineForm.consumption_m1.data
        config['machines']['consumption_m2'] = machineForm.consumption_m2.data
        config['machines']['consumption_m3'] = machineForm.consumption_m3.data
        with open(os.path.join(app.root_path,'settings.cfg'), 'w') as configfile:
            config.write(configfile)
        return redirect('/settings')

    if role != "0":
        return redirect('/')
        
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/settings')

    # change user roles
    if 'entry' in request.args:
        User.query.filter_by(id = request.args.get('entry')).delete()
        db.session.commit()
    elif 'downgrade' in request.args:
        user = User.query.filter_by(id = request.args.get('downgrade')).first()
        user.role = "1"
        db.session.commit()
    elif 'upgrade' in request.args:
        user = User.query.filter_by(id = request.args.get('upgrade')).first()
        user.role = "0"
        db.session.commit()

    if request.method == 'POST':
        # Update the settings based on the form data
        name = request.form['name']
        update_settings(request.form)
        return redirect('/settings')
    else:
        # get list of every user
        userList = User.query.all()

        # Render the settings template
        return render_template('/pages/settings.html', userList=userList, form=form, weatherForm=weatherForm, machineForm=machineForm)


def update_settings(form_data):
    # Update the settings in the database or file system
    pass

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

termine = {}
# optimization route
@app.route('/optimization')
@login_required
def optimization():
    termine.clear()
    return render_template("/pages/optimization.html")
    
# reload route
@app.route('/reload_webapp')
@login_required
def reload():
    subprocess.run('sudo chmod 777 update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    subprocess.run('/var/www/PJS/update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    return redirect('/')

# diese route wird vermutlich nicht gebraucht, da reload_webapp funktioniert 
@app.route('/run_script', methods=['POST'])
def run_script():
    # Call the Python shell script and get the output
    # TODO
    subprocess.run('sudo chmod 777 update_files.sh', shell=True, check=True, text=True, cwd='/var/www/PJS/')
    output = subprocess.run(['bash', '/var/www/PJS/update_files.sh'], shell=True, check=True, text=True, cwd='/var/www/PJS/', capture_output=True)
    print("run script")
    return output.stdout

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
        return optimization_table(start_date, end_date)
    
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
    termine_df_neu['maschine1'].loc[termine_df_neu['maschinen'].str.contains('Wellenlöt')] = 1
    termine_df_neu['maschine2'].loc[termine_df_neu['maschinen'].str.contains('Lötbad3/4')] = 1
    termine_df_neu['maschine3'].loc[termine_df_neu['maschinen'].str.contains('Lötbad5')] = 1
    termine_df_neu['maschine1'].loc[(termine_df_neu['maschine1'].isnull())] = 0
    termine_df_neu['maschine2'].loc[(termine_df_neu['maschine2'].isnull())] = 0
    termine_df_neu['maschine3'].loc[(termine_df_neu['maschine3'].isnull())] = 0

    # define energy consumption per machine (TODO: Later via user input data )    
    consumption_m1 = config['machines']['consumption_m1']
    consumption_m2 = config['machines']['consumption_m2']
    consumption_m3 = config['machines']['consumption_m3']

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
                for datetime in df['dateTime']:
                    if datetime.hour < 18:
                        for i in range(0,termine_length[termin]):
                            if float(netzbezug['balance'][netzbezug['dateTime'] == datetime + pd.Timedelta(hours=i)]) < 0:
                                consumption[datetime,termin] = consumption[datetime,termin] + netzbezug['balance'][netzbezug['dateTime'] == datetime + pd.Timedelta(hours=i)] + (termine_energy[termin]/termine_length[termin])
                            else: 
                                consumption[datetime,termin] = consumption[datetime,termin] + termine_energy[termin]/termine_length[termin]

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

            return render_template("/pages/optimization_table.html", my_list=appointments_dict, obj_value=obj_value, renewable_percent=renewable_percent, energy_consumption=energy_consumption, energy_consumption_list=energy_consumption_list, termin_list=termin_list, netzbezug_termine=netzbezug_termine, netzbezug_termine_percent=netzbezug_termine_percent)

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
    organizer.params['role'] = vText('CEO of Uni Wuerzburg') # ein Macher
    event['organizer'] = organizer
    event['location'] = vText('Würzburg, DE')
    cal.add_component(event)
    buf = io.BytesIO()
    buf.write(cal.to_ical())
    buf.seek(0)
    return send_file(buf, download_name=filename)
            
if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)
