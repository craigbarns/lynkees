from main import app
from models import Document, db

with app.app_context():
    # Vérifier si les documents existent réellement dans le système de fichiers
    print("Vérification des fichiers manquants...")
    import os
    missing_docs = []
    for doc in Document.query.all():
        filepath = os.path.join("static/uploads", doc.filepath)
        if not os.path.exists(filepath):
            print(f"Fichier manquant: {doc.filename} (ID: {doc.id}, Chemin: {filepath})")
            missing_docs.append(doc)
    
    print(f"Total de documents manquants: {len(missing_docs)}")
    
    # Supprimer automatiquement les entrées sans demander de confirmation
    if missing_docs:
        for doc in missing_docs:
            print(f"Suppression de l'entrée pour: {doc.filename} (ID: {doc.id})")
            db.session.delete(doc)
        db.session.commit()
        print("Nettoyage terminé.")