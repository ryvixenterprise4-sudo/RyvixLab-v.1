"""
Blueprint Impression - génération et téléchargement des PDFs.
"""

import os
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, send_file, current_app, abort
)
from flask_login import login_required, current_user

from app.services import pdf_service, resultat_service
from app.models import Examen


impression_bp = Blueprint('impression', __name__, url_prefix='/impression')


# ====================================================================
# LISTE DES EXAMENS PRÊTS À IMPRIMER
# ====================================================================

@impression_bp.route('/')
@login_required
def liste():
    """Liste des examens terminés prêts à imprimer."""
    
    from datetime import datetime
    
    # Filtre par date
    date_str = request.args.get('date', '')
    date_filtre = None
    if date_str:
        try:
            date_filtre = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Filtre par statut (par défaut: 'termine' et 'imprime')
    statut = request.args.get('statut', 'termine')
    
    # Recherche
    recherche = request.args.get('q', '')
    
    # Récupérer les examens
    from app.models import Examen, Patient
    from app.extensions import db
    from sqlalchemy import or_
    
    query = Examen.query.join(Patient)
    
    if statut == 'all':
        query = query.filter(Examen.statut.in_(['termine', 'imprime']))
    elif statut in ('termine', 'imprime'):
        query = query.filter(Examen.statut == statut)
    
    if date_filtre:
        query = query.filter(
            db.func.date(Examen.date_examen) == date_filtre
        )
    
    if recherche:
        terme = f'%{recherche.strip()}%'
        query = query.filter(
            or_(
                Patient.code.ilike(terme),
                Patient.nom_complet.ilike(terme),
                Examen.numero.ilike(terme)
            )
        )
    
    examens = query.order_by(Examen.date_examen.desc()).all()
    
    return render_template(
        'impression/liste.html',
        examens=examens,
        date_filtre=date_str,
        statut_filtre=statut,
        recherche=recherche,
        active_page='resultat'
    )


# ====================================================================
# TÉLÉCHARGEMENT DU PDF
# ====================================================================

@impression_bp.route('/telecharger/<int:examen_id>')
@login_required
def telecharger(examen_id):
    """Génère et télécharge le PDF d'un examen."""
    
    examen = Examen.query.get_or_404(examen_id)
    
    # Vérifier que l'examen a des résultats
    if examen.statut not in ('termine', 'imprime', 'en_cours'):
        flash('Cet examen n\'a pas encore de résultats saisis.', 'warning')
        return redirect(url_for('impression.liste'))
    
    # Générer le PDF en mémoire
    pdf_bytes, erreur = pdf_service.generer_pdf_examen(
        examen_id=examen_id,
        sauvegarder=True  # Sauvegarde aussi sur disque
    )
    
    if erreur:
        flash(f'Erreur : {erreur}', 'danger')
        return redirect(url_for('impression.liste'))
    
    # Si sauvegardé : pdf_bytes contient le chemin
    if isinstance(pdf_bytes, str):
        # Envoyer le fichier depuis le disque
        nom_telechargement = f'{examen.numero}_{examen.patient.nom_complet}.pdf'
        nom_telechargement = nom_telechargement.replace(' ', '_')
        
        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nom_telechargement
        )
    
    # Sinon, c'est des bytes (pas sauvegardé)
    from io import BytesIO
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{examen.numero}.pdf'
    )


# ====================================================================
# APERÇU PDF (dans le navigateur)
# ====================================================================

@impression_bp.route('/apercu/<int:examen_id>')
@login_required
def apercu(examen_id):
    """Affiche le PDF dans le navigateur (sans téléchargement)."""
    
    examen = Examen.query.get_or_404(examen_id)
    
    if examen.statut not in ('termine', 'imprime', 'en_cours'):
        flash('Cet examen n\'a pas encore de résultats saisis.', 'warning')
        return redirect(url_for('impression.liste'))
    
    # Générer en mémoire (sans sauvegarder)
    pdf_bytes, erreur = pdf_service.generer_pdf_examen(
        examen_id=examen_id,
        sauvegarder=False
    )
    
    if erreur:
        flash(f'Erreur : {erreur}', 'danger')
        return redirect(url_for('impression.liste'))
    
    from io import BytesIO
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,  # Affiche dans le navigateur
        download_name=f'{examen.numero}_apercu.pdf'
    )