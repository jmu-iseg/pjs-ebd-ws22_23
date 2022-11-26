import sys
import logging

logging.basicConfig(level=logging.DEBUG, filename='/var/www/PJS/logs/file.log', format='%(asctime)s %(message)s')
sys.path.insert(0, '/var/www/PJS')
sys.path.insert(0, '/var/www/PJS/venv/lib/python3.8/site-packages')

from app import app as application
