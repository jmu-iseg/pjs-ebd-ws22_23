from flask import flash
from datetime import datetime, timedelta
import requests
import json
import os

def flash_errors(form):
    """Flashes form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Fehler im Feld '%s' - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

def get_weekday(day):
    if day == 0:
        return "So"
    elif day == 1:
        return "Mo"
    elif day == 2:
        return "Di"
    elif day == 3:
        return "Mi"
    elif day == 4:
        return "Do"
    elif day == 5:
        return "Fr"
    elif day == 6:
        return "Sa"
    else:
        return "Error"