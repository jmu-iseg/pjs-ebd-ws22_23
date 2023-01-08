from app import bcrypt, db, app, flash_errors
from app.forms import LoginForm, RegisterForm, ProfileForm
from app.models import User
import flask_login
from flask_login import login_required, logout_user
from flask import render_template, redirect, url_for, request
from werkzeug.utils import secure_filename
import os

@app.route('/login', methods=['GET', 'POST'])
def login():
    if User.query.first():
        form = LoginForm()
        if form.validate_on_submit() and 'loginForm' in request.form:
            return redirect('/')
        elif request.method == "POST" and 'loginForm' in request.form:
            flash_errors(form)
            return redirect('/login')
        return render_template('/pages/login.html', form=form)
    else:
        form = RegisterForm()
        if form.validate_on_submit() and 'registerForm' in request.form:
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
        elif request.method == "POST" and 'registerForm' in request.form:
            flash_errors(form)
            return redirect('/login')
        return render_template('/pages/register.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profilepage():
    username = flask_login.current_user.username
    profileForm = ProfileForm(username=username)

    if profileForm.validate_on_submit() and 'profileForm' in request.form:
        user = User.query.filter_by(id = flask_login.current_user.id).first()
        if profileForm.profilepic.data:
            filename = secure_filename(profileForm.profilepic.data.filename)
            profileForm.profilepic.data.save(os.path.join(app.root_path,'static/img/profile',filename))
            filenameDB = os.path.join('img/profile/',filename)
            user.profilepic = filenameDB
        user.username = profileForm.username.data
        user.password = bcrypt.generate_password_hash(profileForm.password.data)
        db.session.commit()
        return redirect('/profile')
    elif request.method == "POST" and 'profileForm' in request.form:
        flash_errors(profileForm)
        return redirect('/profile')
    return render_template('/pages/profil.html', form=profileForm)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))