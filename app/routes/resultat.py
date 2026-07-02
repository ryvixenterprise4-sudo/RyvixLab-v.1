"""
Blueprint Résultats - saisie des résultats d'analyses par le laborantin.
"""

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from flask_login import login_required, current_user

from app.services import resultat_service


resultat_bp = Blueprint('resultat', __name__, url_prefix='/resultats')


# ====================================================================
# LISTE DES EXAMENS À TRAITER
# ====================================================================

@resultat_bp.route('/')
@login_required
def liste():
    """Liste des examens en attente de saisie."""
    
    # Filtre par date (optionnel)
    date_str = request.args.get('date', '')
    date_filtre = None
    if date_str:
        try:
            date_filtre = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Filtre par statut
    statut = request.args.get('statut', '')
    
    # Recherche
    recherche = request.args.get('q', '')
    
    examens = resultat_service.lister_examens_a_traiter(
        date_filtre=date_filtre,
        recherche=recherche,
        statut=statut if statut in ('en_attente', 'en_cours') else None
    )
    
    # Statistiques
    stats = resultat_service.compter_examens_par_statut()
    
    return render_template(
        'resultat/liste_examens.html',
        examens=examens,
        date_filtre=date_str,
        statut_filtre=statut,
        recherche=recherche,
        stats=stats,
        active_page='resultat'
    )


# ====================================================================
# SAISIE DES RÉSULTATS POUR UN EXAMEN
# ====================================================================

@resultat_bp.route('/saisie/<int:examen_id>', methods=['GET', 'POST'])
@login_required
def saisie(examen_id):
    """Page de saisie des résultats pour un examen."""
    
    if request.method == 'POST':
        # Récupérer toutes les valeurs du formulaire
        # Format : resultat_<detail_id>_<parametre_id> = valeur
        resultats_data = []
        
        for key, valeur in request.form.items():
            if key.startswith('resultat_'):
                parts = key.split('_')
                if len(parts) == 3:
                    detail_id = parts[1]
                    parametre_id = parts[2]
                    
                    # Récupérer le commentaire associé si présent
                    comment_key = f'commentaire_{detail_id}_{parametre_id}'
                    commentaire = request.form.get(comment_key, '')
                    
                    resultats_data.append({
                        'examen_detail_id': detail_id,
                        'parametre_id': parametre_id,
                        'valeur': valeur,
                        'commentaire': commentaire
                    })
        
        preleve_par = (request.form.get('preleve_par') or '').strip()

        # Sauvegarder
        nb, erreur = resultat_service.sauvegarder_resultats(
            examen_id=examen_id,
            resultats_data=resultats_data,
            user_id=current_user.id,
            preleve_par=preleve_par
        )
        
        if erreur:
            flash(erreur, 'danger')
        else:
            if nb == 0:
                flash('Aucune valeur saisie.', 'warning')
            else:
                flash(f'✅ {nb} résultat(s) enregistré(s).', 'success')
        
        # Recharger la même page pour voir le résultat
        return redirect(url_for('resultat.saisie', examen_id=examen_id))
    
    # GET : afficher le formulaire
    donnees = resultat_service.obtenir_examen_complet(examen_id)
    
    if not donnees:
        flash('Examen introuvable.', 'danger')
        return redirect(url_for('resultat.liste'))
    
    return render_template(
        'resultat/saisie_resultats.html',
        donnees=donnees,
        active_page='resultat'
    )


# ====================================================================
# API JSON
# ====================================================================

@resultat_bp.route('/api/parametres/<int:detail_id>')
@login_required
def api_parametres(detail_id):
    """Retourne les paramètres et valeurs prédéfinies d'un examen_detail."""
    from app.models import ExamenDetail, Parametre
    
    detail = ExamenDetail.query.get(detail_id)
    if not detail:
        return jsonify({'erreur': 'Détail introuvable'}), 404
    
    parametres = Parametre.query.filter_by(
        analyse_id=detail.analyse_id
    ).order_by(Parametre.ordre).all()
    
    return jsonify([{
        'id': p.id,
        'nom': p.nom_parametre,
        'sous_parametre': p.sous_parametre,
        'unite': p.unite,
        'type_resultat': p.type_resultat,
        'valeur_normale_f': p.valeur_normale_f,
        'valeur_normale_m': p.valeur_normale_m,
        'valeurs_predefinies': [vp.valeur for vp in p.valeurs_predefinies.all()]
    } for p in parametres])