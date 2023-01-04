from flask import Flask
import os

# set template path
template_dir = os.path.abspath('templates')

# set app
app = Flask(__name__, template_folder=template_dir)
from app import main, settings

# run app
if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)