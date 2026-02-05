from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.models import Recipe, ShoppingList, ShoppingListItem

bp = Blueprint("shopping", __name__)


def merge_ingredient(existing_items, name, quantity, unit):
    """Merge ingredient into existing items. Same name+unit gets quantities merged."""
    name_lower = name.strip().lower()
    unit_normalized = (unit or "").strip().lower()
    for item in existing_items:
        if item.ingredient_name.strip().lower() == name_lower and (item.unit or "").strip().lower() == unit_normalized:
            # Try to merge numeric quantities
            try:
                q1 = float(item.quantity or 0)
                q2 = float(quantity or 0)
                item.quantity = str(q1 + q2)
                return
            except (ValueError, TypeError):
                # Non-numeric: append as separate or keep both
                item.quantity = f"{item.quantity} + {quantity}" if item.quantity and quantity else (item.quantity or quantity)
                return
    # New item
    return ShoppingListItem(
        ingredient_name=name.strip(),
        quantity=quantity or "",
        unit=unit or "",
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
    return render_template("shopping/form.html", shopping_list=None)


@bp.route("/<int:id>")
@login_required
def detail(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template("shopping/detail.html", shopping_list=sl)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        sl.name = request.form.get("name", sl.name).strip() or sl.name
        # Update checked state for each item
        for item in sl.items:
            key = f"checked_{item.id}"
            item.checked = key in request.form
        db.session.commit()
        flash("Lista actualizada.", "success")
        return redirect(url_for("shopping.detail", id=sl.id))
    return render_template("shopping/form.html", shopping_list=sl)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(sl)
    db.session.commit()
    flash("Lista eliminada.", "info")
    return redirect(url_for("shopping.list"))


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

        existing = list(sl.items)
        for ing in recipe.ingredients:
            new_item = merge_ingredient(existing, ing.name, ing.quantity, ing.unit)
            if new_item:
                new_item.shopping_list_id = sl.id
                db.session.add(new_item)
                existing.append(new_item)

        db.session.commit()
        flash("Ingredientes añadidos a la lista.", "success")
        return redirect(url_for("shopping.detail", id=sl.id))

    return render_template("shopping/add_from_recipe.html", recipe=recipe, lists=lists)


@bp.route("/<int:id>/toggle/<int:item_id>", methods=["POST"])
@login_required
def toggle_item(id, item_id):
    sl = ShoppingList.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    item = ShoppingListItem.query.filter_by(id=item_id, shopping_list_id=sl.id).first_or_404()
    item.checked = not item.checked
    db.session.commit()
    return redirect(url_for("shopping.detail", id=id))
