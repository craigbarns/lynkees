"""Script pour ajouter la table Expense (charges) à la base de données"""
from main import app
from models import db
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

def add_expenses_table():
    """Ajoute la table pour la gestion des charges (appels de fonds, EDF, etc.)"""
    
    # Utiliser le contexte d'application Flask
    with app.app_context():
        # Définir le modèle Expense
        class Expense(db.Model):
            """Modèle pour les charges (appels de fonds, factures, etc.)"""
            __tablename__ = 'expenses'
            
            id = Column(Integer, primary_key=True)
            property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True)
            building_id = Column(Integer, ForeignKey('buildings.id', ondelete='CASCADE'), nullable=True)
            company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=True)
            
            # Type de charge (appel de fonds, EDF, eau, etc.)
            charge_type = Column(String(50), nullable=False)
            
            # Détails financiers
            amount = Column(Float, nullable=False)
            due_date = Column(Date, nullable=False)  # Date d'échéance
            payment_date = Column(Date, nullable=True)  # Date de paiement effectif
            status = Column(String(20), nullable=False, default='à_payer')  # à_payer, payé, en_retard
            
            # Informations supplémentaires
            reference = Column(String(100), nullable=True)  # Numéro de facture ou référence
            period_start = Column(Date, nullable=True)  # Début de la période concernée
            period_end = Column(Date, nullable=True)  # Fin de la période concernée
            description = Column(Text, nullable=True)
            
            # Champs de suivi
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            
            # Récurrence
            is_recurring = Column(Boolean, default=False)
            recurring_group_id = Column(String(50), nullable=True)
            recurring_frequency = Column(String(20), nullable=True)  # mensuel, trimestriel, annuel
            
            # Document associé (facture, etc.)
            document_id = Column(Integer, ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
            
            # Relations
            property = relationship('Property', backref='expenses')
            building = relationship('Building', backref='expenses')
            company = relationship('Company', backref='expenses')
            document = relationship('Document', backref='expense')
            
            def __repr__(self):
                return f'<Expense {self.id}: {self.charge_type} - {self.amount}€>'
            
            def get_charge_type_display(self):
                """Retourne une version lisible du type de charge"""
                types = {
                    'appel_fonds': 'Appel de fonds',
                    'edf': 'Électricité (EDF)',
                    'eau': 'Eau',
                    'chauffage': 'Chauffage',
                    'syndic': 'Syndic',
                    'taxe_fonciere': 'Taxe foncière',
                    'taxe_habitation': 'Taxe d\'habitation',
                    'assurance': 'Assurance',
                    'travaux': 'Travaux',
                    'autre': 'Autre'
                }
                return types.get(self.charge_type, self.charge_type)
            
            def get_status_display(self):
                """Retourne une version lisible du statut"""
                status_display = {
                    'à_payer': 'À payer',
                    'payé': 'Payé',
                    'en_retard': 'En retard'
                }
                return status_display.get(self.status, self.status)
            
            def check_status(self):
                """Vérifie et met à jour le statut de la charge"""
                today = datetime.now().date()
                
                if self.payment_date:
                    self.status = 'payé'
                elif today > self.due_date and self.status == 'à_payer':
                    self.status = 'en_retard'
                
                return self.status
        
        # Créer la table
        db.create_all()
        print("Table 'expenses' créée avec succès.")

if __name__ == '__main__':
    add_expenses_table()