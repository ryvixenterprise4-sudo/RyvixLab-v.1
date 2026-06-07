from app import create_app, db  # 'db' est temporaire ici
from app.models import User 
import os

app = create_app()

# AJOUTEZ TEMPORAIREmnt
# Le bloc qui crée les tables au démarrage
with app.app_context():
    try:
        db.create_all()
        print(" Base de données initialisée avec succès.")
        
        # Logique de création de l'admin
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                email="admin@ryvixlab.com",
                role="administrateur",
                actif=True
            )
            admin.set_password("@admin12345")
            db.session.add(admin)
            db.session.commit()
            print(" Admin créé.")
    except Exception as e:
        print(f" Erreur lors de la création des tables : {e}")
# FIN

if __name__ == '__main__':
    # On récupère le port de Render, sinon 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
