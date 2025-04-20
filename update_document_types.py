"""
Script pour mettre à jour les types de documents basés sur leur nom de fichier
"""

from app import app
from models import Document, db
import os

def update_document_types():
    """Met à jour les types de documents basés sur leurs noms de fichier"""
    with app.app_context():
        # Récupérer tous les documents sans type défini
        documents = Document.query.filter(Document.document_type.is_(None)).all()
        
        updated_count = 0
        for doc in documents:
            filename = doc.filename.upper()
            
            # Déterminer le type basé sur le nom du fichier
            if 'BAIL' in filename:
                doc.document_type = 'Bail'
            elif 'DPE' in filename or 'DIAG' in filename:
                doc.document_type = 'DPE'
            elif 'VISALE' in filename:
                doc.document_type = 'VISALE'
            elif 'ASSURANCE' in filename and 'LOCATAIRE' in filename:
                doc.document_type = 'Assurance locataire'
            elif 'ASSURANCE' in filename:
                doc.document_type = 'Assurance'
            elif 'ETAT' in filename and 'LIEUX' in filename:
                doc.document_type = 'État des lieux'
            elif 'CAUTION' in filename:
                doc.document_type = 'Caution'
            elif 'RELEVE' in filename or 'BANCAIRE' in filename:
                doc.document_type = 'Relevé'
            elif 'FACTURE' in filename:
                doc.document_type = 'Facture'
            elif 'IMPOT' in filename or 'TAXE' in filename:
                doc.document_type = 'Impôt'
            elif 'CONTRAT' in filename:
                doc.document_type = 'Contrat'
            elif 'APPEL' in filename or 'CHARGES' in filename:
                doc.document_type = 'Appel de charges'
            else:
                doc.document_type = 'Autre'
            
            print(f"Document '{doc.filename}' mis à jour: type = '{doc.document_type}'")
            updated_count += 1
        
        # Sauvegarder les modifications
        if updated_count > 0:
            db.session.commit()
            print(f"{updated_count} documents ont été mis à jour.")
        else:
            print("Aucun document n'a nécessité de mise à jour.")

if __name__ == "__main__":
    update_document_types()