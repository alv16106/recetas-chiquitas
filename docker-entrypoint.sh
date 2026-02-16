#!/bin/sh
set -e

# Run DB migrations / create tables
python -c "
from run import app
with app.app_context():
    from app.models import db
    import os
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///'):
        db_path = uri.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.create_all()
    try:
        from scripts.seed_units import seed_units
        seed_units()
    except Exception:
        pass
"

exec "$@"
