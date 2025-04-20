import os
import sys
import logging
from flask import Flask
from database import db
from models import User
from werkzeug.security import generate_password_hash

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_test_user():
    """Crée un utilisateur de test garantie"""
    try:
        # Création d'une application Flask temporaire pour le contexte
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialiser la base de données
        db.init_app(app)
        
        with app.app_context():
            # Supprimer l'utilisateur test s'il existe déjà
            test_user = User.query.filter_by(username='test').first()
            if test_user:
                logging.info(f"Suppression de l'utilisateur test existant (ID: {test_user.id})")
                db.session.delete(test_user)
                db.session.commit()
            
            # Créer un nouvel utilisateur test
            new_user = User(
                username='test',
                email='test@example.com',
                is_admin=True
            )
            # Définir un mot de passe simple pour les tests
            new_user.password_hash = generate_password_hash('test123')
            
            db.session.add(new_user)
            db.session.commit()
            
            # Vérifier que l'utilisateur a été créé
            created_user = User.query.filter_by(username='test').first()
            if created_user:
                logging.info(f"Utilisateur test créé avec succès (ID: {created_user.id})")
                logging.info(f"Nom d'utilisateur: test")
                logging.info(f"Mot de passe: test123")
                logging.info(f"Email: test@example.com")
                return True
            else:
                logging.error("Impossible de créer l'utilisateur test")
                return False
                
    except Exception as e:
        logging.error(f"Erreur lors de la création de l'utilisateur test: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_test_user()
    if not success:
        sys.exit(1)