"""
Centralisation des modèles RyvixLab.

Importer tous les modèles ici permet à Flask-Migrate
de les détecter automatiquement lors des migrations.

⚠️ Si vous oubliez un modèle ici, Flask-Migrate ne créera PAS sa table.
"""

from app.models.laboratoire import Laboratoire
from app.models.user import User
from app.models.patient import Patient
from app.models.analyse import Analyse
from app.models.parametre import Parametre, ValeurPredefinie
from app.models.examen import Examen, ExamenDetail
from app.models.resultat import Resultat
from app.models.journal_caisse import JournalCaisse

__all__ = [
    'Laboratoire',
    'User',
    'Patient',
    'Analyse',
    'Parametre',
    'ValeurPredefinie',
    'Examen',
    'ExamenDetail',
    'Resultat',
    'JournalCaisse',
]