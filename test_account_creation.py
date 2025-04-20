"""Script pour tester la création d'un compte et l'envoi d'un email de confirmation"""
import sys
import os
import logging
from datetime import datetime
from flask import url_for, Flask
from flask_mail import Message, Mail

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Obtenir le répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import des modules nécessaires
try:
    from app import app, db, User
    logging.info("Modules importés avec succès")
except Exception as e:
    logging.error(f"Erreur lors de l'importation des modules: {str(e)}")
    sys.exit(1)

def send_direct_email(user, token):
    """Envoyer un email de confirmation directement sans passer par email_utils"""
    from flask_mail import Message
    import logging
    
    try:
        # Configuration de l'URL
        base_url = os.environ.get('BASE_URL', 'https://app.lynkees.fr')
        confirm_url = f"{base_url}/confirm/{token}"
        logging.info(f"URL de confirmation: {confirm_url}")
        
        # Vérification de la configuration SMTP
        from app import app
        smtp_server = app.config['MAIL_SERVER']
        smtp_port = app.config['MAIL_PORT']
        smtp_username = app.config['MAIL_USERNAME']
        smtp_password = app.config['MAIL_PASSWORD']
        logging.info(f"Configuration SMTP: {smtp_server}:{smtp_port}, utilisateur: {smtp_username}")
        
        if not smtp_password:
            logging.warning("Mot de passe SMTP non configuré ou vide!")
        
        # Création du message
        subject = "LYNKEES - Confirmez votre adresse email"
        recipients = [user.email]
        
        # Corps du message en texte brut
        text_body = f"""
            Bonjour {user.username},

            Bienvenue sur LYNKEES! Pour confirmer votre adresse email, veuillez cliquer sur le lien suivant:

            {confirm_url}

            Si vous n'avez pas créé de compte sur LYNKEES, veuillez ignorer cet email.

            Cordialement,
            L'équipe LYNKEES
        """
        
        # Corps du message en HTML
        html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #6c5ce7; color: white; padding: 10px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ display: inline-block; background-color: #6c5ce7; color: white; padding: 10px 20px; 
                            text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>LYNKEES - Confirmation de votre compte</h2>
                    </div>
                    <div class="content">
                        <p>Bonjour <strong>{user.username}</strong>,</p>
                        <p>Bienvenue sur LYNKEES! Pour activer votre compte, veuillez confirmer votre adresse email en cliquant sur le bouton ci-dessous :</p>
                        <p><a href="{confirm_url}" class="button">Confirmer mon adresse email</a></p>
                        <p>Si le bouton ne fonctionne pas, vous pouvez copier-coller le lien suivant dans votre navigateur :</p>
                        <p>{confirm_url}</p>
                        <p>Si vous n'avez pas créé de compte sur LYNKEES, veuillez ignorer cet email.</p>
                    </div>
                    <div class="footer">
                        <p>Cet email a été envoyé automatiquement depuis la plateforme LYNKEES.</p>
                        <p>© 2025 LYNKEES. Tous droits réservés.</p>
                    </div>
                </div>
            </body>
            </html>
        """
        
        with app.app_context():
            from app import mail
            try:
                msg = Message(
                    subject=subject,
                    recipients=recipients,
                    body=text_body,
                    html=html_body,
                    sender=app.config['MAIL_DEFAULT_SENDER']
                )
                mail.send(msg)
                logging.info(f"Email envoyé avec succès à {user.email}")
                return True
            except Exception as e:
                logging.error(f"Erreur lors de l'envoi du message: {str(e)}")
                return False
            
    except Exception as e:
        logging.error(f"Erreur lors de la préparation de l'email: {str(e)}")
        return False

def create_test_user(email, username, password):
    """Créer un utilisateur de test et envoyer un email de confirmation"""
    with app.app_context():
        try:
            # Vérifier si l'utilisateur existe déjà
            existing_email = User.query.filter_by(email=email).first()
            existing_username = User.query.filter_by(username=username).first()
            
            if existing_email:
                logging.info(f"Un utilisateur avec l'email {email} existe déjà")
                return False, "Email already exists"
            
            if existing_username:
                logging.info(f"Un utilisateur avec le nom d'utilisateur {username} existe déjà")
                return False, "Username already exists"
            
            # Créer le nouvel utilisateur
            user = User(
                email=email,
                username=username,
                first_name="Test",
                last_name="User",
                email_confirmed=False,
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            
            # Ajouter l'utilisateur à la base de données
            db.session.add(user)
            db.session.commit()
            logging.info(f"Utilisateur {username} créé avec succès")
            
            # Générer un token de confirmation
            token = user.generate_confirmation_token()
            logging.info(f"Token de confirmation généré: {token}")
            
            # Envoyer l'email directement
            email_sent = send_direct_email(user, token)
            
            if email_sent:
                logging.info(f"Email de confirmation envoyé à {email}")
                return True, token
            else:
                logging.error("Échec de l'envoi de l'email de confirmation")
                return False, "Échec de l'envoi de l'email"
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
            return False, str(e)

if __name__ == "__main__":
    # Email de test (peut être modifié en argument)
    test_email = "gregory@superhome.fr"
    if len(sys.argv) > 1:
        test_email = sys.argv[1]
    
    # Nom d'utilisateur et mot de passe pour le test
    test_username = "testuser_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    test_password = "TestPassword123!"
    
    logging.info(f"Création d'un utilisateur de test: {test_username} / {test_email}")
    
    success, result = create_test_user(test_email, test_username, test_password)
    
    if success:
        logging.info("✅ Utilisateur créé et email de confirmation envoyé avec succès")
        logging.info(f"Token de confirmation: {result}")
        logging.info(f"Utilisateur: {test_username}")
        logging.info(f"Email: {test_email}")
        logging.info(f"Mot de passe: {test_password}")
    else:
        logging.error(f"❌ Échec de la création de l'utilisateur: {result}")