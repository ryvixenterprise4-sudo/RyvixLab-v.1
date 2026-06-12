"""
Service de génération PDF pour les résultats d'analyses.

Utilise ReportLab pour créer des PDFs professionnels.
"""

import os
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

from flask import current_app

from app.models import Examen, Patient, Laboratoire, Resultat, Parametre, ExamenDetail


# ====================================================================
# COULEURS ET STYLES
# ====================================================================

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
            fontSize=14,
            textColor=couleur_principale,
            alignment=TA_LEFT,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ),
        'normal': ParagraphStyle(
            'NormalCustom',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        ),
        'gras': ParagraphStyle(
            'Gras',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#333333'),
        ),
        'pied': ParagraphStyle(
            'Pied',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        ),
        'analyse_nom': ParagraphStyle(
            'AnalyseNom',
            parent=styles['Heading3'],
            fontSize=13,
            textColor=colors.white,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            spaceAfter=0,
        ),
    }


# ====================================================================
# CONSTRUCTION DE L'EN-TÊTE
# ====================================================================

def construire_entete(labo, styles):
    """Construit l'en-tête du laboratoire."""
    elements = []
    
    # ===== LOGO (si disponible) =====
    if labo.logo_path:
        chemin_logo = os.path.join(
            current_app.static_folder, labo.logo_path
        )
        if os.path.exists(chemin_logo):
            try:
                img = Image(chemin_logo, width=3*cm, height=3*cm, kind='proportional')
                img.hAlign = 'CENTER'
                elements.append(img)
                elements.append(Spacer(1, 4))
            except Exception as e:
                print(f'Erreur logo : {e}')
    
    # ===== NOM DU LABORATOIRE =====
    elements.append(Paragraph(labo.nom or 'Laboratoire Médical', styles['titre_labo']))
    
    # ===== SLOGAN =====
    if labo.slogan:
        elements.append(Paragraph(labo.slogan, styles['slogan']))
    
    # ===== COORDONNÉES =====
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
        contacts.append(f' {labo.telephone1}')
    if labo.telephone2:
        contacts.append(labo.telephone2)
    if labo.email:
        contacts.append(f'✉ {labo.email}')
    
    if contacts:
        coordonnees.append(' | '.join(contacts))
    
    if labo.numero_licence:
        coordonnees.append(f'Licence N° : {labo.numero_licence}')
    
    for ligne in coordonnees:
        elements.append(Paragraph(ligne, styles['adresse']))
    
    elements.append(Spacer(1, 10))
    
    return elements


# ====================================================================
# INFO PATIENT
# ====================================================================

def construire_infos_patient(examen, patient, styles, couleur):
    """Tableau d'informations du patient."""
    elements = []
    
    # ===== TITRE "RÉSULTATS D'ANALYSES" avec fond coloré (méthode propre) =====
    titre_data = [['RÉSULTATS D\'ANALYSES']]
    titre_table = Table(titre_data, colWidths=[17*cm])
    titre_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), couleur),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(titre_table)
    elements.append(Spacer(1, 8))
    
    # ===== TABLEAU INFOS PATIENT =====
    date_examen = examen.date_examen.strftime('%d/%m/%Y') if examen.date_examen else '-'
    date_naissance = patient.date_naissance.strftime('%d/%m/%Y') if patient.date_naissance else '-'
    age = f'{patient.age} ans' if patient.age else '-'
    sexe = 'Masculin' if patient.sexe == 'M' else ('Féminin' if patient.sexe == 'F' else '-')
    
    data = [
        ['N° Examen :', examen.numero, 'Date :', date_examen],
        ['Patient :', patient.nom_complet, 'Code :', patient.code],
        ['Né(e) le :', date_naissance, 'Âge :', age],
        ['Sexe :', sexe, 'Téléphone :', patient.telephone or '-'],
    ]
    
    if examen.medecin_prescripteur:
        data.append(['Prescripteur :', examen.medecin_prescripteur, '', ''])
    
    table = Table(data, colWidths=[3*cm, 6*cm, 2.5*cm, 5.5*cm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
        ('FONT', (2, 0), (2, -1), 'Helvetica-Bold', 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#eeeeee')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    return elements


# ====================================================================
# TABLEAU DES RÉSULTATS PAR ANALYSE
# ====================================================================

def construire_tableau_analyse(detail, patient, styles, couleur):
    """Tableau des résultats pour UNE analyse."""
    elements = []
    
    analyse = detail.analyse
    
    # En-tête de l'analyse (avec couleur)
    titre_data = [[Paragraph(f'<b>{analyse.nom.upper()}</b>', styles['analyse_nom'])]]
    titre_table = Table(titre_data, colWidths=[17*cm])
    titre_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), couleur),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(titre_table)
    
    # Récupérer les paramètres et résultats
    parametres = Parametre.query.filter_by(
        analyse_id=analyse.id
    ).order_by(Parametre.ordre).all()
    
    # En-têtes du tableau
    data = [['Paramètre', 'Résultat', 'Unité', 'Valeurs normales']]
    
    # Lignes
    for param in parametres:
        resultat = Resultat.query.filter_by(
            examen_detail_id=detail.id,
            parametre_id=param.id
        ).first()
        
        nom_param = param.nom_parametre
        if param.sous_parametre:
            nom_param += f' ({param.sous_parametre})'
        
        valeur = resultat.valeur if resultat and resultat.valeur else '—'
        unite = param.unite or '-'
        
        # Valeur normale selon le sexe
        if patient.sexe == 'F' and param.valeur_normale_f:
            normale = param.valeur_normale_f
        elif patient.sexe == 'M' and param.valeur_normale_m:
            normale = param.valeur_normale_m
        elif param.valeur_normale_f and param.valeur_normale_m:
            normale = f'F: {param.valeur_normale_f}\nH: {param.valeur_normale_m}'
        else:
            normale = param.valeur_normale_f or param.valeur_normale_m or '-'
        
        data.append([nom_param, valeur, unite, normale])
    
    if len(data) == 1:  # Pas de paramètre
        data.append(['Aucun paramètre configuré', '-', '-', '-'])
    
    # Tableau
    table = Table(data, colWidths=[5.5*cm, 4*cm, 2.5*cm, 5*cm])
    
    style_table = [
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        
        # Corps
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
        ('FONT', (1, 1), (1, -1), 'Helvetica-Bold', 10),  # Résultat en gras
        ('TEXTCOLOR', (1, 1), (1, -1), couleur),  # Résultat en couleur
        
        # Bordures et padding
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        
        # Alternance de couleurs
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
    ]
    
    table.setStyle(TableStyle(style_table))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    return elements


# ====================================================================
# PIED DE PAGE
# ====================================================================

def construire_pied_page(labo, styles, couleur):
    """Pied de page avec signature et infos légales."""
    elements = []
    
    elements.append(Spacer(1, 15))
    
    # ===== SIGNATURE DU DIRECTEUR =====
    if labo.directeur_nom or labo.directeur_signature_path:
        data_signature = []
        
        # Si signature image
        if labo.directeur_signature_path:
            chemin_sig = os.path.join(
                current_app.static_folder, labo.directeur_signature_path
            )
            if os.path.exists(chemin_sig):
                try:
                    img_sig = Image(chemin_sig, width=4*cm, height=1.5*cm, kind='proportional')
                    data_signature.append([img_sig])
                except:
                    pass
        
        # Nom et titre du directeur
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
            # Tableau aligné à droite
            tbl = Table(
                [[''] + [data_signature]],
                colWidths=[10*cm, 7*cm]
            )
            tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ]))
            # Simplifié : juste à droite
            sig_table = Table(data_signature, colWidths=[7*cm])
            sig_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            wrapper = Table([['', sig_table]], colWidths=[10*cm, 7*cm])
            wrapper.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(wrapper)
    
    elements.append(Spacer(1, 15))
    
    # ===== TEXTE DE PIED DE PAGE =====
    if labo.pied_page:
        elements.append(Paragraph(labo.pied_page, styles['pied']))
    
    # Mention résultats
    elements.append(Paragraph(
        f'<i> le {datetime.now().strftime("%d/%m/%Y à %H:%M")}</i>',
        styles['pied']
    ))
    
    return elements


# ====================================================================
# GÉNÉRATION COMPLÈTE DU PDF
# ====================================================================

def generer_pdf_examen(examen_id, sauvegarder=True):
    """
    Génère le PDF d'un examen.
    
    Args:
        examen_id (int): ID de l'examen
        sauvegarder (bool): Sauvegarder sur disque ou retourner les bytes
    
    Returns:
        tuple (bytes_pdf | chemin_fichier, message_erreur)
    """
    # Récupérer les données
    examen = Examen.query.get(examen_id)
    if not examen:
        return None, 'Examen introuvable.'
    
    patient = examen.patient
    labo = Laboratoire.get_config()
    
    couleur_principale = hex_to_color(labo.en_tete_couleur)
    styles = obtenir_styles(couleur_principale)
    
    # Buffer en mémoire
    buffer = BytesIO()
    
    # Création du document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
        title=f'Résultats - {patient.nom_complet}',
        author=labo.nom,
        subject=f'Examen {examen.numero}',
    )
    
    # Construction des éléments
    elements = []
    
    # En-tête
    elements.extend(construire_entete(labo, styles))
    
    # Infos patient
    elements.extend(construire_infos_patient(examen, patient, styles, couleur_principale))
    
    # Tableaux des résultats par analyse
    elements.append(Paragraph('Résultats détaillés', styles['titre_section']))
    
    for detail in examen.details.all():
        elements.extend(construire_tableau_analyse(detail, patient, styles, couleur_principale))
    
    # Pied de page
    elements.extend(construire_pied_page(labo, styles, couleur_principale))
    
    # Générer le PDF
    try:
        doc.build(elements)
    except Exception as e:
        return None, f'Erreur lors de la génération : {str(e)}'
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # ===== SAUVEGARDE SUR DISQUE (optionnel) =====
    if sauvegarder:
        dossier_pdf = current_app.config.get('PDF_OUTPUT_FOLDER')
        os.makedirs(dossier_pdf, exist_ok=True)
        
        # Nom du fichier
        nom_fichier = f'{examen.numero}_{patient.nom_complet.replace(" ", "_")}.pdf'
        nom_fichier = ''.join(c for c in nom_fichier if c.isalnum() or c in '._-')
        
        chemin_complet = os.path.join(dossier_pdf, nom_fichier)
        
        with open(chemin_complet, 'wb') as f:
            f.write(pdf_bytes)
        
        # Marquer l'examen comme imprimé
        from app.extensions import db
        examen.statut = 'imprime'
        db.session.commit()
        
        return chemin_complet, None
    
    return pdf_bytes, None