from flask import Blueprint, render_template

hopital_bp = Blueprint('hopital', __name__)

@hopital_bp.route('/hopital')
def hopital():
    return render_template('hopital/dashboard.html')

