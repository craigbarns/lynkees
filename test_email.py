"""Script pour tester l'envoi d'emails"""
import logging
import sys
from app import app, mail
from flask_mail import Message

logging.basicConfig(level=logging.DEBUG)

def test_direct_email_send():
    """Essaie d'envoyer un email directement sans passer par les utilitaires"""
    with app.app_context():
        try:
            # Créer un message simple
            msg = Message(
                "Test LYNKEES - Email de diagnostic",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=["gregory@wemadeinchina.com"]
            )
            msg.body = "Ceci est un email de test envoyé par LYNKEES pour diagnostiquer les problèmes d'envoi."
            msg.html = "<h1>Test d'Email LYNKEES</h1><p>Ceci est un email de test envoyé par LYNKEES.</p>"
            
            # Afficher la configuration email
            logging.info(f"Configuration email:")
            logging.info(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
            logging.info(f"MAIL_PORT: {app.config['MAIL_PORT']}")
            logging.info(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
            logging.info(f"MAIL_USE_SSL: {app.config['MAIL_USE_SSL']}")
            logging.info(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
            logging.info(f"MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")
            
            # Vérifier que mail.send existe et est une méthode
            if not hasattr(mail, 'send'):
                logging.error("L'objet mail n'a pas d'attribut 'send'")
                return False
                
            # Essayer d'envoyer l'email
            logging.info(f"Envoi de l'email à {msg.recipients}")
            mail.send(msg)
            logging.info("Email envoyé avec succès")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
            logging.error(f"Type d'exception: {type(e)}")
            import traceback
            traceback.print_exc(file=sys.stdout)
            return False

if __name__ == "__main__":
    success = test_direct_email_send()
    if success:
        print("Test d'envoi d'email réussi!")
    else:
        print("Échec du test d'envoi d'email.")