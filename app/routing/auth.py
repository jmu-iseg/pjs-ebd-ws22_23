from app import bcrypt, db, app, flash_errors
from app.forms import LoginForm, RegisterForm, ProfileForm, ChangePasswordForm
from app.models import User
import flask_login
from flask_login import login_required, logout_user
from flask import render_template, redirect, url_for, request, session, flash
from werkzeug.utils import secure_filename
import os

# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # only display login form, when a user exists, otherwise show register form
    if User.query.first():
        form = LoginForm()
        # if the login form was valid the user gets logged in and redirected to the home page
        if form.validate_on_submit() and 'loginForm' in request.form:
            return redirect('/')
        elif request.method == "POST" and 'loginForm' in request.form:
            flash_errors(form)
            return redirect('/login')
        return render_template('/pages/login.html', form=form)
    else:
        form = RegisterForm()
        # if the register form was valid and submitted, generate the password hash and create a new user with the form data
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

# profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profilepage():
    username = flask_login.current_user.username
    profileForm = ProfileForm(username=username)
    passwordForm = ChangePasswordForm()

    # if the profile form was valid and submitted, get the corresponding user and change the data that the user wants to change
    if profileForm.validate_on_submit() and 'profileForm' in request.form:
        user = User.query.filter_by(id = flask_login.current_user.id).first()
        # only change the picture when a new one was uploaded
        if profileForm.profilepic.data:
            filename = secure_filename(profileForm.profilepic.data.filename)
            profileForm.profilepic.data.save(os.path.join(app.root_path,'static/img/profile',filename))
            filenameDB = os.path.join('img/profile/',filename)
            user.profilepic = filenameDB
        user.username = profileForm.username.data
        db.session.commit()
        return redirect('/profile')
    elif request.method == "POST" and 'profileForm' in request.form:
        flash_errors(profileForm)
        return redirect('/profile')
    # if the password form was valid and submitted, get the password (password change happens in the validate function of the form)
    if passwordForm.validate_on_submit() and 'passwordForm' in request.form:
        flash('Das Passwort wurde geändert!')
    elif request.method == "POST" and 'passwordForm' in request.form:
        flash_errors(passwordForm)
        return redirect('/profile')

    return render_template('/pages/profil.html', form=profileForm, passwordForm=passwordForm)

# logout route
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    # empty the session when the user logs out
    [session.pop(key) for key in list(session.keys()) if key == str(flask_login.current_user.id)]
    logout_user()
    return redirect(url_for('login'))