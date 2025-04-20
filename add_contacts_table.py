import os
import sys
import logging
from flask import Flask
from sqlalchemy import text, Column, Integer, String, Boolean, Float, DateTime, Text, Date, ForeignKey, Table
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import des modèles pour avoir accès aux définitions des tables
from database import db, init_db
from models import Contact, contact_property, contact_building

def add_contacts_table():
    """Ajoute les tables pour la gestion des contacts"""
    try:
        # Création d'une application Flask temporaire pour le contexte
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialisation de l'application avec la base de données
        init_db(app)
        
        with app.app_context():
            # Vérification si les tables existent déjà
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'contacts' not in existing_tables:
                # Création de la table Contact
                db.metadata.tables['contacts'].create(db.engine)
                logging.info("Table 'contacts' créée avec succès.")
            else:
                logging.info("La table 'contacts' existe déjà.")
                
            if 'contact_property' not in existing_tables:
                # Création de la table de liaison contact_property
                db.metadata.tables['contact_property'].create(db.engine)
                logging.info("Table 'contact_property' créée avec succès.")
            else:
                logging.info("La table 'contact_property' existe déjà.")
                
            if 'contact_building' not in existing_tables:
                # Création de la table de liaison contact_building
                db.metadata.tables['contact_building'].create(db.engine)
                logging.info("Table 'contact_building' créée avec succès.")
            else:
                logging.info("La table 'contact_building' existe déjà.")
                
            logging.info("Migration pour l'ajout des tables de contacts terminée avec succès.")
            
    except SQLAlchemyError as e:
        logging.error(f"Erreur lors de la création des tables de contacts: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Erreur inattendue: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    success = add_contacts_table()
    if success:
        logging.info("Script terminé avec succès.")
        sys.exit(0)
    else:
        logging.error("Échec de la migration.")
        sys.exit(1)