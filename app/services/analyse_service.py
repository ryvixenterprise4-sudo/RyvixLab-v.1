"""
Service métier pour les analyses et paramètres.

Toute la logique de manipulation des analyses passe par ce service.
Les routes ne font qu'appeler ses méthodes.
"""
"""Service métier pour les analyses, paramètres et valeurs prédéfinies."""

from decimal import Decimal, InvalidOperation
from app.extensions import db
from app.models import Analyse, Parametre, ValeurPredefinie


# ====================================================================
# CRUD ANALYSES (inchangé - garder vos fonctions existantes)
# ====================================================================

def lister_analyses(recherche=None, inclure_inactives=False):
    """... votre code existant ..."""
    query = Analyse.query
    if not inclure_inactives:
        query = query.filter_by(actif=True)
    if recherche:
        terme = f'%{recherche.strip()}%'
        query = query.filter(
            db.or_(
                Analyse.nom.ilike(terme),
                Analyse.service.ilike(terme)
            )
        )
    return query.order_by(Analyse.service, Analyse.nom).all()


def creer_analyse(nom, service, prix, description=None):
    """... votre code existant inchangé ..."""
    nom = (nom or '').strip()
    service = (service or '').strip()
    if not nom or len(nom) < 2:
        return None, 'Le nom de l\'analyse doit avoir au moins 2 caractères.'
    if not service:
        return None, 'Le service est obligatoire.'
    try:
        prix_decimal = Decimal(str(prix).replace(',', '.'))
        if prix_decimal < 0:
            return None, 'Le prix ne peut pas être négatif.'
    except (InvalidOperation, ValueError, TypeError):
        return None, 'Prix invalide.'
    if Analyse.query.filter_by(nom=nom).first():
        return None, f'Une analyse nommée "{nom}" existe déjà.'
    analyse = Analyse(
        nom=nom, service=service, prix=prix_decimal,
        description=description.strip() if description else None,
        actif=True
    )
    db.session.add(analyse)
    db.session.commit()
    return analyse, None


def modifier_analyse(analyse_id, nom, service, prix, description=None):
    """... votre code existant inchangé ..."""
    analyse = Analyse.query.get(analyse_id)
    if not analyse:
        return None, 'Analyse introuvable.'
    nom = (nom or '').strip()
    service = (service or '').strip()
    if not nom or len(nom) < 2:
        return None, 'Le nom doit avoir au moins 2 caractères.'
    if not service:
        return None, 'Le service est obligatoire.'
    try:
        prix_decimal = Decimal(str(prix).replace(',', '.'))
        if prix_decimal < 0:
            return None, 'Le prix ne peut pas être négatif.'
    except (InvalidOperation, ValueError, TypeError):
        return None, 'Prix invalide.'
    existante = Analyse.query.filter(
        Analyse.nom == nom, Analyse.id != analyse_id
    ).first()
    if existante:
        return None, f'Une autre analyse nommée "{nom}" existe déjà.'
    analyse.nom = nom
    analyse.service = service
    analyse.prix = prix_decimal
    if description is not None:
        analyse.description = description.strip()
    db.session.commit()
    return analyse, None


def supprimer_analyse(analyse_id):
    """... votre code existant inchangé ..."""
    analyse = Analyse.query.get(analyse_id)
    if not analyse:
        return False, 'Analyse introuvable.'
    analyse.actif = False
    db.session.commit()
    return True, None


# ====================================================================
# CRUD PARAMÈTRES - MIS À JOUR
# ====================================================================

def lister_parametres(analyse_id=None):
    """Retourne la liste des paramètres."""
    query = Parametre.query
    if analyse_id:
        query = query.filter_by(analyse_id=analyse_id)
    return query.order_by(
        Parametre.analyse_id,
        Parametre.ordre,
        Parametre.nom_parametre
    ).all()


def creer_parametre(analyse_id, nom_parametre, sous_parametre=None,
                    unite=None, valeur_normale_f=None, valeur_normale_m=None,
                    type_resultat='numerique', valeurs_predefinies=None):
    """
    Crée un nouveau paramètre lié à une analyse.
    
    Args:
        type_resultat: 'numerique', 'texte', ou 'liste'
        valeurs_predefinies (list[str]): Liste optionnelle de valeurs.
            - Pour 'numerique' et 'texte' : suggestions (cliquables)
            - Pour 'liste' : choix obligatoires
    """
    
    analyse = Analyse.query.get(analyse_id)
    if not analyse:
        return None, 'Analyse introuvable.'
    
    nom_parametre = (nom_parametre or '').strip()
    if not nom_parametre:
        return None, 'Le nom du paramètre est obligatoire.'
    
    # Validation type
    if type_resultat not in ('numerique', 'texte', 'liste'):
        return None, 'Type de résultat invalide.'
    
    # Si type='liste', les valeurs sont OBLIGATOIRES (au moins 2)
    if type_resultat == 'liste':
        if not valeurs_predefinies or len(valeurs_predefinies) < 2:
            return None, 'Pour "Liste de choix", fournissez au moins 2 valeurs.'
    
    # Si type='numerique', vérifier que les valeurs sont bien des nombres
    if type_resultat == 'numerique' and valeurs_predefinies:
        for v in valeurs_predefinies:
            try:
                float(str(v).replace(',', '.'))
            except (ValueError, TypeError):
                return None, f'La valeur "{v}" n\'est pas un nombre valide.'
    
    # Détermine l'ordre automatiquement
    dernier_ordre = db.session.query(
        db.func.max(Parametre.ordre)
    ).filter_by(analyse_id=analyse_id).scalar() or 0
    
    # Création du paramètre
    parametre = Parametre(
        analyse_id=analyse_id,
        nom_parametre=nom_parametre,
        sous_parametre=sous_parametre.strip() if sous_parametre else None,
        unite=unite.strip() if unite else None,
        valeur_normale_f=valeur_normale_f.strip() if valeur_normale_f else None,
        valeur_normale_m=valeur_normale_m.strip() if valeur_normale_m else None,
        type_resultat=type_resultat,
        ordre=dernier_ordre + 1
    )
    db.session.add(parametre)
    db.session.flush()
    
    # Ajout des valeurs prédéfinies (pour TOUS les types maintenant)
    if valeurs_predefinies:
        for ordre, valeur in enumerate(valeurs_predefinies, start=1):
            valeur = str(valeur).strip()
            if valeur:
                vp = ValeurPredefinie(
                    parametre_id=parametre.id,
                    valeur=valeur,
                    ordre=ordre
                )
                db.session.add(vp)
    
    db.session.commit()
    return parametre, None


def modifier_parametre(parametre_id, nom_parametre=None, sous_parametre=None,
                       unite=None, valeur_normale_f=None, valeur_normale_m=None,
                       type_resultat=None, valeurs_predefinies=None):
    """Modifie un paramètre existant et ses valeurs prédéfinies."""
    
    parametre = Parametre.query.get(parametre_id)
    if not parametre:
        return None, 'Paramètre introuvable.'
    
    if nom_parametre is not None:
        nom = nom_parametre.strip()
        if not nom:
            return None, 'Le nom est obligatoire.'
        parametre.nom_parametre = nom
    
    if sous_parametre is not None:
        parametre.sous_parametre = sous_parametre.strip() or None
    
    if unite is not None:
        parametre.unite = unite.strip() or None
    
    if valeur_normale_f is not None:
        parametre.valeur_normale_f = valeur_normale_f.strip() or None
    
    if valeur_normale_m is not None:
        parametre.valeur_normale_m = valeur_normale_m.strip() or None
    
    if type_resultat is not None:
        if type_resultat not in ('numerique', 'texte', 'liste'):
            return None, 'Type de résultat invalide.'
        parametre.type_resultat = type_resultat
    
    # Validation : si type='liste', au moins 2 valeurs requises
    if parametre.type_resultat == 'liste':
        if not valeurs_predefinies or len(valeurs_predefinies) < 2:
            return None, 'Pour "Liste de choix", fournissez au moins 2 valeurs.'
    
    # Validation : si type='numerique', vérifier les nombres
    if parametre.type_resultat == 'numerique' and valeurs_predefinies:
        for v in valeurs_predefinies:
            try:
                float(str(v).replace(',', '.'))
            except (ValueError, TypeError):
                return None, f'La valeur "{v}" n\'est pas un nombre valide.'
    
    # Mise à jour des valeurs prédéfinies
    if valeurs_predefinies is not None:
        # Supprimer les anciennes
        ValeurPredefinie.query.filter_by(parametre_id=parametre.id).delete()
        
        # Ajouter les nouvelles
        for ordre, valeur in enumerate(valeurs_predefinies, start=1):
            valeur = str(valeur).strip()
            if valeur:
                vp = ValeurPredefinie(
                    parametre_id=parametre.id,
                    valeur=valeur,
                    ordre=ordre
                )
                db.session.add(vp)
    
    db.session.commit()
    return parametre, None


def supprimer_parametre(parametre_id):
    """Supprime un paramètre (et ses valeurs prédéfinies via cascade)."""
    parametre = Parametre.query.get(parametre_id)
    if not parametre:
        return False, 'Paramètre introuvable.'
    
    db.session.delete(parametre)
    db.session.commit()
    return True, None