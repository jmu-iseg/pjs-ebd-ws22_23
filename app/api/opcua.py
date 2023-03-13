from flask import jsonify
from app.api import bp
from app.api.auth import token_auth
from app import app, opc_ua_sender
from datetime import datetime, timedelta
from app.models import Termin

# OPC UA connection to start machines
@bp.route('/opcua_start', methods=['GET'])
@token_auth.login_required
def opcua_machine_start_stop():
    # using a timespan of 7 hours in the future, because thats the maximum time needed
    # for a machine to heat up
    cur_date = datetime.utcnow()
    end_date = cur_date + timedelta(hours=7)
    # filter database with created appointments within the timespan
    termine = Termin.query.filter(Termin.dateTime > cur_date).filter(Termin.dateTime < end_date).all()
    output = {
        "Termine": []
    }
    if termine:
        for termin in termine:
            # for each appointment the function opc_ua_sender gets called
            output["Termine"].append({
                "Beschreibung" :termin.description,
                "Status": opc_ua_sender(termin.machines.replace(' ', '').split(','), "on", app.root_path, termin.dateTime)
                })
        return jsonify(output)
    else:
        return jsonify({"Info": "In den nächsten 7 Stunden gibt es keine Maschinen"})