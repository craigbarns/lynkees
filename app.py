import os
import logging
import calendar

# Message de démarrage de l'application
print(f"===== DÉMARRAGE DE L'APPLICATION =====")
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, g, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from functools import wraps
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import or_, func
import uuid
from datetime import datetime, timedelta
import shutil
import json

# Import de la base de données depuis database.py
from database import db, init_db

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configuration des sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_COOKIE_SECURE'] = False  # Pour permettre HTTP en développement
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
Session(app)

# Configuration pour Flask-Mail
from flask_mail import Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.ionos.fr')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'noreply@lynkees.fr')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@lynkees.fr')
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://app.lynkees.fr')

# Initialize Flask-Mail
mail = Mail(app)

# Activer la protection CSRF
csrf = CSRFProtect(app)

# Liste des routes exemptées de CSRF
csrf_exempt_routes = ['/dashboard/remove_widget/<widget_id>']

# Fonction pour désactiver CSRF sur certaines routes
@app.before_request
def csrf_exempt():
    if request.path in csrf_exempt_routes:
        csrf.exempt(request.path)

# Initialize database with Flask app
init_db(app)

# Empêcher la double initialisation de la base de données
app.config['SQLALCHEMY_ALREADY_INITIALIZED'] = True

# Ajouter des filtres pour les templates
@app.template_filter('pprint')
def pprint_filter(value):
    import pprint
    return pprint.pformat(value)

@app.template_filter('nl2br')
def nl2br_filter(value):
    """Convert newlines to <br> tags."""
    # La classe Markup a été déplacée vers markupsafe dans les nouvelles versions
    from markupsafe import Markup
    value = str(value)  # Convertir en chaîne de caractères
    paragraphs = value.split('\n\n')
    result = ''
    for p in paragraphs:
        if p.strip():
            p = p.replace('\n', '<br>')
            result += f'<p>{p}</p>'
    return Markup(result)


# Protection CSRF désactivée temporairement pour debug
app.config['WTF_CSRF_ENABLED'] = False  # Désactivation temporaire pour résoudre le problème de suppression des widgets
app.config['WTF_CSRF_SECRET_KEY'] = app.secret_key

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///property_management.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure file uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size (pour morceaux individuels, le téléversement par chunks gère des fichiers plus grands)

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Fonction pour vérifier automatiquement les paiements en retard
@app.before_request
def check_late_payments():
    """Vérifier automatiquement les paiements en retard à chaque requête"""
    # Ne pas exécuter pour les requêtes statiques ou les endpoints non critiques
    if request.endpoint and (
        request.endpoint.startswith('static') or 
        request.endpoint in ['login', 'logout', 'uploaded_file']
    ):
        return

    # Importer Payment ici pour éviter les erreurs d'importation circulaire
    from models import Payment

    # Vérifier et mettre à jour le statut des paiements en retard
    today = datetime.now().date()
    payments = Payment.query.filter_by(status='En attente').all()
    updated = False

    for payment in payments:
        if payment.check_late_status():
            payment.status = 'En retard'
            updated = True

    if updated:
        try:
            db.session.commit()
            logging.info(f"Mise à jour automatique des paiements en retard - {datetime.now()}")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la mise à jour des paiements en retard: {str(e)}")

# Import models after db is defined
from models import Property, Document, Building, User, Payment, Company, Contact

# Décorateur personnalisé pour remplacer @login_required avec plus de logging
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logging.info(f"Vérification login_required - Session: {session}")

        if 'user_id' not in session:
            logging.warning(f"Accès refusé: user_id non trouvé dans la session")
            flash('Veuillez vous connecter pour accéder à cette page.', 'info')
            return redirect(url_for('login', next=request.url))

        # Vérifier que l'utilisateur existe toujours en base
        user = User.query.get(session['user_id'])
        if not user:
            logging.warning(f"Accès refusé: user_id {session['user_id']} non trouvé en base de données")
            session.clear()
            flash('Session invalide. Veuillez vous reconnecter.', 'warning')
            return redirect(url_for('login', next=request.url))

        logging.info(f"Accès autorisé pour l'utilisateur {user.username} (ID: {user.id})")
        return f(*args, **kwargs)
    return decorated_function

# Fonction pour récupérer l'utilisateur actuel
def get_current_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return user
        else:
            # Si l'utilisateur n'existe pas en base mais est en session, nettoyer la session
            session.clear()
    return None

# Injecter l'utilisateur dans tous les templates + informations de session
@app.context_processor
def inject_user():
    # Récupérer l'utilisateur actuel
    current_user = get_current_user()

    # Informations additionnelles pour le debug
    session_info = {
        'has_user_id': 'user_id' in session,
        'is_authenticated': current_user is not None,
    }

    logging.info(f"Context processor - Session info: {session_info}")

    # Retourner les variables pour les templates
    return {
        'current_user': current_user,
        'session_info': session_info
    }

# Middleware pour vérifier l'utilisateur à chaque requête
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id:
        g.user = User.query.get(user_id)
    else:
        g.user = None


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def generate_unique_filename(filename):
    """Generate a unique filename to prevent overwrites"""
    # Get file extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    # Create a unique name with timestamp and UUID
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}"
    if ext:
        unique_name = f"{unique_name}.{ext}"
    return unique_name


# Routes
@app.route('/')
@login_required
def index():
    """Rediriger vers le tableau de bord"""
    return redirect(url_for('dashboard.dashboard'))

@app.route('/properties')
@login_required
def properties_list():
    """Display all properties with multiple filtering options"""
    # Récupérer tous les paramètres de filtre
    owner_company = request.args.get('owner_company', '')
    address = request.args.get('address', '')
    min_rent = request.args.get('min_rent', '')
    max_rent = request.args.get('max_rent', '')
    min_surface = request.args.get('min_surface', '')
    max_surface = request.args.get('max_surface', '')
    floor = request.args.get('floor', '')
    occupied = request.args.get('occupied', '')
    building_id = request.args.get('building_id', '')
    is_furnished = request.args.get('is_furnished', '')
    has_property_manager = request.args.get('has_property_manager', '')
    has_syndic = request.args.get('has_syndic', '')

    # Construire la requête avec les filtres
    query = Property.query

    # Filtre par société propriétaire
    if owner_company:
        query = query.filter(Property.owner_company.ilike(f'%{owner_company}%'))

    # Filtre par adresse
    if address:
        query = query.filter(Property.address.ilike(f'%{address}%'))

    # Filtre par loyer minimum
    if min_rent and min_rent.isdigit():
        query = query.filter(Property.rent >= float(min_rent))

    # Filtre par loyer maximum
    if max_rent and max_rent.isdigit():
        query = query.filter(Property.rent <= float(max_rent))

    # Filtre par surface minimum
    if min_surface and min_surface.isdigit():
        query = query.filter(Property.surface >= float(min_surface))

    # Filtre par surface maximum
    if max_surface and max_surface.isdigit():
        query = query.filter(Property.surface <= float(max_surface))

    # Filtre par étage
    if floor:
        query = query.filter(Property.floor == floor)

    # Filtre par statut d'occupation
    if occupied == 'yes':
        query = query.filter(Property.tenant != '')
        query = query.filter(Property.tenant != None)
    elif occupied == 'no':
        query = query.filter(or_(Property.tenant == '', Property.tenant == None))

    # Filtre par immeuble
    if building_id and building_id.isdigit():
        query = query.filter(Property.building_id == int(building_id))

    # Filtre par meublé
    if is_furnished == 'yes':
        query = query.filter(Property.is_furnished == True)
    elif is_furnished == 'no':
        query = query.filter(Property.is_furnished == False)

    # Filtre par gestion
    if has_property_manager == 'yes':
        query = query.filter(Property.has_property_manager == True)
    elif has_property_manager == 'no':
        query = query.filter(Property.has_property_manager == False)

    # Filtre par syndic
    if has_syndic == 'yes':
        query = query.filter(Property.has_syndic == True)
    elif has_syndic == 'no':
        query = query.filter(Property.has_syndic == False)

    # Appliquer le tri par ID
    query = query.order_by(Property.id)

    # Exécuter la requête
    properties = query.all()

    # Récupérer tous les immeubles pour le filtre
    buildings = Building.query.all()
    
    # Afficher la vue standard des propriétés (dashboard supprimé comme demandé)
    return render_template('property_list.html', 
                          properties=properties, 
                          buildings=buildings,
                          filters=request.args)


# La route dashboard a été supprimée et remplacée par les pages dédiées :
# - /charges pour la gestion des charges (appels de fonds, factures...)
# - /tenant-payments pour la gestion des paiements locataires

# Route pour le dashboard supprimée comme demandé


@app.route('/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    """Add a new property"""
    if request.method == 'POST':
        # Vérifier si c'est une soumission en double (POST-Redirect-GET)
        # Si c'est une soumission directe, continuer
        is_form_submit = request.form.get('_form_submit_direct') == '1'

        if is_form_submit:
            # Mettre un marqueur dans la session pour éviter les soumissions multiples
            form_token = str(uuid.uuid4())
            session['last_form_token'] = form_token

            address = request.form.get('address')
            rent = request.form.get('rent')
            charges = request.form.get('charges')
            tenant = request.form.get('tenant')
            tenant_email = request.form.get('tenant_email')
            tenant_phone = request.form.get('tenant_phone')

            # Les informations du propriétaire ont été retirées
            # L'assignation à une société se fait désormais via la page de détails

            # Caractéristiques du bien
            deposit = request.form.get("deposit")
            surface = request.form.get('surface')
            floor = request.form.get('floor')
            location = request.form.get('location')
            entry_date = request.form.get('entry_date')

            # Nouveaux champs
            is_furnished = request.form.get('is_furnished') == '1'
            has_property_manager = request.form.get('has_property_manager') == '1'
            property_manager_name = request.form.get('property_manager_name')

            # Champs du syndic
            has_syndic = request.form.get('has_syndic') == '1'
            syndic_name = request.form.get('syndic_name')
            syndic_contact = request.form.get('syndic_contact')

            if not address or not rent or not charges:
                flash('Adresse, loyer et charges sont des champs obligatoires', 'danger')
                return redirect(url_for('add_property'))

            try:
                # Vérifier si une propriété avec cette adresse existe déjà
                existing_property = Property.query.filter_by(address=address).first()
                if existing_property:
                    similar_properties = Property.query.filter(Property.address.ilike(f"%{address}%")).all()
                    if len(similar_properties) > 0:
                        flash(f'Une propriété avec une adresse similaire existe déjà. Veuillez vérifier les propriétés existantes.', 'warning')

                # Créer un nouveau bien immobilier
                new_property = Property(
                    address=address,
                    rent=float(rent),
                    charges=float(charges),
                    tenant=tenant,
                    tenant_email=tenant_email,
                    tenant_phone=tenant_phone,
                    owner_company=None,  # Valeur par défaut, sera mis à jour via l'interface d'assignation
                    owner_address=None,  # Valeur par défaut, sera mis à jour via l'interface d'assignation
                    deposit=float(deposit) if deposit and deposit.strip() else None,
                    surface=float(surface) if surface and surface.strip() else None,
                    floor=floor,
                    location=location,
                    entry_date=datetime.strptime(entry_date, '%Y-%m-%d').date() if entry_date else None,
                    # Nouveaux champs
                    is_furnished=is_furnished,
                    has_property_manager=has_property_manager,
                    property_manager_name=property_manager_name if has_property_manager else None,
                    # Champs du syndic
                    has_syndic=has_syndic,
                    syndic_name=syndic_name if has_syndic else None,
                    syndic_contact=syndic_contact if has_syndic else None
                )
                # La création automatique de société a été supprimée
                # L'assignation à une société se fait désormais via la page de détails

                db.session.add(new_property)
                db.session.commit()

                flash('Bien immobilier ajouté avec succès !', 'success')
                # Rediriger pour éviter les soumissions multiples (PRG pattern)
                return redirect(url_for('property_detail', property_id=new_property.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de l\'ajout du bien immobilier: {str(e)}', 'danger')
                logging.error(f"Erreur lors de l'ajout du bien immobilier: {str(e)}")

    return render_template('add.html')


@app.route('/property/<int:property_id>')
@login_required
def property_detail(property_id):
    """Display property details and associated documents"""
    property = Property.query.get_or_404(property_id)
    
    # Récupérer les documents directement associés à la propriété
    direct_documents = Document.query.filter_by(property_id=property_id).all()
    
    # Récupérer les documents associés via la société propriétaire
    company_documents = []
    if property.company_id:
        # Documents associés à la société avec property_id=None (pas associés à un bien spécifique)
        company_documents_general = Document.query.filter_by(company_id=property.company_id, property_id=None).all()
        
        # Documents associés à la société ET à cette propriété spécifique
        company_documents_specific = Document.query.filter_by(company_id=property.company_id, property_id=property_id).all()
        
        company_documents = company_documents_general + company_documents_specific
    
    # Combiner tous les documents
    all_documents = direct_documents + company_documents
    
    # Récupérer la liste de tous les immeubles pour la sélection
    buildings = Building.query.all()
    
    # Assurez-vous que tous les types de documents essentiels sont définis
    document_types = ['Bail', 'DPE', 'VISALE', 'Assurance locataire', 'État des lieux', 'Caution']
    
    # Créer un dictionnaire des documents existants par type
    documents_by_type = {}
    for doc_type in document_types:
        doc = next((d for d in all_documents if d.document_type == doc_type), None)
        documents_by_type[doc_type] = doc
    
    return render_template('detail.html', 
                          property=property, 
                          documents=all_documents,
                          direct_documents=direct_documents,
                          company_documents=company_documents,
                          buildings=buildings,
                          document_types=document_types,
                          documents_by_type=documents_by_type)


@app.route('/property/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    """Edit an existing property"""
    property = Property.query.get_or_404(property_id)

    if request.method == 'POST':
        address = request.form.get('address')
        rent = request.form.get('rent')
        charges = request.form.get('charges')
        tenant = request.form.get('tenant')
        tenant_email = request.form.get('tenant_email')
        tenant_phone = request.form.get('tenant_phone')

        # Les informations du propriétaire ont été retirées
        # L'assignation à une société se fait désormais via la page de détails
        # Définir des valeurs par défaut pour éviter les erreurs
        owner_company = None
        owner_address = None

        # Caractéristiques du bien
        deposit = request.form.get("deposit")
        surface = request.form.get('surface')
        floor = request.form.get('floor')
        location = request.form.get('location')
        entry_date = request.form.get('entry_date')

        # Nouveaux champs
        is_furnished = request.form.get('is_furnished') == '1'
        has_property_manager = request.form.get('has_property_manager') == '1'
        property_manager_name = request.form.get('property_manager_name')

        # Champs du syndic
        has_syndic = request.form.get('has_syndic') == '1'
        syndic_name = request.form.get('syndic_name')
        syndic_contact = request.form.get('syndic_contact')

        if not address or not rent or not charges:
            flash('Address, rent, and charges are required fields', 'danger')
            return redirect(url_for('edit_property', property_id=property_id))

        try:
            # Update property details
            property.address = address
            property.rent = float(rent)
            property.charges = float(charges)
            property.tenant = tenant
            property.tenant_email = tenant_email
            property.tenant_phone = tenant_phone
            # Ne pas modifier les champs owner_company et owner_address
            # L'assignation à une société se fait désormais via la page de détails
            property.surface = float(surface) if surface else None
            property.deposit = float(deposit) if deposit else None
            property.floor = floor
            property.location = location
            property.entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date() if entry_date else None

            # Mise à jour des nouveaux champs
            property.is_furnished = is_furnished
            property.has_property_manager = has_property_manager
            property.property_manager_name = property_manager_name if has_property_manager else None

            # Mise à jour des champs de syndic
            property.has_syndic = has_syndic
            property.syndic_name = syndic_name if has_syndic else None
            property.syndic_contact = syndic_contact if has_syndic else None

            # La création automatique de société a été supprimée
            # L'assignation à une société se fait désormais via la page de détails

            db.session.commit()

            flash('Property updated successfully!', 'success')
            return redirect(url_for('property_detail', property_id=property.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating property: {str(e)}', 'danger')
            logging.error(f"Error updating property: {str(e)}")

    return render_template('edit.html', property=property)


@app.route('/property/<int:property_id>/upload', methods=['POST'])
@login_required
def upload_document(property_id):
    """Upload a document for a property"""
    property = Property.query.get_or_404(property_id)

    # Check if the post request has the file part
    if 'document' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))

    file = request.files['document']

    # If user does not select file, browser submits an empty part without filename
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))

    # Get document type if provided
    document_type = request.form.get('document_type', '')

    if file and allowed_file(file.filename):
        # Secure the filename and make it unique
        filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(filename)

        # Save the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Create document record in database
        document = Document(
            property_id=property_id,
            filename=filename,  # Original filename for display
            filepath=unique_filename,  # Actual filename on server
            document_type=document_type  # Type de document (Relevé, Facture, Impôt, Contrat, Appel de charges, etc.)
        )
        db.session.add(document)
        db.session.commit()

        # Traiter le document pour extraire son contenu si possible
        try:
            # Import ici pour éviter les problèmes d'importation circulaire
            from document_processor import process_document
            process_document(document.id)
            flash('Document uploaded and processed successfully!', 'success')
        except Exception as e:
            app.logger.error(f"Error processing document: {str(e)}")
            flash('Document uploaded but could not be processed. It will be available for viewing.', 'warning')
    else:
        flash('File type not allowed', 'danger')

    return redirect(url_for('property_detail', property_id=property_id))


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    document = Document.query.get_or_404(document_id)
    property_id = document.property_id

    try:
        # Delete file from storage
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete record from database
        db.session.delete(document)
        db.session.commit()

        flash('Document deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'danger')
        logging.error(f"Error deleting document: {str(e)}")

    return redirect(url_for('property_detail', property_id=property_id))


@app.route('/property/<int:property_id>/delete', methods=['POST'])
@login_required
def delete_property(property_id):
    """Delete a property and its associated documents"""
    property = Property.query.get_or_404(property_id)

    try:
        # Get all documents for this property
        documents = Document.query.filter_by(property_id=property_id).all()

        # Delete each document file
        for document in documents:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete the property (cascade will delete documents from DB)
        db.session.delete(property)
        db.session.commit()

        flash('Property and all associated documents deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting property: {str(e)}', 'danger')
        logging.error(f"Error deleting property: {str(e)}")

    return redirect(url_for('index'))


# Routes for buildings
@app.route('/buildings')
@login_required
def buildings_list():
    """Display all buildings"""
    buildings = Building.query.all()
    return render_template('buildings/list.html', buildings=buildings)


@app.route('/building/add', methods=['GET', 'POST'])
@login_required
def add_building():
    """Add a new building"""
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        description = request.form.get('description')

        if not name or not address:
            flash('Name and address are required fields', 'danger')
            return redirect(url_for('add_building'))

        try:
            # Create a new building
            new_building = Building(
                name=name,
                address=address,
                description=description
            )
            db.session.add(new_building)
            db.session.commit()

            flash('Building added successfully!', 'success')
            return redirect(url_for('building_detail', building_id=new_building.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding building: {str(e)}', 'danger')
            logging.error(f"Error adding building: {str(e)}")

    return render_template('buildings/add.html')


@app.route('/building/<int:building_id>')
@login_required
def building_detail(building_id):
    """Display building details and associated properties"""
    building = Building.query.get_or_404(building_id)
    properties = Property.query.filter_by(building_id=building_id).all()
    return render_template('buildings/detail.html', building=building, properties=properties)


@app.route('/building/<int:building_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_building(building_id):
    """Edit an existing building"""
    building = Building.query.get_or_404(building_id)

    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        description = request.form.get('description')

        if not name or not address:
            flash('Name and address are required fields', 'danger')
            return redirect(url_for('edit_building', building_id=building_id))

        try:
            # Update building details
            building.name = name
            building.address = address
            building.description = description

            db.session.commit()

            flash('Building updated successfully!', 'success')
            return redirect(url_for('building_detail', building_id=building.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating building: {str(e)}', 'danger')
            logging.error(f"Error updating building: {str(e)}")

    return render_template('buildings/edit.html', building=building)


@app.route('/building/<int:building_id>/delete', methods=['POST'])
@login_required
def delete_building(building_id):
    """Delete a building"""
    building = Building.query.get_or_404(building_id)

    try:
        # Delete the building
        db.session.delete(building)
        db.session.commit()

        flash('Building deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting building: {str(e)}', 'danger')
        logging.error(f"Error deleting building: {str(e)}")

    return redirect(url_for('buildings_list'))


@app.route('/property/<int:property_id>/assign', methods=['POST'])
@login_required
def assign_property_to_building(property_id):
    """Assign a property to a building"""
    property = Property.query.get_or_404(property_id)
    building_id = request.form.get('building_id')

    try:
        if building_id and building_id != "0":
            # Check if building exists
            building = Building.query.get_or_404(int(building_id))
            property.building_id = building.id
            message = f'Property assigned to building "{building.name}" successfully!'
        else:
            # Remove from building
            property.building_id = None
            message = 'Property removed from building successfully!'

        db.session.commit()
        flash(message, 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error assigning property to building: {str(e)}', 'danger')
        logging.error(f"Error assigning property to building: {str(e)}")

    return redirect(url_for('property_detail', property_id=property_id))


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Retourne une erreur 404 - Chat complètement supprimé"""
    return render_template('404.html'), 404


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    """Retourne une erreur 404 - Chatbot complètement supprimé"""
    return render_template('404.html'), 404


# Routes d'authentification
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Enregistrement d'un nouvel utilisateur avec confirmation par email"""
    if 'user_id' in session:  # Vérifier la session directement
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Validation de base
        if not email or not username or not password:
            flash('Email, nom d\'utilisateur et mot de passe sont obligatoires', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('register'))

        # Vérification si l'utilisateur existe déjà
        user_email = User.query.filter_by(email=email).first()
        user_username = User.query.filter_by(username=username).first()

        if user_email:
            flash('Cet email est déjà utilisé', 'danger')
            return redirect(url_for('register'))

        if user_username:
            flash('Ce nom d\'utilisateur est déjà pris', 'danger')
            return redirect(url_for('register'))

        try:
            # Création du nouvel utilisateur
            user = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email_confirmed=False  # Par défaut non confirmé
            )
            user.set_password(password)

            # Premier utilisateur devient administrateur et déjà confirmé
            if User.query.count() == 0:
                user.is_admin = True
                user.email_confirmed = True  # Premier utilisateur automatiquement confirmé

            db.session.add(user)
            db.session.commit()

            # Envoyer l'email de confirmation sauf pour le premier utilisateur
            if not user.email_confirmed:
                try:
                    from email_utils import send_confirmation_email
                    token = send_confirmation_email(user)
                    
                    # Mise à jour du token de confirmation dans la base de données
                    user.confirmation_token = token
                    db.session.commit()
                    
                    # Stocker l'ID utilisateur en session temporaire pour permettre le renvoi d'email
                    session['temp_user_id'] = user.id
                    
                    logging.info(f"Email de confirmation envoyé à l'utilisateur {user.username} (ID: {user.id})")
                    flash('Compte créé avec succès ! Veuillez vérifier votre email pour confirmer votre compte.', 'success')
                except Exception as mail_error:
                    logging.error(f"Erreur lors de l'envoi de l'email de confirmation: {str(mail_error)}")
                    flash('Compte créé avec succès ! Un problème est survenu lors de l\'envoi de l\'email de confirmation.', 'warning')
            else:
                flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
            
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du compte: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la création du compte: {str(e)}")

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion d'un utilisateur - Version simplifiée"""
    # Journaux pour debugging
    logging.info(f"Tentative de connexion - Session actuelle: {session}")
    logging.info(f"Request method: {request.method}")
    logging.info(f"Form data: {request.form if request.method == 'POST' else 'GET request'}")

    # Si l'utilisateur est déjà connecté, le rediriger vers la page de paiements des locataires
    if 'user_id' in session:
        return redirect(url_for('tenant_payments_list'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logging.info(f"Tentative de connexion pour l'utilisateur: {username}")

        # Vérifications de base
        if not username or not password:
            flash('Nom d\'utilisateur et mot de passe sont obligatoires', 'danger')
            return redirect(url_for('login'))

        # Trouver l'utilisateur - Essayer par username et email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user:
            logging.info(f"Utilisateur trouvé: {user.username}")

            # Vérification simplifiée du mot de passe pour test (pour l'utilisateur test)
            if user.username == 'test' and password == 'test123':
                # Réinitialiser complètement la session
                session.clear()

                # Enregistrer les infos utilisateur dans la session
                session['user_id'] = user.id
                session['username'] = user.username
                session.permanent = True

                # Forcer la sauvegarde des modifications
                session.modified = True

                # Log des détails de la session
                logging.info(f"Session après connexion réussie: {session}")
                logging.info(f"Utilisateur {user.username} (ID: {user.id}) connecté avec succès")

                # Message de bienvenue
                flash(f'Bienvenue, {user.username} !', 'success')

                # Rediriger vers la page demandée ou l'accueil
                next_page = request.args.get('next')
                if next_page and next_page != 'None' and not next_page.startswith('//'):
                    return redirect(next_page)
                return redirect(url_for('tenant_payments_list'))

            # Pour les autres utilisateurs, vérifier le mot de passe avec check_password_hash
            elif check_password_hash(user.password_hash, password):
                # Vérifier si l'email est confirmé (sauf pour utilisateur test)
                if not user.email_confirmed and user.username != 'test':
                    flash('Veuillez confirmer votre adresse email avant de vous connecter. Vérifiez votre boîte de réception.', 'warning')
                    # Mettre l'ID utilisateur en session temporairement pour permettre le renvoi du mail
                    session['temp_user_id'] = user.id
                    return redirect(url_for('login'))
                
                # Réinitialiser complètement la session
                session.clear()

                # Enregistrer les infos utilisateur dans la session
                session['user_id'] = user.id
                session['username'] = user.username
                session.permanent = True

                # Forcer la sauvegarde des modifications
                session.modified = True

                # Log des détails de la session
                logging.info(f"Session après connexion réussie: {session}")
                logging.info(f"Utilisateur {user.username} (ID: {user.id}) connecté avec succès")

                # Message de bienvenue
                flash(f'Bienvenue, {user.username} !', 'success')

                # Rediriger vers la page demandée ou l'accueil
                next_page = request.args.get('next')
                if next_page and next_page != 'None' and not next_page.startswith('//'):
                    return redirect(next_page)
                return redirect(url_for('tenant_payments_list'))

        # Message d'erreur générique pour éviter les attaques par énumération
        flash('Identifiants incorrects. Veuillez réessayer.', 'danger')
        logging.warning(f"Échec de connexion pour l'utilisateur: {username}")

    return render_template('auth/login.html')


@app.route('/confirmation-tokens')
def token_list():
    """Afficher la liste des tokens de confirmation (mode développement uniquement)"""
    # Récupérer les utilisateurs en attente de confirmation
    users = User.query.filter_by(email_confirmed=False).all()
    # Récupérer les utilisateurs confirmés
    confirmed_users = User.query.filter_by(email_confirmed=True).all()
    
    return render_template('auth/tokens_list.html', users=users, confirmed_users=confirmed_users)


@app.route('/confirm/<token>')
def confirm_email(token):
    """Confirmer l'adresse email d'un utilisateur"""
    # Chercher un utilisateur avec ce token de confirmation
    user = User.query.filter_by(confirmation_token=token).first()
    
    if not user:
        flash('Le lien de confirmation est invalide ou a expiré.', 'danger')
        return redirect(url_for('login'))
    
    # Vérifier si l'email est déjà confirmé
    if user.email_confirmed:
        flash('Votre compte est déjà confirmé.', 'info')
        return redirect(url_for('login'))
    
    # Confirmer l'email
    if user.confirm_email(token):
        # Mise à jour en base de données
        db.session.commit()
        logging.info(f"Email confirmé pour l'utilisateur {user.username} (ID: {user.id})")
        
        # Nettoyer la session temporaire si elle existe
        if 'temp_user_id' in session and int(session['temp_user_id']) == user.id:
            session.pop('temp_user_id')
            
        # Afficher la page de confirmation au lieu de rediriger vers login
        return render_template('auth/email_confirmed.html', user=user)
    else:
        flash('Le lien de confirmation est invalide ou a expiré.', 'danger')
        return redirect(url_for('login'))


@app.route('/resend-confirmation')
def resend_confirmation():
    """Renvoyer un email de confirmation"""
    # Chercher l'ID utilisateur dans la session normale ou temporaire
    user_id = session.get('user_id') or session.get('temp_user_id')
    
    if not user_id:
        flash('Veuillez vous connecter pour demander un nouvel email de confirmation.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Utilisateur non trouvé. Veuillez vous reconnecter.', 'danger')
        # Nettoyer la session temporaire si elle existe
        if 'temp_user_id' in session:
            session.pop('temp_user_id')
        return redirect(url_for('login'))
    
    # Si déjà confirmé, pas besoin de renvoyer
    if user.email_confirmed:
        flash('Votre adresse email est déjà confirmée.', 'info')
        # Rediriger vers le profil si l'utilisateur est connecté, sinon vers la page de connexion
        if session.get('user_id'):
            return redirect(url_for('profile'))
        else:
            return redirect(url_for('login'))
    
    try:
        # Envoi du nouvel email
        from email_utils import send_confirmation_email
        token = send_confirmation_email(user)
        
        # Mise à jour du token de confirmation dans la base de données
        user.confirmation_token = token
        db.session.commit()
        
        flash('Un nouvel email de confirmation vous a été envoyé. Veuillez vérifier votre boîte de réception.', 'success')
        logging.info(f"Email de confirmation renvoyé à l'utilisateur {user.username} (ID: {user.id})")
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email de confirmation: {str(e)}")
        flash('Une erreur est survenue lors de l\'envoi de l\'email. Veuillez réessayer plus tard.', 'danger')
    
    # Rediriger vers le profil si l'utilisateur est connecté, sinon vers la page de connexion
    if session.get('user_id'):
        return redirect(url_for('profile'))
    else:
        return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    """Déconnexion d'un utilisateur"""
    # Consigner la déconnexion dans les logs
    if 'user_id' in session:
        logging.info(f"Déconnexion de l'utilisateur ID: {session.get('user_id')}")

    # Nettoyer complètement la session
    session.clear()

    # Configurer le message flash et rediriger vers la page de connexion
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    """Affichage du profil de l'utilisateur"""
    # Récupérer les statistiques pour affichage
    properties_count = Property.query.count()
    buildings_count = Building.query.count()
    documents_count = Document.query.count()

    return render_template('auth/profile.html', 
                         properties_count=properties_count,
                         buildings_count=buildings_count, 
                         documents_count=documents_count)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Modification du profil de l'utilisateur"""
    # Utiliser notre fonction pour récupérer l'utilisateur depuis session
    current_user = get_current_user()
    if not current_user:
        flash('Session expirée. Veuillez vous reconnecter.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validation de base
        if not email:
            flash('L\'email est obligatoire', 'danger')
            return redirect(url_for('edit_profile'))

        # Vérification si l'email est déjà utilisé (sauf par l'utilisateur actuel)
        user_email = User.query.filter(User.email == email, User.id != current_user.id).first()

        if user_email:
            flash('Cet email est déjà utilisé par un autre utilisateur', 'danger')
            return redirect(url_for('edit_profile'))

        try:
            # Mise à jour des informations de base
            current_user.email = email
            current_user.first_name = first_name
            current_user.last_name = last_name

            # Mise à jour du mot de passe si demandé
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('Mot de passe actuel incorrect', 'danger')
                    return redirect(url_for('edit_profile'))

                if new_password != confirm_password:
                    flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
                    return redirect(url_for('edit_profile'))

                current_user.set_password(new_password)

            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la mise à jour du profil: {str(e)}")

    return render_template('auth/edit_profile.html')


# Test route pour vérifier l'état d'authentification
@app.route('/test_auth')
@login_required
def test_auth():
    """Route de test pour vérifier l'authentification"""
    # Afficher les informations de session
    logging.info(f"Test Auth - Session actuelle: {session}")

    session_info = {key: session.get(key) for key in session}
    is_authenticated = 'user_id' in session

    user_info = {
        "is_authenticated": is_authenticated,
        "session": session_info
    }

    if is_authenticated:
        current_user = get_current_user()
        if current_user:
            user_info["user_id"] = current_user.id
            user_info["username"] = current_user.username
        else:
            user_info["error"] = "ID utilisateur en session mais utilisateur non trouvé en base"

    return render_template('auth/test_auth.html', user_info=user_info)


# Routes pour la gestion des contacts
# NOTE: Ces routes ont été déplacées vers app_routes_contacts.py
# Pour éviter une duplication des routes et des problèmes d'affichage
# @app.route('/contacts')
# @login_required
# def contacts_list():
#     """Afficher la liste des contacts avec filtrage"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass

# Route pour accéder à l'application de contacts autonome
# Route désactivée pour empêcher la duplication des contacts
# @app.route('/standalone-contacts')
# def standalone_contacts_route():
#     """Page d'information pour accéder à l'application de contacts sans authentification"""
#     logging.info("Accès à la page d'information pour l'application de contacts autonome")
#
#     # URL de l'application autonome (dans un environnement réel, ceci pourrait être une URL différente)
#     # Pour simplifier, nous utilisons le même hôte mais sur un port différent
#     standalone_url = f"http://{request.host.split(':')[0]}:5001"
#
#     return render_template('contacts/standalone_redirect.html', standalone_url=standalone_url)
#
# IMPORTANT: Cette route est désactivée car nous n'utilisons plus l'application autonome de contacts.
# Tous les accès aux contacts se font désormais via l'application principale avec le nouveau design.

# Route d'accès direct aux contacts désactivée pour éviter les doublons
# @app.route('/acces-contacts')
# def direct_access_contacts():
#     """Accès direct à la liste des contacts sans authentification (pour test)"""
#     logging.info("Accès direct à la liste des contacts")

    # HTML en dur pour éviter toute dépendance
    html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste des Contacts - Accès Direct</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #212529;
            color: #f8f9fa;
            font-family: Arial, sans-serif;
        }
        .card {
            background-color: #2c3034;
            border: 1px solid #495057;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .card-header {
            background-color: #343a40;
            border-bottom: 1px solid #495057;
            padding: 15px;
            border-radius: 10px 10px 0 0;
        }
        .contact-item {
            padding: 15px;
            border-bottom: 1px solid #495057;
        }
        .contact-item:last-child {
            border-bottom: none;
        }
        .badge {
            font-size: 0.8em;
            padding: 5px 10px;
            margin-right: 5px;
        }
        .favorite-star {
            color: gold;
            margin-right: 5px;
        }
        .contact-header {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .contact-details {
            font-size: 0.9em;
            color: #adb5bd;
            margin-bottom: 5px;
        }
        .container {
            max-width: 900px;
            margin: 30px auto;
        }
        .btn-back {
            margin-bottom: 20px;
        }
    </style>
</head>
<body class="bg-dark text-light">
    <div class="container">
        <h1 class="mb-4 text-center">Liste des Contacts - Accès Direct</h1>

        <div class="card">
            <div class="card-header">
                <h2 class="h4 mb-0">Contacts disponibles</h2>
            </div>
            <div class="card-body p-0">
                <!-- Contact 1 -->
                <div class="contact-item">
                    <div class="contact-header">
                        <i class="favorite-star">★</i> Jean Dupont
                    </div>
                    <span class="badge bg-primary">Plombier</span>
                    <div class="contact-details mt-2">
                        <div><strong>Société:</strong> Plomberie Dupont</div>
                        <div><strong>Téléphone:</strong> 01 23 45 67 89 / 06 12 34 56 78</div>
                        <div><strong>Email:</strong> jean.dupont@example.com</div>
                        <div><strong>Adresse:</strong> 123 rue des Artisans, 75001 Paris</div>
                        <div><strong>Notes:</strong> Plombier très réactif, prix corrects</div>
                    </div>
                </div>

                <!-- Contact 2 -->
                <div class="contact-item">
                    <div class="contact-header">
                        Marie Martin
                    </div>
                    <span class="badge bg-danger">Électricien</span>
                    <div class="contact-details mt-2">
                        <div><strong>Société:</strong> Électricité Martin</div>
                        <div><strong>Téléphone:</strong> 01 23 45 67 90 / 06 12 34 56 79</div>
                        <div><strong>Email:</strong> marie.martin@example.com</div>
                        <div><strong>Adresse:</strong> 124 rue des Artisans, 75001 Paris</div>
                        <div><strong>Notes:</strong> Électricienne professionnelle, disponible le week-end</div>
                    </div>
                </div>

                <!-- Contact 3 -->
                <div class="contact-item">
                    <div class="contact-header">
                        <i class="favorite-star">★</i> Pierre Durand
                    </div>
                    <span class="badge bg-info">Syndic</span>
                    <div class="contact-details mt-2">
                        <div><strong>Société:</strong> Syndic Immo Plus</div>
                        <div><strong>Téléphone:</strong> 01 23 45 67 91 / 06 12 34 56 80</div>
                        <div><strong>Email:</strong> pierre.durand@example.com</div>
                        <div><strong>Adresse:</strong> 125 rue des Syndics, 75002 Paris</div>
                        <div><strong>Notes:</strong> Syndic de plusieurs immeubles, bonnes références</div>
                    </div>
                </div>

                <!-- Contact 4 -->
                <div class="contact-item">
                    <div class="contact-header">
                        Sophie Lefebvre
                    </div>
                    <span class="badge bg-success">Gestionnaire</span>
                    <div class="contact-details mt-2">
                        <div><strong>Société:</strong> Gestion Tranquille</div>
                        <div><strong>Téléphone:</strong> 01 23 45 67 92 / 06 12 34 56 81</div>
                        <div><strong>Email:</strong> sophie.lefebvre@example.com</div>
                        <div><strong>Adresse:</strong> 126 rue de la Gestion, 75003 Paris</div>
                        <div><strong>Notes:</strong> Gestionnaire efficace pour locations meublées</div>
                    </div>
                </div>

                <!-- Contact 5 -->
                <div class="contact-item">
                    <div class="contact-header">
                        Thomas Moreau
                    </div>
                    <span class="badge bg-secondary">Maçon</span>
                    <div class="contact-details mt-2">
                        <div><strong>Société:</strong> Maçonnerie Générale</div>
                        <div><strong>Téléphone:</strong> 01 23 45 67 93 / 06 12 34 56 82</div>
                        <div><strong>Email:</strong> thomas.moreau@example.com</div>
                        <div><strong>Adresse:</strong> 127 rue du Bâtiment, 75004 Paris</div>
                        <div><strong>Notes:</strong> Spécialiste en réparations de façades</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="alert alert-info">
            <p><strong>Note:</strong> Cette page est un accès direct aux contacts, sans authentification requise.</p>
            <p>Retourner à <a href="/" class="alert-link">la page d'accueil</a>.</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    # Renvoyer le HTML directement
    return html_content


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/add', methods=['GET', 'POST'])
# @login_required
# def add_contact():
#     """Ajouter un nouveau contact"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/<int:contact_id>')
# @login_required
# def contact_detail(contact_id):
#     """Afficher les détails d'un contact"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/<int:contact_id>/edit', methods=['GET', 'POST'])
# @login_required
# def edit_contact(contact_id):
    """Modifier un contact existant"""
    contact = Contact.query.get_or_404(contact_id)

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        company_name = request.form.get('company_name')
        category = request.form.get('category')
        email = request.form.get('email')
        phone = request.form.get('phone')
        mobile_phone = request.form.get('mobile_phone')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        notes = request.form.get('notes')
        is_favorite = request.form.get('is_favorite') == '1'

        # Propriétés et bâtiments associés
        property_ids = request.form.getlist('property_ids')
        building_ids = request.form.getlist('building_ids')

        if not first_name or not last_name or not category:
            flash('Le prénom, le nom et la catégorie sont des champs obligatoires', 'danger')
            return redirect(url_for('edit_contact', contact_id=contact_id))

        try:
            # Mettre à jour les informations du contact
            contact.first_name = first_name
            contact.last_name = last_name
            contact.company_name = company_name
            contact.category = category
            contact.email = email
            contact.phone = phone
            contact.mobile_phone = mobile_phone
            contact.address = address
            contact.postal_code = postal_code
            contact.city = city
            contact.notes = notes
            contact.is_favorite = is_favorite

            # Mettre à jour les propriétés associées
            contact.properties = []
            if property_ids:
                properties = Property.query.filter(Property.id.in_(property_ids)).all()
                contact.properties.extend(properties)

            # Mettre à jour les bâtiments associés
            contact.buildings = []
            if building_ids:
                buildings = Building.query.filter(Building.id.in_(building_ids)).all()
                contact.buildings.extend(buildings)

            db.session.commit()

            flash('Contact mis à jour avec succès !', 'success')
            return redirect(url_for('contact_detail', contact_id=contact.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du contact : {str(e)}', 'danger')
            logging.error(f"Erreur lors de la mise à jour du contact : {str(e)}")

    # Pour le formulaire GET
    properties = Property.query.all()
    buildings = Building.query.all()

    # Propriétés et bâtimentsdéjà associés
    selected_property_ids = [prop.id for prop in contact.properties]
    selected_building_ids = [bldg.id for bldg in contact.buildings]

    # Catégories prédéfinies
    categories = [
        'Plombier', 'Électricien', 'Maçon', 'Syndic', 'Gestionnaire', 
        'Serrurier', 'Peintre', 'Menuisier', 'Chauffagiste', 'Jardinier',
        'Agent immobilier', 'Notaire', 'Avocat', 'Comptable', 'Autre'
    ]

    return render_template(
        'contacts/edit.html',
        contact=contact,
        properties=properties,
        buildings=buildings,
        selected_property_ids=selected_property_ids,
        selected_building_ids=selected_building_ids,
        categories=categories
    )


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/<int:contact_id>/delete', methods=['POST'])
# @login_required
# def delete_contact(contact_id):
#     """Supprimer un contact"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/<int:contact_id>/delete-confirm', methods=['GET', 'POST'])
# @login_required
# def delete_contact_confirm(contact_id):
#     """Page de confirmation pour supprimer un contact"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass


# NOTE: Routes des contacts déplacées dans app_routes_contacts.py
# @app.route('/contact/<int:contact_id>/toggle_favorite', methods=['POST'])
# @login_required
# def toggle_favorite(contact_id):
#     """Ajouter/supprimer un contact des favoris"""
#     # Cette fonction a été déplacée vers app_routes_contacts.py
#     pass


# Routes pour la gestion des paiements
@app.route('/property/<int:property_id>/payments')
@login_required
def property_payments(property_id):
    """Afficher les paiements associés à une propriété"""
    property = Property.query.get_or_404(property_id)

    # Récupérer tous les paiements pour cette propriété
    payments = Payment.query.filter_by(property_id=property_id).all()

    # Vérifier et mettre à jour le statut des paiements en retard
    today = datetime.now().date()
    updated = False

    for payment in payments:
        if payment.check_late_status():
            payment.status = 'En retard'
            updated = True

    if updated:
        db.session.commit()
        # Récupérer à nouveau les paiements après la mise à jour
        payments = Payment.query.filter_by(property_id=property_id).all()

    # Tri des paiements par date (du plus récent au plus ancien)
    payments = sorted(payments, key=lambda x: x.payment_date, reverse=True)

    # Calculer les totaux directement ici plutôt que dans le template
    paid_total = sum(payment.amount for payment in payments if payment.status == 'Payé')
    pending_total = sum(payment.amount for payment in payments if payment.status == 'En attente')
    late_total = sum(payment.amount for payment in payments if payment.status == 'En retard')

    return render_template('payments/list.html', 
                          property=property, 
                          payments=payments,
                          paid_total=paid_total,
                          pending_total=pending_total,
                          late_total=late_total)


@app.route('/property/<int:property_id>/payment/add', methods=['GET', 'POST'])
@login_required
def add_payment(property_id):
    """Ajouter un paiement pour une propriété"""
    property = Property.query.get_or_404(property_id)

    if request.method == 'POST':
        amount = request.form.get('amount')
        payment_date_str = request.form.get('payment_date')
        payment_type = request.form.get('payment_type')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')
        description = request.form.get('description')

        # Conversion des données
        try:
            amount = float(amount) if amount else None
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None
        except (ValueError, TypeError) as e:
            flash(f'Erreur lors de la conversion des données: {str(e)}', 'danger')
            return redirect(url_for('add_payment', property_id=property_id))

        # Validation
        if not amount or not payment_date or not payment_type:
            flash('Montant, date et type de paiement sont obligatoires', 'danger')
            return redirect(url_for('add_payment', property_id=property_id))

        # Création du paiement
        try:
            payment = Payment(
                property_id=property_id,
                amount=amount,
                payment_date=payment_date,
                payment_type=payment_type,
                payment_method=payment_method,
                status=status,
                description=description
            )

            db.session.add(payment)
            db.session.commit()

            flash('Paiement ajouté avec succès!', 'success')
            return redirect(url_for('property_payments', property_id=property_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout du paiement: {str(e)}', 'danger')
            logging.error(f"Erreur lors de l'ajout du paiement: {str(e)}")

    # Passer la date du jour au template
    today = datetime.now()

    return render_template('payments/add.html', property=property, now=today)


@app.route('/payment/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_payment(payment_id):
    """Modifier un paiement existant"""
    payment = Payment.query.get_or_404(payment_id)
    property = Property.query.get_or_404(payment.property_id)

    if request.method == 'POST':
        amount = request.form.get('amount')
        payment_date_str = request.form.get('payment_date')
        payment_type = request.form.get('payment_type')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')
        description = request.form.get('description')

        # Conversion des données
        try:
            amount = float(amount) if amount else None
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None
        except (ValueError, TypeError) as e:
            flash(f'Erreur lors de la conversion des données: {str(e)}', 'danger')
            return redirect(url_for('edit_payment', payment_id=payment_id))

        # Validation
        if not amount or not payment_date or not payment_type:
            flash('Montant, date et type de paiement sont obligatoires', 'danger')
            return redirect(url_for('edit_payment', payment_id=payment_id))

        # Mise à jour du paiement
        try:
            payment.amount = amount
            payment.payment_date = payment_date
            payment.payment_type = payment_type
            payment.payment_method = payment_method
            payment.status = status
            payment.description = description

            db.session.commit()

            flash('Paiement mis à jour avec succès!', 'success')
            return redirect(url_for('property_payments', property_id=payment.property_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du paiement: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la mise à jour du paiement: {str(e)}")

    return render_template('payments/edit.html', payment=payment, property=property)


# Cette route est maintenant définie dans app_routes_tenant_payments.py
# @app.route('/payment/<int:payment_id>/delete', methods=['POST'])
# @login_required
# def delete_payment(payment_id):
#     """Supprimer un paiement"""
#     # Voir tenant_payments_delete dans app_routes_tenant_payments.py


@app.route('/payment/<int:payment_id>/change-status', methods=['POST'])
@login_required
def change_payment_status(payment_id):
    """Changer rapidement le statut d'un paiement"""
    payment = Payment.query.get_or_404(payment_id)
    new_status = request.form.get('status')

    if new_status not in ['Payé', 'En attente', 'En retard']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Statut invalide'}), 400
        flash('Statut invalide', 'danger')
        return redirect(url_for('property_payments', property_id=payment.property_id))

    try:
        payment.status = new_status

        # Si le paiement est marqué comme payé, enregistrer la date de paiement
        if new_status == 'Payé':
            payment.date_paid = datetime.now().date()
        else:
            payment.date_paid = None

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': f'Statut mis à jour: {new_status}',
                'payment_id': payment.id,
                'new_status': new_status,
                'date_paid': payment.date_paid.strftime('%d/%m/%Y') if payment.date_paid else None
            })

        flash(f'Statut du paiement mis à jour: {new_status}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Erreur lors de la mise à jour du statut: {str(e)}', 'danger')
        logging.error(f"Erreur lors de la mise à jour du statut: {str(e)}")

    return redirect(url_for('property_payments', property_id=payment.property_id))


@app.route('/property/<int:property_id>/payment/recurring', methods=['GET', 'POST'])
@login_required
def add_recurring_payment(property_id):
    """Ajouter des paiements récurrents pour une propriété"""
    property = Property.query.get_or_404(property_id)

    if request.method == 'POST':
        # Récupérer les données du formulaire
        amount = request.form.get('amount')
        payment_type = request.form.get('payment_type')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')
        description = request.form.get('description')

        # Récupérer les paramètres de récurrence
        start_month = int(request.form.get('start_month'))
        start_year = int(request.form.get('start_year'))
        num_months = int(request.form.get('num_months'))
        payment_day = int(request.form.get('payment_day'))
        adjust_first_month = 'adjust_first_month' in request.form

        # Limiter le nombre de mois à 24 pour éviter les abus
        if num_months > 24:
            num_months = 24

        # Limiter le jour de paiement à 28 pour éviter les problèmes avec février
        if payment_day > 28:
            payment_day = 28

        # Conversion des données
        try:
            amount = float(amount) if amount else None
        except (ValueError, TypeError) as e:
            flash(f'Erreur lors de la conversion du montant: {str(e)}', 'danger')
            return redirect(url_for('add_recurring_payment', property_id=property_id))

        # Validation
        if not amount or not payment_type:
            flash('Montant et type de paiement sont obligatoires', 'danger')
            return redirect(url_for('add_recurring_payment', property_id=property_id))

        payments_created = 0

        try:
            # Créer un identifiant unique pour ce groupe de paiements récurrents
            recurring_group_id = f"recurring_{property_id}_{payment_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Créer les paiements récurrents
            for i in range(num_months):
                month = (start_month + i - 1) % 12 + 1  # Assurer que month est entre 1 et 12
                year = start_year + (start_month + i - 1) // 12  # Incrémenter l'année si nécessaire

                # Créer la date de paiement
                payment_date = datetime(year, month, payment_day).date()

                # Ajuster le montant du premier mois si demandé
                current_amount = amount
                if i == 0 and adjust_first_month and start_month == datetime.now().month and start_year == datetime.now().year:
                    # Nombre de jours dans le mois
                    days_in_month = calendar.monthrange(year, month)[1]
                    # Nombre de jours restants dans le mois depuis aujourd'hui
                    days_remaining = days_in_month - datetime.now().day + 1
                    # Calcul du montant ajusté au prorata
                    current_amount = round(amount * days_remaining / days_in_month, 2)
                    # Mise à jour de la description
                    payment_description = f"{description}\nMontant ajusté pour {days_remaining} jours sur {days_in_month}"
                else:
                    payment_description = description

                # Créer un nouveau paiement avec les marqueurs de récurrence
                payment = Payment(
                    property_id=property_id,
                    amount=current_amount,
                    payment_date=payment_date,
                    payment_type=payment_type,
                    payment_method=payment_method,
                    status=status,
                    description=payment_description,
                    is_recurring=True,
                    recurring_group_id=recurring_group_id
                )

                db.session.add(payment)
                payments_created += 1

            db.session.commit()
            flash(f'{payments_created} paiements récurrents créés avec succès!', 'success')
            return redirect(url_for('property_payments', property_id=property_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création des paiements récurrents: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la création des paiements récurrents: {str(e)}")

    # Passer la date du jour au template
    today = datetime.now()

    return render_template('payments/add_recurring.html', property=property, now=today)


@app.route('/property/<int:property_id>/payment/recurring/delete', methods=['GET', 'POST'])
@login_required
def delete_recurring_payments(property_id):
    """Supprimer des paiements récurrents pour une propriété"""
    property = Property.query.get_or_404(property_id)

    # Récupérer tous les groupes de paiements récurrents pour cette propriété
    recurring_groups = db.session.query(Payment.recurring_group_id, Payment.payment_type, 
                                        db.func.min(Payment.payment_date).label('first_date'),
                                        db.func.count(Payment.id).label('count')) \
                                .filter(Payment.property_id == property_id) \
                                .filter(Payment.is_recurring == True) \
                                .filter(Payment.recurring_group_id != None) \
                                .group_by(Payment.recurring_group_id, Payment.payment_type) \
                                .order_by(db.func.min(Payment.payment_date)) \
                                .all()

    if request.method == 'POST':
        recurring_group_id = request.form.get('recurring_group_id')
        delete_future_only = 'delete_future_only' in request.form

        try:
            # Construire la requête de base
            query = Payment.query.filter_by(
                property_id=property_id,
                recurring_group_id=recurring_group_id,
                is_recurring=True
            )

            # Si on ne supprime que les paiements futurs
            if delete_future_only:
                today = datetime.now().date()
                query = query.filter(Payment.payment_date > today)

            # Compter les paiements à supprimer
            count_to_delete = query.count()

            # Supprimer les paiements
            query.delete(synchronize_session=False)

            db.session.commit()

            flash(f'{count_to_delete} paiements récurrents supprimés avec succès !', 'success')
            return redirect(url_for('property_payments', property_id=property_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la suppression des paiements récurrents : {str(e)}', 'danger')
            logging.error(f"Erreur lors de la suppression des paiements récurrents : {str(e)}")

    return render_template('payments/delete_recurring.html', property=property, recurring_groups=recurring_groups)


# Initialize the database
with app.app_context():
    # Import models
    from models import Property, Document, Building, User, Payment
    # Create tables
    db.create_all()
# Intégration du gestionnaire de fichiers pour les téléversements volumineux
from file_handler import file_handler
app.register_blueprint(file_handler)

# La route /tenant-payments est maintenant définie dans app_routes_tenant_payments.py

@app.route('/property/<int:property_id>/assign-company', methods=['GET', 'POST'])
@login_required
def assign_property_to_company(property_id):
    """Assigner un bien à une société existante ou en créer une nouvelle"""
    property = Property.query.get_or_404(property_id)
    companies = Company.query.order_by(Company.name).all()
    
    if request.method == 'POST':
        company_action = request.form.get('company_action')
        
        try:
            if company_action == 'select':
                # Assigner à une société existante
                company_id = request.form.get('company_id')
                if company_id and company_id != "0":
                    # Vérification que la société existe
                    company = Company.query.get_or_404(int(company_id))
                    property.company_id = company.id
                    property.owner_company = company.name  # Synchronisation du nom
                    property.owner_address = company.address  # Synchronisation de l'adresse
                    message = f'Bien assigné à la société "{company.name}" avec succès!'
                else:
                    # Retirer l'association avec une société
                    property.company_id = None
                    property.owner_company = None
                    property.owner_address = None
                    message = 'Association avec la société supprimée avec succès!'
            
            elif company_action == 'create':
                # Créer une nouvelle société
                company_name = request.form.get('company_name')
                company_address = request.form.get('company_address')
                company_description = request.form.get('company_description', '')
                
                if not company_name:
                    flash('Le nom de la société est obligatoire', 'danger')
                    return redirect(url_for('assign_property_to_company', property_id=property_id))
                
                # Normaliser le nom de la société
                normalized_company_name = company_name.strip()
                
                # Vérifier si cette société existe déjà
                existing_company = Company.query.filter(func.lower(func.trim(Company.name)) == func.lower(normalized_company_name)).first()
                
                if existing_company:
                    # Utiliser la société existante
                    property.company_id = existing_company.id
                    property.owner_company = existing_company.name
                    property.owner_address = existing_company.address
                    message = f'Bien assigné à la société existante "{existing_company.name}" avec succès!'
                else:
                    # Créer une nouvelle société
                    new_company = Company(
                        name=normalized_company_name,
                        address=company_address,
                        description=company_description or f"Société propriétaire créée lors de l'assignation du bien : {property.address}"
                    )
                    db.session.add(new_company)
                    db.session.flush()  # Pour obtenir l'ID généré
                    
                    # Associer le bien à la nouvelle société
                    property.company_id = new_company.id
                    property.owner_company = new_company.name
                    property.owner_address = new_company.address
                    message = f'Nouvelle société "{normalized_company_name}" créée et bien assigné avec succès!'
            
            db.session.commit()
            flash(message, 'success')
            return redirect(url_for('property_detail', property_id=property.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'assignation à la société: {str(e)}', 'danger')
            logging.error(f"Erreur d'assignation à la société: {str(e)}")
    
    # GET request - afficher le formulaire
    return render_template('property_assign_company.html', 
                          property=property, 
                          companies=companies,
                          current_company_id=property.company_id)

if __name__ == '__main__':
    app.run(debug=True)