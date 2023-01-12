from app import app, bcrypt, db, flash_errors, get_config, write_config
import flask_login
from flask_login import login_required
from app.forms import WeatherForm, MachineForm, MailForm, RegisterForm, KafkaForm
from app.models import User
from flask import redirect, render_template, request
from kafka import KafkaConsumer, KafkaProducer

# read settings
config = get_config(app.root_path)

# settings route
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    role = flask_login.current_user.role
    if role != "0":
        return redirect('/')
    
    # specify the location
    lat = config['weather']['lat']
    lon = config['weather']['lon']

    # specify the api key
    apikey = config['weather']['openweatherapikey']

    # set the weatherForm
    weatherForm=WeatherForm(apikey=apikey,lat=lat,lon=lon)
    if weatherForm.validate_on_submit() and 'weatherForm' in request.form:
        config['weather']['lat'] = weatherForm.lat.data
        config['weather']['lon'] = weatherForm.lon.data
        config['weather']['openweatherapikey'] = weatherForm.apikey.data
        write_config(app.root_path, config)
        return redirect('/settings')
    elif request.method == "POST" and 'weatherForm' in request.form:
        flash_errors(weatherForm)
        return redirect('/settings')
    
     # specify the location
    consumption_m1 = config['machines']['consumption_m1']
    consumption_m2 = config['machines']['consumption_m2']
    consumption_m3 = config['machines']['consumption_m3']

    # set the machineForm
    machineForm=MachineForm(consumption_m1=consumption_m1,consumption_m2=consumption_m2,consumption_m3=consumption_m3)
    if machineForm.validate_on_submit() and 'machineForm' in request.form:
        config['machines']['consumption_m1'] = machineForm.consumption_m1.data
        config['machines']['consumption_m2'] = machineForm.consumption_m2.data
        config['machines']['consumption_m3'] = machineForm.consumption_m3.data
        write_config(app.root_path, config)
        return redirect('/settings')
    elif request.method == "POST" and 'weatherForm' in request.form:
        flash_errors(machineForm)
        return redirect('/settings')

    # specify the mail fields
    mail_server = config['mail']['mail_server']
    mail_port = config['mail']['mail_port']
    mail_user = config['mail']['mail_user']
    mail_pw = config['mail']['mail_pw']
    mail_sender = config['mail']['mail_sender']

    # set the mailForm
    mailForm=MailForm(mail_server=mail_server,mail_port=mail_port,mail_user=mail_user,mail_pw=mail_pw, mail_sender=mail_sender)
    if mailForm.validate_on_submit() and 'mailForm' in request.form:
        config['mail']['mail_server'] = mailForm.mail_server.data
        config['mail']['mail_port'] = mailForm.mail_port.data
        config['mail']['mail_user'] = mailForm.mail_user.data
        if mailForm.mail_pw.data:
            config['mail']['mail_pw'] = mailForm.mail_pw.data
        config['mail']['mail_sender'] = mailForm.mail_sender.data
        write_config(app.root_path, config)
        return redirect('/settings')
    elif request.method == "POST" and 'mailForm' in request.form:
        flash_errors(mailForm)
        return redirect('/settings')

        
    registerForm = RegisterForm()
    if registerForm.validate_on_submit() and 'registerForm' in request.form:
        hashed_password = bcrypt.generate_password_hash(registerForm.password.data)
        new_user = User(username=registerForm.username.data, password=hashed_password, role=registerForm.role.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/settings')
    elif request.method == "POST" and 'registerForm' in request.form:
        flash_errors(mailForm)
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

    # get list of every user
    userList = User.query.all()

     # specify the kafka config
    kafka_url = config['kafka']['kafka_url']
    kafka_port = config['kafka']['kafka_port']

    # set the kafkaForm
    kafkaForm=KafkaForm(kafka_url=kafka_url,kafka_port=kafka_port)
    if kafkaForm.validate_on_submit() and 'kafkaForm' in request.form:
        config['kafka']['kafka_url'] = kafkaForm.kafka_url.data
        config['kafka']['kafka_port'] = kafkaForm.kafka_port.data
        write_config(app.root_path, config)
        return redirect('/settings')
    elif request.method == "POST" and 'kafkaForm' in request.form:
        flash_errors(kafkaForm)
        return redirect('/settings')

    # Check the Kafka-Status
    kafka_status = 0
    
    try:
        consumer = KafkaConsumer(bootstrap_servers=[kafka_url+':'+kafka_port])
        print("Kafka broker is running")
        kafka_status = 1
    except:
        print("Kafka broker is not running or not reachable")
        kafka_status = 2

    # Render the settings template
    return render_template('/pages/settings.html', userList=userList, form=registerForm, weatherForm=weatherForm, machineForm=machineForm, mailForm=mailForm, kafkaForm=kafkaForm, kafka_status=kafka_status)