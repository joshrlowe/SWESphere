from app import app, db
from app.forms import EditProfileForm, EmptyForm, LoginForm, PostForm, RegistrationForm
from app.models import User, Post
from datetime import datetime, timezone
from flask import (
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urlsplit
import os
import sqlalchemy as sa


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live!")
        return redirect(url_for("index"))
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=app.config["POSTS_PER_PAGE"],
        error_out=False,
    )
    next_url = url_for("index", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None
    response = make_response(
        render_template(
            "index.html",
            title="Home",
            form=form,
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(
        query, page=page, per_page=app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = url_for("explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("explore", page=posts.prev_num) if posts.has_prev else None
    response = make_response(
        render_template(
            "index.html",
            title="Explore",
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


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
    response = make_response(
        render_template(
            "login.html",
            title="Sign In",
            form=form,
            username_errors_length=(
                len(form.username.errors) if form.username.errors else 0
            ),
            password_errors_length=(
                len(form.password.errors) if form.password.errors else 0
            ),
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


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
    response = make_response(
        render_template(
            "register.html",
            title="Register",
            form=form,
            username_errors_length=(
                len(form.username.errors) if form.username.errors else 0
            ),
            email_errors_length=len(form.email.errors) if form.email.errors else 0,
            password_errors_length=(
                len(form.password.errors) if form.password.errors else 0
            ),
            password2_errors_length=(
                len(form.password2.errors) if form.password2.errors else 0
            ),
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.route("/user/<username>")
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get("page", 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(
        query, page=page, per_page=app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("user", username=user.username, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("user", username=user.username, page=posts.prev_num)
        if posts.has_prev
        else None
    )
    form = EmptyForm()
    response = make_response(
        render_template(
            "user.html",
            user=user,
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
            form=form,
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("user", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    response = make_response(
        render_template(
            "edit_profile.html",
            title="Edit Profile",
            form=form,
            username_errors_length=(
                len(form.username.errors) if form.username.errors else 0
            ),
            about_me_errors_length=(
                len(form.about_me.errors) if form.about_me.errors else 0
            ),
        )
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'strict-dynamic' 'nonce-RANDOM' 'self' https://swesphere.com; style-src 'self' https://cdn.jsdelivr.net; img-src 'self' https://www.gravatar.com/avatar/; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot follow yourself!")
            return redirect(url_for("user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f"You are following {username}!")
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f"User {username} not found.")
            return redirect(url_for("index"))
        if user == current_user:
            flash("You cannot unfollow yourself!")
            return redirect(url_for("user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f"You are not following {username}.")
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "images"),
        "logo32.png",
        mimetype="image/png",
    )
