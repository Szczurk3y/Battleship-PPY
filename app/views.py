
from app import app, db
from flask import render_template, request, redirect, session, flash, jsonify, send_file
from app.models import User
import random
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

EMPTY = ""
SIZE = 10

def create_board():
    return [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]

def place_ship(board, length):
    directions = [(0, 1), (1, 0)]
    while True:
        x = random.randint(0, SIZE - 1)
        y = random.randint(0, SIZE - 1)
        dx, dy = random.choice(directions)
        coords = []
        for i in range(length):
            nx = x + dx * i
            ny = y + dy * i
            if 0 <= nx < SIZE and 0 <= ny < SIZE and board[nx][ny] == EMPTY:
                coords.append((nx, ny))
            else:
                break
        if len(coords) == length:
            for cx, cy in coords:
                board[cx][cy] = "S"
            return coords

def is_winner(board):
    return all(cell != "S" for row in board for cell in row)

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
        user = User(login=form['login'], email=form['email'])
        user.set_password(form['password'])
        db.session.add(user)
        db.session.commit()
        return render_template("login.html")

@app.get("/home")
def home():
    if 'user' in session:
        return render_template("home.html")
    else:
        return redirect("/login")

@app.get("/home/statistics")
def statistics():
    if 'user' in session:
        user = User.query.get(session['user'])
        return render_template("statistics.html", games_won=user.games_won, games_lost=user.games_lost)
    else:
        return redirect("/login")

@app.get("/home/settings")
def settings():
    if 'user' in session:
        return render_template("settings.html")
    else:
        return redirect("/login")

@app.route('/logout-user', methods=['POST', 'GET'])
def logout_user():
    session.pop('user', None)
    return redirect("/login")


@app.get('/home/game')
def game():
    if 'user' in session:
        size = session.get("board_size", 10)
        board = [["" for _ in range(size)] for _ in range(size)]
        return render_template("game.html", board=board)
    else:
        return redirect("/login")



@app.post("/save-settings")
def save_settings():
    board_size = int(request.form.get("board_size", 10))
    fleet_raw = request.form.get("fleet", "4,3,2,2")
    fleet = [int(x) for x in fleet_raw.split(",")]

    session["board_size"] = board_size
    session["fleet"] = fleet
    flash("Ustawienia zapisane!")
    return redirect("/home/settings")

@app.route("/api/init-game", methods=["POST"])
def init_game():
    board_size = session.get("board_size", 10)
    fleet = session.get("fleet", [4, 3, 2, 2])

    def create_board(size):
        return [["" for _ in range(size)] for _ in range(size)]

    def place_ship(board, length, size):
        directions = [(0, 1), (1, 0)]
        max_attempts = 1000

        for _ in range(max_attempts):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            dx, dy = random.choice(directions)
            coords = []

            for i in range(length):
                nx = x + dx * i
                ny = y + dy * i
                if 0 <= nx < size and 0 <= ny < size and board[nx][ny] == "":
                    coords.append((nx, ny))
                else:
                    break

            if len(coords) != length:
                continue

            #blokowanie mozliwosci tworzenia statkow obok siebie
            collision = False
            for cx, cy in coords:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < size and 0 <= ny < size:
                            if board[nx][ny] == "S" and (nx, ny) not in coords:
                                collision = True
            if collision:
                continue

            for cx, cy in coords:
                board[cx][cy] = "S"
            return coords

        raise RuntimeError("Nie udało się rozmieścić statku po wielu próbach.")

    player_board = create_board(board_size)
    bot_board = create_board(board_size)
    for l in fleet:
        place_ship(bot_board, l, board_size)

    session['bot_board'] = bot_board
    session['player_board'] = player_board
    session['ships_to_place'] = fleet.copy()
    session['board_size'] = board_size

    return jsonify({"success": True})


@app.route("/api/place-ship", methods=["POST"])
def place_player_ship():
    data = request.get_json()
    coords = data.get("coords")
    board = session.get("player_board")
    ships_left = session.get("ships_to_place")

    if not board or not coords or not ships_left:
        return jsonify({"error": "Brak danych w sesji."}), 400

    board_size = len(board)

    if len(coords) != ships_left[0]:
        return jsonify({"error": f"Musisz ustawić statek długości {ships_left[0]}"}), 400

    xs = [x for x, y in coords]
    ys = [y for x, y in coords]
    if not (all(x == xs[0] for x in xs) or all(y == ys[0] for y in ys)):
        return jsonify({"error": "Statek musi być w jednej linii"}), 400

    #brak dotyku innych statkow
    for x, y in coords:
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_size and 0 <= ny < board_size:
                    if board[nx][ny] == "S" and (nx, ny) not in coords:
                        return jsonify({"error": "Statki nie mogą się stykać – nawet rogami."}), 400

    #sprawdzenie czy puste
    for x, y in coords:
        if not (0 <= x < board_size and 0 <= y < board_size) or board[x][y] != "":
            return jsonify({"error": "Nieprawidłowa pozycja statku"}), 400

    for x, y in coords:
        board[x][y] = "S"

    ships_left.pop(0)
    session['player_board'] = board
    session['ships_to_place'] = ships_left

    return jsonify({"success": True, "remaining": ships_left})

@app.route("/api/shoot", methods=["POST"])
def shoot():
    data = request.get_json()
    x, y = data.get("x"), data.get("y")

    bot_board = session.get("bot_board")
    player_board = session.get("player_board")
    user_id = session.get("user")

    if not bot_board or not player_board or user_id is None:
        return jsonify({"error": "Brak danych gry."}), 400

    if bot_board[x][y] in ("X", "O"):
        return jsonify({"error": "Już strzelono tutaj!"}), 400

    if bot_board[x][y] == "S":
        bot_board[x][y] = "X"
        player_hit = True
    else:
        bot_board[x][y] = "O"
        player_hit = False

    if is_winner(bot_board):
        user = User.query.get(user_id)
        user.games_won += 1
        db.session.commit()
        return jsonify({"player_hit": player_hit, "winner": "player"})

    board_size = len(player_board)
    while True:
        bx = random.randint(0, board_size - 1)
        by = random.randint(0, board_size - 1)
        if player_board[bx][by] not in ("X", "O"):
            break

    if player_board[bx][by] == "S":
        player_board[bx][by] = "X"
        bot_hit = True
    else:
        player_board[bx][by] = "O"
        bot_hit = False

    if is_winner(player_board):
        user = User.query.get(user_id)
        user.games_lost += 1
        db.session.commit()
        session["bot_board"] = bot_board
        session["player_board"] = player_board
        return jsonify({
            "player_hit": player_hit,
            "bot_hit": bot_hit,
            "bot_move": [bx, by],
            "winner": "bot"
        })

    session["bot_board"] = bot_board
    session["player_board"] = player_board

    return jsonify({
        "player_hit": player_hit,
        "bot_hit": bot_hit,
        "bot_move": [bx, by]
    })

@app.get("/export-pdf")
def export_pdf():
    if 'user' not in session:
        return redirect("/login")

    user = User.query.get(session['user'])
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "Statystyki gracza")
    c.setFont("Helvetica", 12)
    c.drawString(100, 760, f"Login: {user.login}")
    c.drawString(100, 740, f"Wygrane gry: {user.games_won}")
    c.drawString(100, 720, f"Przegrane gry: {user.games_lost}")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="statystyki.pdf", mimetype='application/pdf')
