from flask import Blueprint, render_template

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    return render_template('auth/login.html')


@auth_bp.route('/forgetpassword')
def forgetpassword():
    return render_template('auth/forgetpassword.html')
