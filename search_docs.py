import json
import os
import sys

search_terms = ["webuild", "we build", "sas web", "sas", "appel de charge", "appel des charges", "charges locatives", "relevé de charges", "relevé"]

document_dir = "static/document_contents"
results = []

# Parcourir tous les fichiers JSON dans le répertoire
for filename in os.listdir(document_dir):
    if filename.endswith(".json"):
        filepath = os.path.join(document_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                content = data.get("content", "").lower()
                
                for search_term in search_terms:
                    if search_term.lower() in content:
                        # Document contient le terme recherché
                        found_at = content.find(search_term.lower())
                        context = content[max(0, found_at-50):min(len(content), found_at+100)]
                        
                        result = {
                            "document_id": data.get("document_id"),
                            "filename": data.get("filename"),
                            "found_term": search_term,
                            "context": context.replace('\n', ' ').strip(),
                            "document_type": data.get("document_type"),
                            "document_date": data.get("document_date")
                        }
                        
                        # Vérifier si ce document n'a pas déjà été ajouté
                        doc_id = data.get("document_id")
                        if not any(r.get("document_id") == doc_id for r in results):
                            results.append(result)
                        break  # Passer au document suivant une fois qu'un terme a été trouvé
        except Exception as e:
            print(f"Erreur lors de la lecture de {filepath}: {str(e)}")

# Afficher les résultats
if results:
    print(f"Trouvé {len(results)} document(s) pertinent(s):\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['filename']} (ID: {result['document_id']})")
        print(f"   Terme trouvé: '{result['found_term']}'")
        if result.get("document_type"):
            print(f"   Type: {result['document_type']}")
        if result.get("document_date"):
            print(f"   Date: {result['document_date']}")
        print(f"   Contexte: \"...{result['context']}...\"")
        print("")
else:
    print(f"Aucun document contenant les termes recherchés n'a été trouvé.")