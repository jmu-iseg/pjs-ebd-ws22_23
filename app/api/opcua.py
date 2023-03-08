from flask import jsonify
from app.api import bp
from app.api.auth import token_auth
from app import app, opc_ua_sender
from datetime import datetime, timedelta
from app.models import Termin

# OPC UA Anbindung, um Maschinen über die API zu starten
@bp.route('/opcua_start', methods=['GET'])
@token_auth.login_required
def opcua_machine_start_stop():
    # Es wird ein Zeitraum von 7 Stunden genutzt, da dies (Absprache mit SEHO) die längste Dauer ist, die eine Maschine zum vorheizen brauchen kann
    cur_date = datetime.utcnow()
    end_date = cur_date + timedelta(hours=7)
    # Die Datenbank wird nach allen erstellten Terminen gefiltert, die innerhalb des Zeitraums liegen
    termine = Termin.query.filter(Termin.dateTime > cur_date).filter(Termin.dateTime < end_date).all()
    output = {
        "Termine": []
    }
    if termine:
        for termin in termine:
            # Für jeden Termin wird die Helper Funktion opc_ua_sender aufgerufen
            output["Termine"].append({
                "Beschreibung" :termin.description,
                "Status": opc_ua_sender(termin.machines.replace(' ', '').split(','), "on", app.root_path, termin.dateTime)
                })
        return jsonify(output)
    else:
        return jsonify({"Info": "In den nächsten 7 Stunden gibt es keine Maschinen"})