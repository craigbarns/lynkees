from app import app

# Modification de la configuration de Flask pour augmenter la limite de taille des requêtes
# Cette valeur doit être cohérente avec celle définie dans app.py
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max upload size

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)