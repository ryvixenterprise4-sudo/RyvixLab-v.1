"""
Blueprint Analyses - gestion des services proposés par le laboratoire
et de leurs paramètres mesurables.

 Ces routes sont réservées aux ADMINISTRATEURS.
"""


from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from flask_login import login_required

from app.utils.decorators import admin_required
from app.services import analyse_service
from app.models import Analyse, Parametre


analyse_bp = Blueprint('analyse', __name__, url_prefix='/analyses')


# ====================================================================
# AJOUT D'ANALYSES (inchangé - garder votre code)
# ====================================================================

@analyse_bp.route('/ajout', methods=['GET', 'POST'])
@login_required
@admin_required
def ajout_analyse():
    if request.method == 'POST':
        analyse, erreur = analyse_service.creer_analyse(
            nom=request.form.get('nom'),
            service=request.form.get('service'),
            prix=request.form.get('prix'),
            description=request.form.get('description', '')
        )
        if erreur:
            flash(erreur, 'danger')
        else:
            flash(f'Analyse "{analyse.nom}" ajoutée.', 'success')
            return redirect(url_for('analyse.ajout_analyse'))
    
    recherche = request.args.get('q', '')
    analyses = analyse_service.lister_analyses(
        recherche=recherche, inclure_inactives=True
    )
    return render_template(
        'analyse/ajoutanalyse.html',
        analyses=analyses,
        recherche=recherche,
        active_page='acceuil'
    )


@analyse_bp.route('/modifier/<int:analyse_id>', methods=['POST'])
@login_required
@admin_required
def modifier_analyse(analyse_id):
    analyse, erreur = analyse_service.modifier_analyse(
        analyse_id=analyse_id,
        nom=request.form.get('nom'),
        service=request.form.get('service'),
        prix=request.form.get('prix'),
        description=request.form.get('description', '')
    )
    if erreur:
        flash(erreur, 'danger')
    else:
        flash(f'Analyse "{analyse.nom}" modifiée.', 'success')
    return redirect(url_for('analyse.ajout_analyse'))


@analyse_bp.route('/supprimer/<int:analyse_id>', methods=['POST'])
@login_required
@admin_required
def supprimer_analyse(analyse_id):
    succes, erreur = analyse_service.supprimer_analyse(analyse_id)
    if erreur:
        flash(erreur, 'danger')
    else:
        flash('Analyse désactivée.', 'success')
    return redirect(url_for('analyse.ajout_analyse'))

# activation d'une analyse désactivée
@analyse_bp.route('/activer/<int:analyse_id>', methods=['POST'])
@login_required
@admin_required
def activer_analyse(analyse_id):
    succes, erreur = analyse_service.activer_analyse(analyse_id)
    if erreur:
        flash(erreur, 'danger')
    else:
        flash('Analyse activée.', 'success')
    return redirect(url_for('analyse.ajout_analyse'))

# ====================================================================
# CONFIGURATION DES PARAMÈTRES - MIS À JOUR
# ====================================================================

@analyse_bp.route('/configuration', methods=['GET', 'POST'])
@login_required
@admin_required
def configuration():
    """Page de configuration des paramètres des analyses."""
    
    if request.method == 'POST':
        try:
            analyse_id = int(request.form.get('analyse_id', 0))
        except (ValueError, TypeError):
            flash('Analyse invalide.', 'danger')
            return redirect(url_for('analyse.configuration'))
        
        # Type de résultat et valeurs prédéfinies
        type_resultat = request.form.get('type_resultat', 'numerique')
        valeurs_predefinies = None
        
        if type_resultat == 'liste':
            # Récupérer la liste de valeurs (séparées par |)
            valeurs_str = request.form.get('valeurs_predefinies', '')
            valeurs_predefinies = [
                v.strip() for v in valeurs_str.split('|') if v.strip()
            ]
        
        parametre, erreur = analyse_service.creer_parametre(
            analyse_id=analyse_id,
            nom_parametre=request.form.get('nom_parametre'),
            sous_parametre=request.form.get('sous_parametre'),
            unite=request.form.get('unite'),
            valeur_normale_f=request.form.get('valeur_normale_f'),
            valeur_normale_m=request.form.get('valeur_normale_m'),
            valeur_normale_enfant=request.form.get('valeur_normale_enfant'),
            type_resultat=type_resultat,
            valeurs_predefinies=valeurs_predefinies
        )
        
        if erreur:
            flash(erreur, 'danger')
        else:
            flash(f'Paramètre "{parametre.nom_parametre}" ajouté.', 'success')
            return redirect(url_for('analyse.configuration'))
    
    analyses = analyse_service.lister_analyses(inclure_inactives=False)
    parametres = analyse_service.lister_parametres()
    
    return render_template(
        'analyse/ajoutlab.html',
        analyses=analyses,
        parametres=parametres,
        active_page='acceuil'
    )


@analyse_bp.route('/parametre/modifier/<int:parametre_id>', methods=['POST'])
@login_required
@admin_required
def modifier_parametre(parametre_id):
    """Modifie un paramètre existant."""
    
    type_resultat = request.form.get('type_resultat', 'numerique')
    valeurs_predefinies = None
    
    if type_resultat == 'liste':
        valeurs_str = request.form.get('valeurs_predefinies', '')
        valeurs_predefinies = [
            v.strip() for v in valeurs_str.split('|') if v.strip()
        ]
    
    parametre, erreur = analyse_service.modifier_parametre(
        parametre_id=parametre_id,
        nom_parametre=request.form.get('nom_parametre'),
        sous_parametre=request.form.get('sous_parametre'),
        unite=request.form.get('unite'),
        valeur_normale_f=request.form.get('valeur_normale_f'),
        valeur_normale_m=request.form.get('valeur_normale_m'),
        valeur_normale_enfant=request.form.get('valeur_normale_enfant'),
        type_resultat=type_resultat,
        valeurs_predefinies=valeurs_predefinies
    )
    
    if erreur:
        flash(erreur, 'danger')
    else:
        flash('Paramètre modifié avec succès.', 'success')
    
    return redirect(url_for('analyse.configuration'))


@analyse_bp.route('/parametre/supprimer/<int:parametre_id>', methods=['POST'])
@login_required
@admin_required
def supprimer_parametre(parametre_id):
    succes, erreur = analyse_service.supprimer_parametre(parametre_id)
    if erreur:
        flash(erreur, 'danger')
    else:
        flash('Paramètre supprimé.', 'success')
    return redirect(url_for('analyse.configuration'))


# ====================================================================
# API JSON
# ====================================================================

@analyse_bp.route('/api/parametres/<int:analyse_id>')
@login_required
def api_parametres_analyse(analyse_id):
    parametres = Parametre.query.filter_by(analyse_id=analyse_id)\
        .order_by(Parametre.ordre).all()
    
    return jsonify([{
        'id': p.id,
        'nom_parametre': p.nom_parametre,
        'sous_parametre': p.sous_parametre,
        'unite': p.unite,
        'valeur_normale_f': p.valeur_normale_f,
        'valeur_normale_m': p.valeur_normale_m,
        'valeur_normale_enfant': p.valeur_normale_enfant,
        'type_resultat': p.type_resultat,
        'valeurs_predefinies': [v.valeur for v in p.valeurs_predefinies]
    } for p in parametres])
