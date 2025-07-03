from flask import Blueprint, render_template, session, redirect, url_for, flash , request


from datetime import datetime

from app.models import DossierNaissance, Utilisateur , db

hopital_bp = Blueprint('hopital', __name__)

@hopital_bp.route('/declarations')
def dashboard():
    # Vérifie si l'utilisateur est connecté
    if 'utilisateur_id' not in session:
        flash("Veuillez vous connecter pour accéder à cette page.", "warning")
        return redirect(url_for('auth.login'))

    # Récupère l'utilisateur connecté
    utilisateur_id = session['utilisateur_id']
    utilisateur = Utilisateur.query.get(utilisateur_id)

    if not utilisateur or not utilisateur.hopital_id:
        flash("Accès refusé. Vous n'êtes pas lié à un hôpital.", "danger")
        return redirect(url_for('auth.login'))

    # Filtrer les déclarations pour l'hôpital lié à l'utilisateur
    declarations = DossierNaissance.query.filter_by(hopital_id=utilisateur.hopital_id).all()

    return render_template('hopital/dashboard.html', declarations=declarations)


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
    
@hopital_bp.route('/supprimer_declaration/<int:id>', methods=['POST'])
def supprimer_declaration(id):
    dossier = DossierNaissance.query.get_or_404(id)
    db.session.delete(dossier)
    db.session.commit()
    flash("Déclaration supprimée avec succès.", "success")
    return redirect(url_for('hopital.dashboard'))
