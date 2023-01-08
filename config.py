import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'thisisasecretkey'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://energy:PJS2022@localhost:3306/pjs'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
