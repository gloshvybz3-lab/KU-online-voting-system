#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Initializing database..."
python -c "
from app import create_app
from models import db, Admin

app = create_app()
with app.app_context():
    db.create_all()
    admin_count = Admin.query.count()
    if admin_count == 0:
        print('==> Empty database detected. Seeding initial accounts and election demo data...')
        import seed_data
        seed_data.seed_database()
        print('==> Seeding completed successfully.')
    else:
        print(f'==> Database already contains {admin_count} admin account(s). Skipping seed.')
"
echo "==> Build complete!"
