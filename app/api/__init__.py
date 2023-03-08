from flask import Blueprint

# API Blueprint anlegen
bp = Blueprint('api', __name__)

#Komponenten in den Blueprint importieren
from app.api import users, optimization, errors, tokens, opcua