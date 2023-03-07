from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app.models import User
from app.api.errors import error_response

# Authentifizierungsmethoden festlegen
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

# Checken, ob der Nutzer vorhanden ist und falls ja, checken ob das Passwort vorhanden ist
@basic_auth.verify_password
def verify_password(username, password):
    print(username + "   " + password)
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user

# Error Handler -> Siehe api/error.py
@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)

# Checken, ob der Token korrekt ist / vorhanden ist
@token_auth.verify_token
def verify_token(token):
    return User.check_token(token) if token else None

# Error Handler -> Siehe api/error.py
@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)