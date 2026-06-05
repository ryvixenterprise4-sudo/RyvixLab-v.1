"""
Blueprint Examens - enregistrement et gestion des examens (visites).
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from flask_login import login_required, current_user

from app.services import examen_service, patient_service, analyse_service


examen_bp = Blueprint('examen', __name__, url_prefix='/examens')


# ====================================================================
# ENREGISTREMENT (Page principale)
# ====================================================================

@examen_bp.route('/enregistrement', methods=['GET', 'POST'])
@login_required
def enregistrement():
    """
    Page d'enregistrement : créer un patient + sélectionner ses analyses.
    
    Si ?patient_id=X est passé en URL, le patient est pré-sélectionné.
    """
    
    if request.method == 'POST':
        # Étape 1 : Créer ou récupérer le patient
        patient_id = request.form.get('patient_id', '').strip()
        
        if patient_id and patient_id.isdigit():
            # Patient existant
            patient = patient_service.trouver_patient(int(patient_id))
            if not patient:
                flash('Patient sélectionné introuvable.', 'danger')
                return redirect(url_for('examen.enregistrement'))
        else:
            # Nouveau patient
            patient, erreur = patient_service.creer_patient(
                nom_complet=request.form.get('nom_complet'),
                date_naissance=request.form.get('date_naissance'),
                lieu_naissance=request.form.get('lieu_naissance'),
                adresse=request.form.get('adresse'),
                sexe=request.form.get('sexe'),
                telephone=request.form.get('telephone'),
                user_id=current_user.id
            )
            if erreur:
                flash(erreur, 'danger')
                return redirect(url_for('examen.enregistrement'))
        
        # Étape 2 : Récupérer les analyses sélectionnées
        analyse_ids_str = request.form.getlist('analyses')
        try:
            analyse_ids = [int(x) for x in analyse_ids_str if x.isdigit()]
        except ValueError:
            analyse_ids = []
        
        if not analyse_ids:
            flash('Veuillez sélectionner au moins une analyse.', 'warning')
            return redirect(url_for('examen.enregistrement'))
        
        # Étape 3 : Créer l'examen
        examen, erreur = examen_service.creer_examen(
            patient_id=patient.id,
            analyse_ids=analyse_ids,
            user_id=current_user.id,
            medecin_prescripteur=request.form.get('medecin_prescripteur'),
            notes=request.form.get('notes')
        )
        
        if erreur:
            flash(erreur, 'danger')
            return redirect(url_for('examen.enregistrement'))
        
        flash(
            f'✅ Examen {examen.numero} enregistré pour {patient.nom_complet} - Total : {examen.total} HTG',
            'success'
        )
        return redirect(url_for('examen.enregistrement'))
    
    # ===== GET : afficher le formulaire =====
    
    # 🆕 Récupérer le patient pré-sélectionné depuis l'URL (?patient_id=X)
    patient_preselect = None
    patient_id_url = request.args.get('patient_id', '').strip()
    
    if patient_id_url and patient_id_url.isdigit():
        patient_preselect = patient_service.trouver_patient(int(patient_id_url))
        if not patient_preselect:
            flash('Patient introuvable.', 'warning')
    
    analyses = analyse_service.lister_analyses(inclure_inactives=False)
    
    return render_template(
        'patient/enregistrement.html',
        analyses=analyses,
        patient_preselect=patient_preselect,  # nouveau paramètre pour pré-sélection
        active_page='acceuil'
    )

# ====================================================================
# API JSON
# ====================================================================

@examen_bp.route('/api/calcul-total', methods=['POST'])
@login_required
def api_calcul_total():
    """Calcule le total pour les analyses sélectionnées (AJAX)."""
    data = request.get_json() or {}
    analyse_ids = data.get('analyse_ids', [])
    
    try:
        analyse_ids = [int(x) for x in analyse_ids]
    except (ValueError, TypeError):
        return jsonify({'total': 0, 'erreur': 'IDs invalides'}), 400
    
    total = examen_service.calculer_total(analyse_ids)
    
    return jsonify({
        'total': float(total),
        'total_formate': '{:,.2f} HTG'.format(total)
    })