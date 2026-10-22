"""Journalisation des actions importantes dans la table JournalAudit."""
from flask import current_app, request, session

from app.models import JournalAudit, db


def journaliser(action, type_enregistrement=None, identifiant=None, commit=False):
    """Ajoute une ligne au journal d'audit.

    Par défaut, la ligne est ajoutée à la session et sera enregistrée avec le
    prochain db.session.commit() de la route appelante (même transaction).
    Passer commit=True pour l'enregistrer immédiatement.
    """
    try:
        entree = JournalAudit(
            utilisateur_id=session.get('utilisateur_id'),
            action=(action or '')[:255],
            adresse_ip=(request.remote_addr or None),
            identifiant_enregistrement=identifiant,
            type_enregistrement=type_enregistrement,
        )
        db.session.add(entree)
        if commit:
            db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Impossible d'écrire dans le journal d'audit")