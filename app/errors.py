from flask import render_template, request
from app import app, db
from app.api.errors import error_response as api_error_response

def is_json_response():
    """Prüfen, ob es sich bei der Anfrage um einen Browser oder einen API-Call handelt.
    Falls der Header Accept bevorzugt 'application/json' enthält, handelt es sich um einen API-Call und es wird true zurückgegeben.

    Returns:
        true: falls API-Call,
        false: falls Brower
    """
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']

@app.errorhandler(404)
def not_found_error(error):
    """Error-Handler, falls ein Endpunkt nicht gefunden wird.
    Rendert entweder eine 404-HTML Seite oder wirft einen API-Error.

    Args:
        error (str): Error-Nachricht

    Returns:
        api_error_response(404): falls API-Call,
        render_template('errors/404.html'), falls normaler Call
    """
    if is_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Error-Handler, falls ein Endpunkt nicht gefunden wird.
    Rendert entweder eine 500-HTML Seite oder wirft einen API-Error.
    Zusätzlich wird ein Rollback auf mögliche Datenbankänderungen durchgeführt.

    Args:
        error (str): Error-Nachricht

    Returns:
        api_error_response(500): falls API-Call,
        render_template('errors/500.html'), falls normaler Call
    """
    db.session.rollback()
    if is_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500