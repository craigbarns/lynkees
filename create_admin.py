import os
import sys
from app import app, db
from models import User

def create_admin_user(username, email, password):
    """Create an admin user or update an existing one"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"User '{username}' already exists. Updating...")
            existing_user.email = email
            existing_user.set_password(password)
            existing_user.is_admin = True
            db.session.commit()
            print(f"Admin user '{username}' updated successfully.")
        else:
            # Create new admin user
            user = User(
                username=username,
                email=email,
                is_admin=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            print(f"Admin user '{username}' created successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    create_admin_user(username, email, password)