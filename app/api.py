"""API endpoints for units, ingredients, and recipe search."""
from sqlalchemy import or_

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app import db
from app.models import Unit, IngredientMaster, Recipe, RecipeIngredient, Tag, recipe_tags

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/units")
@login_required
def list_units():
    """Return all units for dropdown."""
    units = Unit.query.order_by(Unit.name).all()
    return jsonify([{"id": u.id, "name": u.name, "symbol": u.symbol} for u in units])


@bp.route("/units", methods=["POST"])
@login_required
def create_unit():
    """Create a new unit. Used when user adds a custom unit."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    existing = Unit.query.filter(Unit.name.ilike(name)).first()
    if existing:
        return jsonify({"id": existing.id, "name": existing.name, "symbol": existing.symbol})
    unit = Unit(name=name, symbol=data.get("symbol", name[:10]))
    db.session.add(unit)
    db.session.commit()
    return jsonify({"id": unit.id, "name": unit.name, "symbol": unit.symbol}), 201


@bp.route("/ingredients")
@login_required
def search_ingredients():
    """Search ingredients by name. For autocomplete."""
    q = (request.args.get("q") or "").strip().lower()
    limit = min(int(request.args.get("limit", 20)), 50)
    if not q:
        # Return recent/popular when no query
        items = IngredientMaster.query.order_by(IngredientMaster.name).limit(limit).all()
    else:
        items = (
            IngredientMaster.query.filter(IngredientMaster.name.ilike(f"%{q}%"))
            .order_by(IngredientMaster.name)
            .limit(limit)
            .all()
        )
    return jsonify([{"id": i.id, "name": i.name} for i in items])


@bp.route("/ingredients", methods=["POST"])
@login_required
def create_ingredient():
    """Create a new ingredient. Used when user adds one not in the list."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    existing = IngredientMaster.query.filter(IngredientMaster.name.ilike(name)).first()
    if existing:
        return jsonify({"id": existing.id, "name": existing.name})
    ing = IngredientMaster(name=name)
    db.session.add(ing)
    db.session.commit()
    return jsonify({"id": ing.id, "name": ing.name}), 201


@bp.route("/recipes")
@login_required
def search_recipes():
    """Search current user's recipes by title, ingredients, or tags. For meal plan add."""
    q = (request.args.get("q") or "").strip()
    limit = min(int(request.args.get("limit", 15)), 30)
    base = Recipe.query.filter_by(user_id=current_user.id)
    if q:
        term = f"%{q}%"
        recipes = (
            base.outerjoin(RecipeIngredient)
            .outerjoin(IngredientMaster)
            .outerjoin(recipe_tags)
            .outerjoin(Tag)
            .filter(
                or_(
                    Recipe.title.ilike(term),
                    IngredientMaster.name.ilike(term),
                    Tag.name.ilike(term),
                )
            )
            .distinct()
            .order_by(Recipe.updated_at.desc())
            .limit(limit)
            .all()
        )
    else:
        recipes = base.order_by(Recipe.updated_at.desc()).limit(limit).all()
    return jsonify([{"id": r.id, "title": r.title} for r in recipes])
