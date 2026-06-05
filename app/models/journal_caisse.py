"""Modèle Journal de Caisse - mouvements financiers."""

from datetime import datetime
from sqlalchemy import CheckConstraint
from app.extensions import db


class JournalCaisse(db.Model):
    """Mouvement financier (encaissement, remboursement, dépense)."""
    
    __tablename__ = 'journal_caisse'
    
    id = db.Column(db.Integer, primary_key=True)
    examen_id = db.Column(
        db.Integer,
        db.ForeignKey('examens.id', ondelete='SET NULL'),
        index=True
    )
    
    montant = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Type : 'encaissement', 'remboursement', 'depense'
    type_operation = db.Column(db.String(20), nullable=False, index=True)
    
    # Mode : 'espece', 'cheque', 'virement', 'carte', 'moncash'
    mode_paiement = db.Column(db.String(20), default='espece')
    
    description = db.Column(db.String(255))
    reference = db.Column(db.String(50))  # N° chèque, transaction, etc.
    
    date_operation = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    enregistre_par = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Contraintes
    __table_args__ = (
        CheckConstraint(
            "type_operation IN ('encaissement', 'remboursement', 'depense')",
            name='check_journal_type'
        ),
        CheckConstraint(
            "mode_paiement IN ('espece', 'cheque', 'virement', 'carte', 'moncash')",
            name='check_journal_mode'
        ),
        CheckConstraint('montant > 0', name='check_journal_montant_positif'),
    )
    
    def __repr__(self):
        return f'<JournalCaisse {self.type_operation} {self.montant} HTG>'