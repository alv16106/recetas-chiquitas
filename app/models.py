from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    recipes = db.relationship("Recipe", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    shopping_lists = db.relationship(
        "ShoppingList", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Unit(db.Model):
    """Global units of measurement. Extensible for future conversion support."""
    __tablename__ = "units"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    symbol = db.Column(db.String(20))
    # For future unit conversion: base_unit_id, conversion_factor to convert to base
    base_unit_id = db.Column(db.Integer, db.ForeignKey("units.id"))
    conversion_factor = db.Column(db.Float, default=1.0)

    def __repr__(self):
        return self.symbol or self.name


class IngredientMaster(db.Model):
    """Global searchable ingredients. Shared across recipes for shopping list merge."""
    __tablename__ = "ingredient_masters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)


class Recipe(db.Model):
    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ingredients = db.relationship(
        "RecipeIngredient", backref="recipe", lazy="dynamic", cascade="all, delete-orphan"
    )
    images = db.relationship("RecipeImage", backref="recipe", lazy="dynamic", cascade="all, delete-orphan")


class RecipeIngredient(db.Model):
    """Links a recipe to a global ingredient with quantity and unit."""
    __tablename__ = "recipe_ingredients"
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    ingredient_master_id = db.Column(db.Integer, db.ForeignKey("ingredient_masters.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"))
    quantity = db.Column(db.String(50))

    ingredient = db.relationship("IngredientMaster", backref="recipe_ingredients")
    unit = db.relationship("Unit", backref="recipe_ingredients")


class RecipeImage(db.Model):
    __tablename__ = "recipe_images"
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class ShoppingList(db.Model):
    __tablename__ = "shopping_lists"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "ShoppingListItem", backref="shopping_list", lazy="dynamic", cascade="all, delete-orphan"
    )


class ShoppingListItem(db.Model):
    __tablename__ = "shopping_list_items"
    id = db.Column(db.Integer, primary_key=True)
    shopping_list_id = db.Column(db.Integer, db.ForeignKey("shopping_lists.id"), nullable=False)
    ingredient_master_id = db.Column(db.Integer, db.ForeignKey("ingredient_masters.id"))
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"))
    ingredient_name = db.Column(db.String(200))  # Fallback for legacy/display
    quantity = db.Column(db.String(50))
    unit = db.Column(db.String(50))  # Fallback for legacy
    checked = db.Column(db.Boolean, default=False)

    ingredient = db.relationship("IngredientMaster", backref="shopping_items")
    unit_obj = db.relationship("Unit", backref="shopping_items")
