"""
Blueprint d'authentification.

Routes :
    GET  /              → Page de connexion
    POST /login         → Traitement du formulaire de connexion
    GET  /logout        → Déconnexion
    GET  /register      → Page création de compte (admin only)
    POST /register      → Traitement création de compte (admin only)
"""

from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User
from app.utils.decorators import admin_required


# Création du blueprint
auth_bp = Blueprint('auth', __name__)


# ====================================================================
# CONNEXION
# ====================================================================

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion."""
    
    # Si déjà connecté, redirection vers l'accueil
    if current_user.is_authenticated:
        return redirect(url_for('main.acceuil'))
    
    if request.method == 'POST':
        # Récupération des champs du formulaire HTML
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validation basique
        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'warning')
            return render_template('auth/index.html')
        
        # Recherche de l'utilisateur (par username OU email)
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        # Vérification : utilisateur existe + actif + mot de passe correct
        if user is None or not user.check_password(password):
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
            return render_template('auth/index.html')
        
        if not user.actif:
            flash('Ce compte a été désactivé. Contactez l\'administrateur.', 'danger')
            return render_template('auth/index.html')
        
        # Connexion réussie
        login_user(user, remember=False)
        
        # Mise à jour de la dernière connexion
        user.derniere_connexion = datetime.utcnow()
        db.session.commit()
        
        flash(f'Bienvenue, {user.username} !', 'success')
        
        # Redirection vers la page demandée initialement OU vers acceuil
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):  # Sécurité : URL relative uniquement
            return redirect(next_page)
        
        return redirect(url_for('main.acceuil'))
    
    # GET : afficher le formulaire
    return render_template('auth/index.html')


# ====================================================================
# DÉCONNEXION
# ====================================================================

@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    username = current_user.username
    logout_user()
    flash(f'À bientôt, {username} !', 'info')
    return redirect(url_for('auth.login'))


# ====================================================================
# CRÉATION DE COMPTE (ADMIN UNIQUEMENT)
# ====================================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    """
    Création d'un nouveau compte utilisateur.
    Réservée aux administrateurs.
    """
    
    if request.method == 'POST':
        # Récupération des champs
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirmation = request.form.get('confirmation', '')
        role = request.form.get('role', 'standard').lower()
        
        # ===== VALIDATIONS =====
        erreurs = []
        
        if not username or len(username) < 3:
            erreurs.append('Le nom d\'utilisateur doit avoir au moins 3 caractères.')
        
        if not email or '@' not in email:
            erreurs.append('Email invalide.')
        
        if not password or len(password) < 6:
            erreurs.append('Le mot de passe doit avoir au moins 6 caractères.')
        
        if password != confirmation:
            erreurs.append('Les mots de passe ne correspondent pas.')
        
        if role not in ('standard', 'administrateur'):
            erreurs.append('Type de compte invalide.')
        
        # Unicité : username
        if User.query.filter_by(username=username).first():
            erreurs.append('Ce nom d\'utilisateur est déjà pris.')
        
        # Unicité : email
        if User.query.filter_by(email=email).first():
            erreurs.append('Cet email est déjà utilisé.')
        
        # Si erreurs, on affiche et on garde les valeurs saisies
        if erreurs:
            for err in erreurs:
                flash(err, 'danger')
            return render_template(
                'auth/compte2.html',
                username=username,
                email=email,
                role=role
            )
        
        # ===== CRÉATION DU COMPTE =====
        nouveau_user = User(
            username=username,
            email=email,
            role=role,
            actif=True
        )
        nouveau_user.set_password(password)
        
        db.session.add(nouveau_user)
        db.session.commit()
        
        flash(
            f'Compte "{username}" créé avec succès ({role}).',
            'success'
        )
        return redirect(url_for('main.acceuil'))
    
    # GET : afficher le formulaire
    return render_template('auth/compte2.html')