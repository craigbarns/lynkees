from flask import render_template, redirect, url_for, flash, request, session
from app import app, db
from models import Payment, Property, Document
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, date
import calendar
import uuid
from app import login_required, allowed_file, generate_unique_filename
import logging
logging.basicConfig(level=logging.DEBUG)


@app.route('/tenant-payments')
@login_required
def tenant_payments_list():
    """Redirection vers la vue autonome des paiements des locataires"""
    return redirect(url_for('tenant_payments_standalone'))


@app.route('/tenant-payments/standalone')
@login_required
def tenant_payments_standalone():
    """Afficher la liste des paiements des locataires avec filtrage - Vue autonome"""
    # Récupérer les paramètres de filtrage
    property_id = request.args.get('property_id', '')
    status = request.args.get('status', '')
    period = request.args.get('period', '')
    payment_type = request.args.get('payment_type', '')
    
    # Base de la requête
    query = Payment.query
    
    # Appliquer les filtres
    if property_id:
        query = query.filter(Payment.property_id == property_id)
    
    if status:
        query = query.filter(Payment.status == status)
    
    if payment_type:
        query = query.filter(Payment.payment_type == payment_type)
    
    if period:
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        if period == 'current_month':
            # Premier jour du mois courant
            start_date = date(current_year, current_month, 1)
            # Dernier jour du mois courant
            if current_month == 12:
                end_date = date(current_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(current_year, current_month + 1, 1) - timedelta(days=1)
        
        elif period == 'last_month':
            # Premier jour du mois précédent
            previous_month = current_month - 1 if current_month > 1 else 12
            previous_year = current_year if current_month > 1 else current_year - 1
            start_date = date(previous_year, previous_month, 1)
            
            # Dernier jour du mois précédent
            if previous_month == 12:
                end_date = date(previous_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(previous_year, previous_month + 1, 1) - timedelta(days=1)
        
        elif period == 'last_3_months':
            # Il y a 3 mois
            three_months_ago = today.replace(day=1)
            for _ in range(3):
                month = three_months_ago.month - 1 if three_months_ago.month > 1 else 12
                year = three_months_ago.year if three_months_ago.month > 1 else three_months_ago.year - 1
                three_months_ago = three_months_ago.replace(year=year, month=month)
            
            start_date = three_months_ago
            end_date = today
        
        elif period == 'current_year':
            # Premier jour de l'année courante
            start_date = date(current_year, 1, 1)
            # Dernier jour de l'année courante
            end_date = date(current_year, 12, 31)
        
        else:
            start_date = None
            end_date = None
        
        if start_date and end_date:
            query = query.filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
    
    # Vérifier et mettre à jour les paiements en retard
    check_late_payments()
    
    # Récupérer les paiements filtrés
    payments = query.order_by(Payment.payment_date.desc()).all()
    
    # Calculer les statistiques
    total_amount = sum(payment.amount for payment in payments)
    paid_payments = [payment for payment in payments if payment.status == 'Payé']
    paid_amount = sum(payment.amount for payment in paid_payments)
    paid_count = len(paid_payments)
    
    pending_payments = [payment for payment in payments if payment.status == 'En attente']
    pending_amount = sum(payment.amount for payment in pending_payments)
    pending_count = len(pending_payments)
    
    late_payments = [payment for payment in payments if payment.status == 'En retard']
    late_amount = sum(payment.amount for payment in late_payments)
    late_count = len(late_payments)
    
    # Calculer le taux de recouvrement
    collection_rate = 0
    if total_amount > 0:
        collection_rate = round((paid_amount / total_amount) * 100)
    
    # Pour le modal de génération des paiements
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Récupérer toutes les propriétés pour le filtre
    properties = Property.query.all()
    
    return render_template(
        'tenant_payments/standalone_list.html',
        payments=payments,
        properties=properties,
        total_amount=total_amount,
        paid_amount=paid_amount,
        paid_count=paid_count,
        pending_amount=pending_amount,
        pending_count=pending_count,
        late_amount=late_amount,
        late_count=late_count,
        collection_rate=collection_rate,
        current_month=current_month,
        current_year=current_year
    )


@app.route('/tenant-payments/add', methods=['GET', 'POST'])
@login_required
def add_tenant_payment():
    """Ajouter un nouveau paiement de locataire"""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            property_id = request.form.get('property_id')
            amount = request.form.get('amount')
            payment_date_str = request.form.get('payment_date')
            payment_type = request.form.get('payment_type')
            payment_method = request.form.get('payment_method', '')
            status = request.form.get('status', 'En attente')
            date_paid_str = request.form.get('date_paid')
            description = request.form.get('description')
            period = request.form.get('period', '')
            is_recurring = 'is_recurring' in request.form
            recurring_frequency = request.form.get('recurring_frequency', '')
            
            # Vérifier les données requises
            if not property_id or not amount or not payment_date_str or not payment_type:
                flash('Veuillez remplir tous les champs obligatoires.', 'danger')
                return redirect(url_for('add_tenant_payment'))
            
            # Convertir les dates
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None
                date_paid = datetime.strptime(date_paid_str, '%Y-%m-%d').date() if date_paid_str else None
            except ValueError:
                # Essayer avec le format français au cas où
                try:
                    payment_date = datetime.strptime(payment_date_str, '%d/%m/%Y').date() if payment_date_str else None
                    date_paid = datetime.strptime(date_paid_str, '%d/%m/%Y').date() if date_paid_str else None
                except:
                    flash('Format de date invalide. Utilisez le format YYYY-MM-DD.', 'danger')
                    return redirect(url_for('add_tenant_payment'))
            
            # Si le statut est Payé mais qu'il n'y a pas de date de paiement, mettre la date actuelle
            if status == 'Payé' and not date_paid:
                date_paid = date.today()
            
            # Créer le paiement
            payment = Payment(
                property_id=property_id,
                amount=float(amount),
                payment_date=payment_date,
                payment_type=payment_type,
                payment_method=payment_method,
                status=status,
                date_paid=date_paid,
                description=description,
                period=period,
                is_recurring=is_recurring,
                recurring_frequency=recurring_frequency if is_recurring else None
            )
            
            db.session.add(payment)
            db.session.commit()
            
            flash('Paiement ajouté avec succès !', 'success')
            return redirect(url_for('tenant_payments_standalone'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout du paiement: {str(e)}", 'danger')
            logging.error(f"Erreur lors de l'ajout du paiement: {str(e)}")
    
    # Récupérer les propriétés ayant des locataires
    properties = Property.query.filter(Property.tenant != '').all()
    
    return render_template(
        'tenant_payments/add.html',
        properties=properties
    )


@app.route('/tenant-payments/generate', methods=['POST'])
@login_required
def generate_tenant_payments():
    """Générer les paiements mensuels pour tous les locataires"""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            month = int(request.form.get('month'))
            year = int(request.form.get('year'))
            day = int(request.form.get('day', 5))  # Jour d'échéance, par défaut le 5
            include_rent = 'include_rent' in request.form
            include_charges = 'include_charges' in request.form
            
            # Valider les dates
            if not (1 <= month <= 12) or not (2000 <= year <= 2100) or not (1 <= day <= 31):
                flash('Veuillez fournir des dates valides.', 'danger')
                return redirect(url_for('tenant_payments_standalone'))
            
            # Calculer la date d'échéance
            # S'assurer que le jour est valide pour le mois donné
            try:
                due_date = date(year, month, day)
            except ValueError:
                # Si le jour est invalide (ex: 31 février), utiliser le dernier jour du mois
                last_day = calendar.monthrange(year, month)[1]
                due_date = date(year, month, last_day)
            
            # Récupérer toutes les propriétés ayant un locataire
            properties = Property.query.filter(Property.tenant != '').all()
            
            if not properties:
                flash('Aucune propriété avec locataire trouvée.', 'warning')
                return redirect(url_for('tenant_payments_standalone'))
            
            # Pour compter combien de paiements ont été créés
            created_count = 0
            
            # Créer un identifiant de groupe pour les paiements générés
            group_id = f"gen_{year}_{month}_{uuid.uuid4().hex[:8]}"
            
            for prop in properties:
                # Vérifier si un paiement de loyer existe déjà pour ce mois/année/propriété
                existing_rent = Payment.query.filter(
                    Payment.property_id == prop.id,
                    Payment.payment_type == 'Loyer',
                    Payment.payment_date.between(
                        date(year, month, 1),
                        date(year, month, calendar.monthrange(year, month)[1])
                    )
                ).first()
                
                # Vérifier si un paiement de charges existe déjà pour ce mois/année/propriété
                existing_charges = Payment.query.filter(
                    Payment.property_id == prop.id,
                    Payment.payment_type == 'Charges',
                    Payment.payment_date.between(
                        date(year, month, 1),
                        date(year, month, calendar.monthrange(year, month)[1])
                    )
                ).first()
                
                # Déterminer le montant total et créer un paiement combiné
                total_amount = 0
                payment_types = []
                
                if include_rent and prop.rent > 0:
                    total_amount += prop.rent
                    payment_types.append('Loyer')
                
                if include_charges and prop.charges > 0:
                    total_amount += prop.charges
                    payment_types.append('Charges')
                
                # Vérifier s'il existe déjà un paiement combiné pour ce mois
                existing_combined = Payment.query.filter(
                    Payment.property_id == prop.id,
                    Payment.payment_type.in_(['Loyer+Charges', 'Loyer', 'Charges']),
                    Payment.payment_date.between(
                        date(year, month, 1),
                        date(year, month, calendar.monthrange(year, month)[1])
                    )
                ).first()
                
                # Créer le paiement combiné s'il n'existe pas déjà et si au moins un type est demandé
                if not existing_combined and total_amount > 0:
                    # Déterminer le type de paiement
                    if 'Loyer' in payment_types and 'Charges' in payment_types:
                        payment_type = 'Loyer+Charges'
                        description = f"Loyer et charges de {calendar.month_name[month]} {year} pour {prop.tenant}"
                    elif 'Loyer' in payment_types:
                        payment_type = 'Loyer'
                        description = f"Loyer de {calendar.month_name[month]} {year} pour {prop.tenant}"
                    else:
                        payment_type = 'Charges'
                        description = f"Charges de {calendar.month_name[month]} {year} pour {prop.tenant}"
                    
                    # Créer le paiement
                    combined_payment = Payment(
                        property_id=prop.id,
                        amount=total_amount,
                        payment_date=due_date,
                        payment_type=payment_type,
                        payment_method='',
                        status='En attente',
                        description=description,
                        recurring_group_id=group_id,
                        is_recurring=True
                    )
                    db.session.add(combined_payment)
                    created_count += 1
            
            db.session.commit()
            
            if created_count > 0:
                flash(f'{created_count} paiements générés avec succès pour {calendar.month_name[month]} {year} !', 'success')
            else:
                flash('Aucun nouveau paiement généré. Les paiements existent peut-être déjà pour ce mois.', 'info')
            
            return redirect(url_for('tenant_payments_standalone'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la génération des paiements: {str(e)}", 'danger')
            logging.error(f"Erreur lors de la génération des paiements: {str(e)}")
            return redirect(url_for('tenant_payments_standalone'))
    
    return redirect(url_for('tenant_payments_standalone'))


@app.route('/tenant-payments/<int:payment_id>')
@login_required
def tenant_payment_detail(payment_id):
    """Afficher les détails d'un paiement"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Préparer un dictionnaire avec les données formatées
    formatted_payment = {
        'id': payment.id,
        'property_id': payment.property_id,
        'property': payment.property,
        'amount': payment.amount,
        'amount_string': str(payment.amount).replace('.', ','),
        'payment_date': payment.payment_date,
        'payment_type': payment.payment_type,
        'payment_method': payment.payment_method,
        'status': payment.status,
        'date_paid': payment.date_paid if hasattr(payment, 'date_paid') else None,
        'description': payment.description if hasattr(payment, 'description') else None,
        'period': payment.period if hasattr(payment, 'period') else None,
        'is_recurring': payment.is_recurring if hasattr(payment, 'is_recurring') else False,
        'recurring_frequency': payment.recurring_frequency if hasattr(payment, 'recurring_frequency') else None,
        'created_at': payment.created_at if hasattr(payment, 'created_at') else None,
        'last_modified': payment.last_modified if hasattr(payment, 'last_modified') else None,
    }
    
    # Récupérer les paiements liés au même locataire
    related_payments = Payment.query.filter(
        Payment.property_id == payment.property_id,
        Payment.id != payment.id
    ).order_by(Payment.payment_date.desc()).limit(5).all()
    
    # Formater les montants des paiements liés
    formatted_related = []
    for rel in related_payments:
        rel_dict = {
            'id': rel.id,
            'property_id': rel.property_id,
            'property': rel.property,
            'amount': rel.amount,
            'amount_string': str(rel.amount).replace('.', ','),
            'payment_date': rel.payment_date,
            'payment_type': rel.payment_type,
            'status': rel.status,
            'period': rel.period if hasattr(rel, 'period') else None,
        }
        formatted_related.append(rel_dict)
    
    return render_template(
        'tenant_payments/detail.html',
        payment=formatted_payment,
        related_payments=formatted_related
    )


@app.route('/tenant-payments/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tenant_payment(payment_id):
    """Modifier un paiement existant"""
    payment = Payment.query.get_or_404(payment_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            property_id = request.form.get('property_id')
            amount = request.form.get('amount')
            payment_date_str = request.form.get('payment_date')
            payment_type = request.form.get('payment_type')
            payment_method = request.form.get('payment_method', '')
            status = request.form.get('status')
            date_paid_str = request.form.get('date_paid')
            description = request.form.get('description')
            period = request.form.get('period', '')
            is_recurring = 'is_recurring' in request.form
            recurring_frequency = request.form.get('recurring_frequency', '')
            
            # Vérifier les données requises
            if not property_id or not amount or not payment_date_str or not payment_type or not status:
                flash('Veuillez remplir tous les champs obligatoires.', 'danger')
                return redirect(url_for('edit_tenant_payment', payment_id=payment.id))
            
            # Convertir les dates (format YYYY-MM-DD du formulaire HTML)
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None
                date_paid = datetime.strptime(date_paid_str, '%Y-%m-%d').date() if date_paid_str else None
            except ValueError:
                flash('Format de date invalide. Utilisez le format YYYY-MM-DD.', 'danger')
                return redirect(url_for('edit_tenant_payment', payment_id=payment.id))
            
            # Mettre à jour le paiement
            payment.property_id = property_id
            payment.amount = float(amount)
            payment.payment_date = payment_date
            payment.payment_type = payment_type
            payment.payment_method = payment_method
            payment.status = status
            payment.date_paid = date_paid
            payment.description = description
            payment.period = period
            payment.is_recurring = is_recurring
            payment.recurring_frequency = recurring_frequency if is_recurring else None
            
            db.session.commit()
            
            flash('Paiement mis à jour avec succès !', 'success')
            return redirect(url_for('tenant_payment_detail', payment_id=payment.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la modification du paiement: {str(e)}", 'danger')
            logging.error(f"Erreur lors de la modification du paiement: {str(e)}")
    
    # Récupérer les propriétés pour le formulaire
    properties = Property.query.all()
    
    return render_template(
        'tenant_payments/edit.html',
        payment=payment,
        properties=properties
    )


@app.route('/tenant-payments/<int:payment_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_tenant_payment(payment_id):
    """Supprimer un paiement"""
    # Phase 1 : Récupérer le paiement
    try:
        payment = Payment.query.get_or_404(payment_id)
    except Exception as e:
        logging.error(f"Erreur de récupération du paiement {payment_id}: {str(e)}")
        flash("Impossible de trouver le paiement demandé.", "danger")
        return redirect(url_for('tenant_payments_standalone'))
    
    # Phase 2 : Méthode POST - Exécution de la suppression
    if request.method == 'POST':
        try:
            # Simple suppression directe
            db.session.delete(payment)
            db.session.commit()
            
            flash('Paiement supprimé avec succès!', 'success')
            return redirect(url_for('tenant_payments_standalone'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la suppression du paiement {payment_id}: {str(e)}")
            flash("Une erreur est survenue lors de la suppression. Veuillez réessayer.", "danger")
            return redirect(url_for('tenant_payments_standalone'))
    
    # Phase 3 : Méthode GET - Affichage de la confirmation
    return render_template('tenant_payments/delete.html', payment=payment)


@app.route('/tenant-payments/<int:payment_id>/status/<status>', methods=['GET', 'POST'])
@login_required
def change_tenant_payment_status(payment_id, status):
    if request.method == 'GET':
        return redirect(url_for('tenant_payments_list'))
    """Changer rapidement le statut d'un paiement"""
    payment = Payment.query.get_or_404(payment_id)
    
    try:
        if status in ['En attente', 'Payé', 'En retard']:
            payment.status = status
            
            # Si marqué comme payé, enregistrer la date de paiement
            if status == 'Payé' and not payment.date_paid:
                payment.date_paid = date.today()
            
            db.session.commit()
            flash(f'Le statut du paiement a été changé en "{status}" !', 'success')
        else:
            flash('Statut non valide', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du changement de statut: {str(e)}", 'danger')
        logging.error(f"Erreur lors du changement de statut: {str(e)}")
    
    # Rediriger vers la page précédente
    return redirect(request.referrer or url_for('tenant_payments_list'))


def check_late_payments():
    """Vérifier si des paiements sont en retard et mettre à jour leur statut"""
    today = date.today()
    
    try:
        # Récupérer les paiements en attente dont la date est passée
        late_payments = Payment.query.filter(
            Payment.status == 'En attente',
            Payment.payment_date < today
        ).all()
        
        # Mettre à jour leur statut
        for payment in late_payments:
            payment.status = 'En retard'
        
        # Sauvegarder les modifications
        if late_payments:
            db.session.commit()
            logging.info(f"{len(late_payments)} paiements mis à jour en 'En retard'")
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la vérification des paiements en retard: {str(e)}")