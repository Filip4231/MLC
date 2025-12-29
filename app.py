import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from sqlalchemy import text

from helpers import login_required

#new SQL database
from flask_sqlalchemy import SQLAlchemy

def time():
    now = str(datetime.now())
    now = now[0:19]
    hour = now[-8:]
    date=now[0:10]
    return hour + " " + date


app = Flask(__name__)

if __name__ == '__main__':
    app.run()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#NOWA SQL

database_url = os.getenv('DATABASE_URL', 'sqlite:///mlc.db')

# WAŻNE: Render/Neon używają 'postgresql://', ale SQLAlchemy czasem wymaga 'postgresql+psycopg2://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#NOWA SQL
#db = SQL("sqlite:///mlc.db")

db = SQLAlchemy(app)

with app.app_context():
    # PostgreSQL używa SERIAL dla automatycznego ID, SQLite używa INTEGER PRIMARY KEY
    id_type = "SERIAL" if "postgresql" in database_url else "INTEGER"
    
    db.session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type} PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    """))
    
    db.session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS friends (
            id {id_type} PRIMARY KEY,
            friend1 INTEGER NOT NULL REFERENCES users(id),
            friend2 INTEGER NOT NULL REFERENCES users(id)
        );
    """))
    
    db.session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS messages (
            id {id_type} PRIMARY KEY,
            sender INTEGER NOT NULL REFERENCES users(id),
            receiver INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL,
            date TEXT NOT NULL
        );
    """))
    db.session.commit()



@app.route("/")
def index():
    if session.get("user_id"):
        # Używamy :u jako placeholder, a w słowniku podajemy session["user_id"]
        users = db.session.execute(
            text("SELECT * FROM users WHERE id = :u"), 
            {"u": session["user_id"]}
        ).mappings().all()

        if len(users) == 0:
            session.clear()
            return render_template("index.html")
        
        # users[0] to teraz słownik-podobny obiekt, więc username=users[0]["username"] zadziała
        return render_template("index.html", username=users[0]["username"])
    
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return render_template("login.html", message="Please provide username")
        if not password:
            return render_template("login.html", message="Please provide password")

        # Zamiana db.execute na SQLAlchemy session execute
        result = db.session.execute(
            text("SELECT * FROM users WHERE username = :u"), 
            {"u": username}
        ).mappings().all()

        # result zachowuje się teraz jak lista słowników (tak jak w CS50)
        if len(result) == 0:
            return render_template("login.html", message="Wrong username and/or password")

        user = result[0]

        if not check_password_hash(user["password"], password):
            return render_template("login.html", message="Wrong username and/or password")
        
        session["user_id"] = user["id"]
        return redirect("/")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return render_template("signup.html", message="Please provide username")
        if not password or not confirmation:
            return render_template("signup.html", message="Please provide password and confirm password")

        if password != confirmation:
            return render_template("signup.html", message="Passwords are not identical")

        # Sprawdzanie czy użytkownik istnieje
        users = db.session.execute(
            text("SELECT * FROM users WHERE username = :u"), 
            {"u": username}
        ).mappings().all()

        if len(users) != 0:
            return render_template("signup.html", message="Username is taken")

        # Rejestracja nowego użytkownika
        hashed_password = generate_password_hash(password)
        
        db.session.execute(
            text("INSERT INTO users (username, password) VALUES (:u, :p)"),
            {"u": username, "p": hashed_password}
        )
        
        # BARDZO WAŻNE: W SQLAlchemy musisz zatwierdzić transakcję
        db.session.commit()

        # Pobieramy ID nowo stworzonego użytkownika
        new_user = db.session.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username}
        ).mappings().all()

        session["user_id"] = new_user[0]["id"]
        return redirect("/")

@app.route("/myprofile")
@login_required
def myprofile():
    return render_template("myprofile.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")

@app.route("/chats")
@login_required
def chats():
    # 1. Pobieramy listę znajomych
    friends_result = db.session.execute(
        text("SELECT * FROM friends WHERE friend1 = :u OR friend2 = :u"),
        {"u": session["user_id"]}
    ).mappings().all()

    # Zamieniamy na listę zwykłych słowników, żeby móc je modyfikować
    friends = [dict(row) for row in friends_result]

    for row in friends:
        # 2. Logika zamiany (uproszczona): chcemy, aby friend2 zawsze był "tym drugim"
        if row["friend2"] == session["user_id"]:
            row["friend2"], row["friend1"] = row["friend1"], row["friend2"]

        # 3. Pobieramy nazwę użytkownika znajomego
        user_result = db.session.execute(
            text("SELECT username FROM users WHERE id = :id"),
            {"id": row["friend2"]}
        ).mappings().all()

        if user_result:
            row["friend_username"] = user_result[0]["username"]

    return render_template("chats.html", friends=friends)


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    friend_id = request.args.get("friend")
    user_id = session["user_id"]

    if not friend_id:
        return redirect("/chats")

    # 1. Pobieramy wiadomości (używamy nazwanych parametrów :u i :f dla czytelności)
    query_messages = text("""
        SELECT * FROM messages 
        WHERE (sender = :u AND receiver = :f) 
           OR (sender = :f AND receiver = :u)
        ORDER BY id ASC
    """)
    
    messages_res = db.session.execute(query_messages, {"u": user_id, "f": friend_id}).mappings().all()
    messages = [dict(row) for row in messages_res]

    # 2. Obsługa wysyłania nowej wiadomości (metoda POST / form)
    new_message_text = request.form.get("message")
    if new_message_text:
        # Prosta walidacja: sprawdź czy wiadomość nie jest identyczna z ostatnią (ochrona przed odświeżaniem strony)
        is_duplicate = False
        if len(messages) > 0 and messages[-1]["message"] == new_message_text:
            is_duplicate = True

        if not is_duplicate:
            db.session.execute(
                text("INSERT INTO messages (sender, receiver, message, date) VALUES (:s, :r, :m, :d)"),
                {"s": user_id, "r": friend_id, "m": new_message_text, "d": time()}
            )
            db.session.commit() # Zapisujemy w bazie Neon
            
            # Odświeżamy listę wiadomości po dodaniu nowej
            messages_res = db.session.execute(query_messages, {"u": user_id, "f": friend_id}).mappings().all()
            messages = [dict(row) for row in messages_res]

    # 3. Pobieramy nazwy użytkowników
    friend_res = db.session.execute(text("SELECT username FROM users WHERE id = :id"), {"id": friend_id}).mappings().all()
    user_res = db.session.execute(text("SELECT username FROM users WHERE id = :id"), {"id": user_id}).mappings().all()

    if not friend_res:
        return redirect("/chats")

    friendname = friend_res[0]["username"]
    username = user_res[0]["username"]

    return render_template(
        "chat.html", 
        friend1_username=username, 
        friend2_username=friendname, 
        friend1=user_id, 
        friend2=friend_id, 
        messages=messages
    )


@app.route("/addfriend", methods=["POST", "GET"])
@login_required
def addfriend():
    if request.method == "GET":
        return render_template("addfriend.html")
    else:
        username_query = request.form.get("username")
        if not username_query:
            return render_template("addfriend.html", message="Provide friend's username")

        # Używamy ILIKE dla wyszukiwania ignorującego wielkość liter
        # % w PostgreSQL dodajemy do wartości parametru, a nie w samym zapytaniu SQL
        search_pattern = f"%{username_query}%"
        
        friends_res = db.session.execute(
            text("SELECT * FROM users WHERE username ILIKE :u AND id != :me"),
            {"u": search_pattern, "me": session["user_id"]}
        ).mappings().all()

        # Konwertujemy na listę słowników, aby szablon Jinja2 mógł łatwo z nich korzystać
        friends = [dict(row) for row in friends_res]

        return render_template("addfriend.html", friends=friends)       

@app.route("/add")
@login_required
def add():
    friend_id = request.args.get("friend")
    user_id = session["user_id"]

    if friend_id:
        # 1. Dodajemy relację do tabeli friends
        db.session.execute(
            text("INSERT INTO friends (friend1, friend2) VALUES (:f1, :f2)"),
            {"f1": user_id, "f2": friend_id}
        )
        
        # 2. Zatwierdzamy zmiany w bazie danych
        db.session.commit()
        
    return redirect("/chats")

    
