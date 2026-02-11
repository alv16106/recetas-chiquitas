import os

from app import create_app
from app.models import db

app = create_app()
port = int(os.environ.get("PORT", 5000))

@app.shell_context_processor
def make_shell_context():
    return {"db": db}


if __name__ == "__main__":
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if uri.startswith("sqlite:///"):
            db_path = uri.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db.create_all()
        try:
            from scripts.seed_units import seed_units
            seed_units()
        except ImportError:
            pass
    app.run(debug=True, port=port)
