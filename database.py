import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Initialisation de la base de données
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialiser la base de données avec l'application Flask"""
    # configure the database, relative to the app instance folder
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///property_management.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    # initialize the app with the extension
    db.init_app(app)
    
    logging.info("Base de données initialisée avec l'application Flask")
    
    return db