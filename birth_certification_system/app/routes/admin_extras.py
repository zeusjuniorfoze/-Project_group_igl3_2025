"""Fonctionnalités supplémentaires de l'espace administrateur.

Ce module AJOUTE des routes au blueprint `admin_bp` existant sans toucher à
tes routes actuelles (ajouter/modifier/supprimer hôpital, mairie, utilisateur).

Branchement (tout en bas de routes/admin.py) :

    from . import admin_extras  # noqa: E402,F401

Et dans ta route du tableau de bord admin, remplace l'appel à render_template par :

    from .admin_extras import contexte_admin
    return render_template('admin/dashboard.html', **contexte_admin())
"""
import csv
import io
import os
import platform
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

import flask
from flask import (Response, abort, current_app, flash, redirect, request,
                   send_from_directory, session, url_for)
from sqlalchemy import func

from app.models import (ActeNaissance, DossierNaissance, Hopital, JournalAudit,
                        Mairie, RoleUtilisateur, StatutDossier, Utilisateur, db)
from app.services.audit import journaliser
from app.services.acte_pdf import resolve_wkhtmltopdf_path
from .admin import admin_bp

MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
            "juil.", "août", "sept.", "oct.", "nov.", "déc."]


# ======================================================================
# Sécurité : réservé aux administrateurs (indépendant du reste de admin.py)
# ======================================================================
def admin_requis(vue):
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        uid = session.get('utilisateur_id')
        utilisateur = db.session.get(Utilisateur, uid) if isinstance(uid, int) else None
        if utilisateur is None:
            session.clear()
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for('auth.login'))
        if utilisateur.role is not RoleUtilisateur.ADMIN:
            abort(403)
        return vue(*args, **kwargs)
    return enveloppe


def _retour(ancre=''):
    """Redirige vers la page d'origine (même site uniquement)."""
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref.split('#')[0] + ancre)
    for endpoint in ('admin.dashboard', 'admin.index'):
        try:
            return redirect(url_for(endpoint) + ancre)
        except Exception:
            continue
    return redirect('/')


# ======================================================================
# Contexte du tableau de bord
# ======================================================================
def _derniers_mois(n=12):
    """Liste des (annee, mois) des n derniers mois, du plus ancien au plus récent."""
    aujourd = datetime.utcnow()
    annee, mois = aujourd.year, aujourd.month
    resultat = []
    for _ in range(n):
        resultat.append((annee, mois))
        mois -= 1
        if mois == 0:
            mois, annee = 12, annee - 1
    return list(reversed(resultat))


def _etat_systeme():
    try:
        chemin_wk = resolve_wkhtmltopdf_path()
    except FileNotFoundError:
        chemin_wk = current_app.config.get('WKHTMLTOPDF_PATH') or 'introuvable'
    wk_ok = os.path.isfile(chemin_wk)

    dossier_img = os.path.join(current_app.root_path, 'static', 'img')
    images = {nom: os.path.exists(os.path.join(dossier_img, nom))
              for nom in ('armoiries.png', 'cachet.png', 'signature_secretaire.png', 'filigrane.png')}

    dossier_pdf = os.path.join(current_app.root_path, 'static', 'pdfs')
    nb_pdfs = len([f for f in os.listdir(dossier_pdf) if f.endswith('.pdf')]) if os.path.isdir(dossier_pdf) else 0

    return {
        'wkhtmltopdf_ok': wk_ok,
        'wkhtmltopdf_chemin': chemin_wk or 'introuvable',
        'images': images,
        'nb_pdfs': nb_pdfs,
        'mail_ok': bool(current_app.config.get('MAIL_SERVER')),
        'db_dialect': db.engine.dialect.name,
        'python': platform.python_version(),
        'flask': getattr(flask, '__version__', ''),
    }


def contexte_admin():
    """Toutes les variables utilisées par admin/dashboard.html."""
    maintenant = datetime.utcnow()

    hopitaux = Hopital.query.order_by(Hopital.nom).all()
    mairies = Mairie.query.order_by(Mairie.nom).all()
    utilisateurs = Utilisateur.query.order_by(Utilisateur.nom_utilisateur).all()
    actes = ActeNaissance.query.order_by(ActeNaissance.genere_le.desc()).all()

    # --- Statuts des dossiers ---
    comptes = dict(db.session.query(DossierNaissance.statut, func.count(DossierNaissance.id))
                   .group_by(DossierNaissance.statut).all())
    stats = {
        'en_attente': comptes.get(StatutDossier.EN_ATTENTE, 0),
        'valide': comptes.get(StatutDossier.VALIDE, 0),
        'rejete': comptes.get(StatutDossier.REJETE, 0),
        'acte_delivre': comptes.get(StatutDossier.ACTE_DELIVRE, 0),
    }
    stats['total'] = sum(stats.values())

    # --- Actes par mois (12 derniers mois) ---
    mois = _derniers_mois(12)
    par_mois = {m: 0 for m in mois}
    for acte in actes:
        if acte.genere_le and (acte.genere_le.year, acte.genere_le.month) in par_mois:
            par_mois[(acte.genere_le.year, acte.genere_le.month)] += 1
    actes_months = [f"{MOIS_COURTS[m - 1]} {a}" for a, m in mois]
    actes_data = [par_mois[m] for m in mois]

    # --- Rôles ---
    roles_labels = ['Administrateurs', 'Agents mairie', 'Agents hôpital']
    roles_data = [
        sum(1 for u in utilisateurs if u.role is RoleUtilisateur.ADMIN),
        sum(1 for u in utilisateurs if u.role is RoleUtilisateur.AGENT_MAIRIE),
        sum(1 for u in utilisateurs if u.role is RoleUtilisateur.AGENT_HOPITAL),
    ]

    # --- Journal ---
    logs = JournalAudit.query.order_by(JournalAudit.horodatage.desc()).limit(300).all()
    types_journal = sorted({l.type_enregistrement for l in logs if l.type_enregistrement})

    # --- Points d'attention ---
    alertes = []
    for m in mairies:
        if not m.departement or not m.arrondissement:
            alertes.append({'niveau': 'warning',
                            'texte': f"Mairie « {m.nom} » : en-tête de l'acte incomplet (département / arrondissement).",
                            'lien': '#page3'})
        if not m.utilisateurs:
            alertes.append({'niveau': 'info', 'texte': f"Mairie « {m.nom} » : aucun agent rattaché.", 'lien': '#page2'})
    for h in hopitaux:
        if not h.utilisateurs:
            alertes.append({'niveau': 'info', 'texte': f"Hôpital « {h.nom} » : aucun agent rattaché.", 'lien': '#page2'})

    limite = maintenant - timedelta(days=7)
    anciens = DossierNaissance.query.filter(
        DossierNaissance.statut == StatutDossier.EN_ATTENTE,
        DossierNaissance.date_soumission < limite).count()
    if anciens:
        alertes.append({'niveau': 'danger',
                        'texte': f"{anciens} dossier(s) en attente depuis plus de 7 jours.", 'lien': '#home'})

    systeme = _etat_systeme()
    if not systeme['wkhtmltopdf_ok']:
        alertes.append({'niveau': 'danger',
                        'texte': "wkhtmltopdf est introuvable : les PDF des actes ne pourront pas être générés.",
                        'lien': '#page6'})

    return {
        'now': maintenant,
        'hopitaux': hopitaux,
        'mairies': mairies,
        'utilisateurs': utilisateurs,
        'actes': actes,
        'actes_count': len(actes),
        'stats': stats,
        'actes_months': actes_months,
        'actes_data': actes_data,
        'roles_labels': roles_labels,
        'roles_data': roles_data,
        'statuts_labels': ['En attente', 'Validé', 'Rejeté', 'Acte délivré'],
        'statuts_data': [stats['en_attente'], stats['valide'], stats['rejete'], stats['acte_delivre']],
        'recent_logs': logs[:10],
        'logs': logs,
        'types_journal': types_journal,
        'alertes': alertes,
        'systeme': systeme,
    }


# ======================================================================
# Actes : téléchargement, annulation / réactivation
# ======================================================================
@admin_bp.route('/actes/<int:acte_id>/telecharger')
@admin_requis
def telecharger_acte_admin(acte_id):
    acte = db.session.get(ActeNaissance, acte_id) or abort(404)
    if not acte.chemin_pdf:
        abort(404)
    journaliser(f"Téléchargement de l'acte {acte.numero_acte}", 'ActeNaissance', acte.id, commit=True)
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        acte.chemin_pdf,
        as_attachment=request.args.get('inline') != '1',
        download_name=f"acte_{acte.numero_acte.replace('/', '-')}.pdf",
    )


@admin_bp.route('/actes/<int:acte_id>/basculer', methods=['POST'])
@admin_requis
def basculer_acte_admin(acte_id):
    """Annule (est_actif = False) ou réactive un acte. Rien n'est supprimé."""
    acte = db.session.get(ActeNaissance, acte_id) or abort(404)
    try:
        acte.est_actif = not bool(acte.est_actif)
        journaliser(f"Acte {acte.numero_acte} {'réactivé' if acte.est_actif else 'annulé'}",
                    'ActeNaissance', acte.id)
        db.session.commit()
        flash(f"Acte {acte.numero_acte} {'réactivé' if acte.est_actif else 'annulé'}.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur basculer_acte_admin")
        flash("❌ Impossible de modifier l'état de l'acte.", "danger")
    return _retour('#page4')


# ======================================================================
# Mairies : en-tête officiel des actes
# ======================================================================
@admin_bp.route('/mairies/<int:mairie_id>/entete', methods=['POST'])
@admin_requis
def definir_entete_mairie(mairie_id):
    mairie = db.session.get(Mairie, mairie_id) or abort(404)

    def champ(nom):
        return (request.form.get(nom) or '').strip()[:50] or None

    try:
        mairie.departement = champ('departement')
        mairie.arrondissement = champ('arrondissement')
        mairie.region_en = champ('region_en')
        journaliser(f"En-tête d'acte mis à jour : {mairie.nom}", 'Mairie', mairie.id)
        db.session.commit()
        flash("✅ En-tête des actes enregistré.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erreur definir_entete_mairie")
        flash("❌ Impossible d'enregistrer l'en-tête.", "danger")
    return _retour('#page3')


# ======================================================================
# Exports CSV (ouverts directement par Excel : séparateur « ; » + BOM UTF-8)
# ======================================================================
def _cellule(valeur):
    texte = '' if valeur is None else str(valeur)
    # Protection contre l'injection de formules dans Excel
    if texte and texte[0] in ('=', '+', '-', '@', '\t', '\r'):
        texte = "'" + texte
    return texte


def _reponse_csv(nom_fichier, entetes, lignes):
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=';')
    ecrivain.writerow(entetes)
    for ligne in lignes:
        ecrivain.writerow([_cellule(c) for c in ligne])
    return Response(
        '\ufeff' + tampon.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={nom_fichier}'},
    )


@admin_bp.route('/export/actes.csv')
@admin_requis
def export_actes_csv():
    actes = ActeNaissance.query.order_by(ActeNaissance.genere_le.desc()).all()
    journaliser("Export CSV des actes", 'ActeNaissance', None, commit=True)
    return _reponse_csv(
        'actes_naissance.csv',
        ['N° acte', 'Enfant', 'Né(e) le', 'Mairie', 'Établi le', 'Statut', 'Mentions marginales'],
        [[a.numero_acte, a.nom_complet_enfant,
          a.date_naissance_enfant.strftime('%d/%m/%Y') if a.date_naissance_enfant else '',
          a.mairie.nom if a.mairie else '',
          (a.dresse_le or a.date_enregistrement).strftime('%d/%m/%Y') if (a.dresse_le or a.date_enregistrement) else '',
          'Actif' if a.est_actif else 'Annulé',
          len(a.mentions_marginales)] for a in actes],
    )


@admin_bp.route('/export/journal.csv')
@admin_requis
def export_journal_csv():
    logs = JournalAudit.query.order_by(JournalAudit.horodatage.desc()).limit(5000).all()
    return _reponse_csv(
        'journal_audit.csv',
        ['Date', 'Utilisateur', 'Action', 'Type', 'ID enregistrement', 'Adresse IP'],
        [[l.horodatage.strftime('%d/%m/%Y %H:%M:%S'),
          l.utilisateur.nom_utilisateur if l.utilisateur else 'Système',
          l.action, l.type_enregistrement or '', l.identifiant_enregistrement or '',
          l.adresse_ip or ''] for l in logs],
    )


@admin_bp.route('/export/utilisateurs.csv')
@admin_requis
def export_utilisateurs_csv():
    """Export sans aucun mot de passe ni code de réinitialisation."""
    utilisateurs = Utilisateur.query.order_by(Utilisateur.nom_utilisateur).all()
    journaliser("Export CSV des utilisateurs", 'Utilisateur', None, commit=True)
    return _reponse_csv(
        'utilisateurs.csv',
        ['Nom', 'Email', 'Rôle', 'Hôpital', 'Mairie', 'Créé le'],
        [[u.nom_utilisateur, u.email, u.role.value,
          u.hopital.nom if u.hopital else '', u.mairie.nom if u.mairie else '',
          u.cree_le.strftime('%d/%m/%Y') if u.cree_le else ''] for u in utilisateurs],
    )