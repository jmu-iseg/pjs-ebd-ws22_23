import sys
sys.path.insert(0, '/var/www/PJS')

activate_this = '/var/www/PJS/venv/bin/activate'
with open(activate_this) as file_:
  exec(file_.read(), dict(__file=activate_this))

from app import app as application
