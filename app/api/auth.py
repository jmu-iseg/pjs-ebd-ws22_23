from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app.models import User
from app.api.errors import error_response

# select auth methods
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

# check if the user exists and if the password is correct. if yes, return the user
@basic_auth.verify_password
def verify_password(username, password):
    print(username + "   " + password)
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user

# Error Handler
@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)

# check, if auth token exists and is valid
@token_auth.verify_token
def verify_token(token):
    return User.check_token(token) if token else None

# Error Handler
@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)