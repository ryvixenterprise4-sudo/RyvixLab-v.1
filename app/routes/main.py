"""
Blueprint principal - pages de l'application.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

from app.utils.decorators import admin_required


main_bp = Blueprint('main', __name__)


# ====================================================================
# ACCUEIL
# ====================================================================

@main_bp.route('/acceuil')
@login_required
def acceuil():
    """Page d'accueil après connexion."""
    return render_template('acceuil.html', active_page='acceuil')


# ====================================================================
# PLACEHOLDERS POUR LES PROCHAINES ÉTAPES
# ====================================================================

@main_bp.route('/enregistrement')
@login_required
def enregistrement():
    """Redirige vers le module examen."""
    return redirect(url_for('examen.enregistrement'))



@main_bp.route('/resultat')
@login_required
def resultat():
    """Redirige vers le module résultat."""
    return redirect(url_for('resultat.liste'))


@main_bp.route('/rapport')
@login_required
def rapport():
    """Rapports (à implémenter)."""
    return render_template('placeholder.html',
                           titre='Rapport',
                           active_page='rapport')


@main_bp.route('/tableau')
@login_required
def tableau():
    """Tableau de bord (à implémenter)."""
    return render_template('placeholder.html',
                           titre='Tableau de bord',
                           active_page='tableau')


@main_bp.route('/ajout-analyse')
@login_required
@admin_required
def ajout_analyse():
    """Redirige vers la vraie route du blueprint analyse."""
    return redirect(url_for('analyse.ajout_analyse'))

# @main_bp.route('/ajout-analyse')
# @login_required
# @admin_required
# def ajout_analyse():
#     """Ajout d'analyses (admin only)."""
#     return render_template('placeholder.html',
#                            titre='Ajouter des Analyses',
#                            active_page='acceuil')




@main_bp.route('/rech-patient')
@login_required
def rech_patient():
    """Redirige vers le module patient."""
    return redirect(url_for('patient.liste'))




@main_bp.route('/paramettre')
@login_required
@admin_required
def paramettre():
    """Paramètres App (admin only)."""
    return render_template('placeholder.html',
                           titre='Paramètres',
                           active_page='paramettre')