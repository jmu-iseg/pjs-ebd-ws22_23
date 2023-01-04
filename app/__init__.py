from flask import Flask
import os

# set template path
template_dir = os.path.abspath('templates')

# sett app
app = Flask(__name__)
from app import main, settings

# run app
if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)