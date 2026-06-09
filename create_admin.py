from app import create_app, db
from app.models import User
# Importez votre modèle User. Vérifiez si c'est 'password_hash' ou 'set_password'

app = create_app() # Crée l'instance de l'app avec la config de production

with app.app_context():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@example.com",
            role="administrateur", 
            actif=True
        )
        # Utilisez la méthode set_password que vous avez définie dans votre modèle
        admin.set_password("@admin12345") 
        
        db.session.add(admin)
        db.session.commit()
        print(" COMPTE ADMIN CRÉÉ AVEC SUCCÈS")
    else:
        print(" L'utilisateur admin existe déjà.")
