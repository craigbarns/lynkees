from flask import render_template, redirect, url_for, flash, request, session
from app import app, db
from models import Expense, Property, Building, Company, Document
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, date
import uuid
from app import login_required, allowed_file, generate_unique_filename
import logging


@app.route('/charges')
@login_required
def charges_list():
    """Afficher la liste des charges avec filtrage"""
    # Récupérer les paramètres de filtrage
    charge_type = request.args.get('type', '')
    property_id = request.args.get('property_id', '')
    status = request.args.get('status', '')
    period = request.args.get('period', '')
    
    # Base de la requête
    query = Expense.query
    
    # Appliquer les filtres
    if charge_type:
        query = query.filter(Expense.charge_type == charge_type)
    
    if property_id:
        query = query.filter(Expense.property_id == property_id)
    
    if status:
        query = query.filter(Expense.status == status)
    
    if period:
        today = date.today()
        if period == '1':  # Ce mois
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        elif period == '3':  # 3 derniers mois
            start_date = today - timedelta(days=90)
            end_date = today
        elif period == '6':  # 6 derniers mois
            start_date = today - timedelta(days=180)
            end_date = today
        elif period == '12':  # Cette année
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        
        query = query.filter(Expense.due_date >= start_date, Expense.due_date <= end_date)
    
    # Mettre à jour les statuts des charges avant l'affichage
    update_expenses_status()
    
    # Récupérer les charges filtrées
    charges = query.order_by(Expense.due_date.desc()).all()
    
    # Calculer les statistiques
    total_amount = sum(charge.amount for charge in charges)
    paid_charges = [charge for charge in charges if charge.status == 'payé']
    paid_amount = sum(charge.amount for charge in paid_charges)
    paid_count = len(paid_charges)
    
    pending_charges = [charge for charge in charges if charge.status == 'à_payer']
    pending_amount = sum(charge.amount for charge in pending_charges)
    pending_count = len(pending_charges)
    
    overdue_charges = [charge for charge in charges if charge.status == 'en_retard']
    overdue_amount = sum(charge.amount for charge in overdue_charges)
    overdue_count = len(overdue_charges)
    
    # Récupérer toutes les propriétés pour le filtre
    properties = Property.query.all()
    
    return render_template(
        'charges/list.html',
        charges=charges,
        properties=properties,
        total_amount=total_amount,
        paid_amount=paid_amount,
        paid_count=paid_count,
        pending_amount=pending_amount,
        pending_count=pending_count,
        overdue_amount=overdue_amount,
        overdue_count=overdue_count
    )


@app.route('/charges/add', methods=['GET', 'POST'])
@login_required
def add_charge():
    """Ajouter une nouvelle charge"""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            charge_type = request.form.get('charge_type')
            association_type = request.form.get('association_type')
            amount = request.form.get('amount')
            due_date_str = request.form.get('due_date')
            reference = request.form.get('reference')
            status = request.form.get('status', 'à_payer')
            payment_date_str = request.form.get('payment_date')
            period_start_str = request.form.get('period_start')
            period_end_str = request.form.get('period_end')
            description = request.form.get('description')
            is_recurring = 'is_recurring' in request.form
            recurring_frequency = request.form.get('recurring_frequency')
            recurring_count = request.form.get('recurring_count')
            
            # Convertir les dates
            due_date = datetime.strptime(due_date_str, '%d/%m/%Y').date() if due_date_str else None
            payment_date = datetime.strptime(payment_date_str, '%d/%m/%Y').date() if payment_date_str else None
            period_start = datetime.strptime(period_start_str, '%d/%m/%Y').date() if period_start_str else None
            period_end = datetime.strptime(period_end_str, '%d/%m/%Y').date() if period_end_str else None
            
            # Récupérer l'ID associé selon le type d'association
            property_id = None
            building_id = None
            company_id = None
            
            if association_type == 'property':
                property_id = request.form.get('property_id')
            elif association_type == 'building':
                building_id = request.form.get('building_id')
            elif association_type == 'company':
                company_id = request.form.get('company_id')
            
            # Gérer le téléchargement de document s'il est fourni
            document_id = None
            if 'document' in request.files and request.files['document'].filename:
                file = request.files['document']
                if allowed_file(file.filename):
                    # Sécuriser le nom de fichier
                    filename = secure_filename(file.filename)
                    unique_filename = generate_unique_filename(filename)
                    
                    # Sauvegarder le fichier
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Créer l'entrée de document en DB
                    document = Document(
                        filename=filename,
                        filepath=unique_filename,
                        document_type=charge_type,
                        document_category='charges',
                        document_date=due_date,
                        property_id=property_id,
                        company_id=company_id,
                        description=f"Document associé à la charge {reference or 'sans référence'}"
                    )
                    db.session.add(document)
                    db.session.flush()  # Pour obtenir l'ID
                    document_id = document.id
            
            # Créer un identifiant de groupe pour les charges récurrentes
            recurring_group_id = str(uuid.uuid4()) if is_recurring else None
            
            # Préparer la première charge (ou la seule si non récurrente)
            charge = Expense(
                charge_type=charge_type,
                property_id=property_id,
                building_id=building_id,
                company_id=company_id,
                amount=float(amount),
                due_date=due_date,
                payment_date=payment_date,
                status=status,
                reference=reference,
                period_start=period_start,
                period_end=period_end,
                description=description,
                is_recurring=is_recurring,
                recurring_frequency=recurring_frequency if is_recurring else None,
                recurring_group_id=recurring_group_id,
                document_id=document_id
            )
            
            db.session.add(charge)
            
            # Si récurrente, créer les charges supplémentaires
            if is_recurring and recurring_count and int(recurring_count) > 1:
                count = int(recurring_count)
                frequency = recurring_frequency
                
                # Déterminer l'intervalle pour les dates suivantes
                if frequency == 'mensuel':
                    delta_months = 1
                elif frequency == 'trimestriel':
                    delta_months = 3
                elif frequency == 'semestriel':
                    delta_months = 6
                elif frequency == 'annuel':
                    delta_months = 12
                else:
                    delta_months = 1  # Par défaut
                
                next_due_date = due_date
                for i in range(1, count):
                    # Calculer la prochaine date d'échéance
                    month = next_due_date.month + delta_months
                    year = next_due_date.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    try:
                        next_due_date = date(year, month, next_due_date.day)
                    except ValueError:  # Si le jour est invalide (ex: 31 février)
                        # Obtenir le dernier jour du mois
                        if month == 12:
                            last_day = date(year + 1, 1, 1) - timedelta(days=1)
                        else:
                            last_day = date(year, month + 1, 1) - timedelta(days=1)
                        next_due_date = last_day
                    
                    # Calculer les nouvelles dates de période si nécessaire
                    next_period_start = None
                    next_period_end = None
                    if period_start and period_end:
                        period_length = (period_end - period_start).days
                        next_period_start = next_due_date - timedelta(days=period_length)
                        next_period_end = next_due_date
                    
                    # Créer la charge récurrente
                    recurring_charge = Expense(
                        charge_type=charge_type,
                        property_id=property_id,
                        building_id=building_id,
                        company_id=company_id,
                        amount=float(amount),
                        due_date=next_due_date,
                        status='à_payer',  # Toujours "à payer" pour les futures charges
                        reference=reference,
                        period_start=next_period_start,
                        period_end=next_period_end,
                        description=description,
                        is_recurring=is_recurring,
                        recurring_frequency=recurring_frequency,
                        recurring_group_id=recurring_group_id
                    )
                    db.session.add(recurring_charge)
            
            db.session.commit()
            flash('Charge ajoutée avec succès !', 'success')
            
            if is_recurring and int(recurring_count) > 1:
                flash(f'{recurring_count} charges récurrentes ont été créées.', 'info')
                
            return redirect(url_for('charges_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout de la charge: {str(e)}", 'danger')
            logging.error(f"Erreur lors de l'ajout de la charge: {str(e)}")
    
    # Récupérer les données pour les listes déroulantes
    properties = Property.query.all()
    buildings = Building.query.all()
    companies = Company.query.all()
    
    return render_template(
        'charges/add.html',
        properties=properties,
        buildings=buildings,
        companies=companies
    )


@app.route('/charges/<int:charge_id>')
@login_required
def charge_detail(charge_id):
    """Afficher les détails d'une charge"""
    charge = Expense.query.get_or_404(charge_id)
    
    # Récupérer les charges liées (si récurrente)
    related_charges = []
    if charge.is_recurring and charge.recurring_group_id:
        related_charges = Expense.query.filter(
            Expense.recurring_group_id == charge.recurring_group_id
        ).order_by(Expense.due_date).all()
    
    return render_template(
        'charges/detail.html',
        charge=charge,
        related_charges=related_charges
    )


@app.route('/charges/<int:charge_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_charge(charge_id):
    """Modifier une charge existante"""
    charge = Expense.query.get_or_404(charge_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            charge_type = request.form.get('charge_type')
            association_type = request.form.get('association_type')
            amount = request.form.get('amount')
            due_date_str = request.form.get('due_date')
            reference = request.form.get('reference')
            status = request.form.get('status')
            payment_date_str = request.form.get('payment_date')
            period_start_str = request.form.get('period_start')
            period_end_str = request.form.get('period_end')
            description = request.form.get('description')
            update_all_recurring = 'update_all_recurring' in request.form
            
            # Convertir les dates
            due_date = datetime.strptime(due_date_str, '%d/%m/%Y').date() if due_date_str else None
            payment_date = datetime.strptime(payment_date_str, '%d/%m/%Y').date() if payment_date_str else None
            period_start = datetime.strptime(period_start_str, '%d/%m/%Y').date() if period_start_str else None
            period_end = datetime.strptime(period_end_str, '%d/%m/%Y').date() if period_end_str else None
            
            # Mettre à jour le type d'association
            property_id = None
            building_id = None
            company_id = None
            
            if association_type == 'property':
                property_id = request.form.get('property_id')
            elif association_type == 'building':
                building_id = request.form.get('building_id')
            elif association_type == 'company':
                company_id = request.form.get('company_id')
            
            # Mettre à jour la charge
            charge.charge_type = charge_type
            charge.property_id = property_id
            charge.building_id = building_id
            charge.company_id = company_id
            charge.amount = float(amount)
            charge.due_date = due_date
            charge.payment_date = payment_date
            charge.status = status
            charge.reference = reference
            charge.period_start = period_start
            charge.period_end = period_end
            charge.description = description
            
            # Si demandé, mettre à jour toutes les charges récurrentes futures
            if update_all_recurring and charge.is_recurring and charge.recurring_group_id:
                future_charges = Expense.query.filter(
                    Expense.recurring_group_id == charge.recurring_group_id,
                    Expense.due_date > datetime.now().date(),
                    Expense.id != charge.id
                ).all()
                
                for future_charge in future_charges:
                    future_charge.charge_type = charge_type
                    future_charge.property_id = property_id
                    future_charge.building_id = building_id
                    future_charge.company_id = company_id
                    future_charge.amount = float(amount)
                    future_charge.reference = reference
                    future_charge.description = description
            
            db.session.commit()
            flash('Charge modifiée avec succès !', 'success')
            return redirect(url_for('charge_detail', charge_id=charge.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la modification de la charge: {str(e)}", 'danger')
            logging.error(f"Erreur lors de la modification de la charge: {str(e)}")
    
    # Déterminer le type d'association actuel
    if charge.property_id:
        association_type = 'property'
    elif charge.building_id:
        association_type = 'building'
    elif charge.company_id:
        association_type = 'company'
    else:
        association_type = 'property'  # Par défaut
    
    # Récupérer les données pour les listes déroulantes
    properties = Property.query.all()
    buildings = Building.query.all()
    companies = Company.query.all()
    
    return render_template(
        'charges/edit.html',
        charge=charge,
        properties=properties,
        buildings=buildings,
        companies=companies,
        association_type=association_type
    )


@app.route('/charges/<int:charge_id>/delete', methods=['POST'])
@login_required
def delete_charge(charge_id):
    """Supprimer une charge"""
    charge = Expense.query.get_or_404(charge_id)
    delete_all_recurring = request.form.get('delete_all_recurring') == 'true'
    
    try:
        # Si demandé, supprimer toutes les charges récurrentes
        if delete_all_recurring and charge.is_recurring and charge.recurring_group_id:
            related_charges = Expense.query.filter(
                Expense.recurring_group_id == charge.recurring_group_id,
                Expense.id != charge.id
            ).all()
            
            for related_charge in related_charges:
                db.session.delete(related_charge)
            
            flash(f'{len(related_charges) + 1} charges récurrentes supprimées avec succès !', 'success')
        else:
            db.session.delete(charge)
            flash('Charge supprimée avec succès !', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression de la charge: {str(e)}", 'danger')
        logging.error(f"Erreur lors de la suppression de la charge: {str(e)}")
    
    return redirect(url_for('charges_list'))


@app.route('/charges/<int:charge_id>/status/<string:status>', methods=['GET', 'POST'])
@login_required
def change_charge_status(charge_id, status):
    """Changer rapidement le statut d'une charge"""
    charge = Expense.query.get_or_404(charge_id)
    
    try:
        if status in ['à_payer', 'payé', 'en_retard']:
            charge.status = status
            
            # Si marqué comme payé, enregistrer la date de paiement
            if status == 'payé' and not charge.payment_date:
                charge.payment_date = date.today()
                
            db.session.commit()
            
            status_display = {
                'à_payer': 'à payer',
                'payé': 'payée',
                'en_retard': 'en retard'
            }
            
            flash(f'La charge a été marquée comme {status_display.get(status, status)} !', 'success')
        else:
            flash('Statut non valide', 'danger')
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du changement de statut: {str(e)}", 'danger')
        logging.error(f"Erreur lors du changement de statut: {str(e)}")
    
    # Rediriger vers la page précédente
    return redirect(request.referrer or url_for('charges_list'))


@app.route('/charges/<int:charge_id>/document/add', methods=['POST'])
@login_required
def add_charge_document(charge_id):
    """Ajouter un document à une charge"""
    charge = Expense.query.get_or_404(charge_id)
    
    # Vérifier si un document est déjà associé
    if charge.document_id:
        flash('Cette charge a déjà un document associé.', 'warning')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    # Vérifier si le fichier est présent
    if 'document' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    file = request.files['document']
    
    # Vérifier si un fichier a été sélectionné
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    # Vérifier le type de fichier
    if file and allowed_file(file.filename):
        try:
            # Sécuriser le nom de fichier
            filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(filename)
            
            # Sauvegarder le fichier
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Créer l'entrée de document en DB
            document = Document(
                filename=filename,
                filepath=unique_filename,
                document_type=charge.charge_type,
                document_category='charges',
                document_date=charge.due_date,
                property_id=charge.property_id,
                company_id=charge.company_id,
                description=f"Document associé à la charge {charge.reference or 'sans référence'}"
            )
            db.session.add(document)
            db.session.flush()  # Pour obtenir l'ID
            
            # Associer le document à la charge
            charge.document_id = document.id
            db.session.commit()
            
            flash('Document ajouté avec succès !', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout du document: {str(e)}", 'danger')
            logging.error(f"Erreur lors de l'ajout du document: {str(e)}")
    else:
        flash('Type de fichier non autorisé', 'danger')
    
    return redirect(url_for('charge_detail', charge_id=charge.id))


@app.route('/charges/<int:charge_id>/document/replace', methods=['POST'])
@login_required
def replace_charge_document(charge_id):
    """Remplacer le document d'une charge"""
    charge = Expense.query.get_or_404(charge_id)
    
    # Vérifier si un document est associé
    if not charge.document_id:
        flash('Cette charge n\'a pas de document à remplacer.', 'warning')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    # Récupérer le document existant
    document = Document.query.get(charge.document_id)
    
    # Vérifier si le fichier est présent
    if 'document' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    file = request.files['document']
    
    # Vérifier si un fichier a été sélectionné
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('charge_detail', charge_id=charge.id))
    
    # Vérifier le type de fichier
    if file and allowed_file(file.filename):
        try:
            # Sécuriser le nom de fichier
            filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(filename)
            
            # Sauvegarder le nouveau fichier
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Supprimer l'ancien fichier
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filepath)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # Mettre à jour l'entrée de document
            document.filename = filename
            document.filepath = unique_filename
            document.uploaded_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Document remplacé avec succès !', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors du remplacement du document: {str(e)}", 'danger')
            logging.error(f"Erreur lors du remplacement du document: {str(e)}")
    else:
        flash('Type de fichier non autorisé', 'danger')
    
    return redirect(url_for('charge_detail', charge_id=charge.id))


def update_expenses_status():
    """Mettre à jour le statut des charges en fonction de la date d'échéance"""
    today = date.today()
    
    try:
        # Mettre à jour les charges en retard
        overdue_charges = Expense.query.filter(
            Expense.status == 'à_payer',
            Expense.due_date < today
        ).all()
        
        for charge in overdue_charges:
            charge.status = 'en_retard'
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la mise à jour des statuts de charges: {str(e)}")