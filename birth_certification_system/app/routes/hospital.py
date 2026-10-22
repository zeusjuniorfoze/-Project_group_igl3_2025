from flask import Blueprint, abort, render_template, session, redirect, url_for, flash , request
from datetime import datetime , time
from app.models import DossierNaissance, Utilisateur , db , Mairie , StatutDossier, RoleUtilisateur
from flask_mail import Message
import logging
from ..config import Config
from .. import mail

hopital_bp = Blueprint('hopital', __name__)


@hopital_bp.before_request
def require_hospital_agent():
    user_id = session.get('utilisateur_id')
    if not isinstance(user_id, int):
        session.clear()
        flash("Veuillez vous connecter avec un compte hospitalier.", "warning")
        return redirect(url_for('auth.login'))

    utilisateur = db.session.get(Utilisateur, user_id)
    if utilisateur is None:
        session.clear()
        flash("Votre session a expiré. Veuillez vous reconnecter.", "warning")
        return redirect(url_for('auth.login'))
    if utilisateur.role is not RoleUtilisateur.AGENT_HOPITAL:
        abort(403)
    if utilisateur.hopital_id is None:
        abort(403)

    session['role'] = utilisateur.role.value
    session['nom_utilisateur'] = utilisateur.nom_utilisateur
    session['hopital_id'] = utilisateur.hopital_id
    session['mairie_id'] = utilisateur.mairie_id


@hopital_bp.route('/declarations')
def dashboard():
    # Vérifie si l'utilisateur est connecté
    if 'utilisateur_id' not in session:
        flash("Veuillez vous connecter pour accéder à cette page.", "warning")
        return redirect(url_for('auth.login'))

    # Récupère l'utilisateur connecté
    utilisateur_id = session['utilisateur_id']
    utilisateur = Utilisateur.query.get(utilisateur_id)
    mairies = Mairie.query.all()

    if not utilisateur or not utilisateur.hopital_id:
        flash("Accès refusé. Vous n'êtes pas lié à un hôpital.", "danger")
        return redirect(url_for('auth.login'))

    # Filtrer les déclarations pour l'hôpital lié à l'utilisateur
    declarations = DossierNaissance.query.filter_by(hopital_id=utilisateur.hopital_id).all()

    return render_template('hopital/dashboard.html', declarations=declarations , mairies=mairies,StatutDossier=StatutDossier)


@hopital_bp.route('/ajouter_declaration', methods=['POST'])
def ajouter_declaration():
    # ✅ Vérifie que l'utilisateur est bien connecté
    if 'utilisateur_id' not in session or 'hopital_id' not in session:
        flash("Vous devez être connecté pour effectuer cette action.", "danger")
        return redirect(url_for('auth.login'))

    try:
        # 🧠 Données obligatoires de l'enfant
        nom_enfant = request.form.get('nom_enfant')
        prenom_enfant = request.form.get('prenom_enfant')
        sexe_enfant = request.form.get('sexe_enfant')
        date_naissance = request.form.get('date_naissance')
        heure_naissance = request.form.get('heure_naissance')
        lieu_naissance = request.form.get('lieu_naissance')

        # 👩 Informations de la mère (obligatoire pour la plupart)
        nom_mere = request.form.get('nom_mere')
        prenom_mere = request.form.get('prenom_mere')

        # 📋 Données facultatives mère
        numero_mere = request.form.get('numero_mere')
        email_mere = request.form.get('email_mere')
        date_naissance_mere = request.form.get('date_naissance_mere')
        lieu_naissance_mere = request.form.get('lieu_naissance_mere')
        nationalite_mere = request.form.get('nationalite_mere')
        profession_mere = request.form.get('profession_mere')
        type_piece_mere = request.form.get('type_piece_mere')
        numero_piece_mere = request.form.get('numero_piece_mere')

        # 👨 Données du père
        nom_pere = request.form.get('nom_pere')
        prenom_pere = request.form.get('prenom_pere')
        numero_pere = request.form.get('numero_pere')
        email_pere = request.form.get('email_pere')
        date_naissance_pere = request.form.get('date_naissance_pere')
        lieu_naissance_pere = request.form.get('lieu_naissance_pere')
        nationalite_pere = request.form.get('nationalite_pere')
        profession_pere = request.form.get('profession_pere')
        type_piece_pere = request.form.get('type_piece_pere')
        numero_piece_pere = request.form.get('numero_piece_pere')

        # 👤 Données du déclarant
        nom_declarant = request.form.get('nom_declarant')
        prenom_declarant = request.form.get('prenom_declarant')
        lien_parente_declarant = request.form.get('lien_parente_declarant')
        type_piece_declarant = request.form.get('type_piece_declarant')
        numero_piece_declarant = request.form.get('numero_piece_declarant')

        # 🏥 Informations médicales
        numero_certificat_medical = request.form.get('numero_certificat_medical')
        date_certificat_medical = request.form.get('date_certificat_medical')
        nom_medecin = request.form.get('nom_medecin')

        # 🆔 ID de l’hôpital et de l'utilisateur à partir de la session
        hopital_id = session.get('hopital_id')
        utilisateur_id = session.get('utilisateur_id')

        # 🛠️ Crée une nouvelle instance du modèle
        nouvelle_declaration = DossierNaissance(
            nom_enfant=nom_enfant,
            prenom_enfant=prenom_enfant,
            sexe_enfant=sexe_enfant,
            date_naissance=datetime.strptime(date_naissance, "%Y-%m-%d"),
            heure_naissance=datetime.strptime(heure_naissance, "%H:%M").time(),
            lieu_naissance=lieu_naissance,
            nom_mere=nom_mere,
            prenom_mere=prenom_mere,
            numero_mere=numero_mere,
            email_mere=email_mere,
            date_naissance_mere=datetime.strptime(date_naissance_mere, "%Y-%m-%d") if date_naissance_mere else None,
            lieu_naissance_mere=lieu_naissance_mere,
            nationalite_mere=nationalite_mere,
            profession_mere=profession_mere,
            type_piece_mere=type_piece_mere,
            numero_piece_mere=numero_piece_mere,
            nom_pere=nom_pere,
            prenom_pere=prenom_pere,
            numero_pere=numero_pere,
            email_pere=email_pere,
            date_naissance_pere=datetime.strptime(date_naissance_pere, "%Y-%m-%d") if date_naissance_pere else None,
            lieu_naissance_pere=lieu_naissance_pere,
            nationalite_pere=nationalite_pere,
            profession_pere=profession_pere,
            type_piece_pere=type_piece_pere,
            numero_piece_pere=numero_piece_pere,
            nom_declarant=nom_declarant,
            prenom_declarant=prenom_declarant,
            lien_parente_declarant=lien_parente_declarant,
            type_piece_declarant=type_piece_declarant,
            numero_piece_declarant=numero_piece_declarant,
            numero_certificat_medical=numero_certificat_medical,
            date_certificat_medical=datetime.strptime(date_certificat_medical, "%Y-%m-%d") if date_certificat_medical else None,
            nom_medecin=nom_medecin,
            hopital_id=hopital_id,
            soumis_par_utilisateur_id=utilisateur_id,
        )

        # 💾 Enregistre dans la base
        db.session.add(nouvelle_declaration)
        db.session.commit()

        flash("Déclaration de naissance ajoutée avec succès ✅", "success")
        return redirect(url_for('hopital.dashboard'))

    except Exception as e:
        print(e)
        flash("Erreur lors de l'ajout de la déclaration. Veuillez vérifier les données.", "danger")
        return redirect(url_for('hopital.dashboard'))
    
@hopital_bp.route('/modifier_declaration/<int:dossier_id>', methods=['POST'])
def modifier_declaration(dossier_id):
    dossier = DossierNaissance.query.filter_by(
        id=dossier_id,
        hopital_id=session['hopital_id'],
    ).first_or_404()
    
    try:
        # Mise à jour des informations sur l'enfant
        dossier.nom_enfant = request.form.get('nom_enfant')
        dossier.prenom_enfant = request.form.get('prenom_enfant')
        dossier.sexe_enfant = request.form.get('sexe_enfant')
        
        # Conversion des dates et heures
        if request.form.get('date_naissance'):
            dossier.date_naissance = datetime.strptime(request.form.get('date_naissance'), '%Y-%m-%d').date()
        if request.form.get('heure_naissance'):
            dossier.heure_naissance = time.fromisoformat(request.form.get('heure_naissance'))
        
        dossier.lieu_naissance = request.form.get('lieu_naissance')
        
        # Mise à jour des informations sur la mère
        dossier.nom_mere = request.form.get('nom_mere')
        dossier.prenom_mere = request.form.get('prenom_mere')
        dossier.numero_mere = request.form.get('numero_mere')
        dossier.email_mere = request.form.get('email_mere')
        
        if request.form.get('date_naissance_mere'):
            dossier.date_naissance_mere = datetime.strptime(request.form.get('date_naissance_mere'), '%Y-%m-%d').date()
        dossier.lieu_naissance_mere = request.form.get('lieu_naissance_mere')
        dossier.nationalite_mere = request.form.get('nationalite_mere')
        dossier.profession_mere = request.form.get('profession_mere')
        dossier.type_piece_mere = request.form.get('type_piece_mere')
        dossier.numero_piece_mere = request.form.get('numero_piece_mere')
        
        # Mise à jour des informations sur le père
        dossier.nom_pere = request.form.get('nom_pere')
        dossier.prenom_pere = request.form.get('prenom_pere')
        dossier.numero_pere = request.form.get('numero_pere')
        dossier.email_pere = request.form.get('email_pere')
        
        if request.form.get('date_naissance_pere'):
            dossier.date_naissance_pere = datetime.strptime(request.form.get('date_naissance_pere'), '%Y-%m-%d').date()
        dossier.lieu_naissance_pere = request.form.get('lieu_naissance_pere')
        dossier.nationalite_pere = request.form.get('nationalite_pere')
        dossier.profession_pere = request.form.get('profession_pere')
        dossier.type_piece_pere = request.form.get('type_piece_pere')
        dossier.numero_piece_pere = request.form.get('numero_piece_pere')
        
        # Mise à jour des informations sur le déclarant
        dossier.nom_declarant = request.form.get('nom_declarant')
        dossier.prenom_declarant = request.form.get('prenom_declarant')
        dossier.lien_parente_declarant = request.form.get('lien_parente_declarant')
        dossier.type_piece_declarant = request.form.get('type_piece_declarant')
        dossier.numero_piece_declarant = request.form.get('numero_piece_declarant')
        
        # Mise à jour du certificat médical
        dossier.numero_certificat_medical = request.form.get('numero_certificat_medical')
        
        if request.form.get('date_certificat_medical'):
            dossier.date_certificat_medical = datetime.strptime(request.form.get('date_certificat_medical'), '%Y-%m-%d').date()
        
        dossier.nom_medecin = request.form.get('nom_medecin')
        
        # Sauvegarde en base de données
        db.session.commit()
        
        flash("✅ Déclaration mise à jour avec succès!", "success")
    
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur lors de la mise à jour: {str(e)}", "danger")
    
    return redirect(url_for('hopital.dashboard'))

    
@hopital_bp.route('/supprimer_declaration/<int:id>', methods=['POST'])
def supprimer_declaration(id):
    dossier = DossierNaissance.query.filter_by(
        id=id,
        hopital_id=session['hopital_id'],
    ).first_or_404()
    db.session.delete(dossier)
    db.session.commit()
    flash("Déclaration supprimée avec succès.", "success")
    return redirect(url_for('hopital.dashboard'))

def send_transfert_email(dossier, mairie):
    """Envoie un email à la mère pour l'informer du transfert à une mairie."""
    try:
        if not dossier.email_mere:
            return  # Pas d'email à envoyer

        msg = Message(
            subject=f"📬 Déclaration transférée à la mairie de {mairie.nom}",  # <-- Correction ici (nom au lieu de nom_mairie)
            sender=Config.MAIL_DEFAULT_SENDER,
            recipients=[dossier.email_mere],
            charset='utf-8'
        )

        msg.body = f"""👋 Bonjour {dossier.prenom_mere} {dossier.nom_mere},

Votre déclaration de naissance pour l'enfant **{dossier.prenom_enfant} {dossier.nom_enfant}** a été transférée avec succès à la mairie suivante :

🏛️ **Mairie :** {mairie.nom}
📍 **Localisation :** {mairie.localisation}  
📞 **Téléphone :** {mairie.numero_telephone if hasattr(mairie, 'numero_telephone') else 'Non renseigné'}
📧 **Email :** {mairie.email_contact if hasattr(mairie, 'email_contact') else 'Non renseigné'}

📌 Pour finaliser la procédure, veuillez vous rendre à la mairie accompagnée du père de l'enfant, avec :
- Vos cartes nationales d'identité (père et mère)
- Vos actes de naissance

Merci de le faire dans les plus brefs délais pour l'établissement de l'acte de naissance.

Bien cordialement,  
L'équipe administrative
"""

        mail.send(msg)
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email de transfert : {str(e)}")

@hopital_bp.route('/declaration/<int:id>/transferer', methods=['POST'])
def transferer_declaration(id):
    dossier = DossierNaissance.query.filter_by(
        id=id,
        hopital_id=session['hopital_id'],
    ).first_or_404()
    mairie_id = request.form.get('mairie_id')

    if mairie_id:
        mairie = Mairie.query.get(mairie_id)
        if not mairie:
            flash("Mairie non trouvée.", "danger")
            return redirect(url_for('hopital.dashboard'))  # <-- Correction ici

        dossier.mairie_id = int(mairie_id)
        dossier.statut = StatutDossier.EN_ATTENTE
        dossier.date_transfert = datetime.utcnow()

        try:
            db.session.commit()
            send_transfert_email(dossier, mairie)
            flash("Déclaration transférée avec succès et email envoyé à la mère.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors du transfert : " + str(e), "danger")
    else:
        flash("Veuillez sélectionner une mairie.", "danger")

    return redirect(url_for('hopital.dashboard'))  # <-- Correction ici