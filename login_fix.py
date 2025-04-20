import os
import sys
from datetime import datetime
from flask import Flask, session, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
db_session = Session()

# Définition du modèle utilisateur
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

print("Connexion à la base de données...")
try:
    # Tester la connexion - d'abord par email
    user = db_session.query(User).filter_by(email='admin@example.com').first()
    
    if not user:
        # Si pas trouvé par email, essayer par username
        user = db_session.query(User).filter_by(username='admin').first()
    
    if user:
        print(f"Trouvé l'utilisateur admin (ID: {user.id}, email: {user.email}, username: {user.username})")
        
        # Mettre à jour l'email et le username pour être cohérent
        user.email = 'admin@example.com'
        user.username = 'admin'
        
        # Réinitialiser le mot de passe
        new_password = 'admin123'
        user.password_hash = generate_password_hash(new_password)
        db_session.commit()
        
        print(f"Email, username et mot de passe mis à jour - Email: admin@example.com, Username: admin, Password: {new_password}")
    else:
        print("Aucun utilisateur admin trouvé")
        
        # Créer un nouvel utilisateur admin
        new_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db_session.add(new_user)
        db_session.commit()
        
        print(f"Nouvel utilisateur admin créé - Email: admin@example.com, Username: admin, Password: admin123")
    
    print("Base de données testée avec succès!")
    
except Exception as e:
    print(f"Erreur lors de la connexion à la base de données: {str(e)}")
finally:
    db_session.close()