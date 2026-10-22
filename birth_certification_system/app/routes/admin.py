from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from app.models import (
    Hopital,
    JournalAudit,
    Mairie,
    RoleUtilisateur,
    Utilisateur,
)
from app.database import db
import secrets
import string
import logging
import os
from app import mail
from app.config import Config
from flask_mail import Message
import click
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# pour generer un mot de passe automatiquement
def generate_random_password(length=12):
    """Génère un mot de passe aléatoire robuste"""
    uppercase = secrets.choice(string.ascii_uppercase)
    lowercase = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
    remaining = length - 4
    characters = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    rest = ''.join(secrets.choice(characters) for _ in range(remaining))
    password = list(uppercase + lowercase + digit + special + rest)
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

# message deja cree
def send_welcome_email(email, nom, role, code=None):
    """Envoie un email de bienvenue personnalisé selon le rôle."""
    try:
        # Définir un nom de rôle lisible
        role_mapping = {
            "ADMIN": "Administrateur",
            "AGENT_MAIRIE": "Agent de Mairie",
            "AGENT_HOPITAL": "Agent d’Hôpital"
        }
        role_display = role_mapping.get(role, "Utilisateur")

        # Objet de l’email
        msg = Message(
            subject=f"🎉 Bienvenue sur la plateforme - {role_display}",
            sender=Config.MAIL_DEFAULT_SENDER,
            recipients=[email],
            charset='utf-8'
        )

        # Informations supplémentaires selon le rôle
        role_instructions = ""
        if role == "ADMIN":
            role_instructions = "\n🔐 Vous avez un accès complet au système en tant qu’administrateur."
        elif role == "AGENT_MAIRIE":
            role_instructions = "\n🏛️ Vous pouvez gérer les actes de naissance liés à votre mairie."
        elif role == "AGENT_HOPITAL":
            role_instructions = "\n🏥 Vous êtes autorisé à enregistrer des naissances depuis l’hôpital associé."

        code_info = f"\n🎫 Code d’identification : {code}" if code else ""

        # Corps de l’email
        msg.body = f"""👋 Bonjour {nom},

Votre compte a été créé avec succès sur la plateforme de gestion des actes de naissance.

📧 Identifiant : {email}{code_info}
Pour définir votre mot de passe, ouvrez la page de connexion et utilisez le lien « Mot de passe oublié ».

{role_instructions}

Bien cordialement,
L’équipe administrative
"""

        mail.send(msg)

    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email de bienvenue : {str(e)}")


admin_bp = Blueprint('admin', __name__)


def _record_admin_action(action, record_type, record_id):
    db.session.add(
        JournalAudit(
            utilisateur_id=session.get('utilisateur_id'),
            action=action,
            type_enregistrement=record_type,
            identifiant_enregistrement=record_id,
            adresse_ip=request.remote_addr,
        )
    )


@admin_bp.before_request
def require_admin():
    user_id = session.get('utilisateur_id')
    if not isinstance(user_id, int):
        session.clear()
        flash("Veuillez vous connecter avec un compte administrateur.", "warning")
        return redirect(url_for('auth.login'))

    utilisateur = db.session.get(Utilisateur, user_id)
    if utilisateur is None:
        session.clear()
        flash("Votre session a expiré. Veuillez vous reconnecter.", "warning")
        return redirect(url_for('auth.login'))
    if utilisateur.role is not RoleUtilisateur.ADMIN:
        abort(403)

    session['role'] = utilisateur.role.value
    session['nom_utilisateur'] = utilisateur.nom_utilisateur
    session['hopital_id'] = utilisateur.hopital_id
    session['mairie_id'] = utilisateur.mairie_id


@admin_bp.cli.command("create-admin")
def create_admin():
    """Cree le compte administrateur initial depuis la CLI Flask."""
    username = os.getenv("ADMIN_USERNAME", "Fozet Junior").strip()
    email = os.getenv("ADMIN_EMAIL", "fozetj29@fmail.com").strip()
    password = os.getenv("ADMIN_PASSWORD")

    if not username or len(username) > 80:
        raise click.ClickException("ADMIN_USERNAME doit contenir entre 1 et 80 caracteres.")
    if not email or len(email) > 120:
        raise click.ClickException("ADMIN_EMAIL doit contenir entre 1 et 120 caracteres.")

    if password is None:
        password = click.prompt(
            "Mot de passe administrateur",
            hide_input=True,
            confirmation_prompt=True,
        )

    if len(password) < 12:
        raise click.ClickException("Le mot de passe doit contenir au moins 12 caracteres.")

    existing_account = Utilisateur.query.filter(
        (Utilisateur.nom_utilisateur == username) | (Utilisateur.email == email)
    ).first()
    if existing_account:
        raise click.ClickException(
            "Un compte utilise deja ce nom ou cette adresse email; aucune modification effectuee."
        )

    admin = Utilisateur(
        nom_utilisateur=username,
        email=email,
        role=RoleUtilisateur.ADMIN,
    )
    admin.set_password(password)
    db.session.add(admin)

    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise click.ClickException("Impossible de creer le compte administrateur.") from error

    click.echo(f"Compte administrateur cree : {username} ({email})")


# Route d'affichage du dashboard
@admin_bp.route('/admin')
def dashboard():
    from .admin_extras import contexte_admin

    return render_template('admin/dashboard.html', **contexte_admin())

# Ajouter un utilisateur (déjà donné par toi)
@admin_bp.route('/utilisateur/ajouter', methods=['POST'])
def ajouter_utilisateur():
    try:
        nom_utilisateur = request.form.get('nom_utilisateur')
        email = request.form.get('email')
        mot_de_passe = request.form.get('mot_de_passe') or generate_random_password()
        role = request.form.get('role')
        hopital_id = request.form.get('hopital_id') or None
        mairie_id = request.form.get('mairie_id') or None

        if not nom_utilisateur or not email or not mot_de_passe:
            flash("Champs obligatoires manquants", "danger")
            return redirect(url_for('admin.dashboard'))
        if len(mot_de_passe) < 12:
            flash("Le mot de passe doit contenir au moins 12 caractères.", "danger")
            return redirect(url_for('admin.dashboard'))

        # Vérifier l’unicité
        existing_user = Utilisateur.query.filter(
            (Utilisateur.nom_utilisateur == nom_utilisateur) |
            (Utilisateur.email == email)
        ).first()
        if existing_user:
            flash("❌ Utilisateur avec ce nom ou cet email existe déjà.", "warning")
            return redirect(url_for('admin.dashboard'))

        utilisateur = Utilisateur(
            nom_utilisateur=nom_utilisateur,
            email=email,
            role=RoleUtilisateur[role],
            hopital_id=hopital_id,
            mairie_id=mairie_id
        )
        utilisateur.set_password(mot_de_passe)

        db.session.add(utilisateur)
        db.session.flush()
        _record_admin_action(
            f"Création du compte {nom_utilisateur}",
            "Utilisateur",
            utilisateur.id,
        )
        db.session.commit()

        send_welcome_email(email=email, nom=nom_utilisateur, role=role)
        flash("✅ Utilisateur ajouté avec succès", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur lors de l'ajout : {str(e)}", "danger")

    return redirect(url_for('admin.dashboard'))



# Modifier un utilisateur
@admin_bp.route('/utilisateur/modifier/<int:utilisateur_id>', methods=['POST'])
def modifier_utilisateur(utilisateur_id):
    utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    try:
        utilisateur.nom_utilisateur = request.form.get('nom_utilisateur')
        utilisateur.email = request.form.get('email')
        role = request.form.get('role')
        utilisateur.role = RoleUtilisateur[role]
        utilisateur.hopital_id = request.form.get('hopital_id') or None
        utilisateur.mairie_id = request.form.get('mairie_id') or None

        mot_de_passe = request.form.get('mot_de_passe')
        if mot_de_passe:
            if len(mot_de_passe) < 12:
                flash("Le mot de passe doit contenir au moins 12 caractères.", "danger")
                return redirect(url_for('admin.dashboard'))
            utilisateur.set_password(mot_de_passe)

        _record_admin_action(
            f"Modification du compte {utilisateur.nom_utilisateur}",
            "Utilisateur",
            utilisateur.id,
        )
        db.session.commit()
        flash("✅ Utilisateur modifié avec succès", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur lors de la modification : {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


# Supprimer un utilisateur
@admin_bp.route('/utilisateur/supprimer/<int:utilisateur_id>', methods=['POST'])
def supprimer_utilisateur(utilisateur_id):
    utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    try:
        username = utilisateur.nom_utilisateur
        _record_admin_action(
            f"Suppression du compte {username}",
            "Utilisateur",
            utilisateur.id,
        )
        db.session.delete(utilisateur)
        db.session.commit()
        flash("✅ Utilisateur supprimé avec succès", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


# Voir un utilisateur (page ou modal, ici exemple page)
@admin_bp.route('/utilisateur/<int:utilisateur_id>')
def voir_utilisateur(utilisateur_id):
    utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    return render_template('admin/voir_utilisateur.html', utilisateur=utilisateur)

#Route pour ajouter une mairie
@admin_bp.route('/admin/mairie/ajouter', methods=['POST'])
def ajouter_mairie():
    mairie = Mairie(
        nom=request.form['nom'],
        localisation=request.form['localisation'],
        region=request.form['region'],
        email_contact=request.form.get('email_contact'),
        numero_telephone=request.form.get('numero_telephone')
    )
    db.session.add(mairie)
    db.session.flush()
    _record_admin_action(f"Création de la mairie {mairie.nom}", "Mairie", mairie.id)
    db.session.commit()
    flash("Mairie ajoutée avec succès", "success")
    return redirect(url_for('admin.dashboard', _anchor='page3'))

#Modifier une mairie
@admin_bp.route('/admin/mairie/modifier/<int:mairie_id>', methods=['POST'])
def modifier_mairie(mairie_id):
    mairie = Mairie.query.get_or_404(mairie_id)
    mairie.nom = request.form['nom']
    mairie.localisation = request.form['localisation']
    mairie.region = request.form['region']
    mairie.email_contact = request.form.get('email_contact')
    mairie.numero_telephone = request.form.get('numero_telephone')
    _record_admin_action(f"Modification de la mairie {mairie.nom}", "Mairie", mairie.id)
    db.session.commit()
    flash("Mairie modifiée avec succès", "warning")
    return redirect(url_for('admin.dashboard', _anchor='page3'))

# Supremer une mairie
@admin_bp.route('/admin/mairie/supprimer/<int:mairie_id>', methods=['POST'])
def supprimer_mairie(mairie_id):
    mairie = Mairie.query.get_or_404(mairie_id)
    _record_admin_action(f"Suppression de la mairie {mairie.nom}", "Mairie", mairie.id)
    db.session.delete(mairie)
    db.session.commit()
    flash("Mairie supprimée", "danger")
    return redirect(url_for('admin.dashboard', _anchor='page3'))

#ajouter hopital
@admin_bp.route('/admin/hopital/ajouter', methods=['POST'])
def ajouter_hopital():
    nom = request.form.get('nom')
    localisation = request.form.get('localisation')
    region = request.form.get('region')
    email_contact = request.form.get('email_contact')
    numero_telephone = request.form.get('numero_telephone')

    if not nom or not localisation or not region:
        flash("Les champs Nom, Localisation et Région sont obligatoires.", "danger")
        return redirect(url_for('admin.dashboard'))

    hopital = Hopital(
        nom=nom,
        localisation=localisation,
        region=region,
        email_contact=email_contact,
        numero_telephone=numero_telephone
    )
    db.session.add(hopital)
    db.session.flush()
    _record_admin_action(f"Création de l'hôpital {hopital.nom}", "Hôpital", hopital.id)
    db.session.commit()
    flash("✅ Hôpital ajouté avec succès", "success")
    return redirect(url_for('admin.dashboard'))

#modifier hopital
@admin_bp.route('/admin/hopital/modifier/<int:hopital_id>', methods=['POST'])
def modifier_hopital(hopital_id):
    hopital = Hopital.query.get_or_404(hopital_id)

    hopital.nom = request.form.get('nom')
    hopital.localisation = request.form.get('localisation')
    hopital.region = request.form.get('region')
    hopital.email_contact = request.form.get('email_contact')
    hopital.numero_telephone = request.form.get('numero_telephone')

    _record_admin_action(f"Modification de l'hôpital {hopital.nom}", "Hôpital", hopital.id)
    db.session.commit()
    flash("✏️ Hôpital modifié avec succès", "info")
    return redirect(url_for('admin.dashboard'))

#suprimer hopital
@admin_bp.route('/admin/hopital/supprimer/<int:hopital_id>', methods=['POST'])
def supprimer_hopital(hopital_id):
    hopital = Hopital.query.get_or_404(hopital_id)
    _record_admin_action(f"Suppression de l'hôpital {hopital.nom}", "Hôpital", hopital.id)
    db.session.delete(hopital)
    db.session.commit()
    flash("🗑️ Hôpital supprimé avec succès", "warning")
    return redirect(url_for('admin.dashboard'))


from . import admin_extras  # noqa: E402,F401
