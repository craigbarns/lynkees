"""Script pour ajouter les colonnes de confirmation d'email à la table users"""
import logging
from models import User
from database import db
from sqlalchemy import Column, Boolean, String, DateTime, text
from sqlalchemy.sql import func

def add_email_confirmation_columns():
    """Ajoute les colonnes email_confirmed, confirmation_token et confirmation_sent_at à la table users"""
    try:
        # Utiliser les commandes SQL brutes via text()
        conn = db.engine.connect()
        
        # Vérifier et ajouter email_confirmed
        try:
            conn.execute(text("SELECT email_confirmed FROM users LIMIT 1"))
            logging.info("La colonne email_confirmed existe déjà")
        except Exception:
            conn.execute(text("ALTER TABLE users ADD COLUMN email_confirmed BOOLEAN DEFAULT FALSE"))
            logging.info("Colonne email_confirmed ajoutée à la table users")
        
        # Vérifier et ajouter confirmation_token
        try:
            conn.execute(text("SELECT confirmation_token FROM users LIMIT 1"))
            logging.info("La colonne confirmation_token existe déjà")
        except Exception:
            conn.execute(text("ALTER TABLE users ADD COLUMN confirmation_token VARCHAR(255)"))
            logging.info("Colonne confirmation_token ajoutée à la table users")
        
        # Vérifier et ajouter confirmation_sent_at
        try:
            conn.execute(text("SELECT confirmation_sent_at FROM users LIMIT 1"))
            logging.info("La colonne confirmation_sent_at existe déjà")
        except Exception:
            conn.execute(text("ALTER TABLE users ADD COLUMN confirmation_sent_at TIMESTAMP"))
            logging.info("Colonne confirmation_sent_at ajoutée à la table users")
        
        # Mise à jour des utilisateurs existants
        conn.execute(text("UPDATE users SET email_confirmed = TRUE WHERE email_confirmed IS NULL"))
        
        logging.info("Colonnes de confirmation d'email ajoutées à la table users")
        conn.close()
        return True
            
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout des colonnes de confirmation d'email: {str(e)}")
        return False

if __name__ == "__main__":
    # Configuration des logs
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s %(levelname)s: %(message)s', 
                      datefmt='%Y-%m-%d %H:%M:%S')
    
    # Importer app pour initialiser la base de données
    from app import app
    
    with app.app_context():
        add_email_confirmation_columns()