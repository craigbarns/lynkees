from main import app
from models import Document

with app.app_context():
    docs = Document.query.all()
    print('Documents disponibles:')
    for doc in docs:
        print(f'ID: {doc.id}, Filename: {doc.filename}, File path: {doc.filepath}')