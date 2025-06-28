from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
import enum
from flask_bcrypt import generate_password_hash, check_password_hash
from .database import db

# --- Énumérations pour les statuts et rôles ---
class StatutDossier(enum.Enum):
    EN_ATTENTE = "En attente"
    VALIDE = "Validé"
    REJETE = "Rejeté"
    ACTE_DELIVRE = "Acte délivré"



class RoleUtilisateur(enum.Enum):
    ADMIN = "ADMIN"
    AGENT_MAIRIE = "AGENT_MAIRIE"
    AGENT_HOPITAL = "AGENT_HOPITAL"



# --- Modèles de base de données ---

class Utilisateur(db.Model):
    """Modèle pour les utilisateurs du système (agents hôpitaux, agents mairies, administrateurs)."""
    __tablename__ = 'utilisateurs'

    id                = db.Column(db.Integer, primary_key=True)
    nom_utilisateur   = db.Column(db.String(80), unique=True, nullable=False)
    email             = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(128), nullable=False)
    role              = db.Column(db.Enum(RoleUtilisateur), nullable=False)
    cree_le           = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Réinitialisation de mot de passe
    reset_code        = db.Column(db.String(10), nullable=True)  # Exemple : code à 6 chiffres ou alphanumérique
    reset_code_expiry = db.Column(db.DateTime(timezone=True))

    # Lien avec un hôpital ou une mairie
    hopital_id        = db.Column(db.Integer, db.ForeignKey('hopitaux.id', ondelete='SET NULL'), nullable=True)
    mairie_id         = db.Column(db.Integer, db.ForeignKey('mairies.id', ondelete='SET NULL'), nullable=True)

    # Relations inverses
    dossiers_soumis  = db.relationship(
        'DossierNaissance',
        foreign_keys='DossierNaissance.soumis_par_utilisateur_id',
        backref='soumis_par_utilisateur',
        lazy='select'
    )
    dossiers_valides = db.relationship(
        'DossierNaissance',
        foreign_keys='DossierNaissance.valide_par_utilisateur_id',
        backref='valide_par_utilisateur',
        lazy='select'
    )
    actes_generes = db.relationship(
        'ActeNaissance',
        foreign_keys='ActeNaissance.genere_par_utilisateur_id',
        backref='genere_par_utilisateur',
        lazy='select'
    )
    journal_audits = db.relationship(
        'JournalAudit',
        backref='utilisateur',
        lazy='select'
    )

    def __repr__(self):
        return f"<Utilisateur {self.nom_utilisateur} ({self.role.value})>"

    def set_password(self, mot_de_passe):
        """Hash le mot de passe avec Werkzeug."""
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe)

    def check_password(self, mot_de_passe):
        """Vérifie que le mot de passe saisi correspond au hash."""
        return check_password_hash(self.mot_de_passe_hash, mot_de_passe)



class Hopital(db.Model):
    __tablename__ = 'hopitaux'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    localisation = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    email_contact = db.Column(db.String(120), unique=True, nullable=True)
    numero_telephone = db.Column(db.String(20), nullable=True)
    cree_le = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    utilisateurs = db.relationship('Utilisateur', backref='hopital', lazy=True)
    dossiers_naissance = db.relationship('DossierNaissance', backref='hopital', lazy=True)

    def __repr__(self):
        return f"<Hopital {self.nom}>"


class Mairie(db.Model):
    __tablename__ = 'mairies'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    localisation = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    email_contact = db.Column(db.String(120), unique=True, nullable=True)
    numero_telephone = db.Column(db.String(20), nullable=True)
    cree_le = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    utilisateurs = db.relationship('Utilisateur', backref='mairie', lazy=True)
    dossiers_traites = db.relationship('DossierNaissance', backref='mairie', lazy=True)
    actes_naissance = db.relationship('ActeNaissance', backref='mairie', lazy=True)

    def __repr__(self):
        return f"<Mairie {self.nom}>"


class DossierNaissance(db.Model):
    __tablename__ = 'dossiers_naissance'

    id = db.Column(db.Integer, primary_key=True)
    nom_enfant = db.Column(db.String(100), nullable=False)
    prenom_enfant = db.Column(db.String(100), nullable=False)
    sexe_enfant = db.Column(db.String(10), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    heure_naissance = db.Column(db.Time, nullable=False)
    lieu_naissance = db.Column(db.String(100), nullable=False)
    nom_mere = db.Column(db.String(100), nullable=False)
    prenom_mere = db.Column(db.String(100), nullable=False)
    date_naissance_mere = db.Column(db.Date, nullable=True)
    lieu_naissance_mere = db.Column(db.String(100), nullable=True)
    nationalite_mere = db.Column(db.String(50), nullable=True)
    profession_mere = db.Column(db.String(100), nullable=True)
    type_piece_mere = db.Column(db.String(50), nullable=True)
    numero_piece_mere = db.Column(db.String(100), nullable=True)
    nom_pere = db.Column(db.String(100), nullable=True)
    prenom_pere = db.Column(db.String(100), nullable=True)
    date_naissance_pere = db.Column(db.Date, nullable=True)
    lieu_naissance_pere = db.Column(db.String(100), nullable=True)
    nationalite_pere = db.Column(db.String(50), nullable=True)
    profession_pere = db.Column(db.String(100), nullable=True)
    type_piece_pere = db.Column(db.String(50), nullable=True)
    numero_piece_pere = db.Column(db.String(100), nullable=True)
    nom_declarant = db.Column(db.String(100), nullable=True)
    prenom_declarant = db.Column(db.String(100), nullable=True)
    lien_parente_declarant = db.Column(db.String(50), nullable=True)
    type_piece_declarant = db.Column(db.String(50), nullable=True)
    numero_piece_declarant = db.Column(db.String(100), nullable=True)
    numero_certificat_medical = db.Column(db.String(100), unique=True, nullable=True)
    date_certificat_medical = db.Column(db.Date, nullable=True)
    nom_medecin = db.Column(db.String(100), nullable=True)
    statut = db.Column(db.Enum(StatutDossier), default=StatutDossier.EN_ATTENTE, nullable=False)

    hopital_id = db.Column(db.Integer, db.ForeignKey('hopitaux.id', ondelete='CASCADE'), nullable=False)
    mairie_id = db.Column(db.Integer, db.ForeignKey('mairies.id', ondelete='SET NULL'), nullable=True)
    soumis_par_utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='RESTRICT'), nullable=False)
    valide_par_utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), nullable=True)

    date_soumission = db.Column(db.DateTime, default=datetime.utcnow)
    date_validation = db.Column(db.DateTime, nullable=True)
    motif_rejet = db.Column(db.String(500), nullable=True)

    acte_naissance = db.relationship('ActeNaissance', backref='dossier_naissance', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DossierNaissance {self.prenom_enfant} {self.nom_enfant} ({self.statut.value})>"


class ActeNaissance(db.Model):
    __tablename__ = 'actes_naissance'

    id = db.Column(db.Integer, primary_key=True)
    numero_acte = db.Column(db.String(100), unique=True, nullable=False)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    lieu_enregistrement = db.Column(db.String(100), nullable=False)
    nom_complet_enfant = db.Column(db.String(200), nullable=False)
    sexe_enfant = db.Column(db.String(10), nullable=False)
    date_naissance_enfant = db.Column(db.Date, nullable=False)
    heure_naissance_enfant = db.Column(db.Time, nullable=False)
    lieu_naissance_enfant = db.Column(db.String(100), nullable=False)
    nom_complet_mere = db.Column(db.String(200), nullable=False)
    nationalite_mere = db.Column(db.String(50), nullable=True)
    nom_complet_pere = db.Column(db.String(200), nullable=True)
    nationalite_pere = db.Column(db.String(50), nullable=True)
    nom_complet_declarant = db.Column(db.String(200), nullable=True)
    lien_parente_declarant = db.Column(db.String(50), nullable=True)

    dossier_naissance_id = db.Column(db.Integer, db.ForeignKey('dossiers_naissance.id', ondelete='CASCADE'), unique=True, nullable=False)
    mairie_id = db.Column(db.Integer, db.ForeignKey('mairies.id', ondelete='RESTRICT'), nullable=False)
    genere_par_utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='RESTRICT'), nullable=False)
    genere_le = db.Column(db.DateTime, default=datetime.utcnow)
    chemin_pdf = db.Column(db.String(255), nullable=True)
    est_actif = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<ActeNaissance {self.numero_acte} pour {self.nom_complet_enfant}>"


class JournalAudit(db.Model):
    __tablename__ = 'journal_audit'

    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    horodatage = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    adresse_ip = db.Column(db.String(45), nullable=True)
    identifiant_enregistrement = db.Column(db.Integer, nullable=True)
    type_enregistrement = db.Column(db.String(50), nullable=True)

    #utilisateur = db.relationship('Utilisateur', backref='journal_audits', lazy='select')

    def __repr__(self):
        return f"<JournalAudit {self.action} par Utilisateur {self.utilisateur_id} à {self.horodatage}>"
