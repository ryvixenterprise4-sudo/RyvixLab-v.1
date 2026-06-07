from app import create_app
import os

app = create_app()
# AJOUTEZ TEMPORAIRE
with app.app_context():
    # Crée les tables si elles n'existent pas
    db.create_all()
    print(" Base de données vérifiée/initialisée.")
# FIN

if __name__ == '__main__':
    # On récupère le port de Render, sinon 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
