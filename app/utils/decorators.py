"""
Décorateurs personnalisés pour RyvixLab.

@admin_required : restreint l'accès aux administrateurs uniquement.
Doit être utilisé APRÈS @login_required.
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """
    Décorateur qui exige que l'utilisateur soit administrateur.
    
    Usage :
        @app.route('/admin-only')
        @login_required
        @admin_required
        def vue_admin():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            flash('Accès refusé. Cette page est réservée aux administrateurs.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    
    return decorated_function