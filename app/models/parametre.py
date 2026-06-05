"""Modèle Paramètre - valeurs mesurables d'une analyse."""

from app.extensions import db


class Parametre(db.Model):
    """Paramètre mesurable d'une analyse (ex: Créatinine, Potassium...)."""
    
    __tablename__ = 'parametres'
    
    id = db.Column(db.Integer, primary_key=True)
    analyse_id = db.Column(
        db.Integer,
        db.ForeignKey('analyses.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    nom_parametre = db.Column(db.String(100), nullable=False)
    sous_parametre = db.Column(db.String(100))
    unite = db.Column(db.String(20))
    
    # Valeurs normales
    valeur_normale_f = db.Column(db.String(50))  # Femme
    valeur_normale_m = db.Column(db.String(50))  # Homme
    valeur_normale_enfant = db.Column(db.String(50))
    
    # Type de résultat : 'numerique', 'texte', 'liste'
    # 'liste' = l'utilisateur choisira parmi des valeurs prédéfinies
    type_resultat = db.Column(db.String(20), default='numerique')
    
    ordre = db.Column(db.Integer, default=0)
    
    # ===== RELATIONS =====
    valeurs_predefinies = db.relationship(
        'ValeurPredefinie',
        backref='parametre',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ValeurPredefinie.ordre'
    )
    
    @property
    def libelle_complet(self):
        if self.sous_parametre:
            return f'{self.nom_parametre} - {self.sous_parametre}'
        return self.nom_parametre
    
    def __repr__(self):
        return f'<Parametre {self.nom_parametre}>'


class ValeurPredefinie(db.Model):
    """
    Valeur prédéfinie pour un paramètre de type 'liste'.
    Exemple : Hépatite B → Positif, Négatif
    """
    
    __tablename__ = 'valeurs_predefinies'
    
    id = db.Column(db.Integer, primary_key=True)
    parametre_id = db.Column(
        db.Integer,
        db.ForeignKey('parametres.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    valeur = db.Column(db.String(100), nullable=False)  # ex: 'Positif'
    ordre = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ValeurPredefinie {self.valeur}>'