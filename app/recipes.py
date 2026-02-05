import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.forms import RecipeForm
from app.models import Recipe, Ingredient, RecipeImage

bp = Blueprint("recipes", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_recipe_or_404(id):
    recipe = db.session.get(Recipe, id)
    if recipe is None:
        abort(404)
    if recipe.user_id != current_user.id:
        abort(403)
    return recipe


@bp.route("/")
def list():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.updated_at.desc()).all()
    return render_template("recipes/list.html", recipes=recipes)


@bp.route("/<int:id>")
@login_required
def detail(id):
    recipe = get_recipe_or_404(id)
    return render_template("recipes/detail.html", recipe=recipe)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def add():
    form = RecipeForm()
    if form.validate_on_submit():
        recipe = Recipe(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data or "",
            instructions=form.instructions.data or "",
        )
        db.session.add(recipe)
        db.session.flush()  # Get recipe.id before adding ingredients/images

        # Parse ingredients from form
        for i in range(len(request.form.getlist("ingredient_name"))):
            name = request.form.getlist("ingredient_name")[i]
            if name.strip():
                ing = Ingredient(
                    recipe_id=recipe.id,
                    name=name.strip(),
                    quantity=request.form.getlist("ingredient_quantity")[i] or "",
                    unit=request.form.getlist("ingredient_unit")[i] or "",
                )
                db.session.add(ing)

        # Handle image uploads
        for file in request.files.getlist("images"):
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                recipe_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(recipe.id))
                os.makedirs(recipe_dir, exist_ok=True)
                filepath = os.path.join(recipe_dir, filename)
                file.save(filepath)
                img = RecipeImage(recipe_id=recipe.id, filename=filename)
                db.session.add(img)

        db.session.commit()
        flash("Receta creada correctamente.", "success")
        return redirect(url_for("recipes.detail", id=recipe.id))
    return render_template("recipes/form.html", form=form, recipe=None)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    recipe = get_recipe_or_404(id)
    form = RecipeForm()
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.description = form.description.data or ""
        recipe.instructions = form.instructions.data or ""

        # Remove ingredients and re-add from form
        Ingredient.query.filter_by(recipe_id=recipe.id).delete()
        for i in range(len(request.form.getlist("ingredient_name"))):
            name = request.form.getlist("ingredient_name")[i]
            if name.strip():
                ing = Ingredient(
                    recipe_id=recipe.id,
                    name=name.strip(),
                    quantity=request.form.getlist("ingredient_quantity")[i] or "",
                    unit=request.form.getlist("ingredient_unit")[i] or "",
                )
                db.session.add(ing)

        # Handle remove images
        remove_ids = request.form.getlist("remove_image")
        for img_id in remove_ids:
            try:
                img = db.session.get(RecipeImage, int(img_id))
                if img and img.recipe_id == recipe.id:
                    filepath = os.path.join(
                        current_app.config["UPLOAD_FOLDER"],
                        str(recipe.id),
                        img.filename,
                    )
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    db.session.delete(img)
            except (ValueError, TypeError):
                pass

        # Handle new image uploads
        for file in request.files.getlist("images"):
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                recipe_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(recipe.id))
                os.makedirs(recipe_dir, exist_ok=True)
                filepath = os.path.join(recipe_dir, filename)
                file.save(filepath)
                img = RecipeImage(recipe_id=recipe.id, filename=filename)
                db.session.add(img)

        db.session.commit()
        flash("Receta actualizada correctamente.", "success")
        return redirect(url_for("recipes.detail", id=recipe.id))

    if request.method == "GET":
        form.title.data = recipe.title
        form.description.data = recipe.description
        form.instructions.data = recipe.instructions
    return render_template("recipes/form.html", form=form, recipe=recipe)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    recipe = get_recipe_or_404(id)
    recipe_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(recipe.id))
    if os.path.isdir(recipe_dir):
        for f in os.listdir(recipe_dir):
            os.remove(os.path.join(recipe_dir, f))
        os.rmdir(recipe_dir)
    db.session.delete(recipe)
    db.session.commit()
    flash("Receta eliminada.", "info")
    return redirect(url_for("recipes.list"))


@bp.route("/<int:recipe_id>/images/<filename>")
def serve_image(recipe_id, filename):
    if not current_user.is_authenticated:
        abort(404)
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.user_id != current_user.id:
        abort(404)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(os.path.join(upload_folder, str(recipe_id)), filename)
