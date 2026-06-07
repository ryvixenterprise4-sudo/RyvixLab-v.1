from app import create_app
import os

app = create_app()
# AJOUTEZ TEMPORAIRE
# 2. Automatisation pour le Plan Free de Render
with app.app_context():
    # Crée les tables dans la base PostgreSQL de Render si elles n'existent pas
    db.create_all()
    print("Base de données initialisée (Tables créées).")

    # Création automatique du compte admin pour le premier test
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@ryvixlab.com",
            role="administrateur",
            actif=True
        )
        # Assurez-vous que votre modèle User a bien la méthode set_password
        admin.set_password("@admin12345")
        
        db.session.add(admin)
        db.session.commit()
        print(" Compte administrateur créé par défaut.")
    else:
        print(" Le compte admin existe déjà, aucune action requise.")
# FIN

if __name__ == '__main__':
    # On récupère le port de Render, sinon 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
