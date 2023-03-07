from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES

# Formatiert eine Error Nachricht im JSON Format, sodass diese via API ausgegeben werden kann
def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    # Der Antwort den passenden Statuscode mitgeben
    response.status_code = status_code
    return response

# Wrapper für die Error Ausgabe. Gibt einen Error 400 mit der übergebenen Nachricht zurück
def bad_request(message):
    return error_response(400, message)