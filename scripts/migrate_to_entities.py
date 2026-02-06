"""
Migrate from string-based ingredients to entity-based (Unit, IngredientMaster, RecipeIngredient).
Run once if you have existing recipe data. Backup your database first.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Unit, IngredientMaster, RecipeIngredient, Recipe, ShoppingListItem
from sqlalchemy import text, inspect


def get_or_create_unit(session, unit_str):
    if not unit_str or not unit_str.strip():
        unit = Unit.query.filter_by(name="unidad").first()
        if not unit:
            unit = Unit(name="unidad", symbol="ud")
            session.add(unit)
            session.flush()
        return unit
    unit = Unit.query.filter(Unit.name.ilike(unit_str.strip())).first()
    if not unit:
        unit = Unit(name=unit_str.strip(), symbol=unit_str.strip()[:10])
        session.add(unit)
        session.flush()
    return unit


def get_or_create_ingredient(session, name):
    if not name or not name.strip():
        return None
    ing = IngredientMaster.query.filter(IngredientMaster.name.ilike(name.strip())).first()
    if not ing:
        ing = IngredientMaster(name=name.strip())
        session.add(ing)
        session.flush()
    return ing


def migrate():
    app = create_app()
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)

        if "ingredients" in inspector.get_table_names():
            print("Migrating from old 'ingredients' table...")
            result = db.session.execute(text(
                "SELECT id, recipe_id, name, quantity, unit FROM ingredients"
            ))
            rows = result.fetchall()
            for row in rows:
                rid, recipe_id, name, quantity, unit_str = row
                ing = get_or_create_ingredient(db.session, name)
                if ing:
                    u = get_or_create_unit(db.session, unit_str)
                    ri = RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_master_id=ing.id,
                        unit_id=u.id if u else None,
                        quantity=quantity or "",
                    )
                    db.session.add(ri)
            db.session.execute(text("DROP TABLE ingredients"))
            db.session.commit()
            print(f"Migrated {len(rows)} recipe ingredients.")
        else:
            print("No old 'ingredients' table found. Skipping recipe migration.")

        if "shopping_list_items" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("shopping_list_items")]
            if "ingredient_master_id" not in cols:
                db.session.execute(text(
                    "ALTER TABLE shopping_list_items ADD COLUMN ingredient_master_id INTEGER REFERENCES ingredient_masters(id)"
                ))
                db.session.execute(text(
                    "ALTER TABLE shopping_list_items ADD COLUMN unit_id INTEGER REFERENCES units(id)"
                ))
                db.session.commit()

            result = db.session.execute(text(
                "SELECT id, ingredient_name, quantity, unit FROM shopping_list_items WHERE ingredient_master_id IS NULL"
            ))
            rows = result.fetchall()
            for row in rows:
                item_id, name, quantity, unit_str = row
                if name:
                    ing = get_or_create_ingredient(db.session, name)
                    u = get_or_create_unit(db.session, unit_str)
                    db.session.execute(
                        text("UPDATE shopping_list_items SET ingredient_master_id = :iid, unit_id = :uid WHERE id = :id"),
                        {"iid": ing.id if ing else None, "uid": u.id if u else None, "id": item_id}
                    )
            db.session.commit()
            print(f"Updated {len(rows)} shopping list items with entity references.")

        print("Migration complete.")


if __name__ == "__main__":
    migrate()
