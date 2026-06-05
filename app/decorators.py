"""
Décorateurs personnalisés pour les routes Flask.

Un décorateur enveloppe une fonction pour y ajouter un comportement
avant ou après son exécution, sans modifier la fonction elle-même.

Flask-Login fournit @login_required.
On ajoute @admin_required sur le même modèle.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """
    Bloque l'accès (HTTP 403) si l'utilisateur connecté n'est pas administrateur.

    Utilise la méthode is_admin() définie dans le modèle User :
        def is_admin(self):
            return self.role == 'administrateur'

    Toujours placer @login_required AU-DESSUS de @admin_required,
    sinon current_user est un utilisateur anonyme et is_admin() plante.

        @route('/register')
        @login_required    ← vérifié en premier
        @admin_required    ← vérifié ensuite
        def register(): ...

    @wraps(f) préserve le __name__ de la fonction originale,
    indispensable pour que Flask identifie les routes sans conflit.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # is_authenticated est False pour les utilisateurs anonymes (AnonymousUser).
        # is_admin() est défini dans app/models/user.py.
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
