import os
import sys
from datetime import datetime
from sqlalchemy import Column, Date

# Ajouter le répertoire parent au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, app
from models import Property

def add_entry_date_column():
    """Ajoute la colonne entry_date à la table properties"""
    with app.app_context():
        # Vérifier si la colonne existe déjà
        try:
            # Tenter d'accéder à la colonne
            Property.query.filter(Property.entry_date.is_(None)).first()
            print("La colonne entry_date existe déjà dans la table properties.")
            return
        except Exception as e:
            print(f"La colonne n'existe pas encore, création en cours... ({str(e)})")
            
        try:
            # Connexion directe à la base de données
            engine = db.engine
            with engine.connect() as conn:
                # Ajout de la colonne entry_date
                conn.execute(db.text("ALTER TABLE properties ADD COLUMN entry_date DATE;"))
                conn.commit()
            
            print("La colonne entry_date a été ajoutée avec succès à la table properties.")
        except Exception as e:
            print(f"Erreur lors de l'ajout de la colonne: {str(e)}")

if __name__ == "__main__":
    add_entry_date_column()