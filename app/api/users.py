from app.api import bp
from app.models import User
from flask import jsonify, request, url_for, abort
from app.api.auth import token_auth
from app.api.errors import bad_request
from app import db


@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    return jsonify(User.query.get_or_404(id).to_dict())

@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    users = User.query.all()
    data = {
        'users': []
    }
    for user in users:
        data['users'].append(user.to_dict())
    return jsonify(data)

@bp.route('/users', methods=['POST'])
@token_auth.login_required
def create_user():
    data = request.get_json() or {}
    if 'username' not in data or 'role' not in data or 'password' not in data:
        return bad_request('Muss den Benutzernamen, Rolle und Passwort enthalten')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('Der Benutzername existiert bereits')
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    response = jsonify(user.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response