"""Route handlers for SWESphere."""
from app import app, db, limiter, audit_logger
from app.email import send_password_reset_email
from app.forms import (
    AvatarUploadForm,
    CommentForm,
    EditProfileForm,
    EmptyForm,
    LoginForm,
    PostForm,
    RegistrationForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
    SearchForm,
)
from app.models import User, Post, Comment, Notification
from datetime import datetime, timezone
from flask import (
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    jsonify,
)
from flask_babel import _, get_locale
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urlsplit
from werkzeug.utils import secure_filename
import base64
import os
import sqlalchemy as sa
import uuid


def generate_nonce():
    """Generate a nonce for CSP."""
    return base64.b64encode(os.urandom(16)).decode("utf-8")


def add_security_headers(response, nonce):
    """Add security headers to response."""
    csp = (
        "default-src 'none'; "
        f"script-src 'self' https://swesphere.com https://cdn.jsdelivr.net 'nonce-{nonce}'; "
        f"style-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; "
        "img-src 'self' https://www.gravatar.com/avatar/ data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=15768000"
    response.headers["Content-Security-Policy"] = csp
    return response


@app.before_request
def before_request():
    """Update last seen and set locale."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale)
    g.search_form = SearchForm()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    """Home page with post feed."""
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
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
    nonce = generate_nonce()

    response = make_response(
        render_template(
            "index.html",
            title=_("Home"),
            form=form,
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/explore")
@login_required
def explore():
    """Explore all posts."""
    page = request.args.get("page", 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(
        query, page=page, per_page=app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = url_for("explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("explore", page=posts.prev_num) if posts.has_prev else None
    nonce = generate_nonce()

    response = make_response(
        render_template(
            "index.html",
            title=_("Explore"),
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )

        # Check if account is locked
        if user and user.is_locked():
            audit_logger.log_login_attempt(
                form.username.data, False, request.remote_addr, "account_locked"
            )
            flash(_("Account is temporarily locked. Please try again later."))
            return redirect(url_for("login"))

        if not user or not user.check_password(form.password.data):
            if user:
                user.record_failed_login()
                db.session.commit()
                if user.is_locked():
                    audit_logger.log_account_lockout(user.username, request.remote_addr)
            audit_logger.log_login_attempt(
                form.username.data, False, request.remote_addr, "invalid_credentials"
            )
            flash(_("Invalid username or password"))
            return redirect(url_for("login"))

        # Successful login
        user.reset_login_attempts()
        db.session.commit()
        audit_logger.log_login_attempt(user.username, True, request.remote_addr)
        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            return redirect(url_for("index"))
        return redirect(next_page)

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "login.html",
            title=_("Sign In"),
            form=form,
            username_errors_length=len(form.username.errors) if form.username.errors else 0,
            password_errors_length=len(form.password.errors) if form.password.errors else 0,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/logout")
def logout():
    """Logout."""
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    """Registration page."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        audit_logger.log_registration(user.username, user.email, request.remote_addr)
        flash(_("Congratulations, you are now a registered user!"))
        login_user(user, False)
        return redirect(url_for("index"))

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "register.html",
            title=_("Register"),
            form=form,
            username_errors_length=len(form.username.errors) if form.username.errors else 0,
            email_errors_length=len(form.email.errors) if form.email.errors else 0,
            password_errors_length=len(form.password.errors) if form.password.errors else 0,
            password2_errors_length=len(form.password2.errors) if form.password2.errors else 0,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/user/<username>")
@login_required
def user(username):
    """User profile page."""
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
    nonce = generate_nonce()

    response = make_response(
        render_template(
            "user.html",
            user=user,
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
            form=form,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit profile page."""
    form = EditProfileForm(current_user.username)
    avatar_form = AvatarUploadForm()

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_("Your changes have been saved."))
        return redirect(url_for("user", username=current_user.username))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "edit_profile.html",
            title=_("Edit Profile"),
            form=form,
            avatar_form=avatar_form,
            username_errors_length=len(form.username.errors) if form.username.errors else 0,
            about_me_errors_length=len(form.about_me.errors) if form.about_me.errors else 0,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/upload_avatar", methods=["POST"])
@login_required
def upload_avatar():
    """Upload user avatar."""
    form = AvatarUploadForm()
    if form.validate_on_submit():
        file = form.avatar.data
        if file:
            # Generate unique filename
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], "avatars", filename)

            # Save file
            file.save(filepath)

            # Delete old avatar if exists
            if current_user.avatar_filename:
                old_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], "avatars", current_user.avatar_filename
                )
                if os.path.exists(old_path):
                    os.remove(old_path)

            current_user.avatar_filename = filename
            db.session.commit()
            flash(_("Avatar updated successfully!"))

    return redirect(url_for("edit_profile"))


@app.route("/uploads/avatars/<filename>")
def uploaded_avatar(filename):
    """Serve uploaded avatars."""
    return send_from_directory(
        os.path.join(app.config["UPLOAD_FOLDER"], "avatars"),
        filename
    )


@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    """Follow a user."""
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(_("User %(username)s not found.", username=username))
            return redirect(url_for("index"))
        if user == current_user:
            flash(_("You cannot follow yourself!"))
            return redirect(url_for("user", username=username))

        current_user.follow(user)

        # Create notification
        user.add_notification(
            "new_follower",
            {"username": current_user.username},
            actor_id=current_user.id
        )

        db.session.commit()
        flash(_("You are following %(username)s!", username=username))
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    """Unfollow a user."""
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(_("User %(username)s not found.", username=username))
            return redirect(url_for("index"))
        if user == current_user:
            flash(_("You cannot unfollow yourself!"))
            return redirect(url_for("user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_("You are not following %(username)s.", username=username))
        return redirect(url_for("user", username=username))
    else:
        return redirect(url_for("index"))


@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    """Like/unlike a post."""
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    if current_user.has_liked(post):
        current_user.unlike_post(post)
        action = "unliked"
    else:
        current_user.like_post(post)
        action = "liked"

        # Create notification
        if post.author.id != current_user.id:
            post.author.add_notification(
                "post_liked",
                {"post_id": post.id, "username": current_user.username},
                actor_id=current_user.id
            )

    db.session.commit()

    return jsonify({
        "action": action,
        "likes_count": post.likes_count()
    })


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    """Add a comment to a post."""
    post = db.session.get(Post, post_id)
    if not post:
        flash(_("Post not found."))
        return redirect(url_for("index"))

    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user, post=post)
        db.session.add(comment)

        # Create notification
        if post.author.id != current_user.id:
            post.author.add_notification(
                "new_comment",
                {"post_id": post.id, "username": current_user.username},
                actor_id=current_user.id
            )

        db.session.commit()
        flash(_("Your comment has been added."))

    return redirect(request.referrer or url_for("index"))


@app.route("/search")
@login_required
def search():
    """Search users and posts."""
    query = request.args.get("q", "")
    if not query:
        return redirect(url_for("explore"))

    page = request.args.get("page", 1, type=int)

    # Search users
    users = db.session.scalars(
        sa.select(User)
        .where(sa.or_(
            User.username.ilike(f"%{query}%"),
            User.about_me.ilike(f"%{query}%")
        ))
        .limit(5)
    ).all()

    # Search posts
    posts_query = sa.select(Post).where(
        Post.body.ilike(f"%{query}%")
    ).order_by(Post.timestamp.desc())

    posts = db.paginate(
        posts_query,
        page=page,
        per_page=app.config["POSTS_PER_PAGE"],
        error_out=False
    )

    next_url = url_for("search", q=query, page=posts.next_num) if posts.has_next else None
    prev_url = url_for("search", q=query, page=posts.prev_num) if posts.has_prev else None

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "search.html",
            title=_("Search"),
            query=query,
            users=users,
            posts=posts.items,
            next_url=next_url,
            prev_url=prev_url,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/notifications")
@login_required
def notifications():
    """View notifications."""
    page = request.args.get("page", 1, type=int)

    notifs = db.paginate(
        current_user.notifications.select().order_by(Notification.timestamp.desc()),
        page=page,
        per_page=app.config.get("NOTIFICATIONS_PER_PAGE", 20),
        error_out=False,
    )

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "notifications.html",
            title=_("Notifications"),
            notifications=notifs.items,
            next_url=url_for("notifications", page=notifs.next_num) if notifs.has_next else None,
            prev_url=url_for("notifications", page=notifs.prev_num) if notifs.has_prev else None,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/notifications/mark_read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = db.session.get(Notification, notification_id)
    if notification and notification.user_id == current_user.id:
        notification.read = True
        db.session.commit()
    return jsonify({"success": True})


@app.route("/notifications/unread_count")
@login_required
def unread_notification_count():
    """Get unread notification count (for AJAX)."""
    return jsonify({"count": current_user.unread_notification_count()})


@app.route("/favicon.ico")
def favicon():
    """Serve favicon."""
    return send_from_directory(
        os.path.join(app.root_path, "static", "images"),
        "logo32.png",
        mimetype="image/png",
    )


@app.route("/reset_password_request", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def reset_password_request():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
            audit_logger.log_password_reset(form.email.data, request.remote_addr)
        flash(
            _(
                "If an account matches your email, we'll send password reset instructions."
            )
        )
        return redirect(url_for("login"))

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "reset_password_request.html",
            title=_("Reset Password"),
            form=form,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_("Your password has been reset."))
        return redirect(url_for("login"))

    nonce = generate_nonce()
    response = make_response(
        render_template(
            "reset_password.html",
            form=form,
            nonce=nonce,
        )
    )
    return add_security_headers(response, nonce)
