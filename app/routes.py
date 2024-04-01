from app import app, db
from app.forms import EditProfileForm, LoginForm, RegistrationForm
from app.models import User
from datetime import datetime, timezone
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urlsplit
import sqlalchemy as sa


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        login_user(user, False)
        return redirect(url_for("index"))
    return render_template(
        "register.html",
        title="Register",
        form=form,
        username_errors_length=len(form.username.errors) if form.username.errors else 0,
        email_errors_length=len(form.email.errors) if form.email.errors else 0,
        password_errors_length=len(form.password.errors) if form.password.errors else 0,
        password2_errors_length=(
            len(form.password2.errors) if form.password2.errors else 0
        ),
    )


@app.route("/user/<username>")
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {"author": user, "body": "This is user1's first post!"},
        {"author": user, "body": "This is user2's first post!"},
    ]
    return render_template("user.html", user=user, posts=posts)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("user", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template(
        "edit_profile.html",
        title="Edit Profile",
        form=form,
        username_errors_length=len(form.username.errors) if form.username.errors else 0,
        about_me_errors_length=len(form.about_me.errors) if form.about_me.errors else 0,
    )
