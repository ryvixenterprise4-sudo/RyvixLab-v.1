"""Modèle Utilisateur - comptes du système."""

from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
from app.extensions import db, bcrypt, login_manager


class User(UserMixin, db.Model):
    """Utilisateur de l'application (Adema, Emeline, etc.)."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Rôle : 'standard' ou 'administrateur'
    role = db.Column(db.String(20), nullable=False, default='standard')
    
    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    derniere_connexion = db.Column(db.DateTime)
    
    # Contraintes au niveau base de données
    __table_args__ = (
        CheckConstraint(
            "role IN ('standard', 'administrateur')",
            name='check_user_role'
        ),
    )
    
    # ===== RELATIONS =====
    patients_crees = db.relationship(
        'Patient',
        backref='createur',
        lazy='dynamic',
        foreign_keys='Patient.created_by'
    )
    examens = db.relationship(
        'Examen',
        backref='operateur',
        lazy='dynamic',
        foreign_keys='Examen.created_by'
    )
    resultats_saisis = db.relationship(
        'Resultat',
        backref='saisisseur',
        lazy='dynamic',
        foreign_keys='Resultat.saisi_par'
    )
    
    # ===== MÉTHODES =====
    def set_password(self, password):
        """Hash le mot de passe avec bcrypt."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Vérifie si le mot de passe correspond."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Vérifie si l'utilisateur est administrateur."""
        return self.role == 'administrateur'
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur depuis son ID (requis par Flask-Login)."""
    return User.query.get(int(user_id))