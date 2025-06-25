from flask import Blueprint, render_template

mairie_bp = Blueprint('mairie', __name__)

@mairie_bp.route('/mairie')
def mairie():
    return render_template('mairie/dashboard.html')

