from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES

# format an error message in JSON format to get returned by API
def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    # give the message the correct status code
    response.status_code = status_code
    return response

# wrapper for error handling
def bad_request(message):
    return error_response(400, message)