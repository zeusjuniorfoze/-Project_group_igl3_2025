from flask import Blueprint, render_template
from app.models import DossierNaissance ,ActeNaissance

mairie_bp = Blueprint('mairie', __name__)

@mairie_bp.route('/dashboard')
def dashboard():
    total_declarations = DossierNaissance.query.count()
    total_actes = ActeNaissance.query.count()
    return render_template("mairie/dashboard.html",
        total_declarations=total_declarations,
        total_actes=total_actes)
