import os
import secrets
import warnings
from urllib.parse import quote_plus
from dotenv import load_dotenv
import time


_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_APP_DIR)
load_dotenv(os.path.join(_PROJECT_DIR, '.env'))
load_dotenv(os.path.join(_APP_DIR, '.env'))

class Config:
    APP_ENV = os.getenv('APP_ENV', 'development').strip().lower()
    TIMEZONE_OFFSET = time.localtime().tm_gmtoff  # Offset en secondes
    """Configuration de l'application Flask."""

    # Paramètres de connexion MySQL (XAMPP)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')  # Chaîne vide si pas de mot de passe
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'acte_naissance')  # À adapter si besoin

    # Chaîne de connexion SQLAlchemy + PyMySQL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:3306/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'

    # Les clés temporaires en développement invalident les sessions au redémarrage.
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if APP_ENV == 'production' and (not SECRET_KEY or not JWT_SECRET_KEY):
        raise RuntimeError('SECRET_KEY et JWT_SECRET_KEY doivent etre configurees en production.')
    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)
        warnings.warn('SECRET_KEY absente : une cle temporaire de developpement est utilisee.', RuntimeWarning)
    if not JWT_SECRET_KEY:
        JWT_SECRET_KEY = secrets.token_hex(32)
        warnings.warn('JWT_SECRET_KEY absente : une cle temporaire de developpement est utilisee.', RuntimeWarning)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = APP_ENV == 'production' or os.getenv(
        'SESSION_COOKIE_SECURE', 'false'
    ).strip().lower() in {'1', 'true', 'yes', 'on'}
    PERMANENT_SESSION_LIFETIME = 1800

    # Expiration du token JWT (en secondes)
    raw_jwt_expires = os.getenv('JWT_ACCESS_TOKEN_EXPIRES', "3600")
    try:
        JWT_ACCESS_TOKEN_EXPIRES = int(raw_jwt_expires.strip())
    except ValueError:
        print("Erreur : JWT_ACCESS_TOKEN_EXPIRES invalide, valeur par defaut utilisee (3600s).")
        JWT_ACCESS_TOKEN_EXPIRES = 3600

    # Configuration pour Flask-Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("Attention : Les variables MAIL_USERNAME et MAIL_PASSWORD ne sont pas definies.")

    WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH') or None
