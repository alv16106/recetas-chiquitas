from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

from app.models import User


class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember_me = BooleanField("Recordarme", default=False)
    submit = SubmitField("Iniciar sesión")


class RegistrationForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=4)])
    password2 = PasswordField("Repetir contraseña", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Registrarse")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Ese nombre de usuario ya está en uso.")


class RecipeForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Descripción")
    instructions = TextAreaField("Instrucciones")
    submit = SubmitField("Guardar")


# Ingredients are handled via JS dynamic rows and submitted as JSON/field arrays
# Images use FileField with multiple upload
