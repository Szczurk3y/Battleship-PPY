from app import app, db
from flask import render_template, request, redirect, session, flash
from app.models import User

@app.errorhandler(404)
def page_not_found(e):
    return redirect("/login")

@app.get("/login")
def login_get():
    return render_template("login.html")

@app.post("/login")
def login_post():
    form = request.form
    user = User.query.filter_by(login=form['login']).first()
    if not user:
        flash('Użytkownik nie istnieje')
        return redirect("/login")
    else:
        if user.check_password(form['password']):
            session['user'] = user.id
            return redirect("/home")
        else:
            flash('Niepoprawne hasło')
            return redirect("/login")

@app.get("/register")
def register_get():
    return render_template("register.html")

@app.post("/register")
def register_post():
    form = request.form
    user = User.query.filter_by(login=form['login']).first()
    if user:
        flash('Użytkownik o takim loginie już istnieje')
        return redirect("/register")
    else:
        user = User(
            login = form['login'],
            email = form['email']
        )
        user.set_password(form['password'])
        db.session.add(user)
        db.session.commit()
        return render_template("login.html")

@app.get("/home")
def home():
    user_id = None
    if 'user' in session:
        user_id = session['user']
        return render_template("home.html")
    else:
        return redirect("/login")

@app.get("/home/statistics")
def statistics():
    user_id = None
    if 'user' in session:
        user_id = session['user']
        return render_template("statistics.html")
    else:
        return redirect("/login")
    
@app.get("/home/settings")
def settings():
    user_id = None
    if 'user' in session:
        user_id = session['user']
        return render_template("settings.html")
    else:
        return redirect("/login")

@app.route('/logout-user', methods=['POST', 'GET'])
def logout_user():
    session.pop('user', None)
    return redirect("/login")
    
