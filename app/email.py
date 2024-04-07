from app import app, mail
from flask import render_template, url_for
from flask_babel import _
from flask_mail import Message
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error("Failed to send email", exc_info=e)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email(app, msg=msg)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    url = url_for("reset_password", token=token, _external=True).split(",")[1]
    send_email(
        _("[SWESphere] Reset Your Password"),
        sender=app.config["ADMINS"][0],
        recipients=[user.email],
        text_body=render_template("email/reset_password.txt", user=user, url=url),
        html_body=render_template("email/reset_password.html", user=user, url=url),
    )
