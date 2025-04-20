#!/usr/bin/env python3
"""
Application Flask indépendante pour afficher les contacts
Ce script peut être exécuté séparément de l'application principale
"""

import os
import logging
from flask import Flask, render_template_string, request, redirect, url_for, flash

# Configurer le logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Créer une application Flask indépendante
standalone_app = Flask(__name__)
standalone_app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Importer les modèles et la base de données à l'intérieur d'une fonction
# pour éviter les problèmes de dépendances circulaires
def get_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base
    from models import Contact
    
    database_url = os.environ.get("DATABASE_URL", "sqlite:///property_management.db")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    return session, Contact

@standalone_app.route('/')
def show_contacts():
    """Afficher la liste des contacts depuis la base de données - Version autonome"""
    try:
        # Obtenir une session de base de données
        session, Contact = get_db_session()
        
        # Récupérer tous les contacts, triés par favori puis par nom
        contacts = session.query(Contact).order_by(Contact.is_favorite.desc(), 
                                                 Contact.last_name, 
                                                 Contact.first_name).all()
        
        # Générer le HTML pour chaque contact
        contact_items_html = ""
        for contact in contacts:
            # Définir une couleur de badge en fonction de la catégorie
            badge_color = "primary"  # Couleur par défaut
            if contact.category.lower() in ["électricien", "electricien"]:
                badge_color = "danger"
            elif contact.category.lower() == "plombier":
                badge_color = "primary"
            elif contact.category.lower() == "syndic":
                badge_color = "info"
            elif contact.category.lower() == "gestionnaire":
                badge_color = "success"
            elif contact.category.lower() == "maçon":
                badge_color = "secondary"
            
            # Construire l'adresse complète si elle existe
            address_parts = []
            if contact.address:
                address_parts.append(contact.address)
            if contact.postal_code and contact.city:
                address_parts.append(f"{contact.postal_code} {contact.city}")
            elif contact.city:
                address_parts.append(contact.city)
                
            full_address = ", ".join(address_parts) if address_parts else "Non renseignée"
            
            # Construire les téléphones
            phones = []
            if contact.phone:
                phones.append(contact.phone)
            if contact.mobile_phone:
                phones.append(contact.mobile_phone)
                
            phone_display = " / ".join(phones) if phones else "Non renseigné"
            
            # Construire l'élément de contact HTML
            contact_items_html += f'''
            <div class="contact-item">
                <div class="contact-header">
                    {('<i class="favorite-star">★</i> ' if contact.is_favorite else '')}
                    {contact.first_name} {contact.last_name}
                </div>
                <span class="badge bg-{badge_color}">{contact.category}</span>
                <div class="contact-details mt-2">
                    <div><strong>Société:</strong> {contact.company_name or 'Non renseignée'}</div>
                    <div><strong>Téléphone:</strong> {phone_display}</div>
                    <div><strong>Email:</strong> {contact.email or 'Non renseigné'}</div>
                    <div><strong>Adresse:</strong> {full_address}</div>
                    <div><strong>Notes:</strong> {contact.notes or 'Aucune note'}</div>
                </div>
            </div>
            '''
            
        # Fermer la session
        session.close()
        
        # Retourner le template HTML complet
        return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste des Contacts</title>
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
    </style>
</head>
<body class="bg-dark text-light">
    <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Liste des Contacts</h1>
            <a href="/add" class="btn btn-success">
                <i class="fas fa-plus-circle"></i> Ajouter un contact
            </a>
        </div>
        
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h2 class="h4 mb-0">Contacts disponibles</h2>
                <span class="badge bg-secondary">{{ contact_count }} contacts</span>
            </div>
            <div class="card-body p-0">
                {% if contacts %}
                    {{ contact_items|safe }}
                {% else %}
                    <div class="p-4 text-center">
                        <p>Aucun contact disponible.</p>
                        <a href="/add" class="btn btn-sm btn-success">Ajouter un contact</a>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <div class="alert alert-info">
            <p><strong>Note:</strong> Cette page est un accès direct aux contacts, sans authentification requise.</p>
            <p>Retourner à <a href="/" class="alert-link">la page d'accueil</a>.</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://kit.fontawesome.com/a076d05399.js" crossorigin="anonymous"></script>
</body>
</html>''', contacts=contacts, contact_items=contact_items_html, contact_count=len(contacts))
        
    except Exception as e:
        logging.error(f"Erreur lors de l'affichage des contacts: {str(e)}")
        return f'''
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Erreur lors de l'affichage des contacts</h4>
                <p>{str(e)}</p>
                <p>Vérifiez les logs pour plus de détails.</p>
            </div>
        </div>
        '''

@standalone_app.route('/add', methods=['GET', 'POST'])
def add_contact():
    """Ajouter un nouveau contact sans authentification"""
    session, Contact = get_db_session()
    
    if request.method == 'POST':
        logging.info("Soumission du formulaire d'ajout de contact - Méthode POST")
        
        # Log tous les champs du formulaire pour déboguer
        form_data = dict(request.form)
        logging.info(f"Données du formulaire : {form_data}")
        
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
        
        logging.info(f"Champs obligatoires : first_name={first_name}, last_name={last_name}, category={category}")
        
        if not first_name or not last_name or not category:
            logging.warning("Validation échouée : champs obligatoires manquants")
            flash('Le prénom, le nom et la catégorie sont des champs obligatoires', 'danger')
            return redirect(url_for('add_contact'))
        
        try:
            logging.info("Création d'un nouveau contact")
            # Créer un nouveau contact
            new_contact = Contact(
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                category=category,
                email=email,
                phone=phone,
                mobile_phone=mobile_phone,
                address=address,
                postal_code=postal_code,
                city=city,
                notes=notes,
                is_favorite=is_favorite
            )
            
            logging.info("Ajout du contact à la session et commit")
            session.add(new_contact)
            session.commit()
            
            logging.info(f"Contact {new_contact.id} ajouté avec succès")
            flash('Contact ajouté avec succès !', 'success')
            return redirect(url_for('show_contacts'))
        except Exception as e:
            session.rollback()
            logging.error(f"Erreur lors de l'ajout du contact : {str(e)}")
            flash(f'Erreur lors de l\'ajout du contact : {str(e)}', 'danger')
    
    # Catégories prédéfinies
    categories = [
        'Plombier', 'Électricien', 'Maçon', 'Syndic', 'Gestionnaire', 
        'Serrurier', 'Peintre', 'Menuisier', 'Chauffagiste', 'Jardinier',
        'Agent immobilier', 'Notaire', 'Avocat', 'Comptable', 'Autre'
    ]
    
    # Fermer la session
    session.close()
    
    # Afficher le formulaire d'ajout
    return render_template_string('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ajouter un contact</title>
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
        }
        .form-control, .form-select {
            background-color: #343a40;
            border: 1px solid #495057;
            color: #f8f9fa;
        }
        .form-control:focus, .form-select:focus {
            background-color: #3a4147;
            color: #f8f9fa;
            border-color: #80bdff;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        .container {
            max-width: 900px;
            margin: 30px auto;
        }
        .btn-primary {
            background-color: #0d6efd;
            border-color: #0d6efd;
        }
        .btn-secondary {
            background-color: #6c757d;
            border-color: #6c757d;
        }
    </style>
</head>
<body class="bg-dark text-light">
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        <div class="card bg-dark">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h1 class="card-title h4 mb-0">Ajouter un contact</h1>
                <a href="/" class="btn btn-outline-secondary">
                    <i class="fas fa-arrow-left me-1"></i> Retour à la liste
                </a>
            </div>
            <div class="card-body">
                <form action="/add" method="post">
                    <div class="row g-3">
                        <!-- Informations personnelles -->
                        <div class="col-md-6">
                            <div class="card bg-dark border-light mb-4">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Informations personnelles</h5>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label for="first_name" class="form-label">Prénom <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="first_name" name="first_name" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="last_name" class="form-label">Nom <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="last_name" name="last_name" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="company_name" class="form-label">Société</label>
                                        <input type="text" class="form-control" id="company_name" name="company_name">
                                    </div>
                                    <div class="mb-3">
                                        <label for="category" class="form-label">Catégorie <span class="text-danger">*</span></label>
                                        <select class="form-select" id="category" name="category" required>
                                            <option value="">Sélectionner une catégorie</option>
                                            {% for category in categories %}
                                            <option value="{{ category }}">{{ category }}</option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="form-check form-switch mb-3">
                                        <input class="form-check-input" type="checkbox" id="is_favorite" name="is_favorite" value="1">
                                        <label class="form-check-label" for="is_favorite">Ajouter aux favoris</label>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Coordonnées -->
                        <div class="col-md-6">
                            <div class="card bg-dark border-light mb-4">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Coordonnées</h5>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label for="email" class="form-label">Email</label>
                                        <input type="email" class="form-control" id="email" name="email">
                                    </div>
                                    <div class="mb-3">
                                        <label for="phone" class="form-label">Téléphone fixe</label>
                                        <input type="tel" class="form-control" id="phone" name="phone">
                                    </div>
                                    <div class="mb-3">
                                        <label for="mobile_phone" class="form-label">Téléphone mobile</label>
                                        <input type="tel" class="form-control" id="mobile_phone" name="mobile_phone">
                                    </div>
                                    <div class="mb-3">
                                        <label for="address" class="form-label">Adresse</label>
                                        <input type="text" class="form-control" id="address" name="address">
                                    </div>
                                    <div class="row">
                                        <div class="col-md-4 mb-3">
                                            <label for="postal_code" class="form-label">Code postal</label>
                                            <input type="text" class="form-control" id="postal_code" name="postal_code">
                                        </div>
                                        <div class="col-md-8 mb-3">
                                            <label for="city" class="form-label">Ville</label>
                                            <input type="text" class="form-control" id="city" name="city">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Notes -->
                        <div class="col-12">
                            <div class="card bg-dark border-light mb-4">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">Notes</h5>
                                </div>
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label for="notes" class="form-label">Notes et commentaires</label>
                                        <textarea class="form-control" id="notes" name="notes" rows="3"></textarea>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Boutons d'action -->
                        <div class="col-12 text-end">
                            <button type="reset" class="btn btn-secondary me-2">Réinitialiser</button>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save me-1"></i> Enregistrer
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://kit.fontawesome.com/a076d05399.js" crossorigin="anonymous"></script>
</body>
</html>''', categories=categories)

if __name__ == "__main__":
    # Exécuter l'application sur le port 5001 pour éviter les conflits
    standalone_app.run(host="0.0.0.0", port=5001, debug=True)