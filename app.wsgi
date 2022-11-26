import sys
import logging

activate_this = '/var/www/PJS/venv/bin/activate'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

logging.basicConfig(level=logging.DEBUG, filename='/var/www/PJS/logs/file.log', format='%(asctime)s %(message)s')
sys.path.insert(0, '/var/www/PJS')
sys.path.insert(0, '/var/www/PJS/venv/lib/python3.8/site-packages')

from app import app as application
