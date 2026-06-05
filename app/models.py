from app.extensions import db, bcrypt, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))


class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='technicien')
    actif = db.Column(db.Boolean, default=True)
    cree_le = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, mot_de_passe):
        self.mot_de_passe = bcrypt.generate_password_hash(mot_de_passe).decode('utf-8')

    def check_password(self, mot_de_passe):
        return bcrypt.check_password_hash(self.mot_de_passe, mot_de_passe)

    def __repr__(self):
        return f'<Utilisateur {self.nom_utilisateur}>'


class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    nom_complet = db.Column(db.String(150), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(150))
    adresse = db.Column(db.String(200))
    enregistre_le = db.Column(db.DateTime, default=datetime.utcnow)

    analyses = db.relationship('Enregistrement', backref='patient', lazy=True)

    def __repr__(self):
        return f'<Patient {self.nom_complet}>'


class Analyse(db.Model):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    service = db.Column(db.String(100))
    prix = db.Column(db.Numeric(10, 2), nullable=False)
    actif = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Analyse {self.nom}>'


class Enregistrement(db.Model):
    __tablename__ = 'enregistrements'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    analyse_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)
    resultat = db.Column(db.Text)
    statut = db.Column(db.String(20), default='en_attente')

    analyse = db.relationship('Analyse', backref='enregistrements')

    def __repr__(self):
        return f'<Enregistrement {self.id}>'
