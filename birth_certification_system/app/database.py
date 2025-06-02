import logging
from flask_sqlalchemy import SQLAlchemy

# Instance de SQLAlchemy
db = SQLAlchemy()


def check_db_connection():
    """Vérifie si la connexion à la base de données fonctionne."""
    try:
        db.engine.connect()
        print("✅ Connexion à la base de données réussie !")
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données : {e}")
        return False



