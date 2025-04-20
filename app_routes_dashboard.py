from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from flask_wtf.csrf import validate_csrf
import json
from database import db
from app import login_required
from models import User, Property, Payment, Expense, UserDashboardPreference
import calendar
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, and_, or_, desc

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Afficher le tableau de bord personnalisé de l'utilisateur"""
    user_id = session.get('user_id')
    
    # Récupérer les préférences de l'utilisateur ou utiliser les widgets par défaut
    user_preference = UserDashboardPreference.query.filter_by(user_id=user_id).first()
    
    # Si aucune préférence n'existe, créer une configuration par défaut
    if not user_preference:
        logging.info(f"Création d'une configuration de tableau de bord par défaut pour l'utilisateur {user_id}")
        default_config = get_default_widgets_config()
        user_preference = UserDashboardPreference(
            user_id=user_id,
            widgets_config=json.dumps(default_config)
        )
        db.session.add(user_preference)
        db.session.commit()
        widgets_config = default_config
    elif not user_preference.widgets_config:
        logging.info(f"Configuration vide trouvée pour l'utilisateur {user_id}, initialisation avec la configuration par défaut")
        default_config = get_default_widgets_config()
        user_preference.widgets_config = json.dumps(default_config)
        db.session.commit()
        widgets_config = default_config
    else:
        try:
            widgets_config = json.loads(user_preference.widgets_config)
        except json.JSONDecodeError:
            logging.warning(f"Configuration JSON invalide pour l'utilisateur {user_id}, réinitialisation avec la configuration par défaut")
            widgets_config = get_default_widgets_config()
            user_preference.widgets_config = json.dumps(widgets_config)
            db.session.commit()
    
    # Récupérer les données pour chaque widget actif
    widget_data = {}
    
    for widget in widgets_config:
        if widget.get('active', True):
            widget_type = widget.get('type')
            widget_id = widget.get('id')
            
            if widget_type == 'late_payments':
                widget_data[widget_id] = get_late_payments_data(user_id)
            elif widget_type == 'upcoming_expenses':
                widget_data[widget_id] = get_upcoming_expenses_data(user_id)
            elif widget_type == 'monthly_income':
                widget_data[widget_id] = get_monthly_income_data(user_id)
            elif widget_type == 'yearly_summary':
                widget_data[widget_id] = get_yearly_summary_data(user_id)
            elif widget_type == 'late_expenses':
                widget_data[widget_id] = get_late_expenses_data(user_id)
            elif widget_type == 'property_status':
                widget_data[widget_id] = get_property_status_data(user_id)
    
    # Données pour la liste des widgets disponibles à ajouter
    available_widgets = [
        {'type': 'late_payments', 'name': 'Paiements en retard', 'icon': 'exclamation-triangle'},
        {'type': 'upcoming_expenses', 'name': 'Charges à venir', 'icon': 'calendar-alt'},
        {'type': 'late_expenses', 'name': 'Charges en retard', 'icon': 'exclamation-circle'},
        {'type': 'monthly_income', 'name': 'Revenus mensuels', 'icon': 'chart-line'},
        {'type': 'yearly_summary', 'name': 'Résumé annuel', 'icon': 'chart-pie'},
        {'type': 'property_status', 'name': 'État des biens', 'icon': 'building'}
    ]
    
    return render_template(
        'dashboard/dashboard.html',
        widgets_config=widgets_config,
        widget_data=widget_data,
        available_widgets=available_widgets
    )

@dashboard_bp.route('/dashboard/save_layout', methods=['POST'])
@login_required
def save_dashboard_layout():
    """Enregistrer la configuration des widgets du tableau de bord"""
    user_id = session.get('user_id')
    data = request.json
    widgets_config = data.get('widgets_config')
    csrf_token = data.get('csrf_token')
    
    # CSRF vérification désactivée temporairement pour debug
    # if not csrf_token or not validate_csrf(csrf_token):
    #     return jsonify({'success': False, 'message': 'Token CSRF invalide'}), 403
    
    if not widgets_config:
        return jsonify({'success': False, 'message': 'Configuration invalide'}), 400
    
    # Convertir en JSON pour stockage
    widgets_config_json = json.dumps(widgets_config)
    
    # Mettre à jour ou créer les préférences
    user_preference = UserDashboardPreference.query.filter_by(user_id=user_id).first()
    
    if user_preference:
        user_preference.widgets_config = widgets_config_json
    else:
        logging.info(f"Création d'une nouvelle configuration pour l'utilisateur {user_id} lors de la sauvegarde de la disposition")
        user_preference = UserDashboardPreference(
            user_id=user_id,
            widgets_config=widgets_config_json
        )
        db.session.add(user_preference)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de l'enregistrement des préférences de dashboard: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@dashboard_bp.route('/dashboard/add_widget', methods=['POST'])
@login_required
def add_widget():
    """Ajouter un nouveau widget au tableau de bord"""
    user_id = session.get('user_id')
    widget_type = request.form.get('widget_type')
    
    if not widget_type:
        flash('Type de widget non spécifié', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Récupérer la configuration actuelle
    user_preference = UserDashboardPreference.query.filter_by(user_id=user_id).first()
    
    # Si aucune préférence n'existe, créer une configuration par défaut
    if not user_preference:
        logging.info(f"Création d'une configuration de tableau de bord par défaut pour l'utilisateur {user_id}")
        default_config = get_default_widgets_config()
        user_preference = UserDashboardPreference(
            user_id=user_id,
            widgets_config=json.dumps(default_config)
        )
        db.session.add(user_preference)
        db.session.commit()
        widgets_config = default_config
    elif not user_preference.widgets_config:
        logging.info(f"Configuration vide trouvée pour l'utilisateur {user_id}, initialisation avec la configuration par défaut")
        widgets_config = get_default_widgets_config()
        user_preference.widgets_config = json.dumps(widgets_config)
        db.session.commit()
    else:
        try:
            widgets_config = json.loads(user_preference.widgets_config)
        except json.JSONDecodeError:
            logging.warning(f"Configuration JSON invalide pour l'utilisateur {user_id}, réinitialisation avec la configuration par défaut")
            widgets_config = get_default_widgets_config()
            user_preference.widgets_config = json.dumps(widgets_config)
            db.session.commit()
    
    # Générer un ID unique pour le widget
    import random
    widget_id = f"{widget_type}_{random.randint(1000, 9999)}"
    
    # Ajouter le nouveau widget à la configuration
    widgets_config.append({
        'id': widget_id,
        'type': widget_type,
        'active': True,
        'position': len(widgets_config),
        'size': 'medium'  # Taille par défaut
    })
    
    # Enregistrer la nouvelle configuration
    if user_preference:
        user_preference.widgets_config = json.dumps(widgets_config)
    else:
        user_preference = UserDashboardPreference(
            user_id=user_id,
            widgets_config=json.dumps(widgets_config)
        )
        db.session.add(user_preference)
    
    try:
        db.session.commit()
        flash('Widget ajouté avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de l'ajout du widget: {str(e)}")
        flash('Erreur lors de l\'ajout du widget', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@dashboard_bp.route('/dashboard/remove_widget/<widget_id>', methods=['POST'])
@login_required
def remove_widget(widget_id):
    """Supprimer un widget du tableau de bord"""
    user_id = session.get('user_id')
    
    # Récupérer la configuration actuelle
    user_preference = UserDashboardPreference.query.filter_by(user_id=user_id).first()
    
    # Si aucune préférence n'existe, créer une configuration par défaut
    if not user_preference:
        logging.info(f"Création d'une configuration de tableau de bord par défaut pour l'utilisateur {user_id}")
        default_config = get_default_widgets_config()
        user_preference = UserDashboardPreference(
            user_id=user_id,
            widgets_config=json.dumps(default_config)
        )
        db.session.add(user_preference)
        db.session.commit()
    elif not user_preference.widgets_config:
        logging.info(f"Configuration vide trouvée pour l'utilisateur {user_id}, initialisation avec la configuration par défaut")
        user_preference.widgets_config = json.dumps(get_default_widgets_config())
        db.session.commit()
    
    try:
        widgets_config = json.loads(user_preference.widgets_config)
        
        # Vérifier si le widget à supprimer existe
        widget_exists = any(w.get('id') == widget_id for w in widgets_config)
        if not widget_exists:
            flash(f'Widget avec ID {widget_id} non trouvé dans la configuration', 'warning')
            return redirect(url_for('dashboard.dashboard'))
        
        # Filtrer pour supprimer le widget spécifié
        widgets_config = [w for w in widgets_config if w.get('id') != widget_id]
        
        # Mettre à jour les positions
        for i, widget in enumerate(widgets_config):
            widget['position'] = i
        
        # Enregistrer la nouvelle configuration
        user_preference.widgets_config = json.dumps(widgets_config)
        db.session.commit()
        
        flash('Widget supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la suppression du widget: {str(e)}")
        flash('Erreur lors de la suppression du widget', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@dashboard_bp.route('/dashboard/widget_data/<widget_type>')
@login_required
def get_widget_data(widget_type):
    """API pour récupérer les données d'un widget spécifique"""
    user_id = session.get('user_id')
    
    data = {}
    if widget_type == 'late_payments':
        data = get_late_payments_data(user_id)
    elif widget_type == 'upcoming_expenses':
        data = get_upcoming_expenses_data(user_id)
    elif widget_type == 'monthly_income':
        data = get_monthly_income_data(user_id)
    elif widget_type == 'yearly_summary':
        data = get_yearly_summary_data(user_id)
    elif widget_type == 'late_expenses':
        data = get_late_expenses_data(user_id)
    elif widget_type == 'property_status':
        data = get_property_status_data(user_id)
    
    return jsonify(data)

# Fonctions auxiliaires pour récupérer les données des widgets

def get_default_widgets_config():
    """Retourne la configuration par défaut des widgets"""
    return [
        {
            'id': 'late_payments_default',
            'type': 'late_payments',
            'active': True,
            'position': 0,
            'size': 'medium'
        },
        {
            'id': 'upcoming_expenses_default',
            'type': 'upcoming_expenses',
            'active': True,
            'position': 1,
            'size': 'medium'
        },
        {
            'id': 'late_expenses_default',
            'type': 'late_expenses',
            'active': True,
            'position': 2,
            'size': 'medium'
        },
        {
            'id': 'monthly_income_default',
            'type': 'monthly_income',
            'active': True,
            'position': 3,
            'size': 'large'
        }
    ]

def get_late_payments_data(user_id):
    """Récupère les paiements en retard"""
    # Note: Dans cette application, les biens n'ont pas de lien direct
    # avec les utilisateurs. Pour simplifier, nous montrons tous les paiements en retard.
    # Dans une version future, nous ajouterons une colonne user_id au modèle Property.
    try:
        # Récupérer tous les paiements en retard (status='En retard')
        late_payments = Payment.query.filter(
            Payment.status == 'En retard'
        ).order_by(
            Payment.payment_date  # utiliser payment_date au lieu de due_date
        ).limit(10).all()
        
        # Formater les données pour l'affichage
        payments_data = []
        for payment in late_payments:
            # Récupérer les informations de la propriété
            if payment.property:
                tenant_display = payment.property.tenant if payment.property.tenant else "Sans locataire"
                property_info = f"{payment.property.address} - {tenant_display}"
            else:
                property_info = "Bien inconnu"
            
            # Calculer le retard en jours en utilisant la méthode get_due_date()
            due_date = payment.get_due_date() if hasattr(payment, 'get_due_date') else payment.payment_date
            if due_date:
                days_late = (datetime.now().date() - due_date).days
            else:
                days_late = 0
                
            payments_data.append({
                'id': payment.id,
                'property': property_info,
                'amount': payment.amount,
                'due_date': due_date.strftime('%d/%m/%Y') if due_date else "Date inconnue",
                'days_late': days_late
            })
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des paiements en retard: {str(e)}")
        payments_data = []
    
    return {
        'payments': payments_data,
        'total_count': len(payments_data),
        'total_amount': sum(payment.get('amount', 0) for payment in payments_data)
    }

def get_upcoming_expenses_data(user_id):
    """Récupère les charges à venir dans les 30 prochains jours"""
    today = datetime.now().date()
    thirty_days_later = today + timedelta(days=30)
    
    try:
        # Récupérer les charges à venir
        upcoming_expenses = Expense.query.filter(
            Expense.status == 'à_payer',
            Expense.due_date >= today,
            Expense.due_date <= thirty_days_later
        ).order_by(
            Expense.due_date
        ).limit(10).all()
        
        # Formater les données pour l'affichage
        expenses_data = []
        for expense in upcoming_expenses:
            property_info = f"{expense.property.address}" if expense.property else "Bien inconnu"
            company_info = f"{expense.company.name}" if expense.company else ""
            
            expenses_data.append({
                'id': expense.id,
                'property': property_info,
                'company': company_info,
                'type': expense.get_charge_type_display(),
                'amount': expense.amount,
                'due_date': expense.due_date.strftime('%d/%m/%Y') if expense.due_date else "Date inconnue",
                'days_remaining': (expense.due_date - today).days if expense.due_date else 0
            })
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des charges à venir: {str(e)}")
        expenses_data = []
    
    return {
        'expenses': expenses_data,
        'total_count': len(expenses_data),
        'total_amount': sum(expense.get('amount', 0) for expense in expenses_data)
    }

def get_monthly_income_data(user_id):
    """Récupère les revenus mensuels des 12 derniers mois"""
    today = datetime.now().date()
    
    try:
        # Calculer la date de début (12 mois en arrière)
        start_date = datetime(today.year - 1, today.month, 1).date()
        
        # Préparer les données mensuelles pour les 12 derniers mois
        monthly_data = {}
        for i in range(12):
            # Calculer le mois (à partir de 11 mois en arrière jusqu'au mois actuel)
            month_date = (today.replace(day=1) - timedelta(days=1)) - timedelta(days=30 * i)
            month_key = month_date.strftime('%Y-%m')
            month_name = month_date.strftime('%b %Y')
            
            monthly_data[month_key] = {
                'month': month_name,
                'income': 0,
                'expenses': 0
            }
        
        # Récupérer tous les paiements payés dans cette période
        payments = Payment.query.filter(
            Payment.status == 'Payé',
            Payment.payment_date >= start_date
        ).all()
        
        # Ajouter les revenus par mois
        for payment in payments:
            if payment.payment_date:
                month_key = payment.payment_date.strftime('%Y-%m')
                if month_key in monthly_data:
                    monthly_data[month_key]['income'] += payment.amount
        
        # Récupérer toutes les charges payées dans cette période
        expenses = Expense.query.filter(
            Expense.status == 'Payé',
            Expense.payment_date >= start_date
        ).all()
        
        # Ajouter les dépenses par mois
        for expense in expenses:
            if expense.payment_date:
                month_key = expense.payment_date.strftime('%Y-%m')
                if month_key in monthly_data:
                    monthly_data[month_key]['expenses'] += expense.amount
        
        # Convertir en liste triée par mois
        chart_data = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            chart_data.append({
                'month': data['month'],
                'income': data['income'],
                'expenses': data['expenses'],
                'profit': data['income'] - data['expenses']
            })
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des revenus mensuels: {str(e)}")
        chart_data = []
    
    # Calculer les totaux
    total_income = sum(data.get('income', 0) for data in chart_data)
    total_expenses = sum(data.get('expenses', 0) for data in chart_data)
    
    return {
        'chart_data': chart_data,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_profit': total_income - total_expenses
    }

def get_yearly_summary_data(user_id):
    """Récupère un résumé des revenus et dépenses de l'année en cours"""
    try:
        current_year = datetime.now().year
        start_date = datetime(current_year, 1, 1).date()
        end_date = datetime(current_year, 12, 31).date()
        
        # Récupérer les paiements de l'année en cours
        payments = Payment.query.filter(
            Payment.status == 'Payé',
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).all()
        
        # Récupérer les charges de l'année en cours
        expenses = Expense.query.filter(
            Expense.status == 'Payé',
            Expense.payment_date >= start_date,
            Expense.payment_date <= end_date
        ).all()
        
        # Calculer les totaux
        total_income = sum(payment.amount for payment in payments)
        total_expenses = sum(expense.amount for expense in expenses)
        
        # Regrouper les dépenses par type
        expense_by_type = {}
        for expense in expenses:
            expense_type = expense.get_charge_type_display()
            if expense_type not in expense_by_type:
                expense_by_type[expense_type] = 0
            expense_by_type[expense_type] += expense.amount
        
        # Convertir en format pour graphique en camembert
        expense_pie_data = [
            {'name': expense_type, 'value': amount}
            for expense_type, amount in expense_by_type.items()
        ]
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du résumé annuel: {str(e)}")
        total_income = 0
        total_expenses = 0
        expense_pie_data = []
    
    profit = total_income - total_expenses
    profit_margin = (profit / total_income * 100) if total_income > 0 else 0
    
    # Utiliser l'année courante en toute sécurité
    current_year_safe = datetime.now().year
    
    return {
        'year': current_year_safe,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit': profit,
        'profit_margin': profit_margin,
        'expense_breakdown': expense_pie_data
    }

def get_property_status_data(user_id):
    """Récupère un aperçu de l'état de tous les biens"""
    try:
        # Récupérer tous les biens (comme nous n'avons pas de colonne user_id,
        # nous récupérons tous les biens pour l'instant)
        properties = Property.query.limit(10).all()
        
        property_stats = []
        for prop in properties:
            # Récupérer les paiements en retard pour ce bien
            late_payments = Payment.query.filter_by(
                property_id=prop.id,
                status='En retard'
            ).count()
            
            # Récupérer les charges à payer pour ce bien
            pending_expenses = Expense.query.filter_by(
                property_id=prop.id,
                status='à_payer'
            ).count()
            
            # Calculer l'état d'occupation (utiliser le nom du locataire ou l'état vacant)
            # Dans notre modèle, l'attribut s'appelle 'tenant'
            if prop.tenant:
                tenant_name = prop.tenant
                occupancy_status = "Occupé"
            else:
                tenant_name = "Aucun"
                occupancy_status = "Vacant"
                
            property_stats.append({
                'id': prop.id,
                'address': prop.address,
                'tenant': tenant_name,
                'occupancy': occupancy_status,
                'late_payments': late_payments,
                'pending_expenses': pending_expenses,
                'last_payment_date': get_last_payment_date(prop.id)
            })
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données des propriétés: {str(e)}")
        property_stats = []
    
    return {
        'properties': property_stats,
        'total_count': len(property_stats),
        'occupied_count': sum(1 for p in property_stats if p.get('occupancy') == "Occupé"),
        'vacant_count': sum(1 for p in property_stats if p.get('occupancy') == "Vacant")
    }

def get_late_expenses_data(user_id):
    """Récupère les charges en retard"""
    today = datetime.now().date()
    
    try:
        # Récupérer les charges en retard 
        late_expenses = Expense.query.filter(
            (Expense.status == 'en_retard') | (Expense.status == 'En retard')
        ).order_by(
            Expense.due_date
        ).limit(10).all()
        
        # Formater les données pour l'affichage
        expenses_data = []
        for expense in late_expenses:
            property_info = f"{expense.property.address}" if expense.property else "Bien inconnu"
            company_info = f"{expense.company.name}" if expense.company else ""
            
            # Calculer le retard en jours
            days_late = (today - expense.due_date).days if expense.due_date else 0
            
            expenses_data.append({
                'id': expense.id,
                'property': property_info,
                'company': company_info,
                'type': expense.get_charge_type_display(),
                'amount': expense.amount,
                'due_date': expense.due_date.strftime('%d/%m/%Y') if expense.due_date else "Date inconnue",
                'days_late': days_late
            })
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des charges en retard: {str(e)}")
        expenses_data = []
    
    return {
        'expenses': expenses_data,
        'total_count': len(expenses_data),
        'total_amount': sum(expense.get('amount', 0) for expense in expenses_data)
    }

def get_last_payment_date(property_id):
    """Récupère la date du dernier paiement reçu pour un bien"""
    last_payment = Payment.query.filter_by(
        property_id=property_id,
        status='Payé'
    ).order_by(
        desc(Payment.payment_date)
    ).first()
    
    if last_payment and last_payment.payment_date:
        return last_payment.payment_date.strftime('%d/%m/%Y')
    return "Aucun"