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
