"""
Blueprint Configuration Laboratoire - paramètres pour les PDFs.
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash
)
from flask_login import login_required, current_user

from app.utils.decorators import admin_required
from app.services import laboratoire_service


laboratoire_bp = Blueprint('laboratoire', __name__, url_prefix='/laboratoire')


@laboratoire_bp.route('/', methods=['GET', 'POST'])
@login_required
@admin_required
def configuration():
    """Page de configuration du laboratoire."""
    
    if request.method == 'POST':
        config, erreur = laboratoire_service.mettre_a_jour_config(
            data=request.form,
            fichiers=request.files
        )
        
        if erreur:
            flash(erreur, 'danger')
        else:
            flash('✅ Configuration du laboratoire mise à jour.', 'success')
            return redirect(url_for('laboratoire.configuration'))
    
    config = laboratoire_service.obtenir_config()
    
    return render_template(
        'laboratoire/configuration.html',
        config=config,
        active_page='paramettre'
    )