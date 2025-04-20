import os
import sys
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importer la base de données et les modèles
sys.path.append('.')
from database import Base
from models import Contact

# Configurer la connexion à la base de données
database_url = os.environ.get("DATABASE_URL", "sqlite:///property_management.db")
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()

def create_test_contacts():
    """Crée des contacts de test dans la base de données"""
    
    try:
        # Vérifie si des contacts existent déjà
        if session.query(Contact).count() > 0:
            print(f"Des contacts existent déjà ({session.query(Contact).count()} contacts)")
            return False
            
        # Crée une liste de contacts
        contacts = [
            Contact(
                first_name="Jean",
                last_name="Dupont",
                company_name="Plomberie Dupont",
                category="Plombier",
                email="jean.dupont@example.com",
                phone="01 23 45 67 89",
                mobile_phone="06 12 34 56 78",
                address="123 rue des Artisans",
                postal_code="75001",
                city="Paris",
                notes="Plombier très réactif, prix corrects",
                is_favorite=True
            ),
            Contact(
                first_name="Marie",
                last_name="Martin",
                company_name="Électricité Martin",
                category="Électricien",
                email="marie.martin@example.com",
                phone="01 23 45 67 90",
                mobile_phone="06 12 34 56 79",
                address="124 rue des Artisans",
                postal_code="75001",
                city="Paris",
                notes="Électricienne professionnelle, disponible le week-end",
                is_favorite=False
            ),
            Contact(
                first_name="Pierre",
                last_name="Durand",
                company_name="Syndic Immo Plus",
                category="Syndic",
                email="pierre.durand@example.com",
                phone="01 23 45 67 91",
                mobile_phone="06 12 34 56 80",
                address="125 rue des Syndics",
                postal_code="75002",
                city="Paris",
                notes="Syndic de plusieurs immeubles, bonnes références",
                is_favorite=True
            ),
            Contact(
                first_name="Sophie",
                last_name="Lefebvre",
                company_name="Gestion Tranquille",
                category="Gestionnaire",
                email="sophie.lefebvre@example.com",
                phone="01 23 45 67 92",
                mobile_phone="06 12 34 56 81",
                address="126 rue de la Gestion",
                postal_code="75003",
                city="Paris",
                notes="Gestionnaire efficace pour locations meublées",
                is_favorite=False
            ),
            Contact(
                first_name="Thomas",
                last_name="Moreau",
                company_name="Maçonnerie Générale",
                category="Maçon",
                email="thomas.moreau@example.com",
                phone="01 23 45 67 93",
                mobile_phone="06 12 34 56 82",
                address="127 rue du Bâtiment",
                postal_code="75004",
                city="Paris",
                notes="Spécialiste en réparations de façades",
                is_favorite=False
            )
        ]
        
        # Ajouter les contacts à la base de données
        for contact in contacts:
            session.add(contact)
        
        # Valider les changements
        session.commit()
        
        print(f"{len(contacts)} contacts ont été ajoutés avec succès!")
        return True
    
    except Exception as e:
        session.rollback()
        print(f"Erreur lors de l'ajout des contacts: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    create_test_contacts()