"""Modèle Résultat - valeurs mesurées par le laborantin."""

from datetime import datetime
from app.extensions import db


class Resultat(db.Model):
    """Résultat saisi pour un paramètre d'une analyse."""
    
    __tablename__ = 'resultats'
    
    id = db.Column(db.Integer, primary_key=True)
    examen_detail_id = db.Column(
        db.Integer,
        db.ForeignKey('examen_details.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    parametre_id = db.Column(
        db.Integer,
        db.ForeignKey('parametres.id'),
        nullable=False
    )
    
    # Valeur saisie (numérique ou textuelle)
    valeur = db.Column(db.String(200))
    
    # Indicateur visuel : 'normal', 'eleve', 'bas', 'critique'
    statut_valeur = db.Column(db.String(20), default='normal')
    
    # Commentaire du laborantin
    commentaire = db.Column(db.Text)
    
    # Audit
    date_saisie = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    saisi_par = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # ===== RELATIONS =====
    parametre = db.relationship('Parametre')
    
    def __repr__(self):
        return f'<Resultat #{self.id} = {self.valeur}>'