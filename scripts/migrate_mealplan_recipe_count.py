"""
Add count column to meal_plan_recipes. Run once for existing databases.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text, inspect


def migrate():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if "meal_plan_recipes" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("meal_plan_recipes")]
            if "count" not in cols:
                db.session.execute(
                    text("ALTER TABLE meal_plan_recipes ADD COLUMN count INTEGER NOT NULL DEFAULT 1")
                )
                db.session.commit()
                print("Added count column to meal_plan_recipes.")
        print("Migration complete.")


if __name__ == "__main__":
    migrate()
