from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.models import Recipe, RecipeIngredient, ShoppingList, ShoppingListItem, IngredientMaster, Unit
from app.recipes import get_or_create_ingredient, get_or_create_unit

bp = Blueprint("shopping", __name__)


def _format_quantity(val):
    """Format numeric quantity: 9.0 -> '9', 4.5 -> '4.5'."""
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return str(f)
    except (ValueError, TypeError):
        return str(val) if val is not None else ""


def merge_ingredient(existing_items, ingredient_master_id, unit_id, quantity):
    """Merge by ingredient_master_id + unit_id. Numeric quantities add together."""
    for item in existing_items:
        if item.ingredient_master_id == ingredient_master_id and item.unit_id == unit_id:
            try:
                q1 = float(item.quantity or 0)
                q2 = float(quantity or 0)
                item.quantity = _format_quantity(q1 + q2)
                return
            except (ValueError, TypeError):
                item.quantity = f"{item.quantity} + {quantity}" if item.quantity and quantity else (item.quantity or quantity)
                return
    return ShoppingListItem(
        ingredient_master_id=ingredient_master_id,
        unit_id=unit_id,
        ingredient_name=None,
        quantity=quantity or "",
        unit=None,
    )


def merge_ingredient_legacy(existing_items, name, quantity, unit_str):
    """Fallback for string-based merge (legacy)."""
    name_lower = name.strip().lower()
    unit_norm = (unit_str or "").strip().lower()
    for item in existing_items:
        iname = (item.ingredient_name or "").strip().lower()
        ustr = (item.unit or "").strip().lower()
        if iname == name_lower and ustr == unit_norm:
            try:
                q1 = float(item.quantity or 0)
                q2 = float(quantity or 0)
                item.quantity = _format_quantity(q1 + q2)
                return
            except (ValueError, TypeError):
                item.quantity = f"{item.quantity} + {quantity}" if item.quantity and quantity else (item.quantity or quantity)
                return
    return ShoppingListItem(
        ingredient_name=name.strip(),
        quantity=quantity or "",
        unit=unit_str or "",
    )


@bp.route("/")
@login_required
def list():
    lists = ShoppingList.query.filter_by(user_id=current_user.id).order_by(ShoppingList.created_at.desc()).all()
    return render_template("shopping/list.html", lists=lists)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        name = request.form.get("name", "Lista de compras").strip() or "Lista de compras"
        sl = ShoppingList(user_id=current_user.id, name=name)
        db.session.add(sl)
        db.session.commit()
        flash("Lista creada.", "success")
        return redirect(url_for("shopping.detail", id=sl.id))
    return render_template("shopping/form.html", shopping_list=None, units=[])


@bp.route("/<int:id>")
@login_required
def detail(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    units = Unit.query.order_by(Unit.name).all()
    return render_template("shopping/detail.html", shopping_list=sl, units=units)


@bp.route("/<int:id>/add-item", methods=["POST"])
@login_required
def add_item(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = (request.form.get("name") or "").strip()
    if name:
        ing = get_or_create_ingredient(name)
        if ing:
            quantity = request.form.get("quantity", "").strip()
            unit_id = request.form.get("unit_id")
            unit_name = request.form.get("unit")
            u = get_or_create_unit(unit_id=unit_id, unit_name=unit_name)
            item = ShoppingListItem(
                shopping_list_id=sl.id,
                ingredient_master_id=ing.id,
                unit_id=u.id if u else None,
                ingredient_name=None,
                quantity=quantity,
                unit=None,
            )
            db.session.add(item)
            db.session.commit()
            flash("Item añadido.", "success")
    return redirect(url_for("shopping.detail", id=id))


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        sl.name = request.form.get("name", sl.name).strip() or sl.name
        # Remove items
        for item in [x for x in sl.items]:
            if f"remove_item_{item.id}" in request.form:
                db.session.delete(item)
        # Add new items
        unit_ids = request.form.getlist("new_item_unit_id")
        unit_names = request.form.getlist("new_item_unit")
        quantities = request.form.getlist("new_item_quantity")
        for i, name in enumerate(request.form.getlist("new_item_name")):
            if name and name.strip():
                ing = get_or_create_ingredient(name.strip())
                if ing:
                    unit_id = unit_ids[i] if i < len(unit_ids) else None
                    unit_name = unit_names[i] if i < len(unit_names) else None
                    u = get_or_create_unit(unit_id=unit_id, unit_name=unit_name)
                    new_item = ShoppingListItem(
                        shopping_list_id=sl.id,
                        ingredient_master_id=ing.id,
                        unit_id=u.id if u else None,
                        ingredient_name=None,
                        quantity=quantities[i] if i < len(quantities) else "",
                        unit=None,
                    )
                    db.session.add(new_item)
        db.session.commit()
        flash("Lista actualizada.", "success")
        return redirect(url_for("shopping.detail", id=sl.id))
    units = Unit.query.order_by(Unit.name).all()
    return render_template("shopping/form.html", shopping_list=sl, units=units)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(sl)
    db.session.commit()
    flash("Lista eliminada.", "info")
    return redirect(url_for("shopping.list"))


@bp.route("/<int:id>/add-recipe/<int:recipe_id>", methods=["POST"])
@login_required
def add_recipe_to_list(id, recipe_id):
    """Add a recipe's ingredients to a specific shopping list (used by modal)."""
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first_or_404()
    existing = [x for x in sl.items]
    for ri in recipe.ingredients:
        if ri.ingredient_master_id and ri.ingredient:
            new_item = merge_ingredient(
                existing,
                ri.ingredient_master_id,
                ri.unit_id,
                ri.quantity,
            )
        else:
            name = ri.ingredient.name if ri.ingredient else ""
            unit_str = (ri.unit.symbol or ri.unit.name) if ri.unit else ""
            new_item = merge_ingredient_legacy(existing, name, ri.quantity, unit_str)
        if new_item:
            new_item.shopping_list_id = sl.id
            db.session.add(new_item)
            existing.append(new_item)
    db.session.commit()
    flash("Ingredientes añadidos.", "success")
    return redirect(url_for("shopping.detail", id=id))


@bp.route("/add-from-recipe/<int:recipe_id>", methods=["GET", "POST"])
@login_required
def add_from_recipe(recipe_id):
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first_or_404()
    lists = ShoppingList.query.filter_by(user_id=current_user.id).order_by(ShoppingList.created_at.desc()).all()

    if request.method == "POST":
        list_id = request.form.get("list_id")
        create_new = request.form.get("create_new") == "1"
        name = request.form.get("new_list_name", "").strip()

        if create_new and name:
            sl = ShoppingList(user_id=current_user.id, name=name)
            db.session.add(sl)
            db.session.flush()
        elif list_id:
            sl = ShoppingList.query.filter_by(id=int(list_id), user_id=current_user.id).first()
            if not sl:
                abort(404)
        else:
            flash("Selecciona una lista o crea una nueva.", "error")
            return render_template("shopping/add_from_recipe.html", recipe=recipe, lists=lists)

        existing = [x for x in sl.items]
        for ri in recipe.ingredients:
            if ri.ingredient_master_id and ri.ingredient:
                new_item = merge_ingredient(
                    existing,
                    ri.ingredient_master_id,
                    ri.unit_id,
                    ri.quantity,
                )
            else:
                name = ri.ingredient.name if ri.ingredient else ""
                unit_str = (ri.unit.symbol or ri.unit.name) if ri.unit else ""
                new_item = merge_ingredient_legacy(existing, name, ri.quantity, unit_str)
            if new_item:
                new_item.shopping_list_id = sl.id
                db.session.add(new_item)
                existing.append(new_item)

        db.session.commit()
        flash("Ingredientes añadidos a la lista.", "success")
        return redirect(url_for("shopping.detail", id=sl.id))

    return render_template("shopping/add_from_recipe.html", recipe=recipe, lists=lists)


@bp.route("/<int:id>/remove-item/<int:item_id>", methods=["POST"])
@login_required
def remove_item(id, item_id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    item = ShoppingListItem.query.filter_by(id=item_id, shopping_list_id=sl.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify({"ok": True})
    return redirect(url_for("shopping.detail", id=id))


@bp.route("/<int:id>/toggle/<int:item_id>", methods=["POST"])
@login_required
def toggle_item(id, item_id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    item = ShoppingListItem.query.filter_by(id=item_id, shopping_list_id=sl.id).first_or_404()
    item.checked = not item.checked
    db.session.commit()
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify({"ok": True, "checked": item.checked})
    return redirect(url_for("shopping.detail", id=id))
