"""
Service de génération PDF pour les résultats d'analyses.
Style inspiré des rapports médicaux professionnels (MedLab).
"""

import os
import re
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
    KeepTogether
)
from reportlab.pdfgen import canvas

from flask import current_app
from itertools import groupby
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import cm
from app.models import (
    Examen, Patient, Laboratoire, Resultat, Parametre, ExamenDetail
)


# ============================================================
# STYLES POUR LA COLONNE TEST (hiérarchique)
# ============================================================

STYLE_NIVEAU_1_ANALYSE = ParagraphStyle(
    'niveau1_analyse',
    fontName='Helvetica-Bold',
    fontSize=11,
    textColor=colors.HexColor('#1a4d2e'),
    alignment=TA_LEFT,
    spaceAfter=6,
    spaceBefore=6,
)

STYLE_NIVEAU_2_PARAMETRE = ParagraphStyle(
    'niveau2_parametre',
    fontName='Helvetica-Bold',
    fontSize=10,
    textColor=colors.HexColor('#2c3e50'),
    alignment=TA_LEFT,
    leftIndent=8,
    spaceAfter=3,
    spaceBefore=3,
)

STYLE_NIVEAU_3_SOUS_PARAMETRE = ParagraphStyle(
    'niveau3_sous_parametre',
    fontName='Helvetica',
    fontSize=9,
    textColor=colors.HexColor('#333333'),
    alignment=TA_LEFT,
    leftIndent=24,  # Indentation visible sous le paramètre parent
)

STYLE_VALEUR_NORMALE = ParagraphStyle(
    'valeur_normale',
    fontName='Helvetica',
    fontSize=9,
    textColor=colors.HexColor('#333333'),
    alignment=TA_CENTER,
)

STYLE_VALEUR_ANORMALE = ParagraphStyle(
    'valeur_anormale',
    fontName='Helvetica-Bold',
    fontSize=9,
    textColor=colors.red,
    alignment=TA_CENTER,
)


def construire_corps_resultats(examen, config_labo):
    """
    Construit le corps du PDF avec structure hiérarchique :

    Niveau 1 : Nom de l'analyse (ex: URINE) - dans la colonne TEST, gras, vert
    Niveau 2 : nom_parametre (ex: Macroscopie) - gras, indenté légèrement
    Niveau 3 : sous_parametre (ex: Couleur) - normal, indenté davantage

    Un seul en-tête de colonnes (TEST | NORMAL | ANORMAL | UNITÉS | VALEURS NORMALES)
    est affiché pour l'ensemble des analyses de l'examen.

    Args:
        examen: instance Examen
        config_labo: config du laboratoire

    Returns:
        list: liste d'éléments Platypus (Table, Spacer, etc.)
    """
    # Récupérer le sexe et l'âge du patient pour choisir la bonne valeur normale
    patient = examen.patient
    sexe_patient = patient.sexe if patient else None
    age_patient = patient.age if patient else None

    # ======================================================
    # En-tête unique (bandeau vert avec titres colonnes, sur 2 lignes :
    # RESULTATS chapeaute NORMAL/ANORMAL)
    # ======================================================
    data = [
        [
            Paragraph('<b>TEST</b>', style_entete_blanc()),
            Paragraph('<b>RESULTATS</b>', style_entete_blanc()),
            '',
            Paragraph('<b>UNITÉS</b>', style_entete_blanc()),
            Paragraph('<b>VALEURS NORMALES</b>', style_entete_blanc()),
        ],
        [
            '',
            Paragraph('<b>NORMAL</b>', style_entete_blanc()),
            Paragraph('<b>ANORMAL</b>', style_entete_blanc()),
            '',
            '',
        ],
    ]
    NB_LIGNES_ENTETE = 2

    spans_parametres = []   # (col1, ligne, col2, ligne) des titres nom_parametre (niveau 2)

    # Pour chaque analyse commandée
    for detail in examen.details.all():
        analyse = detail.analyse

        # ======================================================
        # Récupérer les paramètres ordonnés
        # ======================================================
        parametres = analyse.parametres.order_by(
            Parametre.ordre, Parametre.id
        ).all()

        if not parametres:
            continue

        # ======================================================
        # Récupérer les résultats saisis pour ce detail
        # ======================================================
        resultats_by_param = {
            r.parametre_id: r for r in detail.resultats.all()
        }

        # ======================================================
        # GROUPER les paramètres par nom_parametre
        # ======================================================
        # On utilise dict pour préserver l'ordre d'insertion (Python 3.7+)
        groupes = {}
        for p in parametres:
            groupes.setdefault(p.nom_parametre, []).append(p)

        # ======================================================
        # NIVEAU 1 : Nom de l'analyse, cantonné à la colonne TEST
        # ======================================================
        titre_analyse = Paragraph(
            f'<b>{analyse.nom.upper()}</b>',
            STYLE_NIVEAU_1_ANALYSE
        )
        data.append([titre_analyse, '', '', '', ''])

        # ======================================================
        # Pour chaque groupe de paramètres (Macroscopie, Microscopie...)
        # ======================================================
        for nom_param, params_du_groupe in groupes.items():

            # -----------------------------------------------
            # NIVEAU 2 : Sous-titre du groupe (nom_parametre)
            # -----------------------------------------------
            # On affiche le nom_parametre seulement si :
            # - il y a au moins un sous_parametre non-null dans le groupe
            # OU
            # - il y a plusieurs paramètres partageant ce nom_parametre
            a_des_sous_parametres = any(p.sous_parametre for p in params_du_groupe)

            if a_des_sous_parametres:
                # Cas hiérarchique : Macroscopie / Microscopie / etc.
                titre_niveau2 = Paragraph(
                    f'<b>{nom_param}</b>',
                    STYLE_NIVEAU_2_PARAMETRE
                )
                data.append([titre_niveau2, '', '', '', ''])
                idx_niv2 = len(data) - 1
                spans_parametres.append((0, idx_niv2, 4, idx_niv2))

                # -----------------------------------------------
                # NIVEAU 3 : Sous-paramètres indentés
                # -----------------------------------------------
                for p in params_du_groupe:
                    nom_a_afficher = p.sous_parametre or ''
                    data.append(
                        construire_ligne_parametre(
                            nom_a_afficher,
                            p,
                            resultats_by_param.get(p.id),
                            sexe_patient,
                            age_patient,
                            indent=True
                        )
                    )
            else:
                # Cas plat : pas de sous_parametre, on affiche direct nom_parametre
                for p in params_du_groupe:
                    data.append(
                        construire_ligne_parametre(
                            nom_param,
                            p,
                            resultats_by_param.get(p.id),
                            sexe_patient,
                            age_patient,
                            indent=False
                        )
                    )

    if len(data) == NB_LIGNES_ENTETE:
        # Aucun résultat à afficher (seul l'en-tête est présent)
        return []

    # ======================================================
    # Créer le tableau unique avec les styles appropriés
    # ======================================================
    col_widths = [5.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 4*cm]
    table = Table(data, colWidths=col_widths, repeatRows=NB_LIGNES_ENTETE)

    entete_derniere_ligne = NB_LIGNES_ENTETE - 1
    table_style_cmds = [
        # En-tête (lignes 0-1) : bandeau vert
        ('BACKGROUND', (0, 0), (-1, entete_derniere_ligne), colors.HexColor('#7CBA6F')),
        ('TEXTCOLOR', (0, 0), (-1, entete_derniere_ligne), colors.white),
        ('ALIGN', (0, 0), (-1, entete_derniere_ligne), 'CENTER'),
        ('VALIGN', (0, 0), (-1, entete_derniere_ligne), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, entete_derniere_ligne), 8),
        ('TOPPADDING', (0, 0), (-1, entete_derniere_ligne), 8),

        # SPAN de l'en-tête : TEST / UNITÉS / VALEURS NORMALES sur les 2 lignes,
        # RESULTATS chapeaute NORMAL + ANORMAL
        ('SPAN', (0, 0), (0, entete_derniere_ligne)),
        ('SPAN', (1, 0), (2, 0)),
        ('SPAN', (3, 0), (3, entete_derniere_ligne)),
        ('SPAN', (4, 0), (4, entete_derniere_ligne)),

        # Bordures pour toutes les lignes
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc')),

        # Padding général
        ('LEFTPADDING', (0, NB_LIGNES_ENTETE), (-1, -1), 4),
        ('RIGHTPADDING', (0, NB_LIGNES_ENTETE), (-1, -1), 4),
        ('TOPPADDING', (0, NB_LIGNES_ENTETE), (-1, -1), 4),
        ('BOTTOMPADDING', (0, NB_LIGNES_ENTETE), (-1, -1), 4),
        ('VALIGN', (0, NB_LIGNES_ENTETE), (-1, -1), 'MIDDLE'),
    ]

    # Ajouter les SPAN pour les titres nom_parametre (niveau 2)
    for span in spans_parametres:
        table_style_cmds.append(('SPAN', (span[0], span[1]), (span[2], span[3])))
        # Fond très léger pour titre paramètre
        table_style_cmds.append(
            ('BACKGROUND', (span[0], span[1]), (span[2], span[3]),
             colors.HexColor('#f5f5f5'))
        )

    table.setStyle(TableStyle(table_style_cmds))

    return [table]


def construire_ligne_parametre(nom_affiche, parametre, resultat, sexe, age, indent=True):
    """
    Construit une ligne du tableau pour un paramètre.
    
    Args:
        nom_affiche: le nom à afficher dans la colonne TEST
        parametre: instance Parametre
        resultat: instance Resultat (peut être None)
        sexe: 'M' ou 'F' pour choisir la valeur normale
        age: âge du patient pour choisir enfant/adulte
        indent: True pour indenter (niveau 3), False pour normal
    
    Returns:
        list: [test, normal, anormal, unite, valeur_normale]
    """
    # Choix du style pour la colonne TEST
    style_test = STYLE_NIVEAU_3_SOUS_PARAMETRE if indent else STYLE_NIVEAU_2_PARAMETRE
    cellule_test = Paragraph(nom_affiche, style_test)
    
    # Déterminer la valeur normale selon patient
    valeur_normale = choisir_valeur_normale(parametre, sexe, age)
    
    # Valeur saisie
    valeur = resultat.valeur if resultat else ''
    
    # Est-ce anormal ?
    est_anormal = est_valeur_anormale(valeur, valeur_normale)
    
    # Cellule NORMAL / ANORMAL
    if valeur:
        if est_anormal:
            cellule_normal = Paragraph('', STYLE_VALEUR_NORMALE)
            cellule_anormal = Paragraph(str(valeur), STYLE_VALEUR_ANORMALE)
        else:
            cellule_normal = Paragraph(f'<b>{valeur}</b>', STYLE_VALEUR_NORMALE)
            cellule_anormal = Paragraph('', STYLE_VALEUR_NORMALE)
    else:
        cellule_normal = Paragraph('—', STYLE_VALEUR_NORMALE)
        cellule_anormal = Paragraph('', STYLE_VALEUR_NORMALE)
    
    return [
        cellule_test,
        cellule_normal,
        cellule_anormal,
        Paragraph(parametre.unite or '—', STYLE_VALEUR_NORMALE),
        Paragraph(valeur_normale or '—', STYLE_VALEUR_NORMALE),
    ]


def choisir_valeur_normale(parametre, sexe, age):
    """
    Choisit la valeur normale à afficher selon le patient.
    
    Priorité :
    - Si patient est enfant (< 18 ans) ET valeur_normale_enfant existe → enfant
    - Sinon si Femme → valeur_normale_f
    - Sinon si Homme → valeur_normale_m
    - Fallback : la première valeur non-null
    """
    # Enfant
    if age is not None and age < 18 and parametre.valeur_normale_enfant:
        return parametre.valeur_normale_enfant
    
    # Adulte selon sexe
    if sexe == 'F' and parametre.valeur_normale_f:
        return parametre.valeur_normale_f
    if sexe == 'M' and parametre.valeur_normale_m:
        return parametre.valeur_normale_m
    
    # Fallback
    return (parametre.valeur_normale_f 
            or parametre.valeur_normale_m 
            or parametre.valeur_normale_enfant 
            or '')


def style_entete_blanc():
    """Style pour l'en-tête blanc sur fond vert."""
    return ParagraphStyle(
        'entete_blanc',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER,
    )


def hex_to_color(hex_value):
    """Convertit un code hexadécimal en objet ReportLab Color."""
    if not hex_value or not isinstance(hex_value, str):
        return colors.HexColor('#2c3e50')
    hex_value = hex_value.strip()
    if not hex_value.startswith('#'):
        hex_value = f'#{hex_value}'
    try:
        return colors.HexColor(hex_value)
    except Exception:
        return colors.HexColor('#2c3e50')


def obtenir_styles(couleur_principale):
    """Retourne les styles de paragraphes utilisés dans le PDF."""
    styles = {
        'header': ParagraphStyle(
            'header',
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            alignment=TA_CENTER,
            textColor=couleur_principale,
            spaceAfter=8,
        ),
        'sous_titre': ParagraphStyle(
            'sous_titre',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            alignment=TA_LEFT,
            textColor=couleur_principale,
            spaceAfter=6,
        ),
        'info': ParagraphStyle(
            'info',
            fontName='Helvetica',
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.black,
            spaceAfter=4,
        ),
        'info_centre': ParagraphStyle(
            'info_centre',
            fontName='Helvetica',
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=4,
        ),
        'slogan': ParagraphStyle(
            'slogan',
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.gray,
            spaceAfter=6,
        ),
        'note': ParagraphStyle(
            'note',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.gray,
            spaceAfter=4,
        ),
        'note_centre': ParagraphStyle(
            'note_centre',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.gray,
            spaceAfter=4,
        ),
        'signature_nom': ParagraphStyle(
            'signature_nom',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=2,
        ),
        'signature_titre': ParagraphStyle(
            'signature_titre',
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#444444'),
            spaceAfter=4,
        ),
    }
    return styles


def est_valeur_anormale(valeur, valeur_normale):
    """Détecte si une valeur est en dehors d'une plage normale simple."""
    if valeur is None or valeur == '':
        return False
    if not valeur_normale:
        return False

    def parse_decimal(text):
        if text is None:
            return None
        text = re.sub(r'[^0-9\.,\-]+', '', str(text)).replace(',', '.')
        try:
            return Decimal(text)
        except Exception:
            return None

    valeur_num = parse_decimal(valeur)
    if valeur_num is None:
        return False

    # Plage sous forme "min-max" ou "min - max"
    if '-' in valeur_normale:
        bornes = [b.strip() for b in valeur_normale.split('-') if b.strip()]
        if len(bornes) == 2:
            min_norm = parse_decimal(bornes[0])
            max_norm = parse_decimal(bornes[1])
            if min_norm is not None and max_norm is not None:
                return valeur_num < min_norm or valeur_num > max_norm

    return False


def construire_entete(labo, styles):
    """Construit l'entête du PDF, centrée : logo, nom, slogan, coordonnées."""
    elements = []

    logo_image = charger_logo(labo, largeur=3 * cm, hauteur=3 * cm)
    if logo_image:
        logo_image.hAlign = 'CENTER'
        elements.append(logo_image)
        elements.append(Spacer(1, 0.2 * cm))

    titre = labo.nom or 'Laboratoire'
    elements.append(Paragraph(titre, styles['header']))

    if labo.slogan:
        elements.append(Paragraph(labo.slogan, styles['slogan']))

    adresse = ' - '.join(
        part for part in (
            labo.adresse,
            labo.ville,
            labo.departement,
            labo.pays,
        ) if part
    )
    if adresse:
        elements.append(Paragraph(adresse, styles['info_centre']))

    contacts = ' | '.join(
        part for part in (
            labo.telephone1,
            labo.telephone2,
            labo.email,
            labo.site_web,
        ) if part
    )
    if contacts:
        elements.append(Paragraph(contacts, styles['info_centre']))

    if labo.numero_licence:
        elements.append(Paragraph(f'Licence N°: {labo.numero_licence}', styles['info_centre']))

    elements.append(Spacer(1, 0.4 * cm))
    return elements


def charger_logo(labo, largeur=2.5 * cm, hauteur=2.5 * cm):
    """Charge le logo du laboratoire en tant qu'image ReportLab, si disponible."""
    if not labo.logo_path:
        return None

    chemin_logo = os.path.join(current_app.static_folder, labo.logo_path)
    if not os.path.isfile(chemin_logo):
        return None

    try:
        return RLImage(chemin_logo, width=largeur, height=hauteur)
    except Exception:
        return None


STYLE_CHAMP_INFOS = ParagraphStyle(
    'champ_infos',
    fontName='Helvetica',
    fontSize=9,
    leading=11,
    alignment=TA_LEFT,
    textColor=colors.black,
)

STYLE_NOM_PATIENT = ParagraphStyle(
    'nom_patient',
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=13,
    alignment=TA_LEFT,
    textColor=colors.black,
)


def construire_infos_patient(examen, patient):
    """Construit le bandeau d'identité patient / examen (2 lignes, sans titre ni bordures)."""
    date_naissance = (
        patient.date_naissance.strftime('%d/%m/%Y')
        if patient and patient.date_naissance else '—'
    )
    date_examen = (
        examen.date_examen.strftime('%d/%m/%Y %H:%M')
        if examen.date_examen else '—'
    )
    age_sexe = ' '.join(
        part for part in (
            patient.sexe if patient and patient.sexe else '',
            str(patient.age) if patient and patient.age else '',
        ) if part
    ) or '—'

    data = [
        [
            Paragraph(f'<b>N°:</b> {patient.code if patient else "N/A"}', STYLE_CHAMP_INFOS),
            Paragraph(f'<b>{patient.nom_complet if patient else "N/A"}</b>', STYLE_NOM_PATIENT),
            Paragraph(f'<b>NAISSANCE:</b> {date_naissance}', STYLE_CHAMP_INFOS),
            Paragraph(f'<b>SEXE | AGE:</b> {age_sexe} ans', STYLE_CHAMP_INFOS),
        ],
        [
            Paragraph(f'<b>N° EXAMEN:</b> {examen.numero or "N/A"}', STYLE_CHAMP_INFOS),
            '',
            Paragraph(f'<b>DATE:</b> {date_examen}', STYLE_CHAMP_INFOS),
            Paragraph('<b>PAGE:</b> 1', STYLE_CHAMP_INFOS),
        ],
    ]

    table = Table(data, colWidths=[3 * cm, 5 * cm, 4.5 * cm, 4.5 * cm])
    table.setStyle(TableStyle([
        ('SPAN', (0, 1), (1, 1)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    return [table, Spacer(1, 0.3 * cm)]


def construire_pied_page(examen, labo, styles):
    """Construit le pied de page : marge pour la signature, puis le message final."""
    elements = []

    if examen.preleve_par:
        elements.append(Paragraph(
            f'<b>Prélevé par :</b> {examen.preleve_par}',
            styles['info_centre']
        ))

    # Marge réservée pour la signature manuscrite du responsable
    elements.append(Spacer(1, 2 * cm))

    if labo.directeur_nom:
        elements.append(Paragraph(labo.directeur_nom, styles['signature_nom']))
        if labo.directeur_titre:
            elements.append(Paragraph(labo.directeur_titre, styles['signature_titre']))

    # Message final (mentions légales) + date/heure de génération, affichés en dernier
    if labo.pied_page:
        elements.append(Spacer(1, 0.6 * cm))
        horodatage = datetime.now().strftime('%d/%m/%Y à %H:%M')
        message = f'{labo.pied_page}<br/>Fait le {horodatage}'
        elements.append(Paragraph(message, styles['note_centre']))

    return elements

# ====================================================================
# GÉNÉRATION COMPLÈTE DU PDF
# ====================================================================

def generer_pdf_examen(examen_id, sauvegarder=True):
    """Génère le PDF d'un examen."""
    
    examen = Examen.query.get(examen_id)
    if not examen:
        return None, 'Examen introuvable.'
    
    patient = examen.patient
    labo = Laboratoire.get_config()
    
    couleur_principale = hex_to_color(labo.en_tete_couleur)
    styles = obtenir_styles(couleur_principale)
    
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        title=f'Resultats - {patient.nom_complet}',
        author=labo.nom or 'Laboratoire',
        subject=f'Examen {examen.numero}',
    )
    
    elements = []
    
    # 1. En-tête (logo + nom labo + coordonnées) — INCHANGÉ
    elements.extend(construire_entete(labo, styles))
    
    # 2. Infos patient (style condensé)
    elements.extend(construire_infos_patient(examen, patient))
    
    # 3. CORPS DES RÉSULTATS (NOUVEAU STYLE)
    elements.extend(construire_corps_resultats(examen, labo))
    
    # 4. Pied de page (avec signature) — INCHANGÉ
    elements.extend(construire_pied_page(examen, labo, styles))
    
    try:
        doc.build(elements)
    except Exception as e:
        return None, f'Erreur lors de la génération : {str(e)}'
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    if sauvegarder:
        dossier_pdf = current_app.config.get('PDF_OUTPUT_FOLDER')
        os.makedirs(dossier_pdf, exist_ok=True)
        
        nom_fichier = f'{examen.numero}_{patient.nom_complet.replace(" ", "_")}.pdf'
        nom_fichier = ''.join(c for c in nom_fichier if c.isalnum() or c in '._-')
        
        chemin_complet = os.path.join(dossier_pdf, nom_fichier)
        
        with open(chemin_complet, 'wb') as f:
            f.write(pdf_bytes)
        
        from app.extensions import db
        examen.statut = 'imprime'
        db.session.commit()
        
        return chemin_complet, None
    
    return pdf_bytes, None
