from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta, timezone
import hmac
import secrets
from flask_mail import Message
from sqlalchemy.exc import SQLAlchemyError
from ..config import Config
from app.models import Utilisateur, RoleUtilisateur
from app.database import db
from .. import mail  # Extension mail importée depuis __init__

auth_bp = Blueprint('auth', __name__)
RESET_CODE_LIFETIME = timedelta(minutes=30)
RESET_REQUEST_COOLDOWN = timedelta(minutes=1)
MAX_RESET_ATTEMPTS = 5


def _hash_reset_code(code):
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), "sha256").hexdigest()


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clear_reset_session():
    session.pop('email_reset', None)
    session.pop('email_verified', None)

@auth_bp.route('/login', methods=['GET'])
def login():
    return render_template('auth/login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    email = (request.form.get('email') or '').strip()
    mot_de_passe = request.form.get('mot_de_passe') or ''
    session.clear()

    utilisateur = Utilisateur.query.filter_by(email=email).first()

    if utilisateur and utilisateur.check_password(mot_de_passe):
        session.clear()
        session.permanent = True
        session['utilisateur_id'] = utilisateur.id
        session['role'] = utilisateur.role.value
        session['nom_utilisateur'] = utilisateur.nom_utilisateur
        session['hopital_id'] = utilisateur.hopital_id
        session['mairie_id'] = utilisateur.mairie_id

        if utilisateur.role == RoleUtilisateur.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif utilisateur.role == RoleUtilisateur.AGENT_HOPITAL:
            return redirect(url_for('hopital.dashboard'))
        elif utilisateur.role == RoleUtilisateur.AGENT_MAIRIE:
            return redirect(url_for('mairie.dashboard'))
        else:
            flash("Rôle non reconnu. Contactez l'administrateur.", "danger")
    else:
        flash("Email ou mot de passe incorrect", "danger")

    return redirect(url_for('auth.login'))


@auth_bp.route('/forgetpassword', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        _clear_reset_session()
        utilisateur = (
            Utilisateur.query.filter_by(email=email).with_for_update().first()
        )

        if not utilisateur:
            flash("Aucun compte n'est associé à cette adresse e-mail.", "danger")
            return render_template('auth/forgetpassword.html', email=email)

        now_utc = datetime.now(timezone.utc)
        requested_at = utilisateur.reset_requested_at
        cooldown_active = (
            requested_at is not None
            and now_utc - _as_utc(requested_at) < RESET_REQUEST_COOLDOWN
        )

        if cooldown_active:
            code_is_valid = (
                utilisateur.reset_code
                and utilisateur.reset_code_expiry
                and now_utc <= _as_utc(utilisateur.reset_code_expiry)
            )
            if code_is_valid:
                session['email_reset'] = email
                flash(
                    "Un code vient d'être envoyé. Consultez votre boîte e-mail "
                    "ou attendez une minute avant d'en demander un autre.",
                    "info",
                )
                return redirect(url_for('auth.verify_code'))

            flash(
                "Veuillez attendre une minute avant de demander un nouveau code.",
                "warning",
            )
            return redirect(url_for('auth.forget_password'))

        reset_code = f"{secrets.randbelow(1_000_000):06d}"
        utilisateur.reset_code = _hash_reset_code(reset_code)
        utilisateur.reset_code_expiry = now_utc + RESET_CODE_LIFETIME
        utilisateur.reset_attempts = 0
        utilisateur.reset_requested_at = now_utc
        utilisateur.reset_verified = False

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "Impossible d'enregistrer une demande de reinitialisation."
            )
            flash(
                "Impossible de traiter votre demande pour le moment. Réessayez plus tard.",
                "danger",
            )
            return redirect(url_for('auth.forget_password'))

        try:
            msg = Message(
                subject="Code de vérification",
                sender=Config.MAIL_DEFAULT_SENDER,
                recipients=[email],
                body=(
                    "Votre code de réinitialisation est : "
                    f"{reset_code}\nIl expire dans 30 minutes."
                ),
            )
            mail.send(msg)
        except Exception:
            current_app.logger.exception(
                "Echec d'envoi du code de reinitialisation."
            )
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.reset_attempts = 0
            utilisateur.reset_requested_at = None
            utilisateur.reset_verified = False
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception(
                    "Impossible d'invalider le code apres l'echec d'envoi."
                )
            flash(
                "Le courriel n'a pas pu être envoyé. Vérifiez votre configuration "
                "ou réessayez plus tard.",
                "danger",
            )
            return redirect(url_for('auth.forget_password'))

        session['email_reset'] = email
        flash("Un code de vérification vient de vous être envoyé par e-mail.", "success")
        return redirect(url_for('auth.verify_code'))

    return render_template('auth/forgetpassword.html')


@auth_bp.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    email = session.get('email_reset')
    if not email:
        flash("Aucune demande de vérification active. Demandez d'abord un code.", "warning")
        return redirect(url_for('auth.forget_password'))

    if request.method == 'POST':
        code_saisi = request.form.get('code', '').strip()

        utilisateur = Utilisateur.query.filter_by(email=email).first()
        
        if not utilisateur or not utilisateur.reset_code or not utilisateur.reset_code_expiry:
            flash("❌ Code invalide ou déjà utilisé.", "danger")
            _clear_reset_session()
            return redirect(url_for('auth.forget_password'))

        now_utc = datetime.now(timezone.utc)
        if now_utc > _as_utc(utilisateur.reset_code_expiry):
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.reset_attempts = 0
            utilisateur.reset_verified = False
            db.session.commit()
            _clear_reset_session()
            flash("⌛ Le code a expiré. Veuillez en demander un nouveau.", "warning")
            return redirect(url_for('auth.forget_password'))

        if utilisateur.reset_attempts >= MAX_RESET_ATTEMPTS:
            flash("🔒 Trop de tentatives échouées. La procédure a été bloquée.", "danger")
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.reset_attempts = 0
            utilisateur.reset_verified = False
            db.session.commit()
            _clear_reset_session()
            return redirect(url_for('auth.forget_password'))

        if hmac.compare_digest(utilisateur.reset_code, _hash_reset_code(code_saisi)):
            session['email_verified'] = email
            session.pop('email_reset', None)
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.reset_attempts = 0
            utilisateur.reset_verified = True
            db.session.commit()
            
            flash("✅ Code vérifié avec succès. Vous pouvez maintenant définir un nouveau mot de passe.", "success")
            return redirect(url_for('auth.reset_password'))
        else:
            utilisateur.reset_attempts += 1
            if utilisateur.reset_attempts >= MAX_RESET_ATTEMPTS:
                utilisateur.reset_code = None
                utilisateur.reset_code_expiry = None
                utilisateur.reset_attempts = 0
                utilisateur.reset_verified = False
                _clear_reset_session()
                db.session.commit()
                flash("🔒 Trop de tentatives échouées. Demandez un nouveau code.", "danger")
            else:
                db.session.commit()
                tentatives_restantes = MAX_RESET_ATTEMPTS - utilisateur.reset_attempts
                flash(f"❌ Code incorrect. Il vous reste {tentatives_restantes} tentative(s).", "danger")

    return render_template('auth/verifycode.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('email_verified')
    if not email:
        flash("⛔ Session invalide. Veuillez recommencer la procédure.", "danger")
        return redirect(url_for('auth.forget_password'))

    if request.method == 'POST':
        mot_de_passe = request.form.get('password', '')
        confirmation = request.form.get('confirm_password', '')

        if not mot_de_passe or not confirmation:
            flash("❌ Veuillez remplir tous les champs.", "danger")
            return redirect(url_for('auth.reset_password'))

        if mot_de_passe != confirmation:
            flash("❌ Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('auth.reset_password'))

        if len(mot_de_passe) < 12:
            flash("🔒 Le mot de passe doit contenir au moins 12 caractères.", "warning")
            return redirect(url_for('auth.reset_password'))

        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if not utilisateur or not utilisateur.reset_verified:
            flash("❌ Utilisateur introuvable.", "danger")
            _clear_reset_session()
            return redirect(url_for('auth.forget_password'))

        try:
            utilisateur.set_password(mot_de_passe)
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.reset_attempts = 0
            utilisateur.reset_verified = False
            utilisateur.mis_a_jour_le = datetime.now(timezone.utc)
            
            db.session.commit()
            
            _clear_reset_session()
            flash("✅ Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('auth.login'))

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erreur lors de la reinitialisation du mot de passe."
            )
            flash("❌ Une erreur est survenue lors de la réinitialisation. Veuillez réessayer.", "danger")

    return render_template('auth/reset_password.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
