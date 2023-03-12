from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import flask_login
from flask_bcrypt import Bcrypt
from app.helper import *

# create application and import config
app = Flask(__name__)
app.config.from_object(Config)
# database connection
db = SQLAlchemy(app)
# database migrations
migrate = Migrate(app, db)
# Login
login = LoginManager(app)
login.init_app(app)
login.login_view = 'login'
# password encryption
bcrypt = Bcrypt(app)

@app.context_processor
def inject_userdata():
    """Provide user data globally as a context_processor,
    so that these can be used on every HTML page.

    Returns:
        values: Dictionary with username, userrole, userid and profilepic
    """
    values = {}
    if flask_login.current_user.is_authenticated != True:
        values['username'] = "NotLoggedIn"
        values['userrole'] = "NoRole"
        values['userid'] = "NoID"
        values['profilepic'] = 'img/img1234.jpg'
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

# import api as blueprint
from app.api import bp as api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# import all other routes, models and errors
from app import routes, models, errors