from app import app, db
from models import Company, Document

with app.app_context():
    # Create tables for companies
    print("Création des tables pour les sociétés et documents...")
    db.create_all()
    print("Tables créées avec succès !")