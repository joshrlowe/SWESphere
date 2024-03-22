from app import app
from flask import render_template

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Josh'}
    posts = [
        {
            'author': {'username': 'user1'},
            'body': 'This is user1\'s first post!'
        },
        {
            'author': {'username': 'user2'},
            'body': 'This is user2\'s first post!'
        }
    ]
    return render_template('index.html', title='Home', user=user, posts=posts)