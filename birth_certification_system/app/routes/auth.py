from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask_mail import Message
import random, string, logging

from ..config import Config
from app.models import Utilisateur, RoleUtilisateur
from app.database import db
from .. import mail  # Extension mail importée depuis __init__

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login():
    return render_template('auth/login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    mot_de_passe = request.form.get('mot_de_passe')

    utilisateur = Utilisateur.query.filter_by(email=email).first()

    if utilisateur and utilisateur.check_password(mot_de_passe):
        session['utilisateur_id'] = utilisateur.id
        session['role'] = utilisateur.role.value

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
        email = request.form.get('email').strip()
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur:
            try:
                # Générer code et expiration
                reset_code = ''.join(random.choices(string.digits, k=6))
                expiry = datetime.utcnow() + timedelta(minutes=30)

                # Stocker le code EN CLAIR (ou son hash, mais pas les deux)
                utilisateur.reset_code = reset_code  # Version en clair
                # OU si vous voulez vraiment hasher:
                # utilisateur.reset_code = generate_password_hash(reset_code)
                
                utilisateur.reset_code_expiry = expiry
                db.session.commit()

                # Envoyer le code par email (le vrai code, pas le hash)
                msg = Message(
                    subject="🔐 Code de vérification",
                    sender=Config.MAIL_DEFAULT_SENDER,
                    recipients=[email],
                    html=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
                        <h2 style="color: #2c3e50;">Réinitialisation de mot de passe</h2>
                        <p>Voici votre code de vérification :</p>
                        <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                            {reset_code}
                        </div>
                        <p style="font-size: 12px; color: #7f8c8d;">
                            ⏳ Ce code expire le {expiry.strftime('%d/%m/%Y à %H:%M')} UTC.
                        </p>
                    </div>
                    """
                )
                mail.send(msg)
                session['email_reset'] = email
                flash("✅ Un code a été envoyé à votre adresse email.", "success")
                return redirect(url_for('auth.verify_code'))

            except Exception as e:
                db.session.rollback()
                flash("❌ Erreur lors de l'envoi du code.", "danger")
                logging.error(f"Erreur reset password: {str(e)}")
        else:
            flash("⚠️ Aucun utilisateur trouvé avec cet email.", "warning")

    return render_template('auth/forgetpassword.html')


@auth_bp.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        code_saisi = request.form.get('code').strip()
        email = session.get('email_reset')

        if not email:
            flash("Session expirée. Veuillez recommencer.", "danger")
            return redirect(url_for('auth.forget_password'))

        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if not utilisateur or not utilisateur.reset_code or not utilisateur.reset_code_expiry:
            flash("❌ Code invalide ou expiré.", "danger")
            return redirect(url_for('auth.forget_password'))

        # Vérification expiration
        if datetime.utcnow() > utilisateur.reset_code_expiry:
            flash("⏳ Code expiré. Veuillez redemander un nouveau code.", "warning")
            return redirect(url_for('auth.forget_password'))

        # Gestion des tentatives
        nb_echecs = session.get('nb_echecs', 0)
        if nb_echecs >= 5:
            flash("🚫 Trop de tentatives. Recommencez la procédure.", "danger")
            return redirect(url_for('auth.forget_password'))

        # Vérification du code (selon votre choix de stockage)
        if utilisateur.reset_code == code_saisi:  # Si stocké en clair
        # OU si vous avez hashé:
        # if check_password_hash(utilisateur.reset_code, code_saisi):
            session['email_verified'] = email
            session.pop('nb_echecs', None)
            
            # Nettoyer le code après utilisation
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            db.session.commit()
            
            return redirect(url_for('auth.reset_password'))
        else:
            session['nb_echecs'] = nb_echecs + 1
            tentatives_restantes = 5 - session['nb_echecs']
            flash(f"❌ Code incorrect. Tentatives restantes: {tentatives_restantes}", "danger")

    return render_template('auth/verifycode.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Vérification de l'accès autorisé
    email = session.get('email_verified')
    if not email:
        flash("⛔ Session invalide. Veuillez recommencer la procédure.", "danger")
        return redirect(url_for('auth.forget_password'))

    if request.method == 'POST':
        # Récupération des données du formulaire
        mot_de_passe = request.form.get('password', '').strip()
        confirmation = request.form.get('confirm_password', '').strip()

        # Validation des mots de passe
        if not mot_de_passe or not confirmation:
            flash("❌ Veuillez remplir tous les champs.", "danger")
            return redirect(url_for('auth.reset_password'))

        if mot_de_passe != confirmation:
            flash("❌ Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('auth.reset_password'))

        # Validation de la force du mot de passe
        if len(mot_de_passe) < 8:
            flash("🔒 Le mot de passe doit contenir au moins 8 caractères.", "warning")
            return redirect(url_for('auth.reset_password'))

        # Recherche de l'utilisateur
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if not utilisateur:
            flash("❌ Utilisateur introuvable.", "danger")
            session.pop('email_verified', None)
            return redirect(url_for('auth.forget_password'))

        try:
            # Mise à jour du mot de passe
            utilisateur.mot_de_passe_hash = generate_password_hash(mot_de_passe)
            utilisateur.reset_code = None
            utilisateur.reset_code_expiry = None
            utilisateur.mis_a_jour_le = datetime.utcnow()  # Mise à jour du timestamp
            
            db.session.commit()
            
            # Nettoyage de la session et redirection
            session.pop('email_verified', None)
            flash("✅ Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la réinitialisation du mot de passe: {str(e)}")
            flash("❌ Une erreur est survenue lors de la réinitialisation. Veuillez réessayer.", "danger")

    return render_template('auth/reset_password.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
