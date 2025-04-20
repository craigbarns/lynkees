import os
import json
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from models import Document, db

# Création d'un Blueprint pour les routes de gestion de fichiers
file_handler = Blueprint('file_handler', __name__)

# Configuration des téléchargements
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Crée le dossier s'il n'existe pas

# Dossier temporaire pour les morceaux de fichier
TEMP_UPLOAD_FOLDER = 'static/uploads/temp'
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)  # Crée le dossier temporaire s'il n'existe pas

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(filename):
    """Génère un nom de fichier unique pour éviter les écrasements"""
    # Récupérer l'extension du fichier
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    # Créer un nom unique avec horodatage et UUID
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}"
    if ext:
        unique_name = f"{unique_name}.{ext}"
    return unique_name

@file_handler.route('/api/init-upload', methods=['POST'])
def init_upload():
    """Initialise un téléchargement de fichier"""
    if 'filename' not in request.form or 'property_id' not in request.form:
        return jsonify({'error': 'Missing filename or property_id'}), 400
    
    # Vérifier l'authentification
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    filename = request.form['filename']
    property_id = request.form['property_id']
    
    if not allowed_file(filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Sécuriser le nom de fichier et le rendre unique
    secure_name = secure_filename(filename)
    unique_filename = generate_unique_filename(secure_name)
    upload_id = str(uuid.uuid4())
    
    # Créer un dossier spécifique pour ce téléchargement
    upload_dir = os.path.join(TEMP_UPLOAD_FOLDER, upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Stocker les informations de téléchargement en session
    session['upload_info'] = {
        'upload_dir': upload_dir,
        'original_filename': secure_name,
        'unique_filename': unique_filename,
        'property_id': property_id,
        'chunks_received': 0,
        'total_size': 0
    }
    
    return jsonify({
        'status': 'initialized',
        'upload_id': upload_id
    })

@file_handler.route('/api/upload-chunk', methods=['POST'])
def upload_chunk():
    """Télécharge un morceau de fichier"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
        
    if 'upload_id' not in request.form or 'chunk_index' not in request.form or 'chunk' not in request.files:
        missing = []
        if 'upload_id' not in request.form: missing.append('upload_id')
        if 'chunk_index' not in request.form: missing.append('chunk_index')
        if 'chunk' not in request.files: missing.append('chunk')
        import logging
        logging.error(f"Paramètres manquants: {', '.join(missing)}. Form: {list(request.form.keys())}, Files: {list(request.files.keys())}")
        return jsonify({'error': f"Paramètres manquants: {', '.join(missing)}"}), 400
    
    upload_id = request.form['upload_id']
    chunk_index = int(request.form['chunk_index'])
    chunk_file = request.files['chunk']
    
    # Vérifier si ce téléchargement est en cours
    upload_info = session.get('upload_info')
    if not upload_info:
        import logging
        logging.error(f"Upload non initialisé. Session: {session.keys()}")
        return jsonify({'error': 'Upload not initialized'}), 400
    
    # Enregistrer le morceau dans un fichier séparé
    upload_dir = upload_info['upload_dir']
    chunk_path = os.path.join(upload_dir, f"chunk_{chunk_index}")
    
    import logging
    logging.info(f"Réception du morceau {chunk_index} pour l'upload {upload_id}, taille: {request.content_length} octets")
    
    try:
        # Sauvegarder le morceau dans son propre fichier
        chunk_file.save(chunk_path)
        chunk_size = os.path.getsize(chunk_path)
        
        # Mettre à jour les compteurs
        upload_info['chunks_received'] = upload_info.get('chunks_received', 0) + 1
        upload_info['total_size'] = upload_info.get('total_size', 0) + chunk_size
        session['upload_info'] = upload_info
        
        logging.info(f"Morceau {chunk_index} enregistré avec succès, taille: {chunk_size} octets, total reçu: {upload_info['chunks_received']} morceaux")
        
        return jsonify({
            'status': 'chunk_received',
            'chunks_received': upload_info['chunks_received'],
            'total_size': upload_info['total_size']
        })
    except Exception as e:
        logging.error(f"Erreur lors de l'enregistrement du morceau {chunk_index}: {str(e)}")
        if os.path.exists(chunk_path):
            os.remove(chunk_path)
        return jsonify({'error': str(e)}), 500

@file_handler.route('/api/finalize-upload', methods=['POST'])
def finalize_upload():
    """Finalise le téléchargement et crée l'entrée en base de données"""
    import logging
    
    if 'user_id' not in session:
        logging.error("Tentative de finalisation sans authentification")
        return jsonify({'error': 'Authentication required'}), 401
        
    if 'upload_id' not in request.form:
        logging.error(f"Paramètre upload_id manquant. Form: {list(request.form.keys())}")
        return jsonify({'error': 'Missing upload_id'}), 400
    
    upload_id = request.form['upload_id']
    logging.info(f"Finalisation de l'upload {upload_id}")
    
    # Vérifier si ce téléchargement est en cours
    upload_info = session.get('upload_info')
    if not upload_info:
        logging.error(f"Upload non initialisé. Session: {session.keys()}")
        return jsonify({'error': 'Upload not initialized'}), 400
    
    upload_dir = upload_info['upload_dir']
    final_path = os.path.join(UPLOAD_FOLDER, upload_info['unique_filename'])
    
    try:
        # Vérifier que le répertoire des morceaux existe
        if not os.path.exists(upload_dir):
            logging.error(f"Répertoire des morceaux inexistant: {upload_dir}")
            return jsonify({'error': 'Chunks directory not found'}), 500
        
        # Assembler tous les morceaux en un seul fichier final
        chunks_count = upload_info['chunks_received']
        logging.info(f"Assemblage de {chunks_count} morceaux depuis {upload_dir}")
        
        with open(final_path, 'wb') as output_file:
            # Parcourir tous les morceaux dans l'ordre
            for i in range(chunks_count):
                chunk_path = os.path.join(upload_dir, f"chunk_{i}")
                if os.path.exists(chunk_path):
                    chunk_size = os.path.getsize(chunk_path)
                    logging.info(f"Traitement du morceau {i}, taille: {chunk_size} octets")
                    with open(chunk_path, 'rb') as chunk_file:
                        output_file.write(chunk_file.read())
                else:
                    logging.warning(f"Morceau {i} manquant: {chunk_path}")
        
        # Vérifier que le fichier final a été créé
        if not os.path.exists(final_path):
            logging.error(f"Échec de création du fichier final: {final_path}")
            return jsonify({'error': 'Failed to create final file'}), 500
            
        final_size = os.path.getsize(final_path)
        logging.info(f"Fichier final créé avec succès, taille: {final_size} octets")
            
        # Créer l'entrée en base de données
        document = Document(
            property_id=upload_info['property_id'],
            filename=upload_info['original_filename'],
            filepath=upload_info['unique_filename']
        )
        
        db.session.add(document)
        db.session.commit()
        logging.info(f"Document enregistré en base de données, ID: {document.id}")
        
        # Nettoyer les fichiers temporaires
        import shutil
        if os.path.exists(upload_dir):
            logging.info(f"Nettoyage du répertoire temporaire: {upload_dir}")
            shutil.rmtree(upload_dir)
        
        # Supprimer les informations de téléchargement de la session
        session.pop('upload_info', None)
        
        return jsonify({
            'status': 'success',
            'document_id': document.id,
            'filename': document.filename
        })
    except Exception as e:
        # Nettoyer en cas d'erreur
        if os.path.exists(final_path):
            os.remove(final_path)
            
        # Journaliser l'erreur pour faciliter le débogage
        logging.error(f"Erreur lors de la finalisation du téléversement: {str(e)}", exc_info=True)
        
        return jsonify({'error': str(e)}), 500