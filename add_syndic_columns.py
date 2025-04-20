import os
import sys
import logging
from flask import Flask
from sqlalchemy import Column, Boolean, String
from models import db, Property

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Créer une application Flask pour le contexte
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def add_syndic_columns():
    """Ajoute les colonnes relatives au syndic à la table properties"""
    try:
        with app.app_context():
            # Vérifier si les colonnes existent déjà
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('properties')]
            
            # Si la colonne has_syndic n'existe pas, ajouter les colonnes
            if 'has_syndic' not in columns:
                logging.info("Ajout des colonnes de syndic à la table properties...")
                
                # Ajout des colonnes
                with db.engine.connect() as conn:
                    conn.execute("""
                        ALTER TABLE properties
                        ADD COLUMN has_syndic BOOLEAN NOT NULL DEFAULT false,
                        ADD COLUMN syndic_name VARCHAR(255),
                        ADD COLUMN syndic_contact VARCHAR(255)
                    """)
                
                logging.info("Colonnes de syndic ajoutées avec succès !")
            else:
                logging.info("Les colonnes de syndic existent déjà dans la table properties.")
                
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout des colonnes: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    add_syndic_columns()