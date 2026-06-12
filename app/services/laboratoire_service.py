"""
Service métier pour la configuration du laboratoire.

Le laboratoire est un singleton : il n'y a qu'UNE seule configuration.
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Laboratoire


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def fichier_autorise(filename):
    """Vérifie l'extension du fichier."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def obtenir_config():
    """Retourne la configuration du laboratoire (singleton)."""
    return Laboratoire.get_config()


def mettre_a_jour_config(data, fichiers=None):
    """
    Met à jour la configuration du laboratoire.
    
    Args:
        data (dict): Champs du formulaire
        fichiers (dict): Fichiers uploadés (logo, signature)
    
    Returns:
        tuple (Laboratoire, message_erreur)
    """
    config = Laboratoire.get_config()
    
    # ===== CHAMPS TEXTE =====
    champs_texte = [
        'nom', 'slogan', 'adresse', 'ville', 'departement', 'pays',
        'telephone1', 'telephone2', 'email', 'site_web',
        'directeur_nom', 'directeur_titre',
        'numero_licence', 'numero_fiscal',
        'en_tete_couleur', 'devise', 'pied_page'
    ]
    
    for champ in champs_texte:
        if champ in data:
            valeur = (data[champ] or '').strip() or None
            setattr(config, champ, valeur)
    
    # Validation du nom (obligatoire)
    if not config.nom or len(config.nom) < 2:
        return None, 'Le nom du laboratoire est obligatoire (min. 2 caractères).'
    
    # ===== UPLOAD LOGO =====
    if fichiers and 'logo' in fichiers:
        fichier_logo = fichiers['logo']
        if fichier_logo and fichier_logo.filename:
            if not fichier_autorise(fichier_logo.filename):
                return None, 'Format de logo non autorisé. Utilisez PNG, JPG ou GIF.'
            
            # Sauvegarder le fichier
            from flask import current_app
            
            extension = fichier_logo.filename.rsplit('.', 1)[1].lower()
            nom_fichier = f'logo_{int(datetime.now().timestamp())}.{extension}'
            
            dossier = current_app.config.get('UPLOAD_FOLDER')
            os.makedirs(dossier, exist_ok=True)
            
            chemin_complet = os.path.join(dossier, nom_fichier)
            fichier_logo.save(chemin_complet)
            
            # Stocker le chemin relatif
            config.logo_path = f'uploads/{nom_fichier}'
    
    # ===== UPLOAD SIGNATURE =====
    if fichiers and 'signature' in fichiers:
        fichier_sig = fichiers['signature']
        if fichier_sig and fichier_sig.filename:
            if not fichier_autorise(fichier_sig.filename):
                return None, 'Format de signature non autorisé.'
            
            from flask import current_app
            
            extension = fichier_sig.filename.rsplit('.', 1)[1].lower()
            nom_fichier = f'signature_{int(datetime.now().timestamp())}.{extension}'
            
            dossier = current_app.config.get('UPLOAD_FOLDER')
            os.makedirs(dossier, exist_ok=True)
            
            chemin_complet = os.path.join(dossier, nom_fichier)
            fichier_sig.save(chemin_complet)
            
            config.directeur_signature_path = f'uploads/{nom_fichier}'
    
    config.date_modification = datetime.utcnow()
    db.session.commit()
    
    return config, None