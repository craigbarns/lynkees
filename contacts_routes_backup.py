import os
import logging
from flask import render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from models import Contact, Property, Building
from database import db
from app import app, login_required

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/contacts')
@login_required
def contacts_list():
    """Afficher la liste des contacts avec filtrage"""
    # Récupérer les paramètres de filtrage
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    is_favorite = request.args.get('is_favorite', '')
    
    # Construire la requête
    query = Contact.query
    
    # Filtre de recherche (nom, prénom, société, email, téléphone)
    if search:
        query = query.filter(
            or_(
                Contact.first_name.ilike(f'%{search}%'),
                Contact.last_name.ilike(f'%{search}%'),
                Contact.company_name.ilike(f'%{search}%'),
                Contact.email.ilike(f'%{search}%'),
                Contact.phone.ilike(f'%{search}%'),
                Contact.mobile_phone.ilike(f'%{search}%')
            )
        )
    
    # Filtre par catégorie
    if category:
        query = query.filter(Contact.category == category)
    
    # Filtre par favoris
    if is_favorite == 'yes':
        query = query.filter(Contact.is_favorite == True)
    
    # Trier par nom
    query = query.order_by(Contact.last_name, Contact.first_name)
    
    # Récupérer les contacts
    contacts = query.all()
    
    # Récupérer la liste des catégories pour le filtre
    categories = db.session.query(Contact.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template(
        'contacts/list.html',
        contacts=contacts,
        categories=categories,
        filters=request.args
    )


@app.route('/contact/add', methods=['GET', 'POST'])
@login_required
def add_contact():
    """Ajouter un nouveau contact"""
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
            return redirect(url_for('add_contact'))
        
        try:
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
            
            # Ajouter les propriétés associées
            if property_ids:
                properties = Property.query.filter(Property.id.in_(property_ids)).all()
                new_contact.properties.extend(properties)
            
            # Ajouter les bâtiments associés
            if building_ids:
                buildings = Building.query.filter(Building.id.in_(building_ids)).all()
                new_contact.buildings.extend(buildings)
            
            db.session.add(new_contact)
            db.session.commit()
            
            flash('Contact ajouté avec succès !', 'success')
            return redirect(url_for('contact_detail', contact_id=new_contact.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout du contact : {str(e)}', 'danger')
            logging.error(f"Erreur lors de l'ajout du contact : {str(e)}")
    
    # Pour le formulaire GET
    properties = Property.query.all()
    buildings = Building.query.all()
    
    # Catégories prédéfinies
    categories = [
        'Plombier', 'Électricien', 'Maçon', 'Syndic', 'Gestionnaire', 
        'Serrurier', 'Peintre', 'Menuisier', 'Chauffagiste', 'Jardinier',
        'Agent immobilier', 'Notaire', 'Avocat', 'Comptable', 'Autre'
    ]
    
    return render_template(
        'contacts/add.html',
        properties=properties,
        buildings=buildings,
        categories=categories
    )


@app.route('/contact/<int:contact_id>')
@login_required
def contact_detail(contact_id):
    """Afficher les détails d'un contact"""
    contact = Contact.query.get_or_404(contact_id)
    return render_template('contacts/detail.html', contact=contact)


@app.route('/contact/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
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
    
    # Propriétés et bâtiments déjà associés
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


@app.route('/contact/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Supprimer un contact"""
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        # Supprimer le contact
        db.session.delete(contact)
        db.session.commit()
        
        flash('Contact supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du contact : {str(e)}', 'danger')
        logging.error(f"Erreur lors de la suppression du contact : {str(e)}")
    
    return redirect(url_for('contacts_list'))


@app.route('/contact/<int:contact_id>/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite(contact_id):
    """Ajouter/supprimer un contact des favoris"""
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        # Inverser le statut de favori
        contact.is_favorite = not contact.is_favorite
        db.session.commit()
        
        # En cas d'appel AJAX, retourner un JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'is_favorite': contact.is_favorite,
                'message': f"Contact {'ajouté aux' if contact.is_favorite else 'retiré des'} favoris"
            })
        
        flash(f"Contact {'ajouté aux' if contact.is_favorite else 'retiré des'} favoris", 'success')
    except Exception as e:
        db.session.rollback()
        
        # En cas d'appel AJAX, retourner une erreur
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
            
        flash(f'Erreur : {str(e)}', 'danger')
        logging.error(f"Erreur lors du changement de statut favori : {str(e)}")
    
    # Pour un appel normal, rediriger vers la page de détail
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect(url_for('contact_detail', contact_id=contact_id))
    
    # Si AJAX et nous sommes ici, c'est une erreur
    return jsonify({'success': False, 'error': 'Unknown error'}), 500