from flask import render_template, request
from app import app, db
from app.api.errors import error_response as api_error_response

def is_json_response():
    """Check whether the request is a browser or an API call.
    If the Accept header preferably contains 'application/json', it is an API call and true is returned.

    Returns:
        true: if API-Call,
        false: if Brower
    """
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']

@app.errorhandler(404)
def not_found_error(error):
    """Error handler if an endpoint is not found.
    Renders either a 404 HTML page or throws an API error.

    Args:
        error (str): Error-Message

    Returns:
        api_error_response(404): if API-Call,
        render_template('errors/404.html'), if normaler Call
    """
    if is_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Error handler if an endpoint is not found.
    Renders either a 500-HTML page or throws an API error.
    In addition, a rollback to possible database changes is performed.

    Args:
        error (str): Error-Message

    Returns:
        api_error_response(500): if API-Call,
        render_template('errors/500.html'), if normaler Call
    """
    db.session.rollback()
    if is_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500