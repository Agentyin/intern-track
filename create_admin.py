from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check if admin already exists
    if not User.query.filter_by(email='admin@examples.com').first():
        admin = User(
            first_name='Admin',
            last_name='User',
            email='admin@examples.com',
            password=generate_password_hash('securepassword123'),
            role='admin',
            status='active'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists")
