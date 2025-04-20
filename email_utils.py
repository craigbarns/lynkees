"""Utilities for sending emails"""
import os
import logging
from flask import render_template, current_app
from flask_mail import Message
from threading import Thread

def send_async_email(app, msg):
    """Envoyer un email de manière asynchrone"""
    with app.app_context():
        try:
            from app import mail
            mail.send(msg)
            recipients_str = ", ".join(msg.recipients) if isinstance(msg.recipients, list) else str(msg.recipients)
            logging.info(f"Email envoyé à {recipients_str}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.error(f"Erreur lors de l'envoi de l'email: {str(e)}")

def send_email(subject, recipients, text_body, html_body, sender=None, attachments=None):
    """Envoyer un email avec pièces jointes optionnelles
    
    Args:
        subject: Sujet de l'email
        recipients: Liste des destinataires
        text_body: Corps du message en texte brut
        html_body: Corps du message en HTML
        sender: Expéditeur (utilise la valeur par défaut si non spécifié)
        attachments: Liste de tuples (id, data, mimetype) pour les pièces jointes
    """
    from app import app, mail
    import logging

    if not sender:
        sender = app.config['MAIL_DEFAULT_SENDER']
    
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    # Ajouter les pièces jointes si présentes
    attachment_names = []
    if attachments:
        for attachment in attachments:
            attachment_id, content, mimetype = attachment
            attachment_names.append(attachment_id)
            if mimetype.startswith('image/'):
                # Images inline (pour le HTML)
                msg.attach(
                    attachment_id,  # ID utilisé dans le HTML avec cid:ID
                    mimetype,
                    content,
                    'inline',
                    headers={'Content-ID': f'<{attachment_id}>'}
                )
            else:
                # Pièces jointes standard
                msg.attach(
                    attachment_id,
                    mimetype,
                    content,
                    'attachment'
                )
    
    # Vérifier si les identifiants email sont configurés
    if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
        try:
            # Envoi direct sans thread pour faciliter le débogage
            mail.send(msg)
            logging.info(f"Email envoyé avec succès à {', '.join(recipients)}")
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            # En cas d'erreur, afficher les détails de l'email pour debug
            logging.info(f"=== DÉTAILS DE L'EMAIL QUI A ÉCHOUÉ ===")
            logging.info(f"De: {sender}")
            recipients_str = ", ".join(recipients) if isinstance(recipients, list) else str(recipients)
            logging.info(f"À: {recipients_str}")
            logging.info(f"Sujet: {subject}")
            logging.info(f"=== FIN DÉTAILS ===")
            return False
    else:
        # Mode développement - Afficher l'email dans les logs au lieu de l'envoyer
        logging.info(f"=== EMAIL SIMULÉ ===")
        logging.info(f"De: {sender}")
        recipients_str = ", ".join(recipients) if isinstance(recipients, list) else str(recipients)
        logging.info(f"À: {recipients_str}")
        logging.info(f"Sujet: {subject}")
        logging.info(f"Pièces jointes: {', '.join(attachment_names) if attachment_names else 'Aucune'}")
        logging.info(f"Contenu (texte): {text_body}")
        logging.info(f"Contenu (HTML): [HTML supprimé des logs pour lisibilité]")
        logging.info(f"=== FIN EMAIL ===")
        logging.info(f"Note: Cet email n'a pas été envoyé car MAIL_USERNAME et MAIL_PASSWORD ne sont pas configurés.")
        
        # Simule un envoi réussi pour le développement
        return True

def send_confirmation_email(user):
    """Envoyer un email de confirmation à un nouvel utilisateur"""
    from app import app
    from flask import render_template
    import os
    
    # Génération du token de confirmation
    token = user.generate_confirmation_token()
    
    # Mise à jour de l'URL de base avec le domaine personnalisé app.lynkees.fr
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://app.lynkees.fr')
    
    # Construction de l'URL de confirmation
    confirm_url = f"{app.config['BASE_URL']}/confirm/{token}"
    print(f"URL de confirmation générée : {confirm_url}")
    
    # Préparer les modèles de mail avec les données
    text_body = render_template(
        'emails/confirm_email.txt',
        user=user,
        confirm_url=confirm_url
    )
    
    html_body = render_template(
        'emails/confirm_email.html',
        user=user,
        confirm_url=confirm_url
    )
    
    # Pièces jointes - logo de LYNKEES
    logo_path = os.path.join(app.root_path, 'static', 'images', 'lynkees-logomark.png')
    attachments = []
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            attachments.append(('logo', f.read(), 'image/png'))
    
    send_email(
        subject="LYNKEES - Confirmez votre adresse email",
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body,
        attachments=attachments
    )
    
    return token