from app import app, db
from app.forms import LoginForm
from app.models import User
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urlsplit
import sqlalchemy as sa


@app.route("/")
@app.route("/index")
@login_required
def index():
    posts = [
        {"author": {"username": "user1"}, "body": "This is user1's first post!"},
        {"author": {"username": "user2"}, "body": "This is user2's first post!"},
    ]
    return render_template("index.html", title="Home", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )
        if not user or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            return redirect(url_for("index"))
        return redirect(next_page)
    return render_template(
        "login.html",
        title="Sign In",
        form=form,
        username_errors_length=len(form.username.errors) if form.username.errors else 0,
        password_errors_length=len(form.password.errors) if form.password.errors else 0,
    )


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))
