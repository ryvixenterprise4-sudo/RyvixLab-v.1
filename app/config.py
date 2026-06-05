"""
Configuration de l'application RyvixLab.
Trois environnements : Development, Testing, Production.
Base de données : PostgreSQL pour tous les environnements.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Chargement des variables depuis le fichier .env
load_dotenv()

# Chemin absolu du dossier racine du projet
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """
    Configuration de base commune à tous les environnements.
    Les autres classes héritent de celle-ci.
    """
    
    # ========== SÉCURITÉ ==========
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cle-par-defaut-a-changer'
    
    # ========== BASE DE DONNÉES ==========
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Désactive un avertissement inutile
    SQLALCHEMY_RECORD_QUERIES = True        # Permet de logger les requêtes lentes
    
    # Pool de connexions PostgreSQL (gestion optimale des connexions)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,           # Nombre de connexions simultanées
        'pool_recycle': 3600,      # Recyclage des connexions toutes les heures
        'pool_pre_ping': True,     # Vérifie que la connexion est vivante avant utilisation
    }
    
    # ========== SESSIONS ==========
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 8))
    )
    SESSION_COOKIE_HTTPONLY = True   # Cookies inaccessibles en JavaScript (anti-XSS)
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protection contre les attaques CSRF
    
    # ========== UPLOAD DE FICHIERS ==========
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Mo maximum par fichier
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    PDF_OUTPUT_FOLDER = os.environ.get(
        'PDF_OUTPUT_FOLDER',
        os.path.join(BASE_DIR, 'app', 'static', 'pdf_generated')
    )
    
    # ========== APPLICATION ==========
    APP_NAME = 'RyvixLab'
    APP_VERSION = '1.0.0'
    LANGUAGE = 'fr'
    CURRENCY = 'HTG'
    
    # ========== PAGINATION ==========
    ITEMS_PER_PAGE = 20  # Nombre d'éléments par page (listes patients, analyses, etc.)
    
    @staticmethod
    def init_app(app):
        """Méthode appelée à l'initialisation de l'app. Surchargée dans les sous-classes."""
        # Création des dossiers nécessaires s'ils n'existent pas
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.PDF_OUTPUT_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Configuration pour le développement local (PostgreSQL)."""
    
    DEBUG = True
    TESTING = False
    
    # PostgreSQL obligatoire en développement
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL')
    
    # Affiche les requêtes SQL dans le terminal (utile pour débugger)
    SQLALCHEMY_ECHO = True
    
    # Sessions plus permissives en dev
    SESSION_COOKIE_SECURE = False  # Pas besoin de HTTPS en local
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Vérification : DEV_DATABASE_URL doit être défini
        if not os.environ.get('DEV_DATABASE_URL'):
            raise ValueError(
                '\n⚠️ ERREUR DE CONFIGURATION\n'
                'DEV_DATABASE_URL doit être défini dans le fichier .env\n'
                'Format attendu : postgresql://user:password@localhost:5432/ryvixlab_dev\n'
            )
        
        print('🔧 Mode DÉVELOPPEMENT activé (PostgreSQL)')


class TestingConfig(Config):
    """Configuration pour les tests automatisés (PostgreSQL)."""
    
    DEBUG = False
    TESTING = True
    
    # Base de données dédiée aux tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')
    
    # Désactive la protection CSRF pendant les tests
    WTF_CSRF_ENABLED = False
    
    # Hash bcrypt plus rapide en test
    BCRYPT_LOG_ROUNDS = 4
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        if not os.environ.get('TEST_DATABASE_URL'):
            raise ValueError(
                '\n⚠️ ERREUR DE CONFIGURATION\n'
                'TEST_DATABASE_URL doit être défini dans le fichier .env\n'
                'Format attendu : postgresql://user:password@localhost:5432/ryvixlab_test\n'
            )
        
        print('🧪 Mode TESTS activé (PostgreSQL)')


class ProductionConfig(Config):
    """Configuration pour la production (serveur réel)."""
    
    DEBUG = False
    TESTING = False
    
    # Base de données PostgreSQL obligatoire en production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Sécurité maximale
    SESSION_COOKIE_SECURE = True   # Cookies UNIQUEMENT en HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Hash bcrypt plus fort en production
    BCRYPT_LOG_ROUNDS = 13
    
    # Pool de connexions optimisé pour la production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 10,
    }
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Vérifications critiques pour la production
        if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'cle-par-defaut-a-changer':
            raise ValueError(
                '\n⚠️ ERREUR CRITIQUE\n'
                'SECRET_KEY doit être défini avec une vraie clé en production\n'
                'Générez une clé : python -c "import secrets; print(secrets.token_hex(32))"\n'
            )
        
        if not os.environ.get('DATABASE_URL'):
            raise ValueError(
                '\n⚠️ ERREUR CRITIQUE\n'
                'DATABASE_URL doit être défini dans .env en production\n'
                'Format : postgresql://user:password@host:5432/ryvixlab_prod\n'
            )
        
        print('🚀 Mode PRODUCTION activé (PostgreSQL)')


# ========== DICTIONNAIRE DE SÉLECTION ==========
# Permet de récupérer la bonne config par son nom
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}