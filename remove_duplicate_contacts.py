"""
Script pour supprimer les contacts en double dans la base de données
Ce script identifie les doublons en se basant sur le nom, prénom et la catégorie
"""

from app import app, db
from models import Contact
from sqlalchemy import func

def remove_duplicate_contacts():
    """Supprime les contacts en double de la base de données"""
    with app.app_context():
        print("Recherche des doublons potentiels...")
        
        # Groupe les contacts par nom, prénom et catégorie, et compte les occurrences
        duplicates = db.session.query(
            Contact.first_name,
            Contact.last_name,
            Contact.category,
            func.count(Contact.id).label('count')
        ).group_by(
            Contact.first_name,
            Contact.last_name,
            Contact.category
        ).having(func.count(Contact.id) > 1).all()
        
        if not duplicates:
            print("Aucun doublon trouvé.")
            return
        
        print(f"Nombre de groupes avec doublons: {len(duplicates)}")
        
        # Pour chaque groupe de doublons
        for first_name, last_name, category, count in duplicates:
            print(f"\nDoublons trouvés: {first_name} {last_name} ({category}) - {count} occurrences")
            
            # Récupère tous les contacts de ce groupe
            contacts = db.session.query(Contact).filter(
                Contact.first_name == first_name,
                Contact.last_name == last_name,
                Contact.category == category
            ).order_by(Contact.id).all()
            
            # Garde le premier (avec l'ID le plus bas), supprime les autres
            keep = contacts[0]
            print(f"Contact conservé: ID {keep.id}")
            
            for contact in contacts[1:]:
                print(f"Suppression du doublon: ID {contact.id}")
                db.session.delete(contact)
            
        # Sauvegarde les changements
        db.session.commit()
        print("\nNettoyage terminé. Vérifiez la base de données pour confirmer les suppressions.")

if __name__ == "__main__":
    remove_duplicate_contacts()