"""
Modèle Laboratoire - Configuration de l'entête pour les impressions.

Stocke les informations affichées en haut des résultats PDF :
nom du labo, adresse, logo, directeur, contacts, etc.
Il n'y a qu'UNE SEULE ligne dans cette table (singleton).
"""

from datetime import datetime
from app.extensions import db


class Laboratoire(db.Model):
    """Informations du laboratoire pour les en-têtes d'impression."""
    
    __tablename__ = 'laboratoire'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ===== IDENTITÉ =====
    nom = db.Column(db.String(150), nullable=False, default='Laboratoire Médical')
    slogan = db.Column(db.String(200))  # ex: "Au service de votre santé"
    
    # ===== LOGO =====
    logo_path = db.Column(db.String(255))  # Chemin relatif vers le logo
    
    # ===== COORDONNÉES =====
    adresse = db.Column(db.String(255))
    ville = db.Column(db.String(100))
    departement = db.Column(db.String(100))  # ex: Centre, Ouest, Nord
    pays = db.Column(db.String(50), default='Haïti')
    telephone1 = db.Column(db.String(30))
    telephone2 = db.Column(db.String(30))
    email = db.Column(db.String(120))
    site_web = db.Column(db.String(150))
    
    # ===== DIRECTION & RESPONSABILITÉ =====
    directeur_nom = db.Column(db.String(150))
    directeur_titre = db.Column(db.String(100))  # ex: "Dr. Méd., Biologiste"
    directeur_signature_path = db.Column(db.String(255))  # Image de signature
    
    # ===== INFOS LÉGALES =====
    numero_licence = db.Column(db.String(50))
    numero_fiscal = db.Column(db.String(50))
    
    # ===== PARAMÈTRES D'IMPRESSION =====
    en_tete_couleur = db.Column(db.String(20), default='#2c3e50')  # Couleur hex
    devise = db.Column(db.String(10), default='HTG')
    
    # Texte additionnel dans le pied de page du PDF
    pied_page = db.Column(db.Text)
    
    # ===== MÉTADONNÉES =====
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    @classmethod
    def get_config(cls):
        """
        Retourne la configuration unique du laboratoire.
        Si aucune n'existe, en crée une par défaut.
        """
        config = cls.query.first()
        if not config:
            config = cls(nom='Laboratoire Médical')
            db.session.add(config)
            db.session.commit()
        return config
    
    def __repr__(self):
        return f'<Laboratoire {self.nom}>'