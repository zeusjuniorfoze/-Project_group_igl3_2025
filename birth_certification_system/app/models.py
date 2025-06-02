from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum, text
import enum
from flask_bcrypt import generate_password_hash, check_password_hash
from .database import db

# Initialiser SQLAlchemy (assurez-vous que cette instance est la même que celle utilisée dans votre app/__init__.py)
# Si vous avez déjà 'db = SQLAlchemy()' dans 'app/extensions.py', importez-la comme ceci :
# from .extensions import db
# Sinon, décommentez la ligne ci-dessous :

# --- Énumérations pour les statuts et rôles ---
class StatutDossier(enum.Enum):
    """Statut du dossier de naissance."""
    EN_ATTENTE = "En attente"      # Envoyé par l'hôpital, en attente de vérification mairie
    VALIDE = "Validé"              # Vérifié et validé par la mairie
    REJETE = "Rejeté"              # Rejeté par la mairie
    ACTE_DELIVRE = "Acte délivré"  # Acte de naissance généré et potentiellement délivré


class RoleUtilisateur(enum.Enum):
    """Rôle de l'utilisateur dans le système."""
    ADMIN = "admin"         # Supervision, gestion des entités
    AGENT_MAIRIE = "mairie" # Vérification, validation, génération actes
    AGENT_HOPITAL = "hopital" # Saisie des données de naissance
    CITOYEN = "Citoyen"     # Consultation d'actes (futur, non géré par défaut ici)


# --- Modèles de base de données ---

class Utilisateur(db.Model):
    """Modèle pour les utilisateurs du système (agents hôpitaux, agents mairies, administrateurs)."""
    __tablename__ = 'utilisateurs'

    id                = db.Column(db.Integer, primary_key=True)
    nom_utilisateur   = db.Column(db.String(80), unique=True, nullable=False)
    email             = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hash = db.Column(db.String(128), nullable=False)
    role              = db.Column(db.Enum(RoleUtilisateur), nullable=False)  # Ex : Agent Hôpital, Agent Mairie, Admin
    cree_le           = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations (un utilisateur appartient à un hôpital ou une mairie)
    # ID de l'entité (hôpital ou mairie) à laquelle l'utilisateur est rattaché
    entite_id   = db.Column(db.Integer, nullable=True)
    # Type d'entité ('hopital' ou 'mairie')
    type_entite = db.Column(db.String(50), nullable=True)

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
        """
        Hash le mot de passe en clair avec bcrypt puis
        stocke le résultat (décodé en 'utf-8') dans mot_de_passe_hash.
        """
        # generate_password_hash renvoie un bytes ; on le décode pour garder une str
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe).decode('utf-8')

    def check_password(self, mot_de_passe):
        """
        Vérifie que le mot de passe en clair corresponde au hash stocké.
        Affiche en debug le hash et la saisie pour le développement.
        """
        print(f"Mot de passe stocké (haché) : {self.mot_de_passe_hash}")
        print(f"Mot de passe entré par l'utilisateur : {mot_de_passe}")
        verification = check_password_hash(self.mot_de_passe_hash, mot_de_passe)
        print(f"Résultat de la vérification : {verification}")
        return verification


class Hopital(db.Model):
    """Modèle pour les hôpitaux ou centres de santé."""
    __tablename__ = 'hopitaux'

    id              = db.Column(db.Integer, primary_key=True)
    nom             = db.Column(db.String(100), unique=True, nullable=False)
    localisation    = db.Column(db.String(100), nullable=False)  # Ville, Quartier
    region          = db.Column(db.String(50), nullable=False)   # Région administrative (ex : Littoral, Centre)
    email_contact   = db.Column(db.String(120), unique=True, nullable=True)
    numero_telephone = db.Column(db.String(20), nullable=True)
    cree_le         = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    dossiers_naissance = db.relationship(
        'DossierNaissance',
        backref='hopital',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Hopital {self.nom}>"


class Mairie(db.Model):
    """Modèle pour les mairies (Collectivités Territoriales Décentralisées)."""
    __tablename__ = 'mairies'

    id               = db.Column(db.Integer, primary_key=True)
    nom              = db.Column(db.String(100), unique=True, nullable=False)
    localisation     = db.Column(db.String(100), nullable=False)  # Ville, Arrondissement
    region           = db.Column(db.String(50), nullable=False)   # Région administrative (ex : Littoral, Centre)
    email_contact    = db.Column(db.String(120), unique=True, nullable=True)
    numero_telephone = db.Column(db.String(20), nullable=True)
    cree_le          = db.Column(db.DateTime, default=datetime.utcnow)
    mis_a_jour_le    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    dossiers_traites = db.relationship(
        'DossierNaissance',
        backref='mairie',
        lazy=True
    )
    actes_naissance = db.relationship(
        'ActeNaissance',
        backref='mairie',
        lazy=True
    )

    def __repr__(self):
        return f"<Mairie {self.nom}>"


class DossierNaissance(db.Model):
    """Modèle pour l'enregistrement initial des naissances à l'hôpital."""
    __tablename__ = 'dossiers_naissance'

    id                    = db.Column(db.Integer, primary_key=True)

    # --- Informations sur l'enfant ---
    nom_enfant            = db.Column(db.String(100), nullable=False)
    prenom_enfant         = db.Column(db.String(100), nullable=False)
    sexe_enfant           = db.Column(db.String(10), nullable=False)  # Ex : 'M', 'F'
    date_naissance        = db.Column(db.Date, nullable=False)
    heure_naissance       = db.Column(db.Time, nullable=False)
    lieu_naissance        = db.Column(db.String(100), nullable=False)  # Nom de l'hôpital ou lieu précis

    # --- Informations sur la mère ---
    nom_mere              = db.Column(db.String(100), nullable=False)
    prenom_mere           = db.Column(db.String(100), nullable=False)
    date_naissance_mere   = db.Column(db.Date, nullable=True)
    lieu_naissance_mere   = db.Column(db.String(100), nullable=True)
    nationalite_mere      = db.Column(db.String(50), nullable=True)
    profession_mere       = db.Column(db.String(100), nullable=True)
    type_piece_mere       = db.Column(db.String(50), nullable=True)  # CNI, passeport
    numero_piece_mere     = db.Column(db.String(100), nullable=True)

    # --- Informations sur le père (si disponible) ---
    nom_pere              = db.Column(db.String(100), nullable=True)
    prenom_pere           = db.Column(db.String(100), nullable=True)
    date_naissance_pere   = db.Column(db.Date, nullable=True)
    lieu_naissance_pere   = db.Column(db.String(100), nullable=True)
    nationalite_pere      = db.Column(db.String(50), nullable=True)
    profession_pere       = db.Column(db.String(100), nullable=True)
    type_piece_pere       = db.Column(db.String(50), nullable=True)
    numero_piece_pere     = db.Column(db.String(100), nullable=True)

    # --- Informations du déclarant (personne effectuant la déclaration) ---
    nom_declarant         = db.Column(db.String(100), nullable=True)
    prenom_declarant      = db.Column(db.String(100), nullable=True)
    lien_parente_declarant = db.Column(db.String(50), nullable=True)  # Père, Mère, tiers
    type_piece_declarant  = db.Column(db.String(50), nullable=True)
    numero_piece_declarant = db.Column(db.String(100), nullable=True)

    # --- Données du certificat médical ---
    numero_certificat_medical = db.Column(db.String(100), unique=True, nullable=True)
    date_certificat_medical   = db.Column(db.Date, nullable=True)
    nom_medecin               = db.Column(db.String(100), nullable=True)

    # --- Statut et traçabilité du dossier ---
    statut = db.Column(
        db.Enum(StatutDossier),
        default=StatutDossier.EN_ATTENTE,
        nullable=False
    )  # Enum pour forcer l’un des quatre statuts définis

    # Clés étrangères pour lier les entités :
    hopital_id = db.Column(
        db.Integer,
        db.ForeignKey('hopitaux.id', ondelete='CASCADE'),
        nullable=False
    )  # Hôpital ayant saisi le dossier

    mairie_id = db.Column(
        db.Integer,
        db.ForeignKey('mairies.id', ondelete='SET NULL'),
        nullable=True
    )  # Mairie assignée (peut être en attente)

    soumis_par_utilisateur_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', ondelete='RESTRICT'),
        nullable=False
    )  # Agent hôpital ayant soumis

    valide_par_utilisateur_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', ondelete='SET NULL'),
        nullable=True
    )  # Agent mairie ayant validé/rejeté

    date_soumission  = db.Column(db.DateTime, default=datetime.utcnow)
    date_validation  = db.Column(db.DateTime, nullable=True)
    motif_rejet      = db.Column(db.String(500), nullable=True)

    # Relation vers l'acte de naissance (1-à-1) :
    acte_naissance = db.relationship(
        'ActeNaissance',
        backref='dossier_naissance',
        uselist=False,
        cascade="all, delete-orphan"
    )  # uselist=False assure qu’un seul ActeNaissance par Dossier

    def __repr__(self):
        return f"<DossierNaissance {self.prenom_enfant} {self.nom_enfant} ({self.statut.value})>"


class ActeNaissance(db.Model):
    """Modèle pour l'acte de naissance généré et archivé."""
    __tablename__ = 'actes_naissance'

    id                      = db.Column(db.Integer, primary_key=True)
    numero_acte             = db.Column(db.String(100), unique=True, nullable=False)  # Numéro unique de l'acte
    date_enregistrement      = db.Column(db.DateTime, default=datetime.utcnow)         # Date d'établissement
    lieu_enregistrement      = db.Column(db.String(100), nullable=False)               # Nom de la mairie

    # --- Informations extraites du DossierNaissance (copiées au moment de la génération) ---
    nom_complet_enfant       = db.Column(db.String(200), nullable=False)
    sexe_enfant              = db.Column(db.String(10), nullable=False)
    date_naissance_enfant    = db.Column(db.Date, nullable=False)
    heure_naissance_enfant   = db.Column(db.Time, nullable=False)
    lieu_naissance_enfant    = db.Column(db.String(100), nullable=False)

    nom_complet_mere         = db.Column(db.String(200), nullable=False)
    nationalite_mere         = db.Column(db.String(50), nullable=True)
    nom_complet_pere         = db.Column(db.String(200), nullable=True)
    nationalite_pere         = db.Column(db.String(50), nullable=True)

    nom_complet_declarant    = db.Column(db.String(200), nullable=True)
    lien_parente_declarant   = db.Column(db.String(50), nullable=True)

    # --- Clés étrangères et relations ---
    dossier_naissance_id    = db.Column(
        db.Integer,
        db.ForeignKey('dossiers_naissance.id', ondelete='CASCADE'),
        unique=True,
        nullable=False
    )  # 1-à-1 avec DossierNaissance

    mairie_id               = db.Column(
        db.Integer,
        db.ForeignKey('mairies.id', ondelete='RESTRICT'),
        nullable=False
    )  # Mairie ayant généré l'acte

    genere_par_utilisateur_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', ondelete='RESTRICT'),
        nullable=False
    )  # Agent mairie qui a généré

    genere_le               = db.Column(db.DateTime, default=datetime.utcnow)

    chemin_pdf              = db.Column(db.String(255), nullable=True)  # Chemin relatif du fichier PDF généré
    est_actif               = db.Column(db.Boolean, default=True)        # Pour gérer l'annulation ou la révocation

    def __repr__(self):
        return f"<ActeNaissance {self.numero_acte} pour {self.nom_complet_enfant}>"


class JournalAudit(db.Model):
    """Modèle pour la journalisation des accès et des modifications (traçabilité et sécurité)."""
    __tablename__ = 'journal_audit'

    id                        = db.Column(db.Integer, primary_key=True)
    utilisateur_id            = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', ondelete='SET NULL'),
        nullable=True
    )  # ID de l'utilisateur ayant effectué l'action

    action                    = db.Column(db.String(255), nullable=False)  # Description, ex : "Création dossier X"
    horodatage                = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    adresse_ip                = db.Column(db.String(45), nullable=True)     # IP de l’utilisateur (optionnel)
    identifiant_enregistrement = db.Column(db.Integer, nullable=True)       # ID du dossier ou de l’acte
    type_enregistrement       = db.Column(db.String(50), nullable=True)     # 'DossierNaissance' ou 'ActeNaissance'

    utilisateur = db.relationship(
        'Utilisateur',
        backref='journal_audits',
        lazy='select'
    )

    def __repr__(self):
        return f"<JournalAudit {self.action} par Utilisateur {self.utilisateur_id} à {self.horodatage}>"
