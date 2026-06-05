"""
Service métier pour les patients.

Toute la logique de manipulation des patients passe par ce service.
"""

from datetime import datetime, date
from app.extensions import db
from app.models import Patient
from sqlalchemy import or_, func


# ====================================================================
# GÉNÉRATION DE CODE PATIENT
# ====================================================================

def generer_code_patient(nom_complet):
    """
    Génère un code patient unique basé sur les initiales + numéro.
    
    Exemple : 
        - "Jean Ronel Saint Fort" → "JR-1", "JR-2", etc.
        - "Pierre Resimene" → "PR-1"
    """
    if not nom_complet:
        return None
    
    # Extraire les initiales (2 premières lettres significatives)
    mots = nom_complet.strip().split()
    if len(mots) >= 2:
        initiales = (mots[0][0] + mots[1][0]).upper()
    else:
        initiales = mots[0][:2].upper()
    
    # Compter combien de patients ont déjà ces initiales
    prefix = f'{initiales}-'
    dernier = Patient.query.filter(
        Patient.code.like(f'{prefix}%')
    ).order_by(Patient.id.desc()).first()
    
    if dernier:
        # Extraire le numéro et incrémenter
        try:
            num = int(dernier.code.split('-')[1])
            return f'{prefix}{num + 1}'
        except (ValueError, IndexError):
            return f'{prefix}1'
    
    return f'{prefix}1'


# ====================================================================
# CRUD PATIENTS
# ====================================================================

def lister_patients(recherche=None, sexe=None, limit=None):
    """
    Retourne la liste des patients avec filtres optionnels.
    
    Args:
        recherche (str): Filtre sur code, nom, adresse
        sexe (str): 'M' ou 'F'
        limit (int): Nombre maximum de résultats
    """
    query = Patient.query
    
    if recherche:
        terme = f'%{recherche.strip()}%'
        query = query.filter(
            or_(
                Patient.code.ilike(terme),
                Patient.nom_complet.ilike(terme),
                Patient.adresse.ilike(terme),
                Patient.telephone.ilike(terme)
            )
        )
    
    if sexe in ('M', 'F'):
        query = query.filter_by(sexe=sexe)
    
    query = query.order_by(Patient.date_creation.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def trouver_patient(patient_id):
    """Retourne un patient par son ID."""
    return Patient.query.get(patient_id)


def chercher_par_code(code):
    """Retourne un patient par son code unique."""
    return Patient.query.filter_by(code=code).first()


def parse_date(date_str):
    """Parse une date depuis une chaîne (format YYYY-MM-DD ou DD/MM/YYYY)."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def creer_patient(nom_complet, date_naissance=None, lieu_naissance=None,
                  adresse=None, sexe=None, telephone=None, email=None,
                  user_id=None):
    """
    Crée un nouveau patient avec génération automatique du code.
    
    Returns:
        tuple (Patient, message_erreur)
    """
    # Nettoyage
    nom_complet = (nom_complet or '').strip()
    
    # ===== VALIDATIONS =====
    if not nom_complet or len(nom_complet) < 2:
        return None, 'Le nom complet doit avoir au moins 2 caractères.'
    
    if sexe and sexe not in ('M', 'F'):
        return None, 'Sexe invalide. Utilisez M ou F.'
    
    # Validation de la date
    date_n = None
    if date_naissance:
        if isinstance(date_naissance, str):
            date_n = parse_date(date_naissance)
            if date_naissance and not date_n:
                return None, 'Format de date invalide (utilisez JJ/MM/AAAA ou AAAA-MM-JJ).'
        else:
            date_n = date_naissance
        
        # Vérifier que ce n'est pas dans le futur
        if date_n and date_n > date.today():
            return None, 'La date de naissance ne peut pas être dans le futur.'
    
    # Génération du code
    code = generer_code_patient(nom_complet)
    
    # ===== CRÉATION =====
    patient = Patient(
        code=code,
        nom_complet=nom_complet,
        date_naissance=date_n,
        lieu_naissance=(lieu_naissance or '').strip() or None,
        adresse=(adresse or '').strip() or None,
        sexe=sexe,
        telephone=(telephone or '').strip() or None,
        email=(email or '').strip().lower() or None,
        created_by=user_id
    )
    
    db.session.add(patient)
    db.session.commit()
    
    return patient, None


def modifier_patient(patient_id, **kwargs):
    """Modifie un patient existant."""
    patient = Patient.query.get(patient_id)
    if not patient:
        return None, 'Patient introuvable.'
    
    if 'nom_complet' in kwargs:
        nom = (kwargs['nom_complet'] or '').strip()
        if not nom or len(nom) < 2:
            return None, 'Le nom doit avoir au moins 2 caractères.'
        patient.nom_complet = nom
    
    if 'date_naissance' in kwargs:
        date_val = kwargs['date_naissance']
        if isinstance(date_val, str):
            date_val = parse_date(date_val)
        if date_val and date_val > date.today():
            return None, 'Date de naissance dans le futur.'
        patient.date_naissance = date_val
    
    if 'sexe' in kwargs:
        sexe = kwargs['sexe']
        if sexe and sexe not in ('M', 'F'):
            return None, 'Sexe invalide.'
        patient.sexe = sexe
    
    for field in ['lieu_naissance', 'adresse', 'telephone', 'email']:
        if field in kwargs:
            valeur = kwargs[field]
            setattr(patient, field, valeur.strip() if valeur else None)
    
    db.session.commit()
    return patient, None


def supprimer_patient(patient_id):
    """
    Supprime un patient et tous ses examens (cascade).
    À utiliser avec précaution !
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        return False, 'Patient introuvable.'
    
    db.session.delete(patient)
    db.session.commit()
    return True, None


# ====================================================================
# STATISTIQUES
# ====================================================================

def compter_patients():
    """Retourne le nombre total de patients."""
    return Patient.query.count()


def patients_recents(limit=5):
    """Retourne les N derniers patients enregistrés."""
    return Patient.query.order_by(Patient.date_creation.desc()).limit(limit).all()