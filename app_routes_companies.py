from flask import render_template, redirect, url_for, flash, request, send_from_directory, session
from app import app, db
from models import Company, Document, Property
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
from functools import wraps
import logging

# Récupérer la fonction login_required depuis app.py
from app import login_required, allowed_file, generate_unique_filename


# Routes pour la base documentaire
@app.route('/companies')
@login_required
def companies_list():
    """Afficher la liste des sociétés et leurs documents"""
    companies = Company.query.all()
    current_year = datetime.now().year
    return render_template('companies/list.html', companies=companies, current_year=current_year)


@app.route('/companies/add', methods=['GET', 'POST'])
@login_required
def add_company():
    """Ajouter une nouvelle société"""
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        description = request.form.get('description')
        
        if not name:
            flash('Le nom de la société est obligatoire', 'danger')
            return redirect(url_for('add_company'))
        
        try:
            # Vérifier si une société avec ce nom existe déjà
            existing_company = Company.query.filter_by(name=name).first()
            if existing_company:
                flash(f'Une société avec le nom "{name}" existe déjà', 'warning')
                return redirect(url_for('add_company'))
            
            # Créer une nouvelle société
            new_company = Company(
                name=name,
                address=address,
                description=description
            )
            db.session.add(new_company)
            db.session.commit()
            
            flash('Société ajoutée avec succès !', 'success')
            return redirect(url_for('company_detail', company_id=new_company.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout de la société: {str(e)}', 'danger')
            logging.error(f"Erreur lors de l'ajout de la société: {str(e)}")
    
    return render_template('companies/add.html')


@app.route('/companies/<int:company_id>')
@login_required
def company_detail(company_id):
    """Afficher les détails d'une société et ses documents"""
    company = Company.query.get_or_404(company_id)
    
    # Paramètres de filtrage
    doc_type = request.args.get('doc_type', '')
    doc_category = request.args.get('doc_category', '')
    year = request.args.get('year', '')
    search = request.args.get('search', '')
    
    # Debug des filtres
    logging.info(f"Filtres appliqués - Type: {doc_type}, Catégorie: {doc_category}, Année: {year}, Recherche: {search}")
    
    # Requête de base pour les documents
    query = Document.query.filter_by(company_id=company_id)
    
    # Appliquer les filtres
    if doc_type:
        query = query.filter_by(document_type=doc_type)
        logging.info(f"Filtre par type de document: {doc_type}")
    
    if doc_category:
        query = query.filter_by(document_category=doc_category)
        logging.info(f"Filtre par catégorie: {doc_category}")
    
    if year and year.strip():
        try:
            year_int = int(year)
            start_date = datetime(year_int, 1, 1).date()
            end_date = datetime(year_int, 12, 31).date()
            query = query.filter(Document.document_date >= start_date, Document.document_date <= end_date)
            logging.info(f"Filtre par année: {year_int} (du {start_date} au {end_date})")
        except (ValueError, TypeError) as e:
            logging.error(f"Erreur de conversion de l'année: {str(e)}")
    
    if search:
        query = query.filter(Document.filename.ilike(f'%{search}%'))
        logging.info(f"Filtre par recherche: {search}")
    
    # Récupérer les documents filtrés
    documents = query.order_by(Document.uploaded_at.desc()).all()
    
    # Récupérer les types de documents uniques
    document_types = list(set(doc.document_type for doc in company.documents if doc.document_type))
    
    # Récupérer les années uniques des documents
    document_years = []
    for doc in company.documents:
        if doc.document_date:
            year = doc.document_date.year
            if year not in document_years:
                document_years.append(year)
    document_years.sort(reverse=True)
    
    # Récupérer les propriétés liées à cette société
    properties = Property.query.filter_by(company_id=company.id).all()
    
    return render_template(
        'companies/detail.html',
        company=company,
        documents=documents,
        document_types=document_types,
        document_years=document_years,
        properties=properties
    )


@app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_company(company_id):
    """Modifier une société existante"""
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        description = request.form.get('description')
        
        if not name:
            flash('Le nom de la société est obligatoire', 'danger')
            return redirect(url_for('edit_company', company_id=company_id))
        
        try:
            # Vérifier si une autre société utilise déjà ce nom
            existing_company = Company.query.filter(Company.name == name, Company.id != company_id).first()
            if existing_company:
                flash(f'Une autre société utilise déjà le nom "{name}"', 'warning')
                return redirect(url_for('edit_company', company_id=company_id))
            
            # Mettre à jour la société
            company.name = name
            company.address = address
            company.description = description
            
            db.session.commit()
            flash('Société mise à jour avec succès !', 'success')
            return redirect(url_for('company_detail', company_id=company_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification de la société: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la modification de la société: {str(e)}")
    
    return render_template('companies/edit.html', company=company)


@app.route('/companies/<int:company_id>/delete', methods=['POST'])
@login_required
def delete_company(company_id):
    """Supprimer une société et tous ses documents associés"""
    company = Company.query.get_or_404(company_id)
    
    try:
        # Récupérer tous les documents associés
        documents = Document.query.filter_by(company_id=company_id).all()
        
        # Supprimer les fichiers des documents
        for document in documents:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Supprimer la société (les documents seront supprimés en cascade)
        db.session.delete(company)
        db.session.commit()
        
        flash('Société et tous ses documents supprimés avec succès', 'success')
        return redirect(url_for('companies_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression de la société: {str(e)}', 'danger')
        logging.error(f"Erreur lors de la suppression de la société: {str(e)}")
        return redirect(url_for('company_detail', company_id=company_id))


@app.route('/companies/<int:company_id>/upload', methods=['POST'])
@login_required
def upload_company_document(company_id):
    """Télécharger un document pour une société"""
    company = Company.query.get_or_404(company_id)
    
    # Vérifier si le document est présent dans la requête
    if 'document' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('company_detail', company_id=company_id))
    
    file = request.files['document']
    
    # Vérifier si un fichier a été sélectionné
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('company_detail', company_id=company_id))
    
    # Vérifier si le type de fichier est autorisé
    if file and allowed_file(file.filename):
        # Sécuriser le nom de fichier et le rendre unique
        filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(filename)
        
        # Sauvegarder le fichier
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        try:
            # Récupérer les autres informations du formulaire
            document_type = request.form.get('document_type')
            document_category = request.form.get('document_category')
            document_date_str = request.form.get('document_date')
            amount_str = request.form.get('amount')
            description = request.form.get('description')
            
            # Convertir la date si elle est fournie
            document_date = None
            if document_date_str:
                try:
                    document_date = datetime.strptime(document_date_str, '%d/%m/%Y').date()
                except ValueError:
                    flash('Format de date incorrect, utilisez JJ/MM/AAAA', 'warning')
            
            # Convertir le montant si fourni
            amount = None
            if amount_str:
                try:
                    amount = float(amount_str)
                except ValueError:
                    flash('Format de montant incorrect', 'warning')
            
            # Récupérer l'ID de la propriété si sélectionné
            property_id_str = request.form.get('property_id', '')
            property_id = None
            
            if property_id_str and property_id_str.strip():
                try:
                    property_id = int(property_id_str)
                    # Vérifier que la propriété existe et appartient à cette société
                    property_obj = Property.query.filter_by(id=property_id, company_id=company_id).first()
                    if not property_obj:
                        property_id = None
                        flash('La propriété sélectionnée n\'appartient pas à cette société ou n\'existe pas', 'warning')
                except (ValueError, TypeError):
                    property_id = None
                    flash('ID de propriété invalide', 'warning')
            
            # Créer le document en base de données
            document = Document(
                company_id=company_id,
                property_id=property_id,  # Associer au bien immobilier si sélectionné
                filename=filename,  # Nom d'origine pour l'affichage
                filepath=unique_filename,  # Nom unique sur le serveur
                document_type=document_type,
                document_category=document_category,
                document_date=document_date,
                amount=amount,
                description=description
            )
            db.session.add(document)
            db.session.commit()
            
            flash('Document téléchargé avec succès !', 'success')
            
        except Exception as e:
            db.session.rollback()
            # Supprimer le fichier en cas d'erreur
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f'Erreur lors de l\'enregistrement du document: {str(e)}', 'danger')
            logging.error(f"Erreur lors de l'enregistrement du document: {str(e)}")
    else:
        flash('Type de fichier non autorisé', 'danger')
    
    return redirect(url_for('company_detail', company_id=company_id))


@app.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    """Modifier un document existant"""
    document = Document.query.get_or_404(document_id)
    
    # Déterminer la source du document (société ou propriété)
    is_company_document = document.company_id is not None
    
    # Récupérer les listes pour les menus déroulants
    companies = Company.query.all() if document.property_id else []
    properties = Property.query.all() if document.company_id else []
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            document_type = request.form.get('document_type')
            document_category = request.form.get('document_category')
            document_date_str = request.form.get('document_date')
            amount_str = request.form.get('amount')
            description = request.form.get('description')
            
            # Vérifier si un déplacement est demandé
            new_company_id = request.form.get('company_id', '')
            new_property_id = request.form.get('property_id', '')
            
            # Mettre à jour les champs principaux
            document.document_type = document_type
            document.document_category = document_category
            document.description = description
            
            # Convertir la date si elle est fournie
            if document_date_str:
                try:
                    document.document_date = datetime.strptime(document_date_str, '%d/%m/%Y').date()
                except ValueError:
                    flash('Format de date incorrect, utilisez JJ/MM/AAAA', 'warning')
            else:
                document.document_date = None
            
            # Convertir le montant si fourni
            if amount_str:
                try:
                    document.amount = float(amount_str)
                except ValueError:
                    flash('Format de montant incorrect', 'warning')
            else:
                document.amount = None
            
            # Gérer le déplacement du document si demandé
            if document.property_id and new_company_id:
                # Déplacer de propriété vers société
                document.company_id = int(new_company_id)
                document.property_id = None
                flash('Document déplacé de la propriété vers la société', 'info')
            elif document.company_id and new_property_id:
                # Déplacer de société vers propriété
                document.property_id = int(new_property_id)
                document.company_id = None
                flash('Document déplacé de la société vers la propriété', 'info')
            
            db.session.commit()
            flash('Document mis à jour avec succès !', 'success')
            
            # Rediriger vers la page appropriée
            if document.company_id:
                return redirect(url_for('company_detail', company_id=document.company_id))
            else:
                return redirect(url_for('property_detail', property_id=document.property_id))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification du document: {str(e)}', 'danger')
            logging.error(f"Erreur lors de la modification du document: {str(e)}")
    
    return render_template(
        'documents/edit.html',
        document=document,
        companies=companies,
        properties=properties
    )