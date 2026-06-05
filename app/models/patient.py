"""Modèle Patient - patients du laboratoire."""

from datetime import datetime
from sqlalchemy import CheckConstraint, Index
from app.extensions import db


class Patient(db.Model):
    """Patient enregistré au laboratoire."""
    
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nom_complet = db.Column(db.String(150), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    adresse = db.Column(db.String(255))
    
    # Sexe : 'M' ou 'F'
    sexe = db.Column(db.String(1))
    
    telephone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    notes = db.Column(db.Text)
    
    # Audit
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Contraintes
    __table_args__ = (
        CheckConstraint("sexe IN ('M', 'F') OR sexe IS NULL", name='check_patient_sexe'),
        # Index composite pour recherches rapides nom + date
        Index('idx_patient_nom_date', 'nom_complet', 'date_creation'),
    )
    
    # ===== RELATIONS =====
    examens = db.relationship(
        'Examen',
        backref='patient',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    # ===== PROPRIÉTÉS UTILES =====
    @property
    def age(self):
        """Calcule l'âge actuel du patient."""
        if not self.date_naissance:
            return None
        today = datetime.now().date()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )
    
    @property
    def nombre_visites(self):
        """Compte le nombre total de visites du patient."""
        return self.examens.count()
    
    def __repr__(self):
        return f'<Patient {self.code} - {self.nom_complet}>'