"""Construction du contexte et génération du PDF d'un acte de naissance.

Dépendances : pip install pdfkit num2words qrcode[pil]
(+ le binaire wkhtmltopdf installé sur le serveur)
"""
import base64
import io
import os
from datetime import datetime

import pdfkit
import qrcode
from flask import current_app, render_template, url_for
from num2words import num2words


MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


# ---------- Helpers de formatage ----------
def noms(*parties):
    """Assemble nom + prénoms en ignorant les valeurs vides (évite « None None »)."""
    return " ".join(p.strip() for p in parties if p and str(p).strip())


def date_fr(d):
    """03 novembre 2001"""
    if not d:
        return ""
    return f"{d.day:02d} {MOIS[d.month - 1]} {d.year}"


def date_lettres(d):
    """Onze mai deux mille vingt-cinq"""
    if not d:
        return ""
    jour = "premier" if d.day == 1 else num2words(d.day, lang="fr")
    annee = num2words(d.year, lang="fr")
    return f"{jour} {MOIS[d.month - 1]} {annee}".capitalize()


def libelle_sexe(valeur):
    v = (valeur or "").strip().upper()
    if v.startswith("M"):
        return "Masculin"
    if v.startswith("F"):
        return "Féminin"
    return valeur or ""


def piece(type_piece, numero):
    if not numero:
        return ""
    return f"{type_piece or 'Pièce'} N°{numero}"


# ---------- Images / QR en base64 (fiable avec wkhtmltopdf) ----------
def img_b64(nom_fichier):
    """Lit app/static/img/<nom_fichier> et renvoie un data URI, ou None si absent."""
    chemin = os.path.join(current_app.root_path, "static", "img", nom_fichier)
    if not os.path.exists(chemin):
        return None
    ext = os.path.splitext(chemin)[1].lstrip(".").lower().replace("jpg", "jpeg")
    with open(chemin, "rb") as f:
        return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"


def qr_b64(contenu):
    img = qrcode.make(contenu, box_size=6, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- Contexte du template ----------
def construire_contexte(dossier, acte, mentions=None):
    mairie = dossier.mairie
    url_verif = url_for("main.verifier_acte", numero=acte.numero_acte, _external=True) \
        if "main.verifier_acte" in current_app.view_functions else acte.numero_acte

    return {
        "mairie_nom": mairie.nom,
        "region": mairie.region,
        "region_en": getattr(mairie, "region_en", None) or mairie.region,
        "departement": getattr(mairie, "departement", None) or "",
        "arrondissement": getattr(mairie, "arrondissement", None) or mairie.nom,
        "numero_acte": acte.numero_acte,

        "nom_enfant": (dossier.nom_enfant or "").upper(),
        "prenoms_enfant": (dossier.prenom_enfant or "").upper(),
        "date_naissance_lettres": date_lettres(dossier.date_naissance),
        "lieu_naissance": dossier.lieu_naissance,
        "sexe": libelle_sexe(dossier.sexe_enfant),

        "pere": {
            "nom": noms(dossier.nom_pere, dossier.prenom_pere).upper(),
            "lieu_naissance": dossier.lieu_naissance_pere,
            "date_naissance": date_fr(dossier.date_naissance_pere),
            "domicile": acte.domicile_pere,
            "nationalite": dossier.nationalite_pere,
            "profession": dossier.profession_pere,
            "document": piece(dossier.type_piece_pere, dossier.numero_piece_pere),
        },
        "mere": {
            "nom": noms(dossier.nom_mere, dossier.prenom_mere).upper(),
            "lieu_naissance": dossier.lieu_naissance_mere,
            "date_naissance": date_fr(dossier.date_naissance_mere),
            "domicile": acte.domicile_mere,
            "nationalite": dossier.nationalite_mere,
            "profession": dossier.profession_mere,
            "document": piece(dossier.type_piece_mere, dossier.numero_piece_mere),
        },

        "date_declaration": date_fr(acte.date_declaration or dossier.date_soumission),
        "declarant_nom": noms(dossier.nom_declarant, dossier.prenom_declarant).upper(),
        "declarant_qualite": acte.qualite_declarant or dossier.lien_parente_declarant or "",
        "date_attestation": date_fr(acte.date_attestation or acte.dresse_le or acte.date_enregistrement),
        "officier_nom": acte.officier_nom,
        "secretaire_nom": acte.secretaire_nom,
        "nipu": acte.nipu or "",

        "qr": qr_b64(url_verif),
        "img": {
            "armoiries": img_b64("armoiries.png"),
            "cachet": img_b64("cachet.png"),
            "signature_secretaire": img_b64("signature_secretaire.png"),
            "filigrane": img_b64("filigrane.png"),
        },
        "mentions": [
            {
                "type": m.type_mention,
                "numero": m.numero,
                "date": m.date_mention.strftime("%Y-%m-%d") if m.date_mention else "",
                "texte": m.texte,
                "officier_nom": m.officier_nom or acte.officier_nom,
                "base_legale": m.base_legale or "",
            }
            for m in (mentions or [])
        ],
    }


# ---------- Génération ----------
def _pdfkit_config():
    chemin = current_app.config.get("WKHTMLTOPDF_PATH")  # ex: /usr/bin/wkhtmltopdf
    return pdfkit.configuration(wkhtmltopdf=chemin) if chemin else None


def generer_pdf_acte(dossier, acte):
    """Génère le PDF et renvoie le chemin RELATIF à static/ (ex: 'pdfs/acte_12_xxx.pdf')."""
    contexte = construire_contexte(dossier, acte, getattr(acte, "mentions_marginales", []))
    html = render_template("mairie/documents/acte_naissance.html", c=contexte)

    dossier_pdf = os.path.join(current_app.root_path, "static", "pdfs")
    os.makedirs(dossier_pdf, exist_ok=True)
    nom_fichier = f"acte_{acte.id}_{int(datetime.now().timestamp())}.pdf"
    chemin_abs = os.path.join(dossier_pdf, nom_fichier)

    pdfkit.from_string(
        html,
        chemin_abs,
        options={
            "encoding": "UTF-8",
            "quiet": "",
            "page-size": "A4",
            "margin-top": "10mm",
            "margin-right": "10mm",
            "margin-bottom": "10mm",
            "margin-left": "10mm",
            "dpi": 300,
            "print-media-type": "",
            "enable-local-file-access": "",
        },
        configuration=_pdfkit_config(),
    )
    return f"pdfs/{nom_fichier}"