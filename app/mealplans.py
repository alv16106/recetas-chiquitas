from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.models import MealPlan, MealPlanRecipe, Recipe, ShoppingList, ShoppingListItem
from app.shopping import merge_ingredient

bp = Blueprint("mealplans", __name__)


@bp.route("/")
@login_required
def list():
    plans = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).all()
    return render_template("mealplans/list.html", plans=plans)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duration = request.form.get("duration_days", "").strip()
        if not name:
            flash("El plan necesita un nombre.", "error")
            return render_template("mealplans/form.html", meal_plan=None)
        try:
            duration_days = int(duration) if duration else 7
        except ValueError:
            duration_days = 7
        mp = MealPlan(user_id=current_user.id, name=name, duration_days=duration_days or 7)
        db.session.add(mp)
        db.session.commit()
        flash("Plan de comidas creado.", "success")
        return redirect(url_for("mealplans.detail", id=mp.id))
    return render_template("mealplans/form.html", meal_plan=None)


@bp.route("/<int:id>")
@login_required
def detail(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template("mealplans/detail.html", meal_plan=mp)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        name = request.form.get("name", mp.name).strip() or mp.name
        duration = request.form.get("duration_days", mp.duration_days)
        try:
            duration_days = int(duration)
        except ValueError:
            duration_days = mp.duration_days
        mp.name = name
        mp.duration_days = duration_days
        db.session.commit()
        flash("Plan de comidas actualizado.", "success")
        return redirect(url_for("mealplans.detail", id=mp.id))
    return render_template("mealplans/form.html", meal_plan=mp)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(mp)
    db.session.commit()
    flash("Plan de comidas eliminado.", "info")
    return redirect(url_for("mealplans.list"))


@bp.route("/add-from-recipe/<int:recipe_id>", methods=["GET", "POST"])
@login_required
def add_from_recipe(recipe_id):
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first_or_404()
    plans = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).all()

    if request.method == "POST":
        plan_id = request.form.get("plan_id")
        create_new = request.form.get("create_new") == "1"
        name = request.form.get("new_plan_name", "").strip()
        duration = request.form.get("duration_days", "").strip()

        if create_new and name:
            try:
                duration_days = int(duration) if duration else 7
            except ValueError:
                duration_days = 7
            mp = MealPlan(user_id=current_user.id, name=name, duration_days=duration_days or 7)
            db.session.add(mp)
            db.session.flush()
        elif plan_id:
            mp = MealPlan.query.filter_by(id=int(plan_id), user_id=current_user.id).first()
            if not mp:
                abort(404)
        else:
            flash("Selecciona un plan o crea uno nuevo.", "error")
            return render_template("mealplans/add_from_recipe.html", recipe=recipe, plans=plans)

        existing = {mpr.recipe_id: mpr for mpr in mp.recipes}
        if recipe.id not in existing:
            db.session.add(MealPlanRecipe(meal_plan_id=mp.id, recipe_id=recipe.id))
        else:
            existing[recipe.id].count += 1

        db.session.commit()
        flash("Receta añadida al plan.", "success")
        return redirect(url_for("mealplans.detail", id=mp.id))

    return render_template("mealplans/add_from_recipe.html", recipe=recipe, plans=plans)


@bp.route("/<int:id>/set-recipe-count/<int:recipe_id>", methods=["POST"])
@login_required
def set_recipe_count(id, recipe_id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    mpr = MealPlanRecipe.query.filter_by(
        meal_plan_id=mp.id, recipe_id=recipe_id
    ).first_or_404()
    count = request.form.get("count") or (request.get_json() or {}).get("count")
    try:
        count = max(1, int(count))
    except (ValueError, TypeError):
        count = 1
    mpr.count = count
    db.session.commit()
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify({"ok": True, "count": mpr.count})
    return redirect(url_for("mealplans.detail", id=id))


@bp.route("/<int:id>/remove-recipe/<int:recipe_id>", methods=["POST"])
@login_required
def remove_recipe(id, recipe_id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    mpr = MealPlanRecipe.query.filter_by(
        meal_plan_id=mp.id, recipe_id=recipe_id
    ).first_or_404()
    db.session.delete(mpr)
    db.session.commit()
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify({"ok": True})
    return redirect(url_for("mealplans.detail", id=id))


@bp.route("/<int:id>/add-recipe", methods=["POST"])
@login_required
def add_recipe(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    recipe_id = request.form.get("recipe_id") or (request.get_json() or {}).get("recipe_id")
    if not recipe_id:
        flash("Falta la receta.", "error")
        return redirect(url_for("mealplans.detail", id=id))
    try:
        recipe_id = int(recipe_id)
    except (ValueError, TypeError):
        flash("Receta no válida.", "error")
        return redirect(url_for("mealplans.detail", id=id))
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    if not recipe:
        flash("Receta no encontrada.", "error")
        return redirect(url_for("mealplans.detail", id=id))
    existing = {mpr.recipe_id: mpr for mpr in mp.recipes}
    if recipe_id not in existing:
        db.session.add(MealPlanRecipe(meal_plan_id=mp.id, recipe_id=recipe_id))
        db.session.commit()
        flash(f"«{recipe.title}» añadida al plan.", "success")
    else:
        existing[recipe_id].count += 1
        db.session.commit()
        flash(f"«{recipe.title}»: cantidad aumentada.", "success")
    return redirect(url_for("mealplans.detail", id=id))


@bp.route("/<int:id>/create-shopping-list", methods=["POST"])
@login_required
def create_shopping_list(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    sl = ShoppingList(user_id=current_user.id, name=mp.name)
    db.session.add(sl)
    db.session.flush()

    def scale_quantity(qty, mult):
        """Scale quantity by multiplier; return string."""
        if mult <= 1:
            return qty or ""
        try:
            f = float(qty or 0) * mult
            from app.shopping import _format_quantity

            return _format_quantity(f)
        except (ValueError, TypeError):
            return f"{qty} × {mult}" if qty else str(mult)

    mult = 1
    existing = []
    for mpr in mp.recipes:
        recipe = mpr.recipe
        if not recipe:
            continue
        mult = max(1, mpr.count or 1)
        for ri in recipe.ingredients:
            qty = scale_quantity(ri.quantity, mult)
            if ri.ingredient_master_id and ri.ingredient:
                new_item = merge_ingredient(
                    existing,
                    ri.ingredient_master_id,
                    ri.unit_id,
                    qty,
                )
            else:
                name = ri.ingredient.name if ri.ingredient else ""
                unit_str = (ri.unit.symbol or ri.unit.name) if ri.unit else ""
                from app.shopping import merge_ingredient_legacy

                new_item = merge_ingredient_legacy(existing, name, qty, unit_str)
            if new_item:
                new_item.shopping_list_id = sl.id
                db.session.add(new_item)
                existing.append(new_item)

    db.session.commit()
    flash("Lista de compras creada desde el plan.", "success")
    return redirect(url_for("shopping.detail", id=sl.id))

