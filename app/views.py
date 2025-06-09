from app import app, db
from flask import render_template, request, redirect
from app.models import User

@app.route("/")
def default():
    return redirect("/login")

@app.get("/login")
def login_get():
    return render_template("login.html")

@app.post("/login")
def login_post():
    form = request.form
    user = User.query.filter_by(login=form['login']).first()
    if user.check_password(form['password']):
        return redirect("/home")
    else:
        return render_template("login.html")


@app.get("/register")
def register_get():
    return render_template("register.html")

@app.post("/register")
def register_post():
    form = request.form
    user = User(
        login = form['login'],
        email = form['email']
    )
    user.set_password(form['password'])
    db.session.add(user)
    db.session.commit()
    print(user)
    return render_template("login.html")

@app.get("/home")
def home():
    return render_template("home.html")