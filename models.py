from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship


class User(db.Model):
    """Model for user authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Champs pour la confirmation par email
    email_confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(128), nullable=True)
    confirmation_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Relations with other models (to be added later if needed)
    
    def set_password(self, password):
        """Définir un mot de passe crypté"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Vérifier un mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    def generate_confirmation_token(self):
        """Générer un token de confirmation d'email"""
        from itsdangerous import URLSafeTimedSerializer
        from app import app
        
        s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        self.confirmation_token = s.dumps(self.email, salt='email-confirm')
        self.confirmation_sent_at = datetime.utcnow()
        return self.confirmation_token
    
    def confirm_email(self, token, expiration=86400):
        """Confirmer l'email avec le token (expire après 24h par défaut)"""
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        from app import app
        
        s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        try:
            email = s.loads(token, salt='email-confirm', max_age=expiration)
            if email == self.email:
                self.email_confirmed = True
                self.confirmation_token = None
                return True
        except (SignatureExpired, BadSignature):
            return False
        return False
    
    @property    
    def is_authenticated(self):
        """Utilisateur authentifié"""
        return True
        
    @property
    def is_active(self):
        """Utilisateur actif - tient compte de la confirmation d'email"""
        return self.email_confirmed
        
    @property
    def is_anonymous(self):
        """Utilisateur anonyme"""
        return False
        
    def get_id(self):
        """Obtenir l'ID utilisateur"""
        return str(self.id)
        
    def __repr__(self):
        return f'<User {self.username}>'

class Building(db.Model):
    """Model for buildings containing multiple properties"""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with properties
    properties = db.relationship('Property', backref='building', lazy=True)
    
    def __repr__(self):
        return f'<Building {self.name}>'


class Property(db.Model):
    """Model for real estate properties"""
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)  # Lien vers la société propriétaire
    owner_company = db.Column(db.String(255), nullable=True)  # Nom de société (à migrer vers company_id)
    owner_address = db.Column(db.String(255), nullable=True)  # Adresse de la société propriétaire
    rent = db.Column(db.Float, nullable=False)
    charges = db.Column(db.Float, nullable=False)
    deposit = db.Column(db.Float, nullable=True)  # Montant de la caution
    surface = db.Column(db.Float, nullable=True)  # Surface en m²
    floor = db.Column(db.String(50), nullable=True)  # Étage (ex: "RDC", "1er", "Sous-sol", etc.)
    location = db.Column(db.String(255), nullable=True)  # Emplacement ou description additionnelle
    tenant = db.Column(db.String(255))
    tenant_email = db.Column(db.String(120))
    tenant_phone = db.Column(db.String(20))
    entry_date = db.Column(db.Date, nullable=True)  # Date d'entrée dans les lieux
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Nouvelles colonnes
    is_furnished = db.Column(db.Boolean, default=False)  # Meublé ou non
    has_property_manager = db.Column(db.Boolean, default=False)  # En gestion ou non
    property_manager_name = db.Column(db.String(255), nullable=True)  # Nom du gestionnaire
    
    # Informations sur le syndic
    has_syndic = db.Column(db.Boolean, default=False)  # A un syndic ou non
    syndic_name = db.Column(db.String(255), nullable=True)  # Nom du syndic
    syndic_contact = db.Column(db.String(255), nullable=True)  # Contact du syndic (email ou téléphone)
    
    # Reference to building (optional)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=True)
    
    # Relationship with documents
    documents = db.relationship('Document', backref='property', lazy=True, cascade="all, delete-orphan")
    
    # Relationship with company
    company = db.relationship('Company', backref='properties', lazy=True)
    
    def __repr__(self):
        return f'<Property {self.address}>'


class Company(db.Model):
    """Model for property management companies"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with documents
    documents = db.relationship('Document', backref='company', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Company {self.name}>'


class Document(db.Model):
    """Model for property-related documents"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True)
    document_type = db.Column(db.String(50), nullable=True)  # Type de document: Bail, Relevé, Facture, etc.
    document_category = db.Column(db.String(50), nullable=True)  # Catégorie: Relevé bancaire, Impôt, Facture, etc.
    filename = db.Column(db.String(255), nullable=False)  # Original filename for display
    filepath = db.Column(db.String(255), nullable=False)  # Actual filename in storage
    document_date = db.Column(db.Date, nullable=True)  # Date du document
    amount = db.Column(db.Float, nullable=True)  # Montant (pour factures, relevés, etc.)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)  # Description ou note sur le document
    
    def __repr__(self):
        if self.property_id:
            return f'<Document {self.filename} for Property {self.property_id}>'
        elif self.company_id:
            return f'<Document {self.filename} for Company {self.company_id}>'
        else:
            return f'<Document {self.filename}>'


class Payment(db.Model):
    """Model for tenant payments"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)  # Loyer, Charges, Caution, etc.
    payment_method = db.Column(db.String(50))  # Virement, Chèque, Espèces, etc.
    status = db.Column(db.String(20), nullable=False, default='En attente')  # Payé, En attente, En retard
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    date_paid = db.Column(db.Date, nullable=True)  # Date à laquelle le paiement a été effectivement reçu
    is_recurring = db.Column(db.Boolean, default=False)  # Indique si le paiement fait partie d'une série récurrente
    recurring_group_id = db.Column(db.String(50), nullable=True)  # Identifiant de groupe pour les paiements récurrents
    
    # Relation avec la propriété
    property = db.relationship('Property', backref=db.backref('payments', lazy=True, cascade="all, delete-orphan"))
    
    def check_late_status(self):
        """Vérifie si le paiement est en retard (après la date prévue)"""
        today = datetime.now().date()
        
        # Si nous sommes après la date de paiement prévue et le statut est toujours 'En attente'
        if today > self.payment_date and self.status == 'En attente':
            return True
        return False
    
    def is_rent_payment(self):
        """Vérifie si le paiement concerne un loyer"""
        return self.payment_type.lower() == 'loyer'
    
    def get_due_date(self):
        """Renvoie la date de paiement du loyer"""
        # Retourne simplement la date de paiement au lieu d'une date limite (5 du mois)
        return self.payment_date
        
    def __repr__(self):
        return f'<Payment {self.amount}€ for Property {self.property_id}>'


class Contact(db.Model):
    """Model for contact management"""
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False)  # Plombier, Électricien, Maçon, Syndic, Gestionnaire, etc.
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile_phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations avec les propriétés et bâtiments (optionnel)
    properties = db.relationship('Property', secondary='contact_property', backref='contacts')
    buildings = db.relationship('Building', secondary='contact_building', backref='contacts')

    def __repr__(self):
        return f'<Contact {self.first_name} {self.last_name} - {self.category}>'


# Tables de liaison pour les relations many-to-many
contact_property = db.Table('contact_property',
    db.Column('contact_id', db.Integer, db.ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('property_id', db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), primary_key=True)
)

contact_building = db.Table('contact_building',
    db.Column('contact_id', db.Integer, db.ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('building_id', db.Integer, db.ForeignKey('buildings.id', ondelete='CASCADE'), primary_key=True)
)


class Expense(db.Model):
    """Modèle pour les charges (appels de fonds, factures, etc.)"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True)
    
    # Type de charge (appel de fonds, EDF, eau, etc.)
    charge_type = db.Column(db.String(50), nullable=False)
    
    # Détails financiers
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)  # Date d'échéance
    payment_date = db.Column(db.Date, nullable=True)  # Date de paiement effectif
    status = db.Column(db.String(20), nullable=False, default='à_payer')  # à_payer, payé, en_retard
    
    # Informations supplémentaires
    reference = db.Column(db.String(100), nullable=True)  # Numéro de facture ou référence
    period_start = db.Column(db.Date, nullable=True)  # Début de la période concernée
    period_end = db.Column(db.Date, nullable=True)  # Fin de la période concernée
    description = db.Column(db.Text, nullable=True)
    
    # Champs de suivi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Récurrence
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_group_id = db.Column(db.String(50), nullable=True)
    recurring_frequency = db.Column(db.String(20), nullable=True)  # mensuel, trimestriel, annuel
    
    # Document associé (facture, etc.)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    
    # Relations
    property = db.relationship('Property', backref='expenses')
    building = db.relationship('Building', backref='expenses')
    company = db.relationship('Company', backref='expenses')
    document = db.relationship('Document', backref='expense')
    
    def __repr__(self):
        return f'<Expense {self.id}: {self.charge_type} - {self.amount}€>'
    
    def get_charge_type_display(self):
        """Retourne une version lisible du type de charge"""
        types = {
            'appel_fonds': 'Appel de fonds',
            'edf': 'Électricité (EDF)',
            'eau': 'Eau',
            'chauffage': 'Chauffage',
            'syndic': 'Syndic',
            'taxe_fonciere': 'Taxe foncière',
            'taxe_habitation': 'Taxe d\'habitation',
            'assurance': 'Assurance',
            'travaux': 'Travaux',
            'autre': 'Autre'
        }
        return types.get(self.charge_type, self.charge_type)
    
    def get_status_display(self):
        """Retourne une version lisible du statut"""
        status_display = {
            'à_payer': 'À payer',
            'payé': 'Payé',
            'en_retard': 'En retard'
        }
        return status_display.get(self.status, self.status)
    
    def check_status(self):
        """Vérifie et met à jour le statut de la charge"""
        today = datetime.now().date()
        
        if self.payment_date:
            self.status = 'payé'
        elif today > self.due_date and self.status == 'à_payer':
            self.status = 'en_retard'
        
        return self.status


class UserDashboardPreference(db.Model):
    """Modèle pour stocker les préférences de tableau de bord des utilisateurs"""
    __tablename__ = 'user_dashboard_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    widgets_config = db.Column(db.Text, nullable=True)  # JSON stocké sous forme de texte
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation avec l'utilisateur
    user = relationship('User', backref='dashboard_preferences')
    
    def __repr__(self):
        return f'<UserDashboardPreference {self.id} - User {self.user_id}>'
