# import the app from app/__init__.py
from app import app

# start the application with app.run(). 
# Option debug is enabled for local development,
# not important for the webserver.
if __name__ == "__main__":
    app.run(debug=True)