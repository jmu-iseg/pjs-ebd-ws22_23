from flask import Flask
import os

# set app
app = Flask(__name__)
import main, settings

# run app
if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)