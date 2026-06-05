"""
Modèle Examen - visite d'un patient au laboratoire.

Une "Examen" = la venue d'un patient avec les analyses demandées.
Anciennement nommé "Commande" - renommé pour cohérence avec
le vocabulaire médical.
"""

from datetime import datetime
from sqlalchemy import CheckConstraint
from app.extensions import db


class Examen(db.Model):
    """Visite d'un patient avec ses analyses demandées."""
    
    __tablename__ = 'examens'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Numéro unique lisible (ex: EX-2026-0001)
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey('patients.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    date_examen = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    total = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Statut : 'en_attente', 'en_cours', 'termine', 'imprime', 'annule'
    statut = db.Column(db.String(20), default='en_attente', nullable=False, index=True)
    
    # Médecin prescripteur (optionnel)
    medecin_prescripteur = db.Column(db.String(150))
    
    # Notes du laborantin
    notes = db.Column(db.Text)
    
    # Audit
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Contraintes
    __table_args__ = (
        CheckConstraint(
            "statut IN ('en_attente', 'en_cours', 'termine', 'imprime', 'annule')",
            name='check_examen_statut'
        ),
        CheckConstraint('total >= 0', name='check_examen_total_positif'),
    )
    
    # ===== RELATIONS =====
    details = db.relationship(
        'ExamenDetail',
        backref='examen',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    paiements = db.relationship(
        'JournalCaisse',
        backref='examen',
        lazy='dynamic'
    )
    
    # ===== PROPRIÉTÉS =====
    @property
    def nombre_analyses(self):
        """Nombre d'analyses dans cet examen."""
        return self.details.count()
    
    @property
    def montant_paye(self):
        """Total déjà payé par le patient."""
        from sqlalchemy import func
        result = db.session.query(
            func.coalesce(func.sum(JournalCaisse.montant), 0)
        ).filter_by(examen_id=self.id, type_operation='encaissement').scalar()
        return result or 0
    
    @property
    def solde_restant(self):
        """Montant restant à payer."""
        return float(self.total) - float(self.montant_paye)
    
    def __repr__(self):
        return f'<Examen {self.numero} - {self.statut}>'


class ExamenDetail(db.Model):
    """Ligne de détail d'un examen (une analyse demandée)."""
    
    __tablename__ = 'examen_details'
    
    id = db.Column(db.Integer, primary_key=True)
    examen_id = db.Column(
        db.Integer,
        db.ForeignKey('examens.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    analyse_id = db.Column(
        db.Integer,
        db.ForeignKey('analyses.id'),
        nullable=False
    )
    
    # Snapshot du prix au moment de la commande
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
    
    acheve = db.Column(db.Boolean, default=False, nullable=False)
    date_achevement = db.Column(db.DateTime)
    
    # Contraintes
    __table_args__ = (
        CheckConstraint('prix_unitaire >= 0', name='check_detail_prix_positif'),
    )
    
    # ===== RELATIONS =====
    analyse = db.relationship('Analyse')
    resultats = db.relationship(
        'Resultat',
        backref='examen_detail',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<ExamenDetail #{self.id}>'


# Import en bas pour éviter import circulaire
from app.models.journal_caisse import JournalCaisse