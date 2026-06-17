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

from app.models import (
    Examen, Patient, Laboratoire, Resultat, Parametre, ExamenDetail
)


# ====================================================================
# COULEURS ET STYLES
# ====================================================================

# Couleur verte du style médical (comme MedLab)
COULEUR_BANDEAU = colors.HexColor('#7CBA6F')  # Vert pomme

def hex_to_color(hex_str):
    """Convertit un code hex en couleur ReportLab."""
    if not hex_str:
        return colors.HexColor('#2c3e50')
    if not hex_str.startswith('#'):
        hex_str = '#' + hex_str
    try:
        return colors.HexColor(hex_str)
    except:
        return colors.HexColor('#2c3e50')


def obtenir_styles(couleur_principale):
    """Retourne les styles personnalisés du document."""
    styles = getSampleStyleSheet()
    
    return {
        'titre_labo': ParagraphStyle(
            'TitreLabo',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=couleur_principale,
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ),
        'slogan': ParagraphStyle(
            'Slogan',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName='Helvetica-Oblique'
        ),
        'adresse': ParagraphStyle(
            'Adresse',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            spaceAfter=2
        ),
        'titre_section': ParagraphStyle(
            'TitreSection',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=couleur_principale,
            alignment=TA_LEFT,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ),
        'normal': ParagraphStyle(
            'NormalCustom',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        ),
        'pied': ParagraphStyle(
            'Pied',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        ),
        # Style "catégorie d'analyse" comme ***CHIMIE***
        'categorie': ParagraphStyle(
            'Categorie',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#000000'),
            alignment=TA_LEFT,
            spaceAfter=4,
            spaceBefore=8,
        ),
        # Nom du paramètre (en colonne TEST)
        'param_nom': ParagraphStyle(
            'ParamNom',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            fontName='Helvetica',
        ),
        # Valeur normale (résultat dans plage)
        'valeur_normale': ParagraphStyle(
            'ValeurNormale',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        ),
        # Valeur anormale (résultat hors plage)
        'valeur_anormale': ParagraphStyle(
            'ValeurAnormale',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#cc0000'),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        ),
        # Cellule centrée (unité, valeurs normales)
        'cellule_centree': ParagraphStyle(
            'CelluleCentree',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
        ),
    }


# ====================================================================
# DÉTECTION DE VALEURS ANORMALES
# ====================================================================

def parse_plage(plage_str):
    """
    Parse une plage de valeurs normales.
    
    Exemples :
        '0.5-1.3'  → (0.5, 1.3)
        '< 10'     → (None, 10)
        '> 100'    → (100, None)
        '7 - 18'   → (7, 18)
    
    Returns:
        tuple (min, max) ou (None, None) si non parsable
    """
    if not plage_str:
        return (None, None)
    
    plage_str = plage_str.strip()
    
    # < X ou ≤ X
    match = re.match(r'^[<≤]\s*([\d.,]+)', plage_str)
    if match:
        try:
            return (None, float(match.group(1).replace(',', '.')))
        except ValueError:
            pass
    
    # > X ou ≥ X
    match = re.match(r'^[>≥]\s*([\d.,]+)', plage_str)
    if match:
        try:
            return (float(match.group(1).replace(',', '.')), None)
        except ValueError:
            pass
    
    # X - Y ou X-Y
    match = re.match(r'^([\d.,]+)\s*[-–]\s*([\d.,]+)', plage_str)
    if match:
        try:
            return (
                float(match.group(1).replace(',', '.')),
                float(match.group(2).replace(',', '.'))
            )
        except ValueError:
            pass
    
    return (None, None)


def est_valeur_anormale(valeur, plage_normale):
    """
    Détermine si une valeur est en dehors de la plage normale.
    
    Returns:
        True si anormal, False si normal ou indéterminable
    """
    if not valeur or not plage_normale:
        return False
    
    # Pour les valeurs texte (Positif/Négatif, +/++, etc.)
    if not est_numerique(valeur):
        # Si la valeur normale est aussi du texte, on compare
        valeur_lower = valeur.strip().lower()
        plage_lower = plage_normale.strip().lower()
        
        # Cas spécifiques
        if valeur_lower in ['positif', '+', '++', '+++', '++++', 'présent', 'anormal']:
            return True
        if valeur_lower in ['négatif', 'normal', 'absent', '-']:
            return False
        return False
    
    # Pour les valeurs numériques
    try:
        val = float(str(valeur).replace(',', '.'))
    except (ValueError, TypeError):
        return False
    
    min_v, max_v = parse_plage(plage_normale)
    
    if min_v is None and max_v is None:
        return False  # Plage non parsable
    
    if min_v is not None and val < min_v:
        return True
    if max_v is not None and val > max_v:
        return True
    
    return False


def est_numerique(valeur):
    """Vérifie si une valeur est numérique."""
    if not valeur:
        return False
    try:
        float(str(valeur).replace(',', '.'))
        return True
    except (ValueError, TypeError):
        return False


# ====================================================================
# EN-TÊTE DU LABORATOIRE (inchangé)
# ====================================================================

def construire_entete(labo, styles):
    """Construit l'en-tête du laboratoire."""
    elements = []
    
    if labo.logo_path:
        chemin_logo = os.path.join(
            current_app.static_folder, labo.logo_path
        )
        if os.path.exists(chemin_logo):
            try:
                img = RLImage(chemin_logo, width=3*cm, height=3*cm, kind='proportional')
                img.hAlign = 'CENTER'
                elements.append(img)
                elements.append(Spacer(1, 4))
            except Exception as e:
                print(f'Erreur logo : {e}')
    
    elements.append(Paragraph(labo.nom or 'Laboratoire Médical', styles['titre_labo']))
    
    if labo.slogan:
        elements.append(Paragraph(labo.slogan, styles['slogan']))
    
    coordonnees = []
    if labo.adresse:
        adresse_complete = labo.adresse
        if labo.ville:
            adresse_complete += f', {labo.ville}'
        if labo.pays:
            adresse_complete += f' - {labo.pays}'
        coordonnees.append(adresse_complete)
    
    contacts = []
    if labo.telephone1:
        contacts.append(f'Tel: {labo.telephone1}')
    if labo.telephone2:
        contacts.append(labo.telephone2)
    if labo.email:
        contacts.append(f'Email: {labo.email}')
    
    if contacts:
        coordonnees.append(' | '.join(contacts))
    
    if labo.numero_licence:
        coordonnees.append(f'Licence N°: {labo.numero_licence}')
    
    for ligne in coordonnees:
        elements.append(Paragraph(ligne, styles['adresse']))
    
    elements.append(Spacer(1, 10))
    
    return elements


# ====================================================================
# INFOS PATIENT (style condensé)
# ====================================================================

def construire_infos_patient(examen, patient, styles, couleur):
    """Bandeau d'informations du patient style médical."""
    elements = []
    
    date_examen = examen.date_examen.strftime('%d/%m/%Y %H:%M') if examen.date_examen else '-'
    date_naissance = patient.date_naissance.strftime('%d/%m/%Y') if patient.date_naissance else '-'
    age = f'{patient.age}' if patient.age else '-'
    sexe = patient.sexe or '-'
    
    # Ligne 1 : Code + Patient + Date naissance + Age/Sexe
    ligne1 = [[
        Paragraph(f'<b>ACCOUNT N°:</b> {patient.code}', styles['param_nom']),
        Paragraph(f'<b>{patient.nom_complet}</b>', styles['param_nom']),
        Paragraph(f'<b>NAISSANCE:</b> {date_naissance}', styles['param_nom']),
        Paragraph(f'<b>AGE | SEXE:</b> {sexe}  {age}', styles['param_nom']),
    ]]
    
    table1 = Table(ligne1, colWidths=[4*cm, 6*cm, 4*cm, 3*cm])
    table1.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(table1)
    
    # Ligne 2 : Numéro examen + Date examen
    ligne2 = [[
        Paragraph(f'<b>N° EXAMEN:</b> {examen.numero}', styles['param_nom']),
        Paragraph(f'<b>DATE:</b> {date_examen}', styles['param_nom']),
        Paragraph(f'<b>PAGE:</b> 1', styles['param_nom']),
    ]]
    
    table2 = Table(ligne2, colWidths=[6*cm, 7*cm, 4*cm])
    table2.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table2)
    
    return elements


# ====================================================================
# BANDEAU D'EN-TÊTE DU TABLEAU DE RÉSULTATS (style médical vert)
# ====================================================================

def construire_bandeau_colonnes(styles):
    """
    Bandeau vert qui sert d'en-tête au tableau de résultats.
    Format : TEST | RÉSULTATS (NORMAL | ANORMAL) | UNITÉS | VALEURS NORMALES
    """
    # En-tête avec colonnes RÉSULTATS divisée en NORMAL/ANORMAL
    header_data = [
        # Ligne 1 : Titres principaux
        ['TEST', 'RESULTATS', '', 'UNITES', 'VALEURS NORMALES'],
        # Ligne 2 : Sous-titres (NORMAL | ANORMAL)
        ['', 'NORMAL', 'ANORMAL', '', '']
    ]
    
    table = Table(
        header_data,
        colWidths=[5*cm, 3*cm, 3*cm, 2.5*cm, 3.5*cm]
    )
    
    table.setStyle(TableStyle([
        # Fond vert sur toutes les cellules
        ('BACKGROUND', (0, 0), (-1, -1), COULEUR_BANDEAU),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fusion : TEST sur 2 lignes
        ('SPAN', (0, 0), (0, 1)),
        # Fusion : UNITES sur 2 lignes
        ('SPAN', (3, 0), (3, 1)),
        # Fusion : VALEURS NORMALES sur 2 lignes
        ('SPAN', (4, 0), (4, 1)),
        # Fusion : RESULTATS sur 2 colonnes (ligne 1)
        ('SPAN', (1, 0), (2, 0)),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        
        # Bordures fines blanches entre les sections
        ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.white),
        ('LINEBEFORE', (3, 0), (3, -1), 0.5, colors.white),
        ('LINEBEFORE', (4, 0), (4, -1), 0.5, colors.white),
        ('LINEBEFORE', (2, 1), (2, 1), 0.5, colors.white),
    ]))
    
    return table


# ====================================================================
# CONSTRUCTION DU CORPS DES RÉSULTATS (NOUVEAU STYLE)
# ====================================================================

def construire_corps_resultats(examen, patient, styles):
    """
    Construit le corps des résultats au style MedLab.
    
    Format pour chaque analyse :
        ***NOM ANALYSE***
        [Paramètre]  [Valeur Normal]  [Valeur Anormal]  [Unité]  [Plage normale]
    """
    elements = []
    
    # ===== BANDEAU D'EN-TÊTE DES COLONNES =====
    elements.append(construire_bandeau_colonnes(styles))
    
    # ===== POUR CHAQUE ANALYSE =====
    for detail in examen.details.all():
        analyse = detail.analyse
        
        parametres = Parametre.query.filter_by(
            analyse_id=analyse.id
        ).order_by(Parametre.ordre).all()
        
        if not parametres:
            continue
        
        # ----- Titre de la catégorie : ***NOM*** -----
        titre_categorie = f'{analyse.nom.upper()}'
        
        # Tableau du titre (fond blanc, gras)
        titre_data = [[Paragraph(titre_categorie, styles['categorie'])]]
        titre_table = Table(titre_data, colWidths=[17*cm])
        titre_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(titre_table)
        
        # ----- Tableau des paramètres -----
        donnees_table = []
        
        for param in parametres:
            resultat = Resultat.query.filter_by(
                examen_detail_id=detail.id,
                parametre_id=param.id
            ).first()
            
            # Nom du paramètre
            nom_param = param.nom_parametre
            if param.sous_parametre:
                nom_param += f' ({param.sous_parametre})'
            
            valeur = resultat.valeur if resultat and resultat.valeur else ''
            unite = param.unite or ''
            
            # Déterminer la valeur normale selon le sexe
            if patient.sexe == 'F' and param.valeur_normale_f:
                plage_normale = param.valeur_normale_f
            elif patient.sexe == 'M' and param.valeur_normale_m:
                plage_normale = param.valeur_normale_m
            elif param.valeur_normale_f and param.valeur_normale_m:
                plage_normale = f'F: {param.valeur_normale_f} / H: {param.valeur_normale_m}'
            else:
                plage_normale = param.valeur_normale_f or param.valeur_normale_m or ''
            
            # Déterminer si la valeur est anormale
            anormal = est_valeur_anormale(valeur, plage_normale)
            
            # Placer la valeur dans la colonne NORMAL ou ANORMAL
            if anormal:
                valeur_normale_col = ''
                valeur_anormale_col = Paragraph(
                    f'<b>{valeur}</b>', styles['valeur_anormale']
                ) if valeur else ''
            else:
                valeur_normale_col = Paragraph(
                    f'<b>{valeur}</b>', styles['valeur_normale']
                ) if valeur else ''
                valeur_anormale_col = ''
            
            # Ligne du tableau
            donnees_table.append([
                Paragraph(nom_param, styles['param_nom']),
                valeur_normale_col,
                valeur_anormale_col,
                Paragraph(unite, styles['cellule_centree']),
                Paragraph(plage_normale, styles['cellule_centree']),
            ])
        
        # Créer le tableau
        if donnees_table:
            tbl_parametres = Table(
                donnees_table,
                colWidths=[5*cm, 3*cm, 3*cm, 2.5*cm, 3.5*cm]
            )
            
            tbl_parametres.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                
                # Pas de bordures (look propre comme MedLab)
                # Sauf une ligne fine en bas de chaque ligne
                ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#dddddd')),
            ]))
            
            elements.append(tbl_parametres)
        
        # Espacement entre les analyses
        elements.append(Spacer(1, 8))
    
    return elements


# ====================================================================
# PIED DE PAGE (inchangé, mais simplifié)
# ====================================================================

def construire_pied_page(examen, labo, styles):
    """Pied de page avec signature et infos."""
    elements = []
    
    elements.append(Spacer(1, 15))
    
    # Ligne de séparation
    sep = Table([[''], ['']], colWidths=[17*cm], rowHeights=[0.5, 5])
    sep.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, COULEUR_BANDEAU),
    ]))
    elements.append(sep)
    
    # Infos prélèvement
    date_prelev = examen.date_examen.strftime('%d/%m/%Y %H:%M') if examen.date_examen else '-'
    
    infos = []
    if examen.medecin_prescripteur:
        infos.append(Paragraph(
            f'<b>Prélevé par :</b> {examen.medecin_prescripteur}',
            styles['normal']
        ))
    infos.append(Paragraph(
        f'<b>Date Prélèvement :</b> {date_prelev}',
        styles['normal']
    ))
    
    for info in infos:
        elements.append(info)
        elements.append(Spacer(1, 2))
    
    elements.append(Spacer(1, 20))
    
    # ===== SIGNATURE DU DIRECTEUR =====
    if labo.directeur_nom or labo.directeur_signature_path:
        data_signature = []
        
        if labo.directeur_signature_path:
            chemin_sig = os.path.join(
                current_app.static_folder, labo.directeur_signature_path
            )
            if os.path.exists(chemin_sig):
                try:
                    img_sig = RLImage(chemin_sig, width=4*cm, height=1.5*cm, kind='proportional')
                    data_signature.append([img_sig])
                except Exception as e:
                    print(f'Erreur signature : {e}')
        
        if labo.directeur_nom:
            data_signature.append([Paragraph(
                f'<b>{labo.directeur_nom}</b>',
                styles['normal']
            )])
        
        if labo.directeur_titre:
            data_signature.append([Paragraph(
                f'<i>{labo.directeur_titre}</i>',
                styles['normal']
            )])
        
        if data_signature:
            sig_table = Table(data_signature, colWidths=[7*cm])
            sig_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            wrapper = Table([['', sig_table]], colWidths=[10*cm, 7*cm])
            wrapper.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(wrapper)
    
    elements.append(Spacer(1, 15))
    
    if labo.pied_page:
        elements.append(Paragraph(labo.pied_page, styles['pied']))
    
    elements.append(Paragraph(
        f'<i>Fait le {datetime.now().strftime("%d/%m/%Y à %H:%M")} </i>',
        styles['pied']
    ))
    
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
    elements.extend(construire_infos_patient(examen, patient, styles, couleur_principale))
    
    # 3. CORPS DES RÉSULTATS (NOUVEAU STYLE)
    elements.extend(construire_corps_resultats(examen, patient, styles))
    
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