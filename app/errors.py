from app import app, db
from flask import render_template

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
