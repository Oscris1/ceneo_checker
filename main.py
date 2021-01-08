from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from forms import CreateItemForm, EditValueForm, RegisterForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import ValidationError
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from apscheduler.schedulers.background import BackgroundScheduler

import requests
from bs4 import BeautifulSoup
import lxml
import datetime
import smtplib
import os

from dotenv import load_dotenv


load_dotenv() # Set up your EMAIL_NAME, EMAIL_PASSWORD and SECRET_KEY in .env
EMAIL_NAME = os.environ.get("EMAIL_NAME")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///checker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

year = datetime.datetime.now().year

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    items = db.relationship("Item", backref="users")


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    item_url = db.Column(db.String(150))
    last_value = db.Column(db.Integer)
    check_value = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
db.create_all()


@app.route('/')
def start():
    return render_template("index.html")


@app.route('/rejestracja', methods=["GET", "POST"])
def rejestracja():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash("Ten adres email jest zajęty!")
            return redirect(url_for('rejestracja'))

        secured_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8)
        new_user = User(
            email = form.email.data,
            password = secured_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("sledzenie_cen"))
    return render_template("register.html", form = form, current_user = current_user)


@app.route('/logowanie', methods=["GET", "POST"])
def logowanie():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Ten email nie istnieje, spróbuj ponownie.")
            return redirect(url_for("logowanie"))
        if not check_password_hash(user.password,password):
            flash("Niepoprawne hasło, spróbuj ponownie.")
            return redirect(url_for("logowanie"))
        else:
            login_user(user)
            return redirect(url_for("sledzenie_cen"))
    return render_template("login.html", form = form, current_user = current_user)


@app.route('/wyloguj')
@login_required
def wyloguj():
    logout_user()
    return redirect(url_for('start'))


@app.route('/sledzenie', methods=["GET", "POST"])
@login_required
def sledzenie_cen():
    items = Item.query.filter_by(user_id=current_user.id).all()
    edit_form = EditValueForm()
    return render_template("sledzenie.html", items = items, form=edit_form, current_user = current_user)


@app.route("/sledzenie/zmien_cene/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_check_value(item_id):
    item_to_edit = Item.query.get(item_id)
    if item_to_edit.user_id == current_user.id:
        edit_form = EditValueForm()
        if edit_form.validate_on_submit():
            item_to_edit.check_value = edit_form.check_value.data
            db.session.commit()
            value_checker(item_to_edit)
        
    return redirect(url_for("sledzenie_cen"))


@app.route('/tworzenie_przedmiotu', methods=["GET","POST"])
@login_required
def tworzenie_przedmiotu():
    form = CreateItemForm()
    if form.validate_on_submit():
        url_form = form.item_url.data
        check_prize_form = form.check_value.data

        try:
            data = scraper(url_form) 
        except:
            flash("Niepoprawne URL, spróbuj ponownie.")
            return redirect(url_for("tworzenie_przedmiotu"))
        else:
            new_item = Item(
                name = data["name"],
                last_value = data["lowest_value"],
                item_url = url_form,
                check_value = check_prize_form,
                user_id = current_user.id
            )
            db.session.add(new_item)
            db.session.commit()

            value_checker(new_item)

            return redirect(url_for("sledzenie_cen"))

    return render_template("tworzenie.html", form = form, current_user = current_user)


@app.route("/sledzenie/usun/<int:item_id>", methods=["GET", "POST"])
@login_required
def delete_post(item_id):
    item_to_delete = Item.query.get(item_id)
    if item_to_delete.user_id == current_user.id:
        db.session.delete(item_to_delete)
        db.session.commit()
    return redirect(url_for("sledzenie_cen"))


def scraper(url):
    response = requests.get(url)
    response.raise_for_status
    ceneo_html = response.text
    soup = BeautifulSoup(ceneo_html,"lxml")
    all_items = soup.find_all(class_=f"product-offer-2020__product")
    # class_=f"product-offer-{year}__product"

    values = []

    for item in all_items:
        price = item.find(class_="value").get_text()
        values.append(int(price))
    lowest_value = min(values)

    name = soup.find(class_=f"product-top-2020__product-info__name").get_text()
    # class_=f"product-top-{year}__product-info__name"

    data = {"name" : name, "lowest_value" : lowest_value}

    return data


def value_checker(item):
    data = scraper(item.item_url)
    if data["lowest_value"] < item.check_value:
        print("wyślij maila")
        user = User.query.filter_by(id=item.user_id).first()
        
        message = f"{item.name} kosztuje teraz {data['lowest_value']} pln!"

        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(EMAIL_NAME, EMAIL_PASSWORD)
            connection.sendmail(
                from_addr=EMAIL_NAME,
                to_addrs=user.email,
                msg=(f"Subject:Cena spadła!\n\n{message}\n{item.item_url}").encode('utf-8')
    )       
    else:
        print("Tu nie wysyłam maila")

    item.last_value = data['lowest_value']
    db.session.commit()


def scheduled_check():
    items = Item.query.all()
    for item in items:
        value_checker(item)


sched = BackgroundScheduler(daemon=True)
sched.add_job(
            scheduled_check,
            'interval',
            hours=3,
            misfire_grace_time=10000
            )

sched.start()

if __name__ == "__main__":
    
    app.run(debug=False)
