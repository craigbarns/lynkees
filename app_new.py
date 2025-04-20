import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename
from functools import wraps
from flask_session import Session
import uuid
import datetime
import shutil

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Ajouter un filtre pour pretty printing des objets dans les templates
@app.template_filter('pprint')
def pprint_filter(value):
    import pprint
    return pprint.pformat(value)

# Configuration simplifiée des sessions et cookies pour Replit
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=31)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = 'flask_session'
app.config['SESSION_COOKIE_SECURE'] = False  # Pour permettre HTTP en développement
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = None  # Désactivé pour tester

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
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max upload size

# Initialize the app with SQLAlchemy
db.init_app(app)

# Initialize Flask-Session
Session(app)

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import models after db is defined
from models import Property, Document, Building, User

# Décorateur personnalisé pour remplacer @login_required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'info')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Fonction pour récupérer l'utilisateur actuel
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Injecter l'utilisateur dans tous les templates
@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def generate_unique_filename(filename):
    """Generate a unique filename to prevent overwrites"""
    # Get file extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    # Create a unique name with timestamp and UUID
    unique_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}"
    if ext:
        unique_name = f"{unique_name}.{ext}"
    return unique_name


# Routes
@app.route('/')
def index():
    """Display all properties"""
    properties = Property.query.all()
    return render_template('index.html', properties=properties)


@app.route('/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    """Add a new property"""
    if request.method == 'POST':
        address = request.form.get('address')
        rent = request.form.get('rent')
        charges = request.form.get('charges')
        tenant = request.form.get('tenant')
        tenant_email = request.form.get('tenant_email')
        tenant_phone = request.form.get('tenant_phone')
        
        if not address or not rent or not charges:
            flash('Address, rent, and charges are required fields', 'danger')
            return redirect(url_for('add_property'))
        
        try:
            # Create a new property
            new_property = Property(
                address=address,
                rent=float(rent),
                charges=float(charges),
                tenant=tenant,
                tenant_email=tenant_email,
                tenant_phone=tenant_phone
            )
            db.session.add(new_property)
            db.session.commit()
            
            flash('Property added successfully!', 'success')
            return redirect(url_for('property_detail', property_id=new_property.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding property: {str(e)}', 'danger')
            logging.error(f"Error adding property: {str(e)}")
    
    return render_template('add.html')


@app.route('/property/<int:property_id>')
def property_detail(property_id):
    """Display property details and associated documents"""
    property = Property.query.get_or_404(property_id)
    documents = Document.query.filter_by(property_id=property_id).all()
    buildings = Building.query.all()
    return render_template('detail.html', property=property, documents=documents, buildings=buildings)


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
            filepath=unique_filename  # Actual filename on server
        )
        db.session.add(document)
        db.session.commit()
        
        flash('Document uploaded successfully!', 'success')
    else:
        flash('File type not allowed', 'danger')
    
    return redirect(url_for('property_detail', property_id=property_id))


@app.route('/uploads/<filename>')
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


# Routes d'authentification
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Enregistrement d'un nouvel utilisateur"""
    if 'user_id' in session:
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
                last_name=last_name
            )
            user.set_password(password)
            
            # Premier utilisateur devient administrateur
            if User.query.count() == 0:
                user.is_admin = True
            
            db.session.add(user)
            db.session.commit()
            
            flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du compte: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la création du compte: {str(e)}")
    
    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion d'un utilisateur - Version ultra simplifiée"""
    logging.info(f"Session actuelle à l'entrée de login: {session}")
    
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user:
            logging.info(f"Déjà connecté: {current_user.username} (ID: {current_user.id})")
            return redirect(url_for('index'))
        else:
            # Session invalide, on la nettoie
            session.clear()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session.permanent = True  # Rendre la session permanente
        
        logging.info(f"Tentative de connexion pour: {username}")
        
        if not username or not password:
            flash('Nom d\'utilisateur et mot de passe sont obligatoires', 'danger')
            return redirect(url_for('login'))
        
        # Recherche de l'utilisateur
        user = User.query.filter_by(username=username).first()
        
        if not user:
            logging.warning(f"Échec: utilisateur {username} non trouvé")
            flash('Identifiants incorrects', 'danger')
            return redirect(url_for('login'))
        
        # Vérification du mot de passe
        if not user.check_password(password):
            logging.warning(f"Échec: mot de passe incorrect pour {username}")
            flash('Identifiants incorrects', 'danger')
            return redirect(url_for('login'))
        
        # Connexion réussie
        try:
            # Stocker l'ID utilisateur dans la session
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session.modified = True
            
            logging.info(f"Connexion réussie pour {username} (ID: {user.id})")
            logging.info(f"Session après connexion: {session}")
            
            next_page = request.args.get('next')
            flash(f'Bienvenue, {user.username} !', 'success')
            
            return redirect(next_page if next_page else url_for('index'))
        except Exception as e:
            logging.error(f"Erreur lors de la connexion: {str(e)}")
            flash(f'Erreur lors de la connexion: {str(e)}', 'danger')
            return redirect(url_for('login'))
    
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    """Déconnexion d'un utilisateur - Version simplifiée"""
    logging.info(f"Déconnexion - Session avant: {session}")
    session.clear()
    logging.info(f"Déconnexion - Session après: {session}")
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    """Affichage du profil de l'utilisateur"""
    # Vérification de sécurité supplémentaire
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        session.clear()
        flash('Session expirée ou invalide. Veuillez vous reconnecter.', 'warning')
        return redirect(url_for('login'))
    
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
    # Vérification de sécurité supplémentaire
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    if not current_user:
        session.clear()
        flash('Session expirée ou invalide. Veuillez vous reconnecter.', 'warning')
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
def test_auth():
    """Route de test pour vérifier l'état d'authentification"""
    # Afficher les informations de session
    logging.info(f"Test Auth - Session actuelle: {session}")
    
    session_info = {key: session.get(key) for key in session}
    is_authenticated = 'user_id' in session
    
    user_info = {
        "is_authenticated": is_authenticated,
        "session": session_info
    }
    
    if is_authenticated:
        current_user = User.query.get(session['user_id'])
        if current_user:
            user_info["user_id"] = current_user.id
            user_info["username"] = current_user.username
        else:
            user_info["error"] = "ID utilisateur en session mais utilisateur non trouvé en base"
    
    return render_template('auth/test_auth.html', user_info=user_info)


# Modifier base.html pour vérifier l'état d'authentification
@app.context_processor
def utility_processor():
    def is_user_authenticated():
        if 'user_id' not in session:
            return False
        user = User.query.get(session['user_id'])
        return user is not None
    
    def get_authenticated_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None
    
    return {
        'is_user_authenticated': is_user_authenticated,
        'current_user': get_authenticated_user()
    }


# Initialize the database
with app.app_context():
    # Import models
    from models import Property, Document, Building, User
    # Create tables
    db.create_all()