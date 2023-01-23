from flask import jsonify, request, url_for, redirect
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request
from app.routing.optimization import optimization_table, save_to_calendar
from app import get_graph_params, app
import requests
from datetime import datetime

@bp.route('/maschinen', methods=['GET'])
@token_auth.login_required
def get_machines():
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    payload = {}
    for user in resp['value']:
        if user['jobTitle'] == 'pjs_machine':
            payload[user['displayName']] = user['id']
    return jsonify(payload)

@bp.route('/mitarbeiter', methods=['GET'])
@token_auth.login_required
def get_mitarbeiter():
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    payload = {}
    for user in resp['value']:
        if not user['jobTitle'] == 'pjs_machine':
            payload[user['displayName']] = user['id']
    return jsonify(payload)

@bp.route('/optimization', methods=['POST'])
@token_auth.login_required
def optimize():
    data = request.get_json() or {}
    params = get_graph_params(app.root_path)
    head = {
        'Authorization': params['token']
    }
    resp = requests.get('https://graph.microsoft.com/v1.0/users/', headers=head).json()
    if 'startdate' not in data or 'enddate' not in data or 'termine' not in data:
        return bad_request('Muss das Startdatum, Enddatum und Termine enthalten')
    if len(data['termine']) != 1:
        return bad_request('Es darf nur ein Termin enthalten sein')
    try:
        datetime.strptime(data['startdate'], "%Y-%m-%d")
        datetime.strptime(data['enddate'], "%Y-%m-%d")
    except ValueError:
        return bad_request('Das Start- und Enddatum muss im Format "YYYY-MM-DD" angegeben werden')
    startdate = f"{data['startdate']} 00:00:00"
    enddate = f"{data['enddate']} 23:59:59"
    termine = []
    for termin in data['termine']:
        if 'description' not in termin or 'duration' not in termin or 'machines' not in termin or 'employees' not in termin:
            return bad_request('Jeder Termin muss Beschreibung, Dauer, Maschinen und Mitarbeiter enthalten')
        if len(termin['machines']) < 1 or len(termin['employees']) < 1:
            return bad_request('Jeder Termin muss mindestens einen Mitarbeiter und eine Maschine beinhalten')
        for machine in termin['machines']:
            valid = False
            for id in resp['value']:
                if id['id'] == machine:
                    valid = True
                    break
            if not valid:
                return bad_request(f'Die Maschine mit der ID {machine} existiert nicht')
        for mitarbeiter in termin['employees']:
            valid = False
            for id in resp['value']:
                if id['id'] == mitarbeiter:
                    valid = True
                    break
            if not valid:
                return bad_request(f'Der Mitarbeiter mit der ID {mitarbeiter} existiert nicht')
        termine.append({
            'bezeichnung': termin['description'],
            'dauer': termin['duration'],
            'maschinen': termin['machines'],
            'mitarbeiter': termin['employees']
        })
    payload = optimization_table(start_date=startdate, end_date=enddate, termin=termine[0], api=True, sessiontoken=request.headers.get('Authorization'))
    return jsonify(payload)

@bp.route('/save-appointment', methods=['GET'])
@token_auth.login_required
def save_termin():
    if 'id' in request.args:
        try:
            id = int(request.args.get('id'))
        except:
            return bad_request('Die ID muss ein Integer sein')
    return save_to_calendar(terminId=id, api=True, sessiontoken=request.headers.get('Authorization'))