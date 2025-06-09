from flask import render_template, request, session, jsonify
from app import app
import random

def generate_empty_board(size=10):
    return [["~" for _ in range(size)] for _ in range(size)]

def place_random_ship(board, length):
    size = len(board)
    while True:
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        horizontal = random.choice([True, False])

        positions = []
        for i in range(length):
            dx = x + i if horizontal else x
            dy = y if not horizontal else y
            if dx >= size or dy >= size or board[dy][dx] != "~":
                break
            positions.append((dy, dx))

        if len(positions) == length:
            for r, c in positions:
                board[r][c] = "S"
            break

def generate_bot_board():
    board = generate_empty_board()
    place_random_ship(board, 4)
    place_random_ship(board, 3)
    place_random_ship(board, 3)
    place_random_ship(board, 2)
    place_random_ship(board, 2)
    place_random_ship(board, 2)
    return board

@app.get("/home/game")
def game():
    if "bot_board" not in session:
        session["bot_board"] = generate_bot_board()
        session["shots"] = []
    
    return render_template("game.html", shots=session["shots"])

@app.route("/home/game/fire", methods=["POST"])
def fire():
    data = request.get_json()
    x, y = int(data["x"]), int(data["y"])
    board = session.get("bot_board")
    shots = session.get("shots", [])

    # already fired?
    if (x, y) in shots:
        return jsonify(hit=False, already=True)

    shots.append((x, y))
    session["shots"] = shots

    hit = board[y][x] == "S"
    return jsonify(hit=hit)