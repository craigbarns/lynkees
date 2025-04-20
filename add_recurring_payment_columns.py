"""Script pour ajouter les colonnes is_recurring et recurring_group_id au modèle Payment"""

import os
import sys
import logging
from datetime import datetime

from sqlalchemy import create_engine, Column, Boolean, String, MetaData, Table
from sqlalchemy.dialects.postgresql import TEXT

# Configuration du logging
logging.basicConfig(level=logging.INFO)

def add_recurring_payment_columns():
    """Ajoute les colonnes is_recurring et recurring_group_id à la table payments"""
    try:
        # Connexion à la base de données
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            logging.error("Variable d'environnement DATABASE_URL non définie")
            sys.exit(1)
        
        engine = create_engine(DATABASE_URL)
        
        # Création d'une métadonnée pour refléter la table existante
        metadata = MetaData()
        
        # Reflète la table payments
        payments = Table('payments', metadata, autoload_with=engine)
        
        # Vérifie si les colonnes existent déjà
        has_is_recurring = 'is_recurring' in payments.columns
        has_recurring_group_id = 'recurring_group_id' in payments.columns
        
        if has_is_recurring and has_recurring_group_id:
            logging.info("Les colonnes is_recurring et recurring_group_id existent déjà dans la table payments")
            return
        
        # Ajoute les colonnes manquantes
        with engine.begin() as connection:
            if not has_is_recurring:
                logging.info("Ajout de la colonne is_recurring à la table payments")
                connection.execute("ALTER TABLE payments ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE")
            
            if not has_recurring_group_id:
                logging.info("Ajout de la colonne recurring_group_id à la table payments")
                connection.execute("ALTER TABLE payments ADD COLUMN recurring_group_id VARCHAR(50)")
        
        logging.info("Migration terminée avec succès")
    
    except Exception as e:
        logging.error(f"Erreur lors de la migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    add_recurring_payment_columns()