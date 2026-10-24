import os
import re
from datetime import datetime

from flask import (render_template, session, redirect, url_for, flash, Blueprint,
                request, abort, current_app, send_from_directory)
from flask_mail import Message
from markupsafe import escape

from app.models import (DossierNaissance, db, StatutDossier, ActeNaissance,
                        Utilisateur, RoleUtilisateur, MentionMarginale)
from app.services.acte_pdf import generer_pdf_acte, noms
from .. import mail
from ..config import Config

mairie_bp = Blueprint('mairie', __name__)


# ======================================================================
# Sécurité : seuls les agents de mairie rattachés à une mairie
# ======================================================================
@mairie_bp.before_request
def require_municipal_agent():
    user_id = session.get('utilisateur_id')
    if not isinstance(user_id, int):
        session.clear()
        flash("Veuillez vous connecter avec un compte de mairie.", "warning")
        return redirect(url_for('auth.login'))

    utilisateur = db.session.get(Utilisateur, user_id)
    if utilisateur is None:
        session.clear()
        flash("Votre session a expiré. Veuillez vous reconnecter.", "warning")
        return redirect(url_for('auth.login'))
    if utilisateur.role is not RoleUtilisateur.AGENT_MAIRIE:
        abort(403)
    if utilisateur.mairie_id is None:
        abort(403)

    session['role'] = utilisateur.role.value
    session['nom_utilisateur'] = utilisateur.nom_utilisateur
    session['hopital_id'] = utilisateur.hopital_id
    session['mairie_id'] = utilisateur.mairie_id


# ======================================================================
# Helpers
# ======================================================================
CHAMPS_TEXTE = [
    'nom_enfant', 'prenom_enfant', 'sexe_enfant', 'lieu_naissance',
    'nom_mere', 'prenom_mere', 'numero_mere', 'email_mere', 'lieu_naissance_mere',
    'nationalite_mere', 'profession_mere', 'type_piece_mere', 'numero_piece_mere',
    'nom_pere', 'prenom_pere', 'numero_pere', 'email_pere', 'lieu_naissance_pere',
    'nationalite_pere', 'profession_pere', 'type_piece_pere', 'numero_piece_pere',
    'nom_declarant', 'prenom_declarant', 'lien_parente_declarant',
    'type_piece_declarant', 'numero_piece_declarant',
    'numero_certificat_medical', 'nom_medecin',
]
CHAMPS_DATE_OPTIONNELS = ['date_naissance_mere', 'date_naissance_pere', 'date_certificat_medical']
CHAMPS_OBLIGATOIRES = ['nom_enfant', 'prenom_enfant', 'sexe_enfant', 'lieu_naissance',
                       'nom_mere', 'prenom_mere', 'date_naissance', 'heure_naissance']


def _f(nom):
    """Valeur de formulaire nettoyée ('' -> None)."""
    return (request.form.get(nom) or '').strip() or None


def _date(valeur):
    return datetime.strptime(valeur, '%Y-%m-%d').date() if valeur else None


def _heure(valeur):
    if not valeur:
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(valeur, fmt).time()
        except ValueError:
            continue
    raise ValueError("Heure invalide")


def _remplir_dossier(dossier):
    """Copie le formulaire dans le dossier (utilisé à l'ajout ET à la modification)."""
    for champ in CHAMPS_TEXTE:
        setattr(dossier, champ, _f(champ))
    for champ in CHAMPS_DATE_OPTIONNELS:
        setattr(dossier, champ, _date(_f(champ)))
    dossier.date_naissance = _date(_f('date_naissance'))
    dossier.heure_naissance = _heure(_f('heure_naissance'))


def _parse_statut(valeur):
    """Accepte 'Validé' (valeur) ou 'VALIDE' (nom) et renvoie le membre de l'enum."""
    if not valeur:
        return None
    try:
        return StatutDossier(valeur)
    except ValueError:
        return StatutDossier.__members__.get(valeur.upper())


def _supprimer_pdf(chemin_relatif):
    if not chemin_relatif:
        return
    chemin = os.path.join(current_app.root_path, 'static', chemin_relatif)
    try:
        if os.path.isfile(chemin):
            os.remove(chemin)
    except OSError:
        current_app.logger.warning("Impossible de supprimer %s", chemin)


def _email_valide(email):
    return bool(email and re.match(r"[^@]+@[^@]+\.[^@]+", email))


def _dossier_de_ma_mairie(id):
    return DossierNaissance.query.filter_by(
        id=id, mairie_id=session['mairie_id']
    ).first_or_404()


# ======================================================================
# Dashboard
# ======================================================================
@mairie_bp.route('/dashboard')
def dashboard():
    mairie_id = session.get('mairie_id')
    if not mairie_id:
        flash("Accès refusé : vous n'êtes pas connecté comme agent de mairie.", "danger")
        return redirect(url_for('auth.login'))

    declarations = DossierNaissance.query.filter_by(mairie_id=mairie_id).all()
    return render_template("mairie/dashboard.html", declarations=declarations,
                           StatutDossier=StatutDossier, current_date=datetime.utcnow())


# ======================================================================
# CRUD déclarations
# ======================================================================
@mairie_bp.route('/ajouter_declaration', methods=['POST'])
def ajouter_declaration():
    manquants = [c for c in CHAMPS_OBLIGATOIRES if not _f(c)]
    if manquants:
        flash("Veuillez remplir tous les champs obligatoires.", "danger")
        return redirect(url_for('mairie.dashboard'))

    try:
        dossier = DossierNaissance(
            hopital_id=None,
            mairie_id=session['mairie_id'],
            soumis_par_utilisateur_id=session['utilisateur_id'],
        )
        _remplir_dossier(dossier)
        db.session.add(dossier)
        db.session.commit()
        flash("Déclaration de naissance ajoutée avec succès ✅", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur ajouter_declaration")
        flash("Erreur lors de l'ajout de la déclaration. Veuillez vérifier les données.", "danger")
    return redirect(url_for('mairie.dashboard'))


@mairie_bp.route('/modifier_declaration/<int:dossier_id>', methods=['POST'])
def modifier_declaration(dossier_id):
    dossier = _dossier_de_ma_mairie(dossier_id)
    try:
        _remplir_dossier(dossier)
        db.session.commit()
        flash("✅ Déclaration mise à jour avec succès!", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur modifier_declaration")
        flash("❌ Erreur lors de la mise à jour. Vérifiez les données saisies.", "danger")
    return redirect(url_for('mairie.dashboard'))


@mairie_bp.route('/supprimer_declaration/<int:id>', methods=['POST'])
def supprimer_declaration(id):
    dossier = _dossier_de_ma_mairie(id)
    chemin_pdf = dossier.acte_naissance.chemin_pdf if dossier.acte_naissance else None
    try:
        db.session.delete(dossier)
        db.session.commit()
        _supprimer_pdf(chemin_pdf)
        flash("Déclaration supprimée avec succès.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur supprimer_declaration")
        flash("❌ Impossible de supprimer cette déclaration.", "danger")
    return redirect(url_for('mairie.dashboard'))


# ======================================================================
# Validation / rejet
# ======================================================================
def _envoyer_mail_rejet(dossier, motif_rejet):
    destinataires = []
    if _email_valide(dossier.email_mere):
        destinataires.append(dossier.email_mere)
    if dossier.hopital and _email_valide(getattr(dossier.hopital, 'email_contact', None)):
        destinataires.append(dossier.hopital.email_contact)
    if not destinataires:
        return False

    msg = Message(
        subject="🛑 Notification de rejet - Déclaration de naissance",
        sender=Config.MAIL_DEFAULT_SENDER,
        recipients=destinataires,
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #dc3545; margin: 0; font-size: 24px;">🛑 Déclaration de naissance rejetée</h2>
                </div>

                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #856404; margin: 0 0 15px 0; font-size: 18px;">📋 Informations de la déclaration</h3>
                    <p style="margin: 8px 0; color: #333;"><strong>Enfant :</strong> {escape(dossier.prenom_enfant)} {escape(dossier.nom_enfant)}</p>
                    <p style="margin: 8px 0; color: #333;"><strong>Date de naissance :</strong> {dossier.date_naissance.strftime('%d/%m/%Y')}</p>
                </div>

                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #721c24; margin: 0 0 15px 0; font-size: 18px;">❌ Motif du rejet</h3>
                    <p style="margin: 0; color: #721c24; font-weight: 500;">{escape(motif_rejet or '')}</p>
                </div>

                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #0c5460; margin: 0 0 15px 0; font-size: 18px;">📝 Prochaines étapes</h3>
                    <p style="margin: 8px 0; color: #0c5460;">• Veuillez corriger les informations selon le motif indiqué ci-dessus</p>
                    <p style="margin: 8px 0; color: #0c5460;">• Soumettez une nouvelle déclaration avec les corrections apportées</p>
                    <p style="margin: 8px 0; color: #0c5460;">• Contactez-nous si vous avez des questions concernant ce rejet</p>
                </div>

                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                    <p style="color: #6c757d; font-size: 14px; margin: 0;">Service d'État civil - Mairie</p>
                    <p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                </div>
            </div>
        </div>
        """
    )
    mail.send(msg)
    return True


@mairie_bp.route('/declaration/<int:id>/valider', methods=['POST'])
def valider_declaration(id):
    dossier = _dossier_de_ma_mairie(id)

    nouveau_statut = _parse_statut(request.form.get('statut'))
    motif_rejet = _f('motif_rejet')

    if nouveau_statut is None or nouveau_statut is StatutDossier.ACTE_DELIVRE:
        flash("❌ Veuillez choisir un statut valide.", "warning")
        return redirect(url_for('mairie.dashboard'))
    if nouveau_statut is StatutDossier.REJETE and not motif_rejet:
        flash("❌ Le motif du rejet est obligatoire.", "warning")
        return redirect(url_for('mairie.dashboard'))

    try:
        dossier.statut = nouveau_statut
        dossier.motif_rejet = motif_rejet if nouveau_statut is StatutDossier.REJETE else None
        dossier.valide_par_utilisateur_id = session['utilisateur_id']
        dossier.date_validation = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur valider_declaration")
        flash("❌ Erreur lors de la mise à jour du statut.", "danger")
        return redirect(url_for('mairie.dashboard'))

    flash("✅ Statut de la déclaration mis à jour avec succès !", "success")

    if nouveau_statut is StatutDossier.REJETE:
        try:
            if _envoyer_mail_rejet(dossier, motif_rejet):
                flash("📧 Notification de rejet envoyée aux destinataires.", "success")
            else:
                flash("⚠️ Aucun email trouvé pour notifier du rejet.", "warning")
        except Exception:
            current_app.logger.exception("Erreur envoi mail de rejet")
            flash("⚠️ Le statut est enregistré mais l'e-mail n'a pas pu être envoyé.", "warning")

    return redirect(url_for('mairie.dashboard'))


# ======================================================================
# Génération de l'acte (PDF identique au modèle officiel)
# ======================================================================
def _envoyer_mail_acte(dossier, date_etablissement):
    destinataires = [e for e in (dossier.email_mere, dossier.email_pere) if _email_valide(e)]
    if not destinataires:
        return
    msg = Message(
        subject="📄 Acte de naissance disponible",
        sender=Config.MAIL_DEFAULT_SENDER,
        recipients=destinataires,
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #28a745; margin: 0; font-size: 24px;">✅ Acte de naissance prêt !</h2>
                    <p style="color: #555;">📍 Mairie de {escape(dossier.mairie.nom)}</p>
                </div>

                <div style="background-color: #e2f7e1; border: 1px solid #c3e6cb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #155724; margin: 0 0 15px 0; font-size: 18px;">👶 Informations de l’enfant</h3>
                    <p style="margin: 8px 0; color: #333;"><strong>Nom :</strong> {escape(dossier.nom_enfant.upper())} {escape(dossier.prenom_enfant.title())}</p>
                    <p style="margin: 8px 0; color: #333;"><strong>Date de naissance :</strong> {dossier.date_naissance.strftime('%d/%m/%Y')}</p>
                </div>

                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #0c5460; margin: 0 0 15px 0; font-size: 18px;">📬 Instructions de retrait</h3>
                    <p style="margin: 8px 0; color: #0c5460;">• Présentez-vous à la mairie munis de vos pièces d’identité</p>
                    <p style="margin: 8px 0; color: #0c5460;">• Demandez à retirer l’acte de naissance de votre enfant</p>
                    <p style="margin: 8px 0; color: #0c5460;">• Disponible à partir du <strong>{date_etablissement.strftime('%d/%m/%Y')}</strong></p>
                </div>

                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                    <p style="color: #6c757d; font-size: 14px; margin: 0;">Service d'État civil - Mairie</p>
                    <p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">Cet email est généré automatiquement. Merci de ne pas y répondre.</p>
                </div>
            </div>
        </div>
        """
    )
    mail.send(msg)


@mairie_bp.route('/declaration/<int:id>/generer-acte', methods=['POST'])
def generer_acte(id):
    dossier = _dossier_de_ma_mairie(id)

    if dossier.statut not in (StatutDossier.VALIDE, StatutDossier.ACTE_DELIVRE):
        flash("❌ Le dossier doit être validé avant de générer l'acte.", "danger")
        return redirect(url_for('mairie.dashboard'))

    numero_acte = _f('numero_acte')
    if not numero_acte:
        flash("❌ Le numéro d'acte est requis.", "danger")
        return redirect(url_for('mairie.dashboard'))

    try:
        # 1 dossier = 1 acte : on cherche par dossier, pas par numéro
        acte = ActeNaissance.query.filter_by(dossier_naissance_id=dossier.id).first()

        doublon = ActeNaissance.query.filter(
            ActeNaissance.numero_acte == numero_acte,
            ActeNaissance.dossier_naissance_id != dossier.id
        ).first()
        if doublon:
            flash("❌ Ce numéro d'acte existe déjà.", "danger")
            return redirect(url_for('mairie.dashboard'))

        aujourdhui = datetime.utcnow()
        ancien_pdf = acte.chemin_pdf if acte else None

        valeurs = {
            "numero_acte": numero_acte,
            "date_enregistrement": aujourdhui,
            "lieu_enregistrement": dossier.lieu_naissance,

            "nom_complet_enfant": noms(dossier.nom_enfant, dossier.prenom_enfant),
            "sexe_enfant": dossier.sexe_enfant,
            "date_naissance_enfant": dossier.date_naissance,
            "heure_naissance_enfant": dossier.heure_naissance,
            "lieu_naissance_enfant": dossier.lieu_naissance,

            "nom_complet_mere": noms(dossier.nom_mere, dossier.prenom_mere),
            "nationalite_mere": dossier.nationalite_mere,
            "lieu_naissance_mere": dossier.lieu_naissance_mere,
            "profession_mere": dossier.profession_mere,
            "domicile_mere": _f('domicile_mere'),

            "nom_complet_pere": noms(dossier.nom_pere, dossier.prenom_pere) or None,
            "nationalite_pere": dossier.nationalite_pere,
            "lieu_naissance_pere": dossier.lieu_naissance_pere,
            "profession_pere": dossier.profession_pere,
            "domicile_pere": _f('domicile_pere'),

            "nom_complet_declarant": noms(dossier.nom_declarant, dossier.prenom_declarant) or None,
            "lien_parente_declarant": dossier.lien_parente_declarant,
            "qualite_declarant": _f('qualite_declarant') or dossier.lien_parente_declarant,

            "date_declaration": _date(_f('date_declaration')) or dossier.date_soumission.date(),
            "date_attestation": _date(_f('date_attestation')) or aujourdhui.date(),
            "dresse_le": _date(_f('dresse_le')) or aujourdhui.date(),
            "officier_nom": _f('officier_nom'),
            "secretaire_nom": _f('secretaire_nom'),
            "nipu": _f('nipu'),

            "genere_par_utilisateur_id": session['utilisateur_id'],
            "genere_le": aujourdhui,
            "est_actif": True,
        }

        if acte:
            for cle, val in valeurs.items():
                setattr(acte, cle, val)
            action = "mis à jour"
        else:
            acte = ActeNaissance(dossier_naissance_id=dossier.id,
                                 mairie_id=dossier.mairie_id, **valeurs)
            db.session.add(acte)
            action = "créé"
        db.session.flush()  # obtient acte.id avant la génération du PDF

        try:
            acte.chemin_pdf = generer_pdf_acte(dossier, acte)
        except Exception:
            current_app.logger.exception("Erreur génération PDF")
            db.session.commit()  # l'acte reste enregistré
            flash("⚠️ Acte enregistré mais le PDF n'a pas pu être généré.", "warning")
            return redirect(url_for('mairie.dashboard'))

        dossier.statut = StatutDossier.ACTE_DELIVRE
        db.session.commit()
        if ancien_pdf and ancien_pdf != acte.chemin_pdf:
            _supprimer_pdf(ancien_pdf)

        try:
            _envoyer_mail_acte(dossier, aujourdhui.date())
        except Exception:
            current_app.logger.exception("Erreur envoi mail acte")

        flash(f"✅ Acte {action} avec succès. Vous pouvez maintenant le télécharger.", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur generer_acte")
        flash("❌ Une erreur est survenue lors de la génération de l'acte.", "danger")

    return redirect(url_for('mairie.dashboard'))


@mairie_bp.route('/acte/<int:id>/telecharger')
def telecharger_acte(id):
    acte = ActeNaissance.query.filter_by(id=id, mairie_id=session['mairie_id']).first_or_404()
    if not acte.chemin_pdf:
        abort(404)
    ouvrir_dans_navigateur = request.args.get('inline') == '1'
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        acte.chemin_pdf,
        as_attachment=not ouvrir_dans_navigateur,
        download_name=f"acte_{acte.numero_acte.replace('/', '-')}.pdf",
    )


# ======================================================================
# Mentions marginales (page 2 du PDF)
# ======================================================================
@mairie_bp.route('/acte/<int:id>/mention', methods=['POST'])
def ajouter_mention(id):
    acte = ActeNaissance.query.filter_by(id=id, mairie_id=session['mairie_id']).first_or_404()

    type_mention = _f('type_mention')
    texte = _f('texte')
    if not type_mention or not texte:
        flash("❌ Le type et le texte de la mention sont requis.", "danger")
        return redirect(url_for('mairie.dashboard'))

    try:
        mention = MentionMarginale(
            acte_id=acte.id,
            type_mention=type_mention,
            numero=_f('numero'),
            date_mention=_date(_f('date_mention')) or datetime.utcnow().date(),
            texte=texte,
            officier_nom=_f('officier_nom') or acte.officier_nom,
            base_legale=_f('base_legale'),
        )
        db.session.add(mention)
        db.session.flush()
        db.session.expire(acte, ['mentions_marginales'])

        ancien_pdf = acte.chemin_pdf
        acte.chemin_pdf = generer_pdf_acte(acte.dossier_naissance, acte)
        db.session.commit()
        if ancien_pdf and ancien_pdf != acte.chemin_pdf:
            _supprimer_pdf(ancien_pdf)
        flash("✅ Mention marginale ajoutée et PDF régénéré.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur ajouter_mention")
        flash("❌ Impossible d'ajouter la mention marginale.", "danger")

    return redirect(url_for('mairie.dashboard'))