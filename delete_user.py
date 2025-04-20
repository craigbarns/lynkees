"""Script pour supprimer un utilisateur spécifique"""
import sys
import os
import logging
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Obtenir le répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import des modules nécessaires
try:
    from app import app, db, User
    logging.info("Modules importés avec succès")
except Exception as e:
    logging.error(f"Erreur lors de l'importation des modules: {str(e)}")
    sys.exit(1)

def delete_user_by_email(email):
    """Supprime un utilisateur par son email"""
    with app.app_context():
        try:
            user = User.query.filter_by(email=email).first()
            if user:
                logging.info(f"Utilisateur trouvé: {user.username} ({user.email})")
                db.session.delete(user)
                db.session.commit()
                logging.info(f"Utilisateur {user.username} supprimé avec succès")
                return True
            else:
                logging.warning(f"Aucun utilisateur trouvé avec l'email: {email}")
                return False
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
            return False

def delete_user_by_username(username):
    """Supprime un utilisateur par son nom d'utilisateur"""
    with app.app_context():
        try:
            user = User.query.filter_by(username=username).first()
            if user:
                logging.info(f"Utilisateur trouvé: {user.username} ({user.email})")
                db.session.delete(user)
                db.session.commit()
                logging.info(f"Utilisateur {user.username} supprimé avec succès")
                return True
            else:
                logging.warning(f"Aucun utilisateur trouvé avec le nom d'utilisateur: {username}")
                return False
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
            return False

def delete_user_by_email_fragment(email_fragment):
    """Supprime tous les utilisateurs dont l'email contient un fragment spécifique"""
    with app.app_context():
        try:
            users = User.query.filter(User.email.like(f"%{email_fragment}%")).all()
            if users:
                count = len(users)
                logging.info(f"{count} utilisateur(s) trouvé(s) avec le fragment '{email_fragment}' dans leur email")
                
                for user in users:
                    logging.info(f"Suppression de l'utilisateur: {user.username} ({user.email})")
                    db.session.delete(user)
                
                db.session.commit()
                logging.info(f"{count} utilisateur(s) supprimé(s) avec succès")
                return True, count
            else:
                logging.warning(f"Aucun utilisateur trouvé avec le fragment '{email_fragment}' dans leur email")
                return False, 0
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la suppression des utilisateurs: {str(e)}")
            return False, 0

if __name__ == "__main__":
    # Vérifier les arguments
    if len(sys.argv) < 2:
        print("Usage: python delete_user.py <email|username> [--by-username]")
        sys.exit(1)
    
    target = sys.argv[1]
    by_username = "--by-username" in sys.argv
    
    if by_username:
        logging.info(f"Recherche de l'utilisateur par nom d'utilisateur: {target}")
        success = delete_user_by_username(target)
    else:
        # Si l'argument ressemble à un email (contient un @), supprimer par email
        if "@" in target:
            logging.info(f"Recherche de l'utilisateur par email: {target}")
            success = delete_user_by_email(target)
        else:
            # Sinon, considérer comme un fragment d'email
            logging.info(f"Recherche des utilisateurs contenant '{target}' dans leur email")
            success, count = delete_user_by_email_fragment(target)
    
    if success:
        logging.info("✅ Opération terminée avec succès")
    else:
        logging.error("❌ Échec de l'opération")