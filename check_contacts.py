from app import app, db
from models import Contact

with app.app_context():
    contacts = db.session.query(Contact).all()
    print(f'Nombre de contacts en base de données : {len(contacts)}')
    print('Contacts avec leurs ID :')
    for contact in contacts:
        print(f'- ID: {contact.id}, Nom: {contact.first_name} {contact.last_name}, Catégorie: {contact.category}')
