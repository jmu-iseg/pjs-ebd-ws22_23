from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField, HiddenField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError
from app.models import User
from app import bcrypt

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    role = SelectField(u'role', choices=[('0', 'Admin'), ('1', 'Standard')])

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register', name='registerForm', id='submit')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login', name='loginForm', id='submit')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        user = User.query.filter_by(username=self.username.data).first()
        if user:
            if not bcrypt.check_password_hash(user.password, self.password.data):
                self.password.errors.append('Das Passwort ist falsch')
                return False
        else:
            self.username.errors.append('Der Benutzer existiert nicht')
            return False
        return True

class ProfileForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    profilepic = FileField()

    submit = SubmitField('Aktualisieren', name='profileForm', id='submit')


class SendMailForm(FlaskForm):
    mailAddress = StringField(validators=[
        InputRequired()], render_kw={"placeholder": "Adressen"})

    mailText = TextAreaField(validators=[
                             InputRequired()], render_kw={"placeholder": "Nachricht"})

    dauer = HiddenField()
    bezeichnung = HiddenField()
    date = HiddenField()
    time = HiddenField()
    terminID = HiddenField()

    submit = SubmitField('Absenden', name='sendMailForm', id='submit')


class WeatherForm(FlaskForm):
    apikey = StringField(validators=[
        InputRequired()])

    lat = StringField(validators=[
        InputRequired()])

    lon = StringField(validators=[
        InputRequired()])

    submit = SubmitField('Aktualisieren', name='weatherForm', id='submit')

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

    submit = SubmitField('Aktualisieren', name='machineForm', id='submit')


class MailForm(FlaskForm):
    mail_server = StringField(validators=[
        InputRequired()])

    mail_port = StringField(validators=[
        InputRequired()])

    mail_user = StringField(validators=[
        InputRequired()])

    mail_pw = PasswordField(validators=[
        InputRequired()])

    mail_sender = StringField(validators=[
        InputRequired()])

    submit = SubmitField('Aktualisieren', name='mailForm', id='submit')
