"""
Factory pattern - point d'entrée de l'application.
"""

import os
import click
from flask import Flask
from app.config import config
from app.extensions import db, migrate, login_manager, bcrypt, csrf


def create_app(config_name=None):
    """Construit l'application Flask."""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # Configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    
    # Import des modèles (pour Flask-Migrate)
    from app import models  # noqa: F401
    
    # ===== ENREGISTREMENT DES BLUEPRINTS =====
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.analyse import analyse_bp
    from app.routes.patient import patient_bp
    from app.routes.examen import examen_bp
    from app.routes.resultat import resultat_bp

    
    app.register_blueprint(patient_bp)
    app.register_blueprint(examen_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(analyse_bp)
    app.register_blueprint(resultat_bp)
    
    # ===== COMMANDES CLI PERSONNALISÉES =====
    register_cli_commands(app)
    
    return app


def register_cli_commands(app):
    """Enregistre les commandes Flask CLI personnalisées."""
    
    @app.cli.command('create-admin')
    @click.option('--username', prompt='Nom d\'utilisateur')
    @click.option('--email', prompt='Email')
    @click.option('--password', prompt='Mot de passe', hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):
        """Crée le premier utilisateur administrateur."""
        from app.models import User
        
        # Vérifications
        if User.query.filter_by(username=username).first():
            click.echo(f'❌ L\'utilisateur "{username}" existe déjà.')
            return
        
        if User.query.filter_by(email=email).first():
            click.echo(f'❌ L\'email "{email}" est déjà utilisé.')
            return
        
        if len(password) < 6:
            click.echo('❌ Le mot de passe doit avoir au moins 6 caractères.')
            return
        
        # Création
        admin = User(
            username=username,
            email=email.lower(),
            role='administrateur',
            actif=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'\n✅ Administrateur "{username}" créé avec succès !')
        click.echo(f'📧 Email : {email}')
        click.echo(f'🔑 Vous pouvez maintenant vous connecter.\n')
    
    @app.cli.command('list-users')
    def list_users():
        """Liste tous les utilisateurs."""
        from app.models import User
        users = User.query.all()
        if not users:
            click.echo('Aucun utilisateur trouvé.')
            return
        click.echo('\n📋 Liste des utilisateurs :')
        click.echo('-' * 70)
        for u in users:
            status = '✅' if u.actif else '❌'
            click.echo(f'{status} {u.username:20} | {u.email:30} | {u.role}')
        click.echo('-' * 70)
    
    @app.cli.command('db-check')
    def db_check():
        """Vérifie la connexion à la BD et liste les tables."""
        from sqlalchemy import inspect
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            click.echo(f'\n✅ Connexion réussie à la base de données')
            click.echo(f'📊 Tables trouvées : {len(tables)}')
            for table in tables:
                click.echo(f'   • {table}')
        except Exception as e:
            click.echo(f'\n❌ Erreur : {e}')