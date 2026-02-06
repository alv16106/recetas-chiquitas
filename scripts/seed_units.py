"""Seed default units of measurement. Run once or when adding new defaults."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Unit

DEFAULT_UNITS = [
    ("unidad", "ud"),
    ("cucharada", "cda"),
    ("cucharadita", "cdta"),
    ("taza", "taza"),
    ("tazas", "tazas"),
    ("gramos", "g"),
    ("kilogramos", "kg"),
    ("mililitros", "ml"),
    ("litros", "L"),
    ("libra", "lb"),
    ("onza", "oz"),
    ("pizca", "pizca"),
    ("hojas", "hojas"),
    ("diente", "diente"),
    ("rodaja", "rodaja"),
    ("rebanada", "rebanada"),
    ("tallo", "tallo"),
    ("manojo", "manojo"),
    ("sobre", "sobre"),
]


def seed_units():
    app = create_app()
    with app.app_context():
        for name, symbol in DEFAULT_UNITS:
            if Unit.query.filter_by(name=name).first() is None:
                db.session.add(Unit(name=name, symbol=symbol))
        db.session.commit()
        print(f"Seeded units. Total: {Unit.query.count()}")


if __name__ == "__main__":
    seed_units()
