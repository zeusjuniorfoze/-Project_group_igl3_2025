import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from .config import Config
from .database import db, check_db_connection

from .routes.main import main_bp
from .routes.auth import auth_bp
from  .routes.admin import admin_bp
from .routes.hospital import hopital_bp
from .routes.mairie import mairie_bp
# Extensions
jwt = JWTManager()
mail = Mail()

def create_app():
    """Crée et configure l'application Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialiser les extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # Activer le logging SQLAlchemy pour debug
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

    with app.app_context():
        print("🔍 Vérification de la base de données...")
        if check_db_connection():
            # Importer explicitement les modèles pour remplir la métadonnée
            #from .models import (
            #    Utilisateur,
            #    Hopital,
            #    Mairie,
            #    DossierNaissance,
            #    ActeNaissance,
            #    JournalAudit
            #)
            #db.create_all()
            print("✅ Tables créées (si elles n'existaient pas déjà).")
        else:
            print("❌ La base de données est inaccessible. Vérifie tes paramètres de connexion.")

    # Enregistrement des blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(hopital_bp, url_prefix='/hopital')
    app.register_blueprint(mairie_bp, url_prefix='/mairie')

    return app
