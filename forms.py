from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, PasswordField, ValidationError
from wtforms.validators import DataRequired, URL, Email, Length, EqualTo


class CreateItemForm(FlaskForm):
    item_url = StringField("URL wybranego produktu w ceneo:", validators=[DataRequired(),URL(message='Niepoprawne URL, wklej pełne URL.')])
    check_value = IntegerField("Cena poniżej jakiej ma zejść:", validators=[DataRequired(message='Podana wartość nie jest liczbą całkowitą.')])
    submit = SubmitField("Utwórz")

class EditValueForm(FlaskForm):
    check_value = IntegerField("Cena poniżej jakiej ma zejść:", validators=[DataRequired(message='Podana wartość nie jest liczbą całkowitą.')])

class RegisterForm(FlaskForm):
    email = StringField("Adres email: ",validators=[DataRequired(), Email(message="Niepoprawny adres email.")])
    password = PasswordField("Hasło: ", validators=[DataRequired(),Length(min=8,message='Wymagane jest conajmniej 8 znaków.'),EqualTo('confirm', message='Hasła muszą się zgadzać.')])
    confirm  = PasswordField('Powtórz hasło: ')

class LoginForm(FlaskForm):
    email = StringField("Adres email:", validators=[DataRequired(),Email()])
    password = PasswordField("Hasło: ", validators=[DataRequired()])