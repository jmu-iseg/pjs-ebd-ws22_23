from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField, HiddenField, TextAreaField, DateField, FieldList, SelectMultipleField, IntegerField, FormField
from wtforms.validators import InputRequired, Length, ValidationError
from app.models import User
from app import bcrypt, get_graph_params, app, db
from flask_login import login_user
import flask_login
import requests
import re

"""
Register Form
    Used to create a new user, needs username, role and password.
    Validation:
        Doesn't allow already existing usernames
"""
class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"}, label='Benutzername')

    role = SelectField(choices=[('0', 'Admin'), ('1', 'Standard')], label='Rolle', render_kw={'data-suggestions-threshold': '0','data-allow-clear':'true'})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Passwort')

    submit = SubmitField('Register', name='registerForm', id='submit')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError('Der Benutzername existiert bereits.')


"""
Login Form
    Used to login a user entering the correct username and password combination.
    Validation:
        Only allows existing usernames
        Only allows correct combinations of username and password
"""
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


"""
Profile Form
    Used to show / edit a user profile -> username and profile picture.
    Validation:
        None
"""
class ProfileForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"}, label='Benutzername')

    profilepic = FileField(label='Profilbild')

    submit = SubmitField('Aktualisieren', name='profileForm', id='submit')


"""
Change Password Form
    Used to change the password.
    Validation:
        Old password has to be correct
        New Passwords have to match
"""
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Altes Passwort')

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Neues Passwort')

    val_password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"}, label='Neues Passwort wiederholen')

    submit = SubmitField('Aktualisieren', name='passwordForm', id='submit')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        user = User.query.filter_by(id = flask_login.current_user.id).first()
        if not bcrypt.check_password_hash(user.password, self.old_password.data):
            self.old_password.errors.append('Das alte Passwort ist nicht korrekt')
            return False
        if not self.password.data == self.val_password.data:
            self.password.errors.append('Die neuen Passwörter stimmen nicht überein')
            return False
        user.password = bcrypt.generate_password_hash(self.password.data)
        db.session.commit()
        return True


"""
SendMail Form
    Used to prepare an email. Asks for the Mail-Body and Mail-Texts. Has hidden fields to secretly insert content from the frontend.
    Validation:
        Only allows E-Mails in correct format (split by string)
"""
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

    def validate_mailAddress(self, mailAddress):
        mailAddresses = mailAddress.data.split(',')
        EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
        for mail in mailAddresses:
            if not EMAIL_REGEX.match(mail):
                raise ValidationError("Bitte geben Sie alle Mail-Adressen im richtigen Format an")


"""
Weather Form
    Settings Form to edit the config
    Validation:
        Only allows ASCII characters in API Key
        Only allows float values for lat and lon
"""
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

    def validate_lat(self, lat):
        try:
            float(lat.data)
        except:
            raise ValidationError("Bitte geben Sie die Koordinaten als Float Werte (Dezimalstellen durch Punkte getrennt) an.")

    def validate_lon(self, lon):
        try:
            float(lon.data)
        except:
            raise ValidationError("Bitte geben Sie die Koordinaten als Float Werte (Dezimalstellen durch Punkte getrennt) an.")


"""
Machine Form
    Settings Form to edit the config
    Validation:
        Only allows float values m1, m2 and m3
"""
class MachineForm(FlaskForm):
    consumption_m1 = StringField(validators=[
        InputRequired()], label='Verbrauch Wellenlöt')

    consumption_m2 = StringField(validators=[
        InputRequired()], label='Verbrauch Lötbad 3/4')

    consumption_m3 = StringField(validators=[
        InputRequired()], label='Verbrauch Lötbad 5')

    heating_m1 = StringField(validators=[
        InputRequired()], label='Aufheizverbrauch Wellenlöt')

    heating_m2 = StringField(validators=[
        InputRequired()], label='Aufheizverbrauch Lötbad 3/4')

    heating_m3 = StringField(validators=[
        InputRequired()], label='Aufheizverbrauch Lötbad 5')
    
    basicConsumption = StringField(validators=[
        InputRequired()], label='Grundlast der SEHO')

    submit = SubmitField('Aktualisieren', name='machineForm', id='submit')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        try:
            float(self.consumption_m1.data)
        except:
            self.consumption_m1.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.consumption_m2.data)
        except:
            self.consumption_m2.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.consumption_m3.data)
        except:
            self.consumption_m3.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.heating_m1.data)
        except:
            self.heating_m1.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.heating_m2.data)
        except:
            self.heating_m2.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.heating_m3.data)
        except:
            self.heating_m3.errors.append("Bitte geben Sie die Maschinenverbräuche als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        try:
            float(self.basicConsumption.data)
        except:
            self.basicConsumption.errors.append("Bitte geben Sie die Grundlast als Float Werte (Dezimalstellen durch Punkte getrennt) an.")
            return False
        return True


"""
Mail Form
    Settings Form to edit the config
    Validation:
        Only allows int for port
        Only allows Mail-Format for mail_user
"""
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

    def validate_mail_port(self, mail_port):
        try:
            int(mail_port.data)
        except:
            raise ValidationError("Bitte geben Sie einen korrekten Port an.")

    def validate_mail_user(self, mail_user):
        EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
        if not EMAIL_REGEX.match(mail_user.data):
            raise ValidationError("Bitte geben Sie eine korrekte Mailadresse an")


"""
Kafka Form
    Settings Form to edit the config
    Validation:
        Only allows int for port
"""
class KafkaForm(FlaskForm):
    kafka_url = StringField(validators=[
        InputRequired()], label='Server-URL')

    kafka_port = StringField(validators=[
        InputRequired()], label='Server-Port')

    submit = SubmitField('Aktualisieren', name='kafkaForm', id='submit')

    def validate_kafka_port(self, kafka_port):
        try:
            int(kafka_port.data)
        except:
            raise ValidationError("Bitte geben Sie einen korrekten Port an.")


"""
OPC UA Form
    Settings Form to edit the config
    Validation:
        TO DO @NILS
"""
class OpcForm(FlaskForm):
    value_on = StringField(validators=[
        InputRequired()], label='Einschalt-Wert')

    value_off = StringField(validators=[
        InputRequired()], label='Ausschalt-Wert')

    url1 = StringField(validators=[
        InputRequired()], label='Maschine 1 URL')

    var1 = StringField(validators=[
        InputRequired()], label='Maschine 1 Objekt')

    url2 = StringField(validators=[
        InputRequired()], label='Maschine 2 URL')

    var2 = StringField(validators=[
        InputRequired()], label='Maschine 2 Objekt')

    url3 = StringField(validators=[
        InputRequired()], label='Maschine 3 URL')

    var3 = StringField(validators=[
        InputRequired()], label='Maschine 3 Objekt')

    submit = SubmitField('Aktualisieren', name='opcForm', id='submit')


"""
Termin Optimization Form
    Sub-Form of Termin Form to add multiple appointments
    Validation:
        everything allowed so far
"""
class TerminOptimizationForm(FlaskForm):

    terminbeschreibung = StringField(validators=[
        InputRequired()])
    
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    mitarbeiterlist = []
    machinelist = []
    for user in resp['value']:
        if user['jobTitle'] == 'pjs_machine':
            machinelist.append((user['id'], user['displayName']))
        else:
            mitarbeiterlist.append((user['id'], user['displayName']))

    machines = SelectMultipleField(u'Maschinen', choices=machinelist, validators=[InputRequired()], render_kw={'data-suggestions-threshold': '0','data-allow-clear':'true'})

    product = SelectField(u'Lötprodukt', choices=['Einfach','Normal','Komplex'], validators=[InputRequired()], render_kw={'data-suggestions-threshold': '0','data-allow-clear':'true'})

    mitarbeiter = SelectMultipleField(u'Mitarbeiter', choices=mitarbeiterlist, validators=[InputRequired()], render_kw={'data-suggestions-threshold': '0','data-allow-clear':'true'})

    duration = IntegerField(validators=[InputRequired()])

    delete = SubmitField('Entfernen')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        return True


"""
Optimization Form Form
    first step of optimization
    Validation:
        exactly one termin in termine-list
        start date before end date
        generic validation for each termin in termine list
    Update-self:
        add a new termin
    delete-termin:
        deletes a termin
"""
class OptimizationForm(FlaskForm):
    # see https://stackoverflow.com/questions/51817148/dynamically-add-new-wtforms-fieldlist-entries-from-user-interface

    startdate = DateField(validators=[
        InputRequired()], label='Beginn')

    enddate = DateField(validators=[
        InputRequired()], label='Ende')

    termine = FieldList(FormField(TerminOptimizationForm), min_entries=1, max_entries=4)

    optimization_identifier = HiddenField(default='Identify')

    optimize = SubmitField('Optimieren')

    addline = SubmitField('Neuer Termin')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        if len(self.data['termine']) < 1:
            self.termine.errors.append('Es wurde kein Termin hinzugefügt')
            return False
        if len(self.data['termine']) > 1:
            self.termine.errors.append('Es kann nur ein Termin hinzugefügt werden')
            return False
        if self.startdate.data > self.enddate.data:
            self.enddate.errors.append('Das Enddatum darf nicht vor dem Startdatum liegen')
            return False
        for index, termin in enumerate(self.termine.entries):
            if not termin.validate(termin):
                self.termine.errors.append(f'Es gibt ein Problem mit dem Termin {index+1} namens {termin.data["terminbeschreibung"]}')
                return False
        return True

    def update_self(self):
        read_form_data = self.data
        updated_list = read_form_data['termine']
        if read_form_data['addline']:
            updated_list.append({})
        read_form_data['termine'] = updated_list

        self.__init__(formdata=None, **read_form_data)

    def delete_termin(self, termin):
        read_form_data = self.data
        updated_list = read_form_data['termine']
        updated_list.remove(termin)
        read_form_data['termine'] = updated_list

        self.__init__(formdata=None, **read_form_data)