#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application autonome pour la gestion des contacts
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, or_
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from sqlalchemy.sql import func

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL")
Base = declarative_base()

# Modèle Contact (simplifié, sans relations avec Property/Building)
class Contact(Base):
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(120))
    phone = Column(String(20))
    mobile_phone = Column(String(20))
    address = Column(String(120))
    postal_code = Column(String(10))
    city = Column(String(64))
    category = Column(String(64))
    company_name = Column(String(120))
    notes = Column(Text)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Contact {self.first_name} {self.last_name}>"


# Initialisation de la connexion à la base de données et création des tables
def get_db_session():
    """Initialiser la connexion à la base de données et retourner une session"""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    return Session(), Contact


# Routes pour l'application
@app.route('/')
def index():
    """Page d'accueil avec liste des contacts"""
    try:
        # Obtenir la session et le modèle
        session, Contact = get_db_session()
        
        # Récupérer les paramètres de recherche et de filtre
        search_query = request.args.get('search', '')
        category_filter = request.args.get('category', 'all')
        sort_by = request.args.get('sort', 'last_name')
        favorites_only = request.args.get('favorites', '') == '1'
        
        # Construire la requête de base
        query = session.query(Contact)
        
        # Appliquer le filtre de recherche
        if search_query:
            query = query.filter(or_(
                Contact.first_name.ilike(f"%{search_query}%"),
                Contact.last_name.ilike(f"%{search_query}%"),
                Contact.email.ilike(f"%{search_query}%"),
                Contact.phone.ilike(f"%{search_query}%"),
                Contact.mobile_phone.ilike(f"%{search_query}%"),
                Contact.company_name.ilike(f"%{search_query}%")
            ))
        
        # Appliquer le filtre de catégorie
        if category_filter != 'all':
            query = query.filter(Contact.category == category_filter)
        
        # Appliquer le filtre des favoris
        if favorites_only:
            query = query.filter(Contact.is_favorite == True)
        
        # Appliquer le tri
        if sort_by == 'first_name':
            query = query.order_by(Contact.first_name)
        elif sort_by == 'category':
            query = query.order_by(Contact.category)
        elif sort_by == 'company':
            query = query.order_by(Contact.company_name)
        elif sort_by == 'created_at':
            query = query.order_by(Contact.created_at.desc())
        else:
            query = query.order_by(Contact.last_name)
        
        # Exécuter la requête
        contacts = query.all()
        
        # Récupérer toutes les catégories uniques pour le filtre
        categories = [cat[0] for cat in session.query(Contact.category).distinct().all()]
        categories.sort()
        
        # Rendre le template HTML avec la nouvelle interface
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste des contacts</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1d21;
            color: #f8f9fa;
            padding-top: 20px;
            padding-bottom: 40px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
        }
        .header {
            background-color: #242930;
            padding: 15px 20px;
            border-radius: 8px 8px 0 0;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .search-bar {
            background-color: #242930;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .contact-row {
            background-color: #242930;
            padding: 15px 20px;
            border-radius: 5px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        .contact-row:hover {
            background-color: #2c3036;
        }
        .contact-header {
            background-color: #1e2226;
            padding: 12px 20px;
            border-radius: 5px;
            margin-bottom: 10px;
            color: #a0a0a0;
        }
        .contact-col {
            flex: 1;
            padding: 5px 10px;
        }
        .actions-col {
            width: 120px;
            text-align: right;
        }
        .btn-action {
            color: #a0a0a0;
            background-color: transparent;
            border: 1px solid #3d4148;
            width: 36px;
            height: 36px;
            border-radius: 5px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-left: 5px;
            transition: all 0.2s;
        }
        .btn-action:hover {
            background-color: #3d4148;
            color: white;
        }
        .btn-action.edit:hover {
            background-color: #2b5a8e;
            border-color: #2b5a8e;
        }
        .btn-action.delete:hover {
            background-color: #a02c2c;
            border-color: #a02c2c;
        }
        .btn-action.view:hover {
            background-color: #2f6e43;
            border-color: #2f6e43;
        }
        .badge {
            font-size: 0.75rem;
            padding: 5px 10px;
            border-radius: 15px;
        }
        .badge-plombier {
            background-color: #3b76ef;
        }
        .badge-electricien {
            background-color: #e74c3c;
        }
        .badge-serrurier {
            background-color: #8e44ad;
        }
        .badge-syndic {
            background-color: #16a2b8;
        }
        .badge-gestionnaire {
            background-color: #28a745;
        }
        .badge-macon {
            background-color: #6c757d;
        }
        .search-input {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
            color: #f8f9fa;
            border-radius: 5px;
            padding: 8px 15px;
        }
        .search-input:focus {
            background-color: #242930;
            color: #f8f9fa;
            border-color: #5b6bff;
            box-shadow: none;
        }
        .filter-select {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
            color: #f8f9fa;
            border-radius: 5px;
            padding: 8px 15px;
        }
        .filter-select:focus {
            background-color: #242930;
            color: #f8f9fa;
            border-color: #5b6bff;
            box-shadow: none;
        }
        .btn-custom {
            background-color: #5b6bff;
            border: none;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
            transition: all 0.2s;
        }
        .btn-custom:hover {
            background-color: #4959d9;
            color: white;
        }
        .btn-filter {
            background-color: #5b6bff;
            border: none;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
        }
        .phone-icon {
            margin-right: 8px;
            color: #6c757d;
        }
        .company-text {
            color: #a0a0a0;
            font-size: 0.9rem;
            white-space: normal;
            word-break: break-word;
            text-align: left;
        }
        .favorite-star {
            color: #ffc107;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="h4 mb-0">Liste des contacts</h1>
            <a href="/add" class="btn btn-custom">
                <i class="fas fa-plus"></i> Ajouter Un Contact
            </a>
        </div>
        
        <div class="search-bar">
            <form id="filterForm" action="/" method="get">
                <div class="row align-items-center">
                    <div class="col-md-4 mb-2 mb-md-0">
                        <div class="input-group">
                            <span class="input-group-text bg-dark" style="border-color: #3d4148;">
                                <i class="fas fa-search text-light"></i>
                            </span>
                            <input type="text" class="form-control search-input" name="search" placeholder="Rechercher un contact..." value="{{ request.args.get('search', '') }}">
                        </div>
                    </div>
                    <div class="col-md-3 mb-2 mb-md-0">
                        <select class="form-select filter-select" name="category" id="categoryFilter">
                            <option value="all">Toutes les catégories</option>
                            {% for cat in categories %}
                            <option value="{{ cat }}" {% if request.args.get('category') == cat %}selected{% endif %}>{{ cat }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-3 mb-2 mb-md-0">
                        <select class="form-select filter-select" name="sort" id="sortFilter">
                            <option value="last_name" {% if request.args.get('sort') == 'last_name' or not request.args.get('sort') %}selected{% endif %}>Tri par nom</option>
                            <option value="first_name" {% if request.args.get('sort') == 'first_name' %}selected{% endif %}>Tri par prénom</option>
                            <option value="category" {% if request.args.get('sort') == 'category' %}selected{% endif %}>Tri par catégorie</option>
                            <option value="company" {% if request.args.get('sort') == 'company' %}selected{% endif %}>Tri par société</option>
                        </select>
                    </div>
                    <div class="col-md-2 d-flex justify-content-end">
                        <button type="submit" class="btn btn-filter">
                            <i class="fas fa-filter"></i> Filtrer
                        </button>
                    </div>
                </div>
            </form>
        </div>
        
        <!-- En-tête du tableau des contacts -->
        <div class="contact-header">
            <div class="row">
                <div class="col-md-3">
                    <i class="fas fa-user"></i> Nom
                </div>
                <div class="col-md-2">
                    <i class="fas fa-tag"></i> Catégorie
                </div>
                <div class="col-md-3">
                    <i class="fas fa-building"></i> Société
                </div>
                <div class="col-md-3">
                    <i class="fas fa-phone"></i> Contact
                </div>
                <div class="col-md-1 text-end">
                    Actions
                </div>
            </div>
        </div>
        
        {% if contacts %}
            {% for contact in contacts %}
                {% set badge_color = "badge-" %}
                {% if contact.category and contact.category.lower() in ["électricien", "electricien"] %}
                    {% set badge_color = badge_color + "electricien" %}
                {% elif contact.category and contact.category.lower() == "plombier" %}
                    {% set badge_color = badge_color + "plombier" %}
                {% elif contact.category and contact.category.lower() == "syndic" %}
                    {% set badge_color = badge_color + "syndic" %}
                {% elif contact.category and contact.category.lower() == "gestionnaire" %}
                    {% set badge_color = badge_color + "gestionnaire" %}
                {% elif contact.category and contact.category.lower() == "serrurier" %}
                    {% set badge_color = badge_color + "serrurier" %}
                {% elif contact.category and contact.category.lower() in ["maçon", "macon"] %}
                    {% set badge_color = badge_color + "macon" %}
                {% else %}
                    {% set badge_color = badge_color + "macon" %}
                {% endif %}
                
                <div class="contact-row">
                    <div class="col-md-3">
                        {% if contact.is_favorite %}
                            <i class="fas fa-star favorite-star"></i>
                        {% endif %}
                        {{ contact.first_name }} {{ contact.last_name }}
                    </div>
                    <div class="col-md-2">
                        <span class="badge {{ badge_color }}">{{ contact.category or 'Non défini' }}</span>
                    </div>
                    <div class="col-md-3 company-text" style="white-space: normal; word-break: break-word;">
                        {{ contact.company_name or '' }}
                    </div>
                    <div class="col-md-3">
                        {% if contact.phone %}
                            <i class="fas fa-phone phone-icon"></i>{{ contact.phone }}
                        {% elif contact.mobile_phone %}
                            <i class="fas fa-mobile-alt phone-icon"></i>{{ contact.mobile_phone }}
                        {% endif %}
                    </div>
                    <div class="col-md-1 text-end">
                        <a href="/detail/{{ contact.id }}" class="btn btn-action view" title="Voir les détails">
                            <i class="fas fa-eye"></i>
                        </a>
                        <a href="/edit/{{ contact.id }}" class="btn btn-action edit" title="Modifier">
                            <i class="fas fa-edit"></i>
                        </a>
                        <a href="/delete/{{ contact.id }}" class="btn btn-action delete" title="Supprimer">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i> Aucun contact trouvé avec les critères de recherche actuels.
            </div>
        {% endif %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Script pour soumettre automatiquement le formulaire lors du changement des filtres
        document.getElementById('categoryFilter').addEventListener('change', function() {
            document.getElementById('filterForm').submit();
        });
        
        document.getElementById('sortFilter').addEventListener('change', function() {
            document.getElementById('filterForm').submit();
        });
    </script>
</body>
</html>''', contacts=contacts, categories=categories, request=request)
    
    except Exception as e:
        logging.error(f"Erreur lors de l'affichage des contacts: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        # En cas d'erreur, afficher un message simple
        return f'''
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Erreur lors de l'affichage des contacts</h4>
                <p>{str(e)}</p>
                <p>Veuillez vérifier les logs pour plus de détails.</p>
            </div>
        </div>
        '''

@app.route('/detail/<int:contact_id>')
def contact_detail(contact_id):
    """Afficher les détails d'un contact"""
    try:
        session, Contact = get_db_session()
        
        # Récupérer le contact avec ses relations
        contact = session.query(Contact).get(contact_id)
        
        if not contact:
            flash("Contact non trouvé", "danger")
            return redirect(url_for('index'))
            
        # Fermer la session
        session.remove()
        
        # Rendre le template HTML
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ contact.first_name }} {{ contact.last_name }} - Détails du contact</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1d21;
            color: #f8f9fa;
            padding-top: 20px;
            padding-bottom: 40px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
        }
        .card {
            background-color: #242930;
            border: 1px solid #3d4148;
            border-radius: 8px;
            overflow: hidden;
        }
        .card-header {
            background-color: #1e2226;
            border-bottom: 1px solid #3d4148;
            padding: 15px 20px;
        }
        .card-body {
            padding: 25px;
        }
        .btn-back {
            background-color: #3d4148;
            border: none;
            color: #f8f9fa;
            margin-right: 15px;
        }
        .btn-custom {
            background-color: #5b6bff;
            border: none;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
            transition: all 0.2s;
        }
        .btn-custom:hover {
            background-color: #4959d9;
            color: white;
        }
        .btn-danger-soft {
            background-color: #422;
            border: 1px solid #733;
            color: #f8f9fa;
        }
        .btn-danger-soft:hover {
            background-color: #933;
            border-color: #c33;
            color: white;
        }
        .info-label {
            color: #a0a0a0;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        .info-value {
            color: #f8f9fa;
            font-size: 1.1rem;
            margin-bottom: 20px;
        }
        .favorite-star {
            color: #ffc107;
            margin-right: 5px;
        }
        .badge {
            font-size: 0.75rem;
            padding: 5px 10px;
            border-radius: 15px;
        }
        .badge-plombier {
            background-color: #3b76ef;
        }
        .badge-electricien {
            background-color: #e74c3c;
        }
        .badge-serrurier {
            background-color: #8e44ad;
        }
        .badge-syndic {
            background-color: #16a2b8;
        }
        .badge-gestionnaire {
            background-color: #28a745;
        }
        .badge-macon {
            background-color: #6c757d;
        }
        .notes-box {
            background-color: #1a1d21;
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
            min-height: 120px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="d-flex align-items-center mb-4">
            <a href="/" class="btn btn-back">
                <i class="fas fa-arrow-left"></i>
            </a>
            <h1 class="h4 mb-0">
                {% if contact.is_favorite %}
                    <i class="fas fa-star favorite-star"></i>
                {% endif %}
                {{ contact.first_name }} {{ contact.last_name }}
                {% set badge_color = "badge-" %}
                {% if contact.category and contact.category.lower() in ["électricien", "electricien"] %}
                    {% set badge_color = badge_color + "electricien" %}
                {% elif contact.category and contact.category.lower() == "plombier" %}
                    {% set badge_color = badge_color + "plombier" %}
                {% elif contact.category and contact.category.lower() == "syndic" %}
                    {% set badge_color = badge_color + "syndic" %}
                {% elif contact.category and contact.category.lower() == "gestionnaire" %}
                    {% set badge_color = badge_color + "gestionnaire" %}
                {% elif contact.category and contact.category.lower() == "serrurier" %}
                    {% set badge_color = badge_color + "serrurier" %}
                {% elif contact.category and contact.category.lower() in ["maçon", "macon"] %}
                    {% set badge_color = badge_color + "macon" %}
                {% else %}
                    {% set badge_color = badge_color + "macon" %}
                {% endif %}
                <span class="badge {{ badge_color }} ms-2">{{ contact.category or 'Non défini' }}</span>
            </h1>
        </div>
        
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Informations de contact</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-building me-2"></i>Société</div>
                                <div class="info-value">{{ contact.company_name or 'Non renseignée' }}</div>
                            </div>
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-envelope me-2"></i>Email</div>
                                <div class="info-value">{{ contact.email or 'Non renseigné' }}</div>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-phone me-2"></i>Téléphone fixe</div>
                                <div class="info-value">{{ contact.phone or 'Non renseigné' }}</div>
                            </div>
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-mobile-alt me-2"></i>Téléphone mobile</div>
                                <div class="info-value">{{ contact.mobile_phone or 'Non renseigné' }}</div>
                            </div>
                        </div>
                        
                        <div class="info-label"><i class="fas fa-map-marker-alt me-2"></i>Adresse</div>
                        <div class="info-value">
                            {% if contact.address %}
                                {{ contact.address }}<br>
                                {% if contact.postal_code or contact.city %}
                                    {{ contact.postal_code or '' }} {{ contact.city or '' }}
                                {% endif %}
                            {% else %}
                                Non renseignée
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Notes et informations supplémentaires</h5>
                    </div>
                    <div class="card-body">
                        <div class="info-label"><i class="fas fa-sticky-note me-2"></i>Notes</div>
                        <div class="notes-box">{{ contact.notes or 'Aucune note disponible' }}</div>
                        
                        <div class="row mt-4">
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-calendar-plus me-2"></i>Date de création</div>
                                <div class="info-value">{{ contact.created_at.strftime('%d/%m/%Y à %H:%M') }}</div>
                            </div>
                            <div class="col-md-6">
                                <div class="info-label"><i class="fas fa-calendar-check me-2"></i>Dernière mise à jour</div>
                                <div class="info-value">{{ contact.updated_at.strftime('%d/%m/%Y à %H:%M') }}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="d-flex justify-content-between mb-5">
            <a href="/" class="btn btn-back">
                <i class="fas fa-arrow-left me-1"></i> Retour à la liste
            </a>
            <div>
                <a href="/edit/{{ contact.id }}" class="btn btn-custom me-2">
                    <i class="fas fa-edit me-1"></i> Modifier
                </a>
                <a href="/delete/{{ contact.id }}" class="btn btn-danger-soft">
                    <i class="fas fa-trash-alt me-1"></i> Supprimer
                </a>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''', contact=contact)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'affichage du contact: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_contact():
    """Ajouter un nouveau contact"""
    try:
        session, Contact = get_db_session()
        
        # Récupérer toutes les catégories uniques pour le formulaire
        categories = [cat[0] for cat in session.query(Contact.category).distinct().all() if cat[0]]
        categories.sort()
        
        if request.method == 'POST':
            # Créer un nouveau contact à partir des données du formulaire
            new_contact = Contact(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                mobile_phone=request.form.get('mobile_phone'),
                address=request.form.get('address'),
                postal_code=request.form.get('postal_code'),
                city=request.form.get('city'),
                category=request.form.get('category'),
                company_name=request.form.get('company_name'),
                notes=request.form.get('notes'),
                is_favorite=bool(request.form.get('is_favorite')),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Ajouter et enregistrer le contact
            session.add(new_contact)
            session.commit()
            session.remove()
            
            # Rediriger vers la liste des contacts
            return redirect(url_for('index'))
        
        # Afficher le formulaire d'ajout
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ajouter un contact</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1d21;
            color: #f8f9fa;
            padding-top: 20px;
            padding-bottom: 40px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
        }
        .card {
            background-color: #242930;
            border: 1px solid #3d4148;
            border-radius: 8px;
            overflow: hidden;
        }
        .card-header {
            background-color: #1e2226;
            border-bottom: 1px solid #3d4148;
            padding: 15px 20px;
        }
        .card-body {
            padding: 25px;
        }
        .btn-back {
            background-color: #3d4148;
            border: none;
            color: #f8f9fa;
            margin-right: 15px;
        }
        .btn-custom {
            background-color: #5b6bff;
            border: none;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
            transition: all 0.2s;
        }
        .btn-custom:hover {
            background-color: #4959d9;
            color: white;
        }
        .form-label {
            color: #a0a0a0;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        .form-control, .form-select {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
            color: #f8f9fa;
            border-radius: 5px;
            padding: 10px 15px;
        }
        .form-control:focus, .form-select:focus {
            background-color: #1e2226;
            color: #f8f9fa;
            border-color: #5b6bff;
            box-shadow: none;
        }
        .form-check-input {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
        }
        .form-check-input:checked {
            background-color: #5b6bff;
            border-color: #5b6bff;
        }
        .section-title {
            font-size: 1.2rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #3d4148;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="d-flex align-items-center mb-4">
            <a href="/" class="btn btn-back">
                <i class="fas fa-arrow-left"></i>
            </a>
            <h1 class="h4 mb-0">Ajouter un nouveau contact</h1>
        </div>
        
        <form method="post" action="/add">
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Informations générales</h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="first_name" class="form-label">Prénom*</label>
                            <input type="text" class="form-control" id="first_name" name="first_name" required>
                        </div>
                        <div class="col-md-6">
                            <label for="last_name" class="form-label">Nom*</label>
                            <input type="text" class="form-control" id="last_name" name="last_name" required>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="category" class="form-label">Catégorie</label>
                            <select class="form-select" id="category" name="category">
                                <option value="">Sélectionner une catégorie</option>
                                {% for cat in categories %}
                                <option value="{{ cat }}">{{ cat }}</option>
                                {% endfor %}
                                <option value="Plombier">Plombier</option>
                                <option value="Électricien">Électricien</option>
                                <option value="Serrurier">Serrurier</option>
                                <option value="Syndic">Syndic</option>
                                <option value="Gestionnaire">Gestionnaire</option>
                                <option value="Maçon">Maçon</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="company_name" class="form-label">Société</label>
                            <input type="text" class="form-control" id="company_name" name="company_name">
                        </div>
                    </div>
                    
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="is_favorite" name="is_favorite" value="1">
                        <label class="form-check-label" for="is_favorite">
                            <i class="fas fa-star text-warning me-1"></i> Marquer comme favori
                        </label>
                    </div>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Coordonnées</h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="phone" class="form-label">Téléphone fixe</label>
                            <input type="tel" class="form-control" id="phone" name="phone">
                        </div>
                        <div class="col-md-6">
                            <label for="mobile_phone" class="form-label">Téléphone mobile</label>
                            <input type="tel" class="form-control" id="mobile_phone" name="mobile_phone">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email">
                    </div>
                    
                    <div class="mb-3">
                        <label for="address" class="form-label">Adresse</label>
                        <input type="text" class="form-control" id="address" name="address">
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4">
                            <label for="postal_code" class="form-label">Code postal</label>
                            <input type="text" class="form-control" id="postal_code" name="postal_code">
                        </div>
                        <div class="col-md-8">
                            <label for="city" class="form-label">Ville</label>
                            <input type="text" class="form-control" id="city" name="city">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Notes et informations supplémentaires</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label for="notes" class="form-label">Notes</label>
                        <textarea class="form-control" id="notes" name="notes" rows="4"></textarea>
                    </div>
                </div>
            </div>
            
            <div class="d-flex justify-content-between mb-5">
                <a href="/" class="btn btn-back">
                    <i class="fas fa-times me-1"></i> Annuler
                </a>
                <button type="submit" class="btn btn-custom">
                    <i class="fas fa-save me-1"></i> Enregistrer le contact
                </button>
            </div>
        </form>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''', categories=categories)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout du contact: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('index'))

@app.route('/edit/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    """Modifier un contact existant"""
    try:
        session, Contact = get_db_session()
        
        # Récupérer le contact
        contact = session.query(Contact).get(contact_id)
        
        if not contact:
            flash("Contact non trouvé", "danger")
            return redirect(url_for('index'))
            
        # Récupérer toutes les catégories uniques pour le formulaire
        categories = [cat[0] for cat in session.query(Contact.category).distinct().all() if cat[0]]
        categories.sort()
        
        if request.method == 'POST':
            # Mettre à jour le contact avec les données du formulaire
            contact.first_name = request.form.get('first_name')
            contact.last_name = request.form.get('last_name')
            contact.email = request.form.get('email')
            contact.phone = request.form.get('phone')
            contact.mobile_phone = request.form.get('mobile_phone')
            contact.address = request.form.get('address')
            contact.postal_code = request.form.get('postal_code')
            contact.city = request.form.get('city')
            contact.category = request.form.get('category')
            contact.company_name = request.form.get('company_name')
            contact.notes = request.form.get('notes')
            contact.is_favorite = bool(request.form.get('is_favorite'))
            contact.updated_at = datetime.now()
            
            # Enregistrer les modifications
            session.commit()
            session.remove()
            
            # Rediriger vers la liste des contacts
            return redirect(url_for('index'))
        
        # Afficher le formulaire d'édition
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modifier le contact</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1d21;
            color: #f8f9fa;
            padding-top: 20px;
            padding-bottom: 40px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
        }
        .card {
            background-color: #242930;
            border: 1px solid #3d4148;
            border-radius: 8px;
            overflow: hidden;
        }
        .card-header {
            background-color: #1e2226;
            border-bottom: 1px solid #3d4148;
            padding: 15px 20px;
        }
        .card-body {
            padding: 25px;
        }
        .btn-back {
            background-color: #3d4148;
            border: none;
            color: #f8f9fa;
            margin-right: 15px;
        }
        .btn-custom {
            background-color: #5b6bff;
            border: none;
            color: white;
            border-radius: 5px;
            padding: 8px 15px;
            transition: all 0.2s;
        }
        .btn-custom:hover {
            background-color: #4959d9;
            color: white;
        }
        .form-label {
            color: #a0a0a0;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        .form-control, .form-select {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
            color: #f8f9fa;
            border-radius: 5px;
            padding: 10px 15px;
        }
        .form-control:focus, .form-select:focus {
            background-color: #1e2226;
            color: #f8f9fa;
            border-color: #5b6bff;
            box-shadow: none;
        }
        .form-check-input {
            background-color: #1a1d21;
            border: 1px solid #3d4148;
        }
        .form-check-input:checked {
            background-color: #5b6bff;
            border-color: #5b6bff;
        }
        .section-title {
            font-size: 1.2rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #3d4148;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="d-flex align-items-center mb-4">
            <a href="/" class="btn btn-back">
                <i class="fas fa-arrow-left"></i>
            </a>
            <h1 class="h4 mb-0">Modifier le contact</h1>
        </div>
        
        <form method="post" action="/edit/{{ contact.id }}">
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Informations générales</h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="first_name" class="form-label">Prénom*</label>
                            <input type="text" class="form-control" id="first_name" name="first_name" value="{{ contact.first_name }}" required>
                        </div>
                        <div class="col-md-6">
                            <label for="last_name" class="form-label">Nom*</label>
                            <input type="text" class="form-control" id="last_name" name="last_name" value="{{ contact.last_name }}" required>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="category" class="form-label">Catégorie</label>
                            <select class="form-select" id="category" name="category">
                                <option value="">Sélectionner une catégorie</option>
                                {% for cat in categories %}
                                <option value="{{ cat }}" {% if contact.category == cat %}selected{% endif %}>{{ cat }}</option>
                                {% endfor %}
                                {% if contact.category and contact.category not in categories %}
                                <option value="{{ contact.category }}" selected>{{ contact.category }}</option>
                                {% endif %}
                                {% if "Plombier" not in categories %}
                                <option value="Plombier" {% if contact.category == "Plombier" %}selected{% endif %}>Plombier</option>
                                {% endif %}
                                {% if "Électricien" not in categories %}
                                <option value="Électricien" {% if contact.category == "Électricien" %}selected{% endif %}>Électricien</option>
                                {% endif %}
                                {% if "Serrurier" not in categories %}
                                <option value="Serrurier" {% if contact.category == "Serrurier" %}selected{% endif %}>Serrurier</option>
                                {% endif %}
                                {% if "Syndic" not in categories %}
                                <option value="Syndic" {% if contact.category == "Syndic" %}selected{% endif %}>Syndic</option>
                                {% endif %}
                                {% if "Gestionnaire" not in categories %}
                                <option value="Gestionnaire" {% if contact.category == "Gestionnaire" %}selected{% endif %}>Gestionnaire</option>
                                {% endif %}
                                {% if "Maçon" not in categories %}
                                <option value="Maçon" {% if contact.category == "Maçon" %}selected{% endif %}>Maçon</option>
                                {% endif %}
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="company_name" class="form-label">Société</label>
                            <input type="text" class="form-control" id="company_name" name="company_name" value="{{ contact.company_name or '' }}">
                        </div>
                    </div>
                    
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="is_favorite" name="is_favorite" value="1" {% if contact.is_favorite %}checked{% endif %}>
                        <label class="form-check-label" for="is_favorite">
                            <i class="fas fa-star text-warning me-1"></i> Marquer comme favori
                        </label>
                    </div>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Coordonnées</h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="phone" class="form-label">Téléphone fixe</label>
                            <input type="tel" class="form-control" id="phone" name="phone" value="{{ contact.phone or '' }}">
                        </div>
                        <div class="col-md-6">
                            <label for="mobile_phone" class="form-label">Téléphone mobile</label>
                            <input type="tel" class="form-control" id="mobile_phone" name="mobile_phone" value="{{ contact.mobile_phone or '' }}">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" value="{{ contact.email or '' }}">
                    </div>
                    
                    <div class="mb-3">
                        <label for="address" class="form-label">Adresse</label>
                        <input type="text" class="form-control" id="address" name="address" value="{{ contact.address or '' }}">
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4">
                            <label for="postal_code" class="form-label">Code postal</label>
                            <input type="text" class="form-control" id="postal_code" name="postal_code" value="{{ contact.postal_code or '' }}">
                        </div>
                        <div class="col-md-8">
                            <label for="city" class="form-label">Ville</label>
                            <input type="text" class="form-control" id="city" name="city" value="{{ contact.city or '' }}">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Notes et informations supplémentaires</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label for="notes" class="form-label">Notes</label>
                        <textarea class="form-control" id="notes" name="notes" rows="4">{{ contact.notes or '' }}</textarea>
                    </div>
                </div>
            </div>
            
            <div class="d-flex justify-content-between mb-5">
                <a href="/" class="btn btn-back">
                    <i class="fas fa-times me-1"></i> Annuler
                </a>
                <button type="submit" class="btn btn-custom">
                    <i class="fas fa-save me-1"></i> Enregistrer les modifications
                </button>
            </div>
        </form>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''', contact=contact, categories=categories)
        
    except Exception as e:
        logging.error(f"Erreur lors de la modification du contact: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('index'))

@app.route('/delete/<int:contact_id>', methods=['GET', 'POST'])
def delete_contact(contact_id):
    """Supprimer un contact"""
    try:
        session, Contact = get_db_session()
        
        # Récupérer le contact
        contact = session.query(Contact).get(contact_id)
        
        if not contact:
            flash("Contact non trouvé", "danger")
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            # Supprimer le contact
            session.delete(contact)
            session.commit()
            session.remove()
            
            # Rediriger vers la liste des contacts
            return redirect(url_for('index'))
        
        # Afficher la page de confirmation
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Supprimer le contact</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #1a1d21;
            color: #f8f9fa;
            padding-top: 20px;
            padding-bottom: 40px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 800px;
        }
        .card {
            background-color: #242930;
            border: 1px solid #3d4148;
            border-radius: 8px;
            overflow: hidden;
        }
        .card-header {
            background-color: #1e2226;
            border-bottom: 1px solid #3d4148;
            padding: 15px 20px;
        }
        .card-body {
            padding: 25px;
        }
        .alert-danger-soft {
            background-color: #422;
            border: 1px solid #733;
            color: #f8f9fa;
        }
        .btn-back {
            background-color: #3d4148;
            border: none;
            color: #f8f9fa;
        }
        .btn-danger-soft {
            background-color: #933;
            border: none;
            color: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card mt-5">
            <div class="card-header">
                <h4 class="mb-0 text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i> Supprimer le contact
                </h4>
            </div>
            <div class="card-body">
                <div class="alert alert-danger-soft mb-4">
                    <h5><i class="fas fa-exclamation-circle me-2"></i> Êtes-vous sûr de vouloir supprimer ce contact ?</h5>
                    <p>Cette action est irréversible. Toutes les informations de ce contact seront perdues définitivement.</p>
                </div>
                
                <div class="mb-4">
                    <h5>Détails du contact à supprimer :</h5>
                    <ul class="list-group list-group-flush bg-transparent">
                        <li class="list-group-item bg-transparent">
                            <strong>Nom :</strong> {{ contact.first_name }} {{ contact.last_name }}
                            {% if contact.is_favorite %}
                                <i class="fas fa-star text-warning ms-2"></i>
                            {% endif %}
                        </li>
                        {% if contact.category %}
                        <li class="list-group-item bg-transparent">
                            <strong>Catégorie :</strong> {{ contact.category }}
                        </li>
                        {% endif %}
                        {% if contact.company_name %}
                        <li class="list-group-item bg-transparent">
                            <strong>Société :</strong> {{ contact.company_name }}
                        </li>
                        {% endif %}
                        {% if contact.phone or contact.mobile_phone %}
                        <li class="list-group-item bg-transparent">
                            <strong>Téléphone :</strong> {{ contact.phone or contact.mobile_phone }}
                        </li>
                        {% endif %}
                    </ul>
                </div>
                
                <form method="post" action="/delete/{{ contact.id }}">
                    <div class="d-flex justify-content-between">
                        <a href="/" class="btn btn-back">
                            <i class="fas fa-arrow-left me-2"></i> Annuler
                        </a>
                        <button type="submit" class="btn btn-danger-soft">
                            <i class="fas fa-trash-alt me-2"></i> Confirmer la suppression
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''', contact=contact)
        
    except Exception as e:
        logging.error(f"Erreur lors de la suppression du contact: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('index'))

# Lancement de l'application en mode standalone
if __name__ == '__main__':
    # Vérifier si la base de données est configurée
    if not DATABASE_URL:
        print("Erreur: Variable d'environnement DATABASE_URL non définie")
        exit(1)
        
    # Lancer le serveur Flask
    app.run(host='0.0.0.0', port=5001, debug=True)