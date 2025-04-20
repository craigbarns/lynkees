"""Script pour ajouter les colonnes last_modified et date_paid au modèle Payment"""
import os
import sys
from datetime import datetime
from sqlalchemy import Column, DateTime, Date, text

# Assurez-vous que le répertoire courant est dans le path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db
from models import Payment

def add_payment_columns():
    """Ajoute les colonnes last_modified et date_paid à la table payments"""
    print("Ajout des colonnes last_modified et date_paid à la table payments...")
    
    with app.app_context():
        # Vérifier si les colonnes existent déjà
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('payments')]
        
        # Ajouter la colonne last_modified si elle n'existe pas
        if 'last_modified' not in columns:
            db.session.execute(text('ALTER TABLE payments ADD COLUMN last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
            print("Colonne last_modified ajoutée.")
        else:
            print("La colonne last_modified existe déjà.")
        
        # Ajouter la colonne date_paid si elle n'existe pas
        if 'date_paid' not in columns:
            db.session.execute(text('ALTER TABLE payments ADD COLUMN date_paid DATE'))
            print("Colonne date_paid ajoutée.")
        else:
            print("La colonne date_paid existe déjà.")
        
        db.session.commit()
        
        try:
            # Mettre à jour les paiements existants avec statut 'Payé' pour définir date_paid
            payments = Payment.query.filter_by(status='Payé').all()
            count = 0
            for payment in payments:
                if not hasattr(payment, 'date_paid') or not payment.date_paid:
                    payment.date_paid = payment.payment_date
                    count += 1
                    
            db.session.commit()
            print(f"Mise à jour des dates de paiement pour {count} paiements avec statut 'Payé'.")
        except Exception as e:
            print(f"Erreur lors de la mise à jour des paiements: {str(e)}")
            db.session.rollback()
        
    print("Opération terminée avec succès.")

if __name__ == "__main__":
    add_payment_columns()