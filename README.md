# Recetas Chiquitas

A simple household recipe web app with user authentication, recipe management, ingredient lists, image support, and shopping list generation.

## Features

- **Authentication**: Register and login with username and password
- **Recipes**: Add, edit, and delete recipes with title, description, and instructions
- **Ingredients**: Each recipe has ingredient lists (quantity, unit, name)
- **Images**: Upload multiple images per recipe
- **Shopping lists**: Create lists and add ingredients from recipes; quantities merge for matching ingredients

## Setup

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The app runs at http://127.0.0.1:5000/

## Usage

1. Register a new account
2. Create recipes with ingredients and optional images
3. Use "Añadir a lista de compras" on a recipe to add its ingredients to a new or existing shopping list
4. Check off items on your shopping list as you shop

## Customization

### Colors and look and feel

Edit `app/static/css/custom.css` and change the CSS variables in the `:root` block:

| Variable | Description |
|----------|-------------|
| `--theme-primary` | Primary brand color (navbar, primary buttons, links) |
| `--theme-secondary` | Secondary buttons and accents |
| `--theme-navbar-bg` | Navbar background (defaults to primary) |
| `--theme-body-bg` | Page background |
| `--theme-success` | Success buttons and highlights |
| `--theme-danger` | Delete buttons and errors |
| `--theme-font-family` | Font family |
| `--theme-logo-height` | Logo height in navbar (e.g. 32px, 40px) |

### Custom logo

Replace `app/static/images/logo.png` with your own logo. Use PNG or SVG (rename to `logo.svg` and update the template if using SVG). Recommended size: 64x64 to 128x128 pixels.

To show only the logo (hide the site name), add to `custom.css`:
```css
.navbar-brand-text { display: none; }
```
