from app import app, db, Building, Property
from datetime import datetime

with app.app_context():
    # Création d'un bien
    new_property = Property(
        address='123 Test Street',
        rent=1000,
        charges=200,
        tenant='Test Tenant',
        tenant_email='test@example.com',
        tenant_phone='1234567890',
        created_at=datetime.utcnow()
    )
    db.session.add(new_property)
    db.session.commit()
    
    # Création d'un immeuble
    new_building = Building(
        name='Test Building',
        address='456 Building Street',
        description='Test Description',
        created_at=datetime.utcnow()
    )
    db.session.add(new_building)
    db.session.commit()
    
    print('Property ID:', new_property.id, 'Building ID:', new_building.id)