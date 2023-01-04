from lib2to3.pgen2.pgen import DFAState
from flask import Flask, jsonify, render_template, request, url_for, flash, redirect, send_file, session, escape, Response
import subprocess
import pandas as pd
import numpy as np
import mysql.connector as sql
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from datetime import datetime, timedelta
import subprocess
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
from app import app

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

class MailForm(FlaskForm):
    mail_server = StringField(validators=[
                           InputRequired()])

    mail_port = StringField(validators=[
                           InputRequired()])

    mail_user = StringField(validators=[
                             InputRequired()])
    
    mail_pw = PasswordField(validators=[
                             InputRequired()])

    submit = SubmitField('Aktualisieren')

# settings route
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def app():
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


    # specify the mail fields
    mail_server = config['mail']['mail_server']
    mail_port = config['mail']['mail_port']
    mail_user = config['mail']['mail_user']
    mail_pw = config['mail']['mail_pw']

    # set the mailForm
    mailForm=MailForm(mail_server=mail_server,mail_port=mail_port,mail_user=mail_user,mail_pw=mail_pw)
    if mailForm.validate_on_submit():
        config['mail']['mail_server'] = mailForm.mail_server.data
        config['mail']['mail_port'] = mailForm.mail_port.data
        config['mail']['mail_user'] = mailForm.mail_user.data
        config['mail']['mail_pw'] = mailForm.mail_pw.data
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
        return render_template('/pages/settings.html', userList=userList, form=form, weatherForm=weatherForm, machineForm=machineForm, mailForm=mailForm)