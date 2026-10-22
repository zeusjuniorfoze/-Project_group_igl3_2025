import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from .config import Config
from .database import db, check_db_connection

# Extensions
jwt = JWTManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config=None):
    """Crée et configure l'application Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # Initialiser les extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.setLevel(
        logging.INFO if app.config['SQLALCHEMY_ECHO'] else logging.WARNING
    )

    with app.app_context():
        print("Verification de la base de donnees...")
        # if check_db_connection():
        #     from .models import ...
        #     db.create_all()
        #     print("Tables creees.")
        # else:
        #     print("Probleme de connexion.")

    # ⬇️ Import des blueprints après initialisation complète
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.hospital import hopital_bp
    from .routes.mairie import mairie_bp

    # Enregistrement des blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(hopital_bp, url_prefix='/hopital')
    app.register_blueprint(mairie_bp, url_prefix='/mairie')

    return app
