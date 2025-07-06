from flask import render_template, session, redirect, url_for, flash , Blueprint ,request
from app.models import DossierNaissance  , db ,StatutDossier ,ActeNaissance
from datetime import datetime , time
from flask_mail import Message
from .. import mail 
from ..config import Config,os
import pdfkit
import re

mairie_bp = Blueprint('mairie', __name__)

@mairie_bp.route('/dashboard')
def dashboard():
    mairie_id = session.get('mairie_id')
    if not mairie_id:
        flash("Accès refusé : vous n'êtes pas connecté comme agent de mairie.", "danger")
        return redirect(url_for('auth.login'))

    # Récupération des déclarations avec jointure pour vérification
    declarations = DossierNaissance.query.filter_by(mairie_id=mairie_id).all()

    return render_template("mairie/dashboard.html",declarations=declarations,StatutDossier=StatutDossier,current_date=datetime.utcnow() )

@mairie_bp.route('/ajouter_declaration', methods=['POST'])
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
        return redirect(url_for('mairie.dashboard'))

    except Exception as e:
        print(e)
        flash("Erreur lors de l'ajout de la déclaration. Veuillez vérifier les données.", "danger")
        return redirect(url_for('mairie.dashboard'))
    
@mairie_bp.route('/modifier_declaration/<int:dossier_id>', methods=['POST'])
def modifier_declaration(dossier_id):
    dossier = DossierNaissance.query.get_or_404(dossier_id)
    
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
    
    return redirect(url_for('mairie.dashboard'))

    
@mairie_bp.route('/supprimer_declaration/<int:id>', methods=['POST'])
def supprimer_declaration(id):
    dossier = DossierNaissance.query.get_or_404(id)
    db.session.delete(dossier)
    db.session.commit()
    flash("Déclaration supprimée avec succès.", "success")
    return redirect(url_for('mairie.dashboard'))

@mairie_bp.route('/declaration/<int:id>/valider', methods=['POST'])
def valider_declaration(id):
    dossier = DossierNaissance.query.get_or_404(id)

    try:
        statut = request.form.get('statut')
        motif_rejet = request.form.get('motif_rejet')

        if not statut:
            flash("❌ Veuillez choisir un statut.", "warning")
            return redirect(url_for('mairie.dashboard'))

        dossier.statut = statut
        dossier.motif_rejet = motif_rejet if statut == "Rejeté" else None

        db.session.commit()
        flash("✅ Statut de la déclaration mis à jour avec succès !", "success")

        # ✅ Envoi de mail si rejeté
        if statut == "Rejeté":
            destinataires = []

            # Ajoute l'email de la mère s'il est présent
            if dossier.email_mere:
                destinataires.append(dossier.email_mere)

            # Ajoute l'email de l'hôpital s'il existe et est lié
            if dossier.hopital and getattr(dossier.hopital, 'email_contact', None):
                destinataires.append(dossier.hopital.email_contact)

            # Si on a des destinataires, on envoie le mail
            if destinataires:
                msg = Message(
                    subject="🛑 Notification de rejet - Déclaration de naissance",
                    sender=Config.MAIL_DEFAULT_SENDER,
                    recipients=destinataires,
                    html=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                            <div style="text-align: center; margin-bottom: 30px;">
                                <h2 style="color: #dc3545; margin: 0; font-size: 24px;">
                                    🛑 Déclaration de naissance rejetée
                                </h2>
                            </div>
                            
                            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 20px; margin: 20px 0;">
                                <h3 style="color: #856404; margin: 0 0 15px 0; font-size: 18px;">
                                    📋 Informations de la déclaration
                                </h3>
                                <p style="margin: 8px 0; color: #333;">
                                    <strong>Enfant :</strong> {dossier.prenom_enfant} {dossier.nom_enfant}
                                </p>
                                <p style="margin: 8px 0; color: #333;">
                                    <strong>Date de naissance :</strong> {dossier.date_naissance.strftime('%d/%m/%Y')}
                                </p>
                            </div>
                            
                            <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                                <h3 style="color: #721c24; margin: 0 0 15px 0; font-size: 18px;">
                                    ❌ Motif du rejet
                                </h3>
                                <p style="margin: 0; color: #721c24; font-weight: 500;">
                                    {motif_rejet}
                                </p>
                            </div>
                            
                            <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                                <h3 style="color: #0c5460; margin: 0 0 15px 0; font-size: 18px;">
                                    📝 Prochaines étapes
                                </h3>
                                <p style="margin: 8px 0; color: #0c5460;">
                                    • Veuillez corriger les informations selon le motif indiqué ci-dessus
                                </p>
                                <p style="margin: 8px 0; color: #0c5460;">
                                    • Soumettez une nouvelle déclaration avec les corrections apportées
                                </p>
                                <p style="margin: 8px 0; color: #0c5460;">
                                    • Contactez-nous si vous avez des questions concernant ce rejet
                                </p>
                            </div>
                            
                            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                                <p style="color: #6c757d; font-size: 14px; margin: 0;">
                                    Service d'État civil - Mairie
                                </p>
                                <p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">
                                    Cet email a été envoyé automatiquement, merci de ne pas y répondre.
                                </p>
                            </div>
                        </div>
                    </div>
                    """
                )
                mail.send(msg)
                flash("✅ Statut de la déclaration mis à jour avec succès et Notification de rejet envoyée aux destinataires.", "success")
            else:
                flash("⚠️ Aucun email trouvé pour notifier du rejet.", "warning")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur lors de la mise à jour : {str(e)}", "danger")

    return redirect(url_for('mairie.dashboard'))

@mairie_bp.route('/declaration/<int:id>/generer-acte', methods=['POST'])
def generer_acte(id):
    dossier = DossierNaissance.query.get_or_404(id)

    # Vérifier que le dossier est validé
    if dossier.statut != StatutDossier.VALIDE:
        flash("❌ Le dossier doit être validé avant de générer l'acte.", "danger")
        return redirect(url_for('mairie.dashboard'))

    try:
        numero_acte = request.form.get('numero_acte')
        if not numero_acte:
            flash("❌ Le numéro d'acte est requis.", "danger")
            return redirect(url_for('mairie.dashboard'))

        date_etablissement = datetime.now().date()
        acte_existant = ActeNaissance.query.filter_by(
            numero_acte=numero_acte,
            mairie_id=dossier.mairie_id
        ).first()

        infos_acte = {
            "numero_acte": numero_acte,
            "date_enregistrement": date_etablissement,
            "lieu_enregistrement": dossier.lieu_naissance,
            "nom_complet_enfant": f"{dossier.nom_enfant} {dossier.prenom_enfant}",
            "sexe_enfant": dossier.sexe_enfant,
            "date_naissance_enfant": dossier.date_naissance,
            "heure_naissance_enfant": dossier.heure_naissance,
            "lieu_naissance_enfant": dossier.lieu_naissance,
            "nom_complet_mere": f"{dossier.nom_mere} {dossier.prenom_mere}",
            "nationalite_mere": dossier.nationalite_mere,
            "nom_complet_pere": f"{dossier.nom_pere} {dossier.prenom_pere}",
            "nationalite_pere": dossier.nationalite_pere,
            "nom_complet_declarant": f"{dossier.nom_declarant} {dossier.prenom_declarant}",
            "lien_parente_declarant": dossier.lien_parente_declarant,
            "dossier_naissance_id": dossier.id,
            "genere_par_utilisateur_id": session['utilisateur_id'],
            "genere_le": datetime.now(),
            "est_actif": True
        }

        if acte_existant:
            for key, value in infos_acte.items():
                setattr(acte_existant, key, value)
            acte = acte_existant
            action = "mis à jour"
            print(f"✅ Acte existant mis à jour - ID: {acte.id}")
        else:
            acte = ActeNaissance(**infos_acte, mairie_id=dossier.mairie_id)
            db.session.add(acte)
            action = "créé"
            print(f"✅ Nouvel acte créé - Numéro: {numero_acte}")

        db.session.commit()
        print(f"✅ Acte {action} avec succès - ID: {acte.id}")

        # Envoi d'email aux parents
        def is_valid_email(email):
            return email and re.match(r"[^@]+@[^@]+\.[^@]+", email)

        destinataires = []
        if is_valid_email(dossier.email_mere):
            destinataires.append(dossier.email_mere)
        if is_valid_email(dossier.email_pere):
            destinataires.append(dossier.email_pere)

        if destinataires:
            try:
                msg = Message(
                subject="📄 Acte de naissance disponible",
                sender=Config.MAIL_DEFAULT_SENDER,
                recipients=destinataires,
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h2 style="color: #28a745; margin: 0; font-size: 24px;">
                                ✅ Acte de naissance prêt !
                            </h2>
                            <p style="color: #555;">📍 Mairie de {dossier.mairie.nom}</p>
                        </div>

                        <div style="background-color: #e2f7e1; border: 1px solid #c3e6cb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                            <h3 style="color: #155724; margin: 0 0 15px 0; font-size: 18px;">
                                👶 Informations de l’enfant
                            </h3>
                            <p style="margin: 8px 0; color: #333;"><strong>Nom :</strong> {dossier.nom_enfant.upper()} {dossier.prenom_enfant.title()}</p>
                            <p style="margin: 8px 0; color: #333;"><strong>Date de naissance :</strong> {dossier.date_naissance.strftime('%d/%m/%Y')}</p>
                        </div>

                        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                            <h3 style="color: #0c5460; margin: 0 0 15px 0; font-size: 18px;">
                                📬 Instructions de retrait
                            </h3>
                            <p style="margin: 8px 0; color: #0c5460;">• Présentez-vous à la mairie munis de vos pièces d’identité</p>
                            <p style="margin: 8px 0; color: #0c5460;">• Demandez à retirer l’acte de naissance de votre enfant</p>
                            <p style="margin: 8px 0; color: #0c5460;">• Disponible à partir du <strong>{date_etablissement.strftime('%d/%m/%Y')}</strong></p>
                        </div>

                        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                            <p style="color: #6c757d; font-size: 14px; margin: 0;">
                                Service d'État civil - Mairie
                            </p>
                            <p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">
                                Cet email est généré automatiquement. Merci de ne pas y répondre.
                            </p>
                        </div>
                    </div>
                </div>
                """
            )
                mail.send(msg)
                print(f"✅ Email envoyé avec succès à {', '.join(destinataires)}")
            except Exception as email_error:
                print(f"⚠️ Erreur lors de l'envoi de l'email : {str(email_error)}")

        # Génération PDF
        try:
            html = render_template('mairie/documents/acte_naissance.html', dossier=dossier, acte=acte)
            filename = f"acte_{acte.id}_{int(datetime.now().timestamp())}.pdf"
            pdf_path = os.path.join('static', 'pdfs', filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

            pdfkit.from_string(html, pdf_path, options={
                'encoding': 'UTF-8',
                'quiet': '',
                'page-size': 'A4',
                'margin-top': '10mm',
                'margin-right': '10mm',
                'margin-bottom': '10mm',
                'margin-left': '10mm',
                'enable-local-file-access': ''
            })

            acte.chemin_pdf = pdf_path
            db.session.commit()
            print(f"✅ PDF généré avec succès : {pdf_path}")

        except Exception as pdf_error:
            print(f"⚠️ Erreur génération PDF : {str(pdf_error)}")
            flash("⚠️ Acte généré mais erreur PDF", "warning")

        flash(f"✅ Acte {action} avec succès. Cliquez ici pour le télécharger.", "success")
        return redirect(url_for('mairie.dashboard'))

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur générale : {str(e)}")
        flash(f"❌ Une erreur est survenue : {str(e)}", "danger")
        return redirect(url_for('mairie.dashboard'))
