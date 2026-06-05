"""Modèle Analyse - services proposés par le laboratoire."""

from datetime import datetime
from sqlalchemy import CheckConstraint
from app.extensions import db


class Analyse(db.Model):
    """Service d'analyse (ex: Hépatite B, URINES, Bilan Thyroïdien)."""
    
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True, index=True)
    service = db.Column(db.String(100), index=True)  # Catégorie/Service
    description = db.Column(db.Text)
    prix = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Contrainte : prix non négatif
    __table_args__ = (
        CheckConstraint('prix >= 0', name='check_analyse_prix_positif'),
    )
    
    # ===== RELATIONS =====
    parametres = db.relationship(
        'Parametre',
        backref='analyse',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Parametre.ordre'
    )
    
    @property
    def nombre_parametres(self):
        """Nombre de paramètres associés à cette analyse."""
        return self.parametres.count()
    
    def __repr__(self):
        return f'<Analyse {self.nom} - {self.prix} HTG>'