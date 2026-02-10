import os
import uuid

import requests
from recipe_scrapers import scrape_html

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from sqlalchemy import or_

from app import db
from app.forms import RecipeForm
from app.models import Recipe, RecipeIngredient, RecipeImage, IngredientMaster, Unit, Tag, recipe_tags

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


def get_or_create_ingredient(name):
    if not name or not name.strip():
        return None
    ing = IngredientMaster.query.filter(IngredientMaster.name.ilike(name.strip())).first()
    if not ing:
        ing = IngredientMaster(name=name.strip())
        db.session.add(ing)
        db.session.flush()
    return ing


def get_or_create_tag(name):
    if not name or not name.strip():
        return None
    tag = Tag.query.filter(Tag.name.ilike(name.strip())).first()
    if not tag:
        tag = Tag(name=name.strip())
        db.session.add(tag)
        db.session.flush()
    return tag


def get_or_create_unit(unit_id=None, unit_name=None):
    if unit_id:
        u = db.session.get(Unit, int(unit_id))
        if u:
            return u
    if unit_name and unit_name.strip():
        u = Unit.query.filter(Unit.name.ilike(unit_name.strip())).first()
        if not u:
            u = Unit(name=unit_name.strip(), symbol=unit_name.strip()[:10])
            db.session.add(u)
            db.session.flush()
        return u
    return Unit.query.filter_by(name="unidad").first()


@bp.route("/")
def list():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    q = request.args.get("q", "").strip()
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
            .all()
        )
    else:
        recipes = base.order_by(Recipe.updated_at.desc()).all()
    return render_template("recipes/list.html", recipes=recipes, search_query=q)


# Browser-like headers to reduce blocking (e.g. Bon Appétit, paywalled sites)
_IMPORT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


@bp.route("/import-from-url", methods=["POST"])
@login_required
def import_from_url():
    """Fetch a recipe from a URL and return title, instructions, ingredients (raw strings), image_url for form prefill."""
    data = request.get_json() or {}
    url = (data.get("url") or request.form.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid url"}), 400
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers=_IMPORT_HEADERS,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": "No se pudo cargar la página: " + str(e)}), 400

    scraper = None
    last_error = None
    try:
        scraper = scrape_html(resp.text, org_url=resp.url)
    except Exception as e:
        last_error = e
        try:
            scraper = scrape_html(resp.text, org_url=resp.url, wild_mode=True)
        except TypeError:
            pass  # library doesn't support wild_mode
        except Exception as e2:
            last_error = e2

    if scraper is None:
        err_msg = str(last_error) if last_error else "No se pudo extraer la receta."
        return jsonify({
            "error": "No se pudo extraer la receta de esta página. Prueba con otra URL o con un sitio de la lista soportada.",
            "detail": err_msg[:200] if err_msg else None,
        }), 400

    def _safe(method, default=None):
        try:
            out = method()
            return default if out is None else out
        except Exception:
            return default

    title = _safe(scraper.title, "") or ""
    instructions = _safe(scraper.instructions, "") or ""
    ingredients = _safe(scraper.ingredients, [])
    ingredients = [x for x in (ingredients or [])]
    image_url = _safe(scraper.image, "") or ""

    if not title and not ingredients and not instructions:
        return jsonify({"error": "No se encontró ninguna receta en esta URL."}), 400
    return jsonify({
        "title": title,
        "instructions": instructions,
        "ingredients": ingredients,
        "image_url": image_url,
    })


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
        db.session.flush()

        unit_ids = request.form.getlist("ingredient_unit_id")
        unit_names = request.form.getlist("ingredient_unit")
        quantities = request.form.getlist("ingredient_quantity")
        optional_indices = {int(x) for x in request.form.getlist("ingredient_optional") if x.isdigit()}
        for i, name in enumerate(request.form.getlist("ingredient_name")):
            if name.strip():
                ing = get_or_create_ingredient(name)
                if ing:
                    unit_id = unit_ids[i] if i < len(unit_ids) else None
                    unit_name = unit_names[i] if i < len(unit_names) else None
                    u = get_or_create_unit(unit_id=unit_id, unit_name=unit_name)
                    opt = i in optional_indices
                    ri = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_master_id=ing.id,
                        unit_id=u.id if u else None,
                        quantity=quantities[i] if i < len(quantities) else "",
                        optional=opt,
                    )
                    db.session.add(ri)

        # Tags
        tags_str = (form.tags.data or "").strip()
        recipe.tags = []
        for tname in [t.strip() for t in tags_str.split(",") if t.strip()]:
            tag = get_or_create_tag(tname)
            if tag:
                recipe.tags.append(tag)

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
    units = Unit.query.order_by(Unit.name).all()
    return render_template("recipes/form.html", form=form, recipe=None, units=units)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    recipe = get_recipe_or_404(id)
    form = RecipeForm()
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.description = form.description.data or ""
        recipe.instructions = form.instructions.data or ""

        RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
        unit_ids = request.form.getlist("ingredient_unit_id")
        unit_names = request.form.getlist("ingredient_unit")
        quantities = request.form.getlist("ingredient_quantity")
        optional_indices = {int(x) for x in request.form.getlist("ingredient_optional") if x.isdigit()}
        for i, name in enumerate(request.form.getlist("ingredient_name")):
            if name.strip():
                ing = get_or_create_ingredient(name)
                if ing:
                    unit_id = unit_ids[i] if i < len(unit_ids) else None
                    unit_name = unit_names[i] if i < len(unit_names) else None
                    u = get_or_create_unit(unit_id=unit_id, unit_name=unit_name)
                    opt = i in optional_indices
                    ri = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_master_id=ing.id,
                        unit_id=u.id if u else None,
                        quantity=quantities[i] if i < len(quantities) else "",
                        optional=opt,
                    )
                    db.session.add(ri)

        # Tags
        tags_str = (form.tags.data or "").strip()
        recipe.tags = []
        for tname in [t.strip() for t in tags_str.split(",") if t.strip()]:
            tag = get_or_create_tag(tname)
            if tag:
                recipe.tags.append(tag)

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
        form.tags.data = ", ".join(t.name for t in recipe.tags)
    units = Unit.query.order_by(Unit.name).all()
    return render_template("recipes/form.html", form=form, recipe=recipe, units=units)


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
