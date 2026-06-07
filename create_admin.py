from app import app, db
from app.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("@admin12345"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(" COMPTE ADMIN CREE EN PRODUCTION ")
