from flask import Blueprint

# create API Blueprint
bp = Blueprint('api', __name__)

# import components for API
from app.api import users, optimization, errors, tokens, opcua