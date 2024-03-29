from app import app
from app.forms import LoginForm
from flask import flash, redirect, render_template, url_for


@app.route("/")
@app.route("/index")
def index():
    user = {"username": "Josh"}
    posts = [
        {"author": {"username": "user1"}, "body": "This is user1's first post!"},
        {"author": {"username": "user2"}, "body": "This is user2's first post!"},
    ]
    return render_template("index.html", title="Home", user=user, posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash(
            f"Login requested for user {form.username.data}, remember_me={form.remember_me.data}"
        )
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        title="Sign In",
        form=form,
        username_errors_length=len(form.username.errors) if form.username.errors else 0,
        password_errors_length=len(form.password.errors) if form.password.errors else 0,
    )
