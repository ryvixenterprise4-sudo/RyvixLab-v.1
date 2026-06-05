"""
Blueprint Patients - gestion des patients du laboratoire.

Routes accessibles aux utilisateurs connectés.
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from flask_login import login_required, current_user
from app.services import patient_service


patient_bp = Blueprint('patient', __name__, url_prefix='/patients')


# ====================================================================
# LISTE / RECHERCHE
# ====================================================================

@patient_bp.route('/')
@login_required
def liste():
    """Liste et recherche des patients."""
    recherche = request.args.get('q', '')
    sexe = request.args.get('sexe', '')
    
    patients = patient_service.lister_patients(
        recherche=recherche,
        sexe=sexe if sexe in ('M', 'F') else None
    )
    
    return render_template(
        'patient/rechpatient.html',
        patients=patients,
        recherche=recherche,
        sexe_filtre=sexe,
        active_page='acceuil'
    )


# ====================================================================
# MODIFICATION
# ====================================================================

@patient_bp.route('/modifier/<int:patient_id>', methods=['POST'])
@login_required
def modifier(patient_id):
    """Modifie un patient existant."""
    patient, erreur = patient_service.modifier_patient(
        patient_id=patient_id,
        nom_complet=request.form.get('nom_complet'),
        date_naissance=request.form.get('date_naissance'),
        lieu_naissance=request.form.get('lieu_naissance'),
        adresse=request.form.get('adresse'),
        sexe=request.form.get('sexe'),
        telephone=request.form.get('telephone'),
        email=request.form.get('email')
    )
    
    if erreur:
        flash(erreur, 'danger')
    else:
        flash(f'Patient "{patient.nom_complet}" modifié.', 'success')
    
    return redirect(url_for('patient.liste'))


# ====================================================================
# SUPPRESSION
# ====================================================================

@patient_bp.route('/supprimer/<int:patient_id>', methods=['POST'])
@login_required
def supprimer(patient_id):
    """Supprime un patient (et tous ses examens)."""
    from app.utils.decorators import admin_required
    
    # Vérification admin (manuelle car on ne peut pas chaîner les décorateurs facilement)
    if not current_user.is_admin():
        flash('Seul un administrateur peut supprimer un patient.', 'danger')
        return redirect(url_for('patient.liste'))
    
    succes, erreur = patient_service.supprimer_patient(patient_id)
    
    if erreur:
        flash(erreur, 'danger')
    else:
        flash('Patient supprimé avec succès.', 'success')
    
    return redirect(url_for('patient.liste'))


# ====================================================================
# API JSON (pour recherche AJAX)
# ====================================================================

@patient_bp.route('/api/recherche')
@login_required
def api_recherche():
    """API de recherche rapide de patients (pour autocomplete)."""
    q = request.args.get('q', '').strip()
    
    if len(q) < 2:
        return jsonify([])
    
    patients = patient_service.lister_patients(recherche=q, limit=10)
    
    return jsonify([{
        'id': p.id,
        'code': p.code,
        'nom_complet': p.nom_complet,
        'date_naissance': p.date_naissance.strftime('%d/%m/%Y') if p.date_naissance else None,
        'sexe': p.sexe,
        'adresse': p.adresse,
        'telephone': p.telephone
    } for p in patients])