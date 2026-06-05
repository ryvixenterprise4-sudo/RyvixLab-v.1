"""
Service métier pour les examens (visites de patients).

Un "Examen" = la venue d'un patient avec les analyses demandées.
"""

from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models import Examen, ExamenDetail, Analyse, Patient


# ====================================================================
# GÉNÉRATION DU NUMÉRO D'EXAMEN
# ====================================================================

def generer_numero_examen():
    """
    Génère un numéro unique d'examen.
    Format : EX-2026-0001, EX-2026-0002, etc.
    """
    annee = datetime.now().year
    prefix = f'EX-{annee}-'
    
    dernier = Examen.query.filter(
        Examen.numero.like(f'{prefix}%')
    ).order_by(Examen.id.desc()).first()
    
    if dernier:
        try:
            num = int(dernier.numero.split('-')[2])
            return f'{prefix}{num + 1:04d}'
        except (ValueError, IndexError):
            return f'{prefix}0001'
    
    return f'{prefix}0001'


# ====================================================================
# CRÉATION D'EXAMEN
# ====================================================================

def creer_examen(patient_id, analyse_ids, user_id=None, medecin_prescripteur=None, notes=None):
    """
    Crée un nouvel examen avec ses détails.
    
    Args:
        patient_id (int): ID du patient
        analyse_ids (list[int]): Liste des IDs des analyses sélectionnées
        user_id (int): ID de l'utilisateur qui enregistre
        medecin_prescripteur (str): Nom du médecin prescripteur
        notes (str): Notes du laborantin
    
    Returns:
        tuple (Examen, message_erreur)
    """
    # Vérifier le patient
    patient = Patient.query.get(patient_id)
    if not patient:
        return None, 'Patient introuvable.'
    
    # Vérifier qu'il y a au moins une analyse
    if not analyse_ids:
        return None, 'Veuillez sélectionner au moins une analyse.'
    
    # Récupérer les analyses
    analyses = Analyse.query.filter(
        Analyse.id.in_(analyse_ids),
        Analyse.actif == True
    ).all()
    
    if not analyses:
        return None, 'Aucune analyse valide sélectionnée.'
    
    if len(analyses) != len(analyse_ids):
        return None, 'Certaines analyses sélectionnées sont introuvables ou inactives.'
    
    # Calculer le total
    total = sum(a.prix for a in analyses)
    
    # ===== CRÉATION =====
    examen = Examen(
        numero=generer_numero_examen(),
        patient_id=patient_id,
        date_examen=datetime.utcnow(),
        total=total,
        statut='en_attente',
        medecin_prescripteur=(medecin_prescripteur or '').strip() or None,
        notes=(notes or '').strip() or None,
        created_by=user_id
    )
    db.session.add(examen)
    db.session.flush()  # Pour avoir l'ID
    
    # Créer les détails (snapshot du prix)
    for analyse in analyses:
        detail = ExamenDetail(
            examen_id=examen.id,
            analyse_id=analyse.id,
            prix_unitaire=analyse.prix,
            acheve=False
        )
        db.session.add(detail)
    
    db.session.commit()
    
    return examen, None


# ====================================================================
# LISTE / RECHERCHE
# ====================================================================

def lister_examens(patient_id=None, statut=None, limit=None):
    """Liste les examens avec filtres."""
    query = Examen.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    if statut:
        query = query.filter_by(statut=statut)
    
    query = query.order_by(Examen.date_examen.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def trouver_examen(examen_id):
    """Retourne un examen par son ID avec ses détails."""
    return Examen.query.get(examen_id)


# ====================================================================
# CALCULS
# ====================================================================

def calculer_total(analyse_ids):
    """Calcule le total pour une liste d'IDs d'analyses."""
    if not analyse_ids:
        return Decimal('0.00')
    
    analyses = Analyse.query.filter(
        Analyse.id.in_(analyse_ids),
        Analyse.actif == True
    ).all()
    
    return sum(a.prix for a in analyses)