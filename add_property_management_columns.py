import os
import logging
from datetime import datetime
from flask import Flask
from models import db, Property

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# Créer une application Flask minimale
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///property_management.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def add_property_management_columns():
    """Ajoute les colonnes is_furnished, has_property_manager et property_manager_name à la table properties"""
    with app.app_context():
        logging.info("Vérification de l'existence des colonnes...")
        
        # Vérifier si les colonnes existent déjà dans la table
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_columns = [column['name'] for column in inspector.get_columns('properties')]
        
        if 'is_furnished' in existing_columns:
            logging.info("Les colonnes existent déjà.")
            return
        
        logging.info("Les colonnes n'existent pas. Création en cours...")
        
        # Si les colonnes n'existent pas, les ajouter
        try:
            with db.engine.begin() as conn:
                # Ajouter la colonne is_furnished
                conn.execute(db.text("ALTER TABLE properties ADD COLUMN is_furnished BOOLEAN DEFAULT FALSE"))
                logging.info("Colonne is_furnished ajoutée avec succès.")
                
                # Ajouter la colonne has_property_manager
                conn.execute(db.text("ALTER TABLE properties ADD COLUMN has_property_manager BOOLEAN DEFAULT FALSE"))
                logging.info("Colonne has_property_manager ajoutée avec succès.")
                
                # Ajouter la colonne property_manager_name
                conn.execute(db.text("ALTER TABLE properties ADD COLUMN property_manager_name VARCHAR(255)"))
                logging.info("Colonne property_manager_name ajoutée avec succès.")
                
            logging.info("Migration terminée avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la migration: {str(e)}")

if __name__ == "__main__":
    add_property_management_columns()
    logging.info("Script terminé.")