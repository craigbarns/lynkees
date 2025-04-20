"""Script pour confirmer l'utilisateur 'test'"""

from app import app, db
from models import User

def confirm_test_user():
    """Confirme l'utilisateur 'test'"""
    with app.app_context():
        user = User.query.filter_by(username='test').first()
        if user:
            user.email_confirmed = True
            db.session.commit()
            print(f"Utilisateur '{user.username}' confirmé avec succès")
        else:
            print("Utilisateur 'test' non trouvé")

if __name__ == "__main__":
    confirm_test_user()