"""
Service métier pour la saisie des résultats d'analyses.

Workflow :
- Le laborantin sélectionne un examen en attente
- Il saisit les valeurs pour chaque paramètre
- Quand tout est saisi, l'examen passe en 'termine'
"""

from datetime import datetime
from app.extensions import db
from app.models import (
    Examen, ExamenDetail, Analyse, Parametre, 
    Resultat, Patient
)
from sqlalchemy import or_, and_


# ====================================================================
# LISTE DES EXAMENS À TRAITER
# ====================================================================

def lister_examens_a_traiter(date_filtre=None, recherche=None, statut=None):
    """
    Liste des examens à traiter (en_attente ou en_cours).
    
    Args:
        date_filtre (date): Filtrer par date d'examen
        recherche (str): Recherche sur patient (code, nom)
        statut (str): Filtre par statut
    """
    query = Examen.query.join(Patient).filter(
        Examen.statut.in_(['en_attente', 'en_cours'])
    )
    
    if statut:
        query = query.filter(Examen.statut == statut)
    
    if date_filtre:
        query = query.filter(
            db.func.date(Examen.date_examen) == date_filtre
        )
    
    if recherche:
        terme = f'%{recherche.strip()}%'
        query = query.filter(
            or_(
                Patient.code.ilike(terme),
                Patient.nom_complet.ilike(terme),
                Examen.numero.ilike(terme)
            )
        )
    
    return query.order_by(Examen.date_examen.desc()).all()


# ====================================================================
# DÉTAILS D'UN EXAMEN
# ====================================================================

def obtenir_examen_complet(examen_id):
    """
    Retourne un examen avec :
    - Le patient
    - Les détails (analyses)
    - Les paramètres de chaque analyse
    - Les résultats déjà saisis
    """
    examen = Examen.query.get(examen_id)
    if not examen:
        return None
    
    # Construction d'une structure facile à utiliser dans le template
    donnees = {
        'examen': examen,
        'patient': examen.patient,
        'analyses_a_saisir': []
    }
    
    for detail in examen.details.all():
        analyse = detail.analyse
        parametres = Parametre.query.filter_by(
            analyse_id=analyse.id
        ).order_by(Parametre.ordre).all()
        
        # Pour chaque paramètre, vérifier s'il y a déjà un résultat
        parametres_avec_resultats = []
        for param in parametres:
            resultat_existant = Resultat.query.filter_by(
                examen_detail_id=detail.id,
                parametre_id=param.id
            ).first()
            
            parametres_avec_resultats.append({
                'parametre': param,
                'valeurs_predefinies': [
                    vp.valeur for vp in param.valeurs_predefinies.all()
                ],
                'resultat': resultat_existant
            })
        
        donnees['analyses_a_saisir'].append({
            'detail': detail,
            'analyse': analyse,
            'parametres': parametres_avec_resultats,
            'tous_remplis': all(p['resultat'] for p in parametres_avec_resultats)
        })
    
    return donnees


# ====================================================================
# SAUVEGARDE DES RÉSULTATS
# ====================================================================

def sauvegarder_resultats(examen_id, resultats_data, user_id=None):
    """
    Sauvegarde plusieurs résultats en une transaction.
    
    Args:
        examen_id (int): ID de l'examen
        resultats_data (list[dict]): Liste de :
            {
                'examen_detail_id': X,
                'parametre_id': Y,
                'valeur': "...",
                'commentaire': "..."  (optionnel)
            }
        user_id (int): ID de l'utilisateur qui saisit
    
    Returns:
        tuple (nb_enregistres, message_erreur)
    """
    examen = Examen.query.get(examen_id)
    if not examen:
        return 0, 'Examen introuvable.'
    
    nb_enregistres = 0
    
    for data in resultats_data:
        valeur = (data.get('valeur') or '').strip()
        if not valeur:
            continue  # Skip les valeurs vides
        
        try:
            detail_id = int(data.get('examen_detail_id'))
            parametre_id = int(data.get('parametre_id'))
        except (ValueError, TypeError):
            continue
        
        # Vérifier que le détail appartient bien à cet examen
        detail = ExamenDetail.query.filter_by(
            id=detail_id,
            examen_id=examen.id
        ).first()
        
        if not detail:
            continue
        
        # Vérifier que le paramètre existe
        parametre = Parametre.query.get(parametre_id)
        if not parametre:
            continue
        
        # Validation selon le type
        if parametre.type_resultat == 'numerique':
            try:
                float(valeur.replace(',', '.'))
            except ValueError:
                return 0, f'Valeur non numérique pour "{parametre.nom_parametre}" : "{valeur}"'
        
        if parametre.type_resultat == 'liste':
            valeurs_autorisees = [
                vp.valeur for vp in parametre.valeurs_predefinies.all()
            ]
            if valeur not in valeurs_autorisees:
                return 0, f'Valeur invalide pour "{parametre.nom_parametre}" : doit être {", ".join(valeurs_autorisees)}'
        
        # Chercher si un résultat existe déjà (mise à jour) ou créer un nouveau
        resultat = Resultat.query.filter_by(
            examen_detail_id=detail_id,
            parametre_id=parametre_id
        ).first()
        
        commentaire = (data.get('commentaire') or '').strip() or None
        
        if resultat:
            resultat.valeur = valeur
            resultat.commentaire = commentaire
            resultat.date_modification = datetime.utcnow()
            resultat.saisi_par = user_id
        else:
            resultat = Resultat(
                examen_detail_id=detail_id,
                parametre_id=parametre_id,
                valeur=valeur,
                commentaire=commentaire,
                saisi_par=user_id
            )
            db.session.add(resultat)
        
        nb_enregistres += 1
    
    # Mettre à jour le statut de l'examen
    mettre_a_jour_statut_examen(examen)
    
    db.session.commit()
    
    return nb_enregistres, None


def mettre_a_jour_statut_examen(examen):
    """
    Met à jour le statut de l'examen selon les résultats saisis :
    - Aucun résultat → en_attente
    - Quelques résultats → en_cours
    - Tous les résultats saisis → termine
    """
    tous_remplis = True
    au_moins_un_rempli = False
    
    for detail in examen.details.all():
        parametres = Parametre.query.filter_by(
            analyse_id=detail.analyse_id
        ).all()
        
        for param in parametres:
            resultat = Resultat.query.filter_by(
                examen_detail_id=detail.id,
                parametre_id=param.id
            ).first()
            
            if resultat and resultat.valeur:
                au_moins_un_rempli = True
                # Marquer le détail comme achevé si tous ses paramètres ont un résultat
            else:
                tous_remplis = False
        
        # Mettre à jour le statut du détail
        params_ids = [p.id for p in parametres]
        if params_ids:
            nb_resultats = Resultat.query.filter(
                Resultat.examen_detail_id == detail.id,
                Resultat.parametre_id.in_(params_ids)
            ).count()
            detail.acheve = (nb_resultats == len(params_ids))
            if detail.acheve and not detail.date_achevement:
                detail.date_achevement = datetime.utcnow()
    
    # Mettre à jour le statut global de l'examen
    if tous_remplis and au_moins_un_rempli:
        examen.statut = 'termine'
    elif au_moins_un_rempli:
        examen.statut = 'en_cours'
    else:
        examen.statut = 'en_attente'


# ====================================================================
# STATISTIQUES
# ====================================================================

def compter_examens_par_statut():
    """Retourne le nombre d'examens par statut."""
    statuts = ['en_attente', 'en_cours', 'termine', 'imprime']
    resultat = {}
    for s in statuts:
        resultat[s] = Examen.query.filter_by(statut=s).count()
    return resultat