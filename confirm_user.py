"""Script pour confirmer manuellement un compte utilisateur"""
from app import app, db
from models import User

def confirm_user_by_username(username):
    """Confirme manuellement un utilisateur par son nom d'utilisateur"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            try:
                # Marquer l'utilisateur comme confirmé
                user.email_confirmed = True
                user.confirmation_token = None
                db.session.commit()
                print(f"Compte de l'utilisateur {username} confirmé avec succès")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Erreur lors de la confirmation de l'utilisateur: {str(e)}")
                return False
        else:
            print(f"Aucun utilisateur trouvé avec le nom {username}")
            return False

if __name__ == "__main__":
    # Confirmer l'utilisateur gregorybaranes
    confirm_user_by_username("gregorybaranes")