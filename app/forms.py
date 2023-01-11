from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField, HiddenField, TextAreaField, DateField, FieldList, SelectMultipleField, IntegerField, FormField
from wtforms.validators import InputRequired, Length, ValidationError
from app.models import User
from app import bcrypt
from flask_login import login_user

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"}, label='Benutzername')

    role = SelectField(choices=[('0', 'Admin'), ('1', 'Standard')], label='Rolle')

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Passwort')

    submit = SubmitField('Register', name='registerForm', id='submit')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError('Der Benutzername existiert bereits.')

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"}, label='Benutzername')

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Passwort')

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
        login_user(user)
        return True

class ProfileForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"}, label='Benutzername')

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Passwort')

    val_password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Passwort wiederholen')

    profilepic = FileField(label='Profilbild')

    submit = SubmitField('Aktualisieren', name='profileForm', id='submit')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        if not self.password.data == self.val_password.data:
            self.password.errors.append('Die Passwörter stimmen nicht überein')
            return False
        return True


class SendMailForm(FlaskForm):
    mailAddress = StringField(validators=[
        InputRequired()], render_kw={"placeholder": "Adressen"}, label='Mailaddressen')

    mailText = TextAreaField(validators=[
                             InputRequired()], render_kw={"placeholder": "Nachricht"}, label='Mail-Text')

    dauer = HiddenField()
    bezeichnung = HiddenField()
    date = HiddenField()
    time = HiddenField()
    terminID = HiddenField()

    submit = SubmitField('Absenden', name='sendMailForm', id='submit')


class WeatherForm(FlaskForm):
    apikey = StringField(validators=[
        InputRequired()], label='API-Schlüssel')

    lat = StringField(validators=[
        InputRequired()], label='Latitude')

    lon = StringField(validators=[
        InputRequired()], label='Longitude')

    submit = SubmitField('Aktualisieren', name='weatherForm', id='submit')

    def validate_apikey(self, apikey):
        def is_ascii(s):
            return all(ord(c) < 128 for c in s)
        if not is_ascii(apikey.data):
            raise ValidationError("Bitte geben Sie valide Zeichen an.")


class MachineForm(FlaskForm):
    consumption_m1 = StringField(validators=[
        InputRequired()], label='Verbrauch Maschine 1')

    consumption_m2 = StringField(validators=[
        InputRequired()], label='Verbrauch Maschine 2')

    consumption_m3 = StringField(validators=[
        InputRequired()], label='Verbrauch Maschine 3')

    submit = SubmitField('Aktualisieren', name='machineForm', id='submit')


class MailForm(FlaskForm):
    mail_server = StringField(validators=[
        InputRequired()], label='Mail-Server')

    mail_port = StringField(validators=[
        InputRequired()], label='Mail-Port')

    mail_user = StringField(validators=[
        InputRequired()], label='Mail-Nutzer')

    mail_pw = PasswordField(validators=[
        InputRequired()], label='Mail-Passwort')

    mail_sender = StringField(validators=[
        InputRequired()], label='Absendername')

    submit = SubmitField('Aktualisieren', name='mailForm', id='submit')


class TerminOptimizationForm(FlaskForm):

    terminbeschreibung = StringField(validators=[
        InputRequired()])

    machines = SelectMultipleField(u'Maschinen', choices=[('welle', 'Wellenlöt'), ('3x4', 'Lötbad 3/4'), ('5', 'Lötbad 5')], validators=[InputRequired()])

    duration = IntegerField(validators=[
        InputRequired()])

    delete = SubmitField('Entfernen')


class OptimizationForm(FlaskForm):
    # see https://stackoverflow.com/questions/51817148/dynamically-add-new-wtforms-fieldlist-entries-from-user-interface

    startdate = DateField(validators=[
        InputRequired()], label='Beginn')

    enddate = DateField(validators=[
        InputRequired()], label='Ende')

    termine = FieldList(FormField(TerminOptimizationForm), min_entries=1)

    optimize = SubmitField('Optimieren')

    addline = SubmitField('Neuer Termin')

    def update_self(self):
        read_form_data = self.data
        self.termine.append_entry()
        updated_list = read_form_data['termine']
        #if read_form_data['addline']:
        #updated_list.append({})
        read_form_data['termine'] = updated_list

        self.__init__(formdata=None, **self.data)
        self.validate()