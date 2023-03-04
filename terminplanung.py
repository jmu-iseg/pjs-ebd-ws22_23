# Importieren der App aus app/__init__.py
from app import app

# Starten der Applikation mit app.run(). 
# Option debug ist für lokale Entwicklung immer aktiviert, 
# spielt auf dem Webserver allerdings keine Rolle.
if __name__ == "__main__":
    app.run(debug=True)