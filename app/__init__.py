from flask import Flask

app = Flask(__name__)
from app import main, settings

if __name__ == "__main__":
    app.run(ssl_context='adhoc', debug=True)