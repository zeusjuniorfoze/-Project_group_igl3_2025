import os
from dotenv import load_dotenv
import time

# Charger les variables d'environnement depuis .env
load_dotenv()

class Config:
    TIMEZONE_OFFSET = time.localtime().tm_gmtoff  # Offset en secondes
    """Configuration de l'application Flask."""

    # Paramètres de connexion MySQL (XAMPP)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')  # Chaîne vide si pas de mot de passe
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'acte_naissance')  # À adapter si besoin

    # Chaîne de connexion SQLAlchemy + PyMySQL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}@{DB_HOST}:3306/{DB_NAME}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'

    # Clé secrète Flask (session, CSRF, etc.)
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')
    # Clé secrète JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-key')

    # Expiration du token JWT (en secondes)
    raw_jwt_expires = os.getenv('JWT_ACCESS_TOKEN_EXPIRES', "3600")
    try:
        JWT_ACCESS_TOKEN_EXPIRES = int(raw_jwt_expires.strip())
    except ValueError:
        print("❌ Erreur : JWT_ACCESS_TOKEN_EXPIRES invalide, valeur par défaut utilisée (3600s).")
        JWT_ACCESS_TOKEN_EXPIRES = 3600

    # Configuration pour Flask-Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("⚠️ Attention : Les variables MAIL_USERNAME et MAIL_PASSWORD ne sont pas définies.")
