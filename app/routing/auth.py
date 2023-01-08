from app import bcrypt, db, app, flash_errors
from app.forms import LoginForm, RegisterForm, ProfileForm
from app.models import User
import flask_login
from flask_login import login_user, login_required, logout_user
from flask import render_template, redirect, url_for, flash, request
from werkzeug.utils import secure_filename
import os

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
        elif request.method == "POST":
            flash_errors(form)
            return redirect('/login')
        return render_template('/pages/login.html', form=form)
    else:
        form = RegisterForm()

        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
        elif request.method == "POST":
            flash_errors(form)
            return redirect('/login')
        return render_template('/pages/register.html', form=form)

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

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))