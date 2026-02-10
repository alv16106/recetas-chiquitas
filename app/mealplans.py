from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
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

        # Avoid duplicates
        existing_ids = {mpr.recipe_id for mpr in mp.recipes}
        if recipe.id not in existing_ids:
            db.session.add(MealPlanRecipe(meal_plan_id=mp.id, recipe_id=recipe.id))

        db.session.commit()
        flash("Receta añadida al plan.", "success")
        return redirect(url_for("mealplans.detail", id=mp.id))

    return render_template("mealplans/add_from_recipe.html", recipe=recipe, plans=plans)


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
    existing_ids = {mpr.recipe_id for mpr in mp.recipes}
    if recipe_id not in existing_ids:
        db.session.add(MealPlanRecipe(meal_plan_id=mp.id, recipe_id=recipe_id))
        db.session.commit()
        flash(f"«{recipe.title}» añadida al plan.", "success")
    else:
        flash("Esa receta ya está en el plan.", "info")
    return redirect(url_for("mealplans.detail", id=id))


@bp.route("/<int:id>/create-shopping-list", methods=["POST"])
@login_required
def create_shopping_list(id):
    mp = MealPlan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    sl = ShoppingList(user_id=current_user.id, name=mp.name)
    db.session.add(sl)
    db.session.flush()

    existing = []
    for mpr in mp.recipes:
        recipe = mpr.recipe
        if not recipe:
            continue
        for ri in recipe.ingredients:
            if ri.ingredient_master_id and ri.ingredient:
                new_item = merge_ingredient(
                    existing,
                    ri.ingredient_master_id,
                    ri.unit_id,
                    ri.quantity,
                )
            else:
                # Legacy fallback
                name = ri.ingredient.name if ri.ingredient else ""
                unit_str = (ri.unit.symbol or ri.unit.name) if ri.unit else ""
                from app.shopping import merge_ingredient_legacy

                new_item = merge_ingredient_legacy(existing, name, ri.quantity, unit_str)
            if new_item:
                new_item.shopping_list_id = sl.id
                db.session.add(new_item)
                existing.append(new_item)

    db.session.commit()
    flash("Lista de compras creada desde el plan.", "success")
    return redirect(url_for("shopping.detail", id=sl.id))

