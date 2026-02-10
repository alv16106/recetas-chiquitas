"""
Add optional column to recipe_ingredients and create tags/recipe_tags tables.
Run once for existing databases.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text, inspect


def migrate():
    app = create_app()
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)

        # Add optional column to recipe_ingredients if missing
        if "recipe_ingredients" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("recipe_ingredients")]
            if "optional" not in cols:
                db.session.execute(text("ALTER TABLE recipe_ingredients ADD COLUMN optional BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("Added optional column to recipe_ingredients.")

        print("Migration complete.")


if __name__ == "__main__":
    migrate()
