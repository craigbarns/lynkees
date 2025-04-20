"""Script pour tester l'envoi d'email avec le nouveau domaine"""
import os
import sys
from flask import Flask
from flask_mail import Mail

# Créer une mini-application Flask pour le test
app = Flask(__name__)

# Configuration email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.ionos.fr')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'noreply@lynkees.fr')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # Utilise le mot de passe des variables d'environnement
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@lynkees.fr')
app.config['BASE_URL'] = 'https://app.lynkees.fr'  # Nouveau domaine

# Initialiser l'extension Mail
mail = Mail(app)

def send_test_email(recipient_email):
    """Envoyer un email de test simple"""
    from flask_mail import Message
    
    subject = "LYNKEES - Test de configuration du domaine app.lynkees.fr"
    
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
                <h2>LYNKEES - Test de configuration du domaine</h2>
            </div>
            <div class="content">
                <p>Bonjour,</p>
                <p>Ceci est un email de test pour vérifier la configuration du nouveau domaine <strong>app.lynkees.fr</strong>.</p>
                <p>Si vous recevez cet email, cela signifie que :</p>
                <ul>
                    <li>La configuration du domaine fonctionne correctement</li>
                    <li>Le serveur SMTP est correctement configuré</li>
                    <li>Les emails sont envoyés depuis le bon domaine</li>
                </ul>
                <p>Vous pouvez maintenant accéder à votre application à l'adresse :</p>
                <p><a href="{app.config['BASE_URL']}" class="button">Accéder à LYNKEES</a></p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement depuis la plateforme LYNKEES.</p>
                <p>© 2025 LYNKEES. Tous droits réservés.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    LYNKEES - Test de configuration du domaine app.lynkees.fr
    
    Bonjour,
    
    Ceci est un email de test pour vérifier la configuration du nouveau domaine app.lynkees.fr.
    
    Si vous recevez cet email, cela signifie que :
    - La configuration du domaine fonctionne correctement
    - Le serveur SMTP est correctement configuré
    - Les emails sont envoyés depuis le bon domaine
    
    Vous pouvez maintenant accéder à votre application à l'adresse : {app.config['BASE_URL']}
    
    -------
    Cet email a été envoyé automatiquement depuis la plateforme LYNKEES.
    © 2025 LYNKEES. Tous droits réservés.
    """
    
    with app.app_context():
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                body=text_body,
                html=html_body
            )
            mail.send(msg)
            print(f"✅ Email envoyé avec succès à {recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de l'email: {str(e)}")
            return False

if __name__ == "__main__":
    # Vérifier si un destinataire a été fourni en argument
    recipient = "gregory@superhome.fr"
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    
    print(f"Envoi d'un email de test à {recipient}...")
    success = send_test_email(recipient)
    
    if success:
        print("L'email a été envoyé avec succès!")
    else:
        print("Échec de l'envoi de l'email. Vérifiez les logs pour plus de détails.")