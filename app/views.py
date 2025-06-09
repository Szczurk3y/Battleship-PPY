from app import app
from flask import render_template, request

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.post("/register")
def register_user():
    login = request.form["login"]
    password = request.form["password"]
    email = request.form["email"]
    print(login)
    return render_template("login.html")

@app.route("/home")
def home():
    return render_template("home.html")