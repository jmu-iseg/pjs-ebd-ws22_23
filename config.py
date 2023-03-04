import os
basedir = os.path.abspath(os.path.dirname(__file__))

# Enthält Parameter für die Datenbankanbindung
class Config(object):
    # Secret Key, un die Echtheit zu verifzieren
    SECRET_KEY = 'thisisasecretkey'
    # Connection String
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://energy:PJS2022@localhost:3306/pjs'
    # Modification-Tracking deaktivieren
    SQLALCHEMY_TRACK_MODIFICATIONS = False
