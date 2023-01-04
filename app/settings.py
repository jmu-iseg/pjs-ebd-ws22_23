from app import app

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

# read settings
config = configparser.ConfigParser()
config.read(os.path.join(app.root_path,'settings.cfg'))

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