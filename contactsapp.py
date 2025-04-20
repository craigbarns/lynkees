#!/usr/bin/env python3
"""
Script pour exécuter une application contacts sans authentification
Ce fichier est conçu pour être facilement exécuté depuis la ligne de commande
"""
import sys
import logging
from standalone_contacts_app import app

if __name__ == "__main__":
    # Configurer le logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Par défaut, port 5001
    port = 5001
    
    # Si un argument a été fourni, essayer de l'utiliser comme port
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logging.warning(f"Port invalide spécifié: {sys.argv[1]}. Utilisation du port par défaut: 5001")
    
    logging.info(f"Démarrage de l'application de contacts sur le port {port}")
    
    # Lancer l'application
    app.run(host="0.0.0.0", port=port, debug=True)