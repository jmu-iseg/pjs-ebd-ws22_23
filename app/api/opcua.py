from flask import jsonify
from app.api import bp
from app.api.auth import basic_auth
from app import app, opc_ua_sender
from datetime import datetime, timedelta
from app.models import Termin

@bp.route('/opcua_start', methods=['GET'])
@basic_auth.login_required
def opcua_machine_start_stop():
    cur_date = datetime.utcnow()
    end_date = cur_date + timedelta(hours=7)
    termine = Termin.query.filter(Termin.dateTime > cur_date).filter(Termin.dateTime < end_date).all()
    output = {}
    if termine:
        for termin in termine:
            output[termin.description] = opc_ua_sender(termin.machines.replace(' ', '').split(','), "on", app.root_path, termin.dateTime)
        return jsonify(output)
    else:
        return jsonify({"Info": "In den nächsten 7 Stunden gibt es keine Maschinen"})