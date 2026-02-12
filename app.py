import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from sqlalchemy import text
from dotenv import load_dotenv

from helpers import login_required

#new SQL database
from flask_sqlalchemy import SQLAlchemy

def get_username():
    if session.get("user_id"):
        users = db.session.execute(
            text("SELECT * FROM users WHERE id = :u"), 
            {"u": session["user_id"]}
        ).mappings().all()
    else:
        return -1

        if len(users) == 0:
            session.clear()
            return -1
    return users[0]["username"]


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

load_dotenv()
#path string to 'neon' database in Environment Variable

database_url = os.getenv('DATABASE_URL')


if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
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
    if get_username()!=-1:
        return render_template("index.html", username=get_username())
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

        result = db.session.execute(
            text("SELECT * FROM users WHERE username = :u"), 
            {"u": username}
        ).mappings().all()

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

        users = db.session.execute(
            text("SELECT * FROM users WHERE username = :u"), 
            {"u": username}
        ).mappings().all()

        if len(users) != 0:
            return render_template("signup.html", message="Username is taken")

        hashed_password = generate_password_hash(password)
        
        db.session.execute(
            text("INSERT INTO users (username, password) VALUES (:u, :p)"),
            {"u": username, "p": hashed_password}
        )
        
        db.session.commit()

        new_user = db.session.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username}
        ).mappings().all()

        session["user_id"] = new_user[0]["id"]
        return redirect("/")

@app.route("/myprofile")
@login_required
def myprofile():
    return render_template("myprofile.html", username = get_username())


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")

@app.route("/chats")
@login_required
def chats():
    friends_result = db.session.execute(
        text("SELECT * FROM friends WHERE friend1 = :u OR friend2 = :u"),
        {"u": session["user_id"]}
    ).mappings().all()

    friends = [dict(row) for row in friends_result]

    for row in friends:
        if row["friend2"] == session["user_id"]:
            row["friend2"], row["friend1"] = row["friend1"], row["friend2"]

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

    if request.method == "POST":
        new_message_text = request.form.get("message")

        db.session.execute(
            text("INSERT INTO messages (sender, receiver, message, date) VALUES (:s, :r, :m, :d)"),
            {"s": user_id, "r": friend_id, "m": new_message_text, "d": time()}
        )
        db.session.commit()
            
        return redirect(f'/chat?friend={friend_id}')



    query_messages = text("""
        SELECT * FROM messages 
        WHERE (sender = :u AND receiver = :f) 
           OR (sender = :f AND receiver = :u)
        ORDER BY id ASC
    """)
    
    messages_res = db.session.execute(query_messages, {"u": user_id, "f": friend_id}).mappings().all()
    messages = [dict(row) for row in messages_res]

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

        search_pattern = f"%{username_query}%"
        
        friends_res = db.session.execute(
            text("SELECT * FROM users WHERE username ILIKE :u AND id != :me"),
            {"u": search_pattern, "me": session["user_id"]}
        ).mappings().all()
        friends = [dict(row) for row in friends_res]

        friends_added = db.session.execute(
            text("SELECT * FROM friends WHERE friend1 = :me OR friend2 = :me"),
            {"me": session["user_id"]}
        ).mappings().all()
        print(friends_added)
        friends_added = [row["friend1"] for row in friends_added] + [row["friend2"] for row in friends_added]

        print(friends_added)
        print(friends)
        friends = [friend for friend in friends if friend["id"] not in friends_added]
        print(friends)

        return render_template("addfriend.html", friends=friends)       

@app.route("/add")
@login_required
def add():
    friend_id = request.args.get("friend")
    user_id = session["user_id"]

    if friend_id:
        
        db.session.execute(
            text("INSERT INTO friends (friend1, friend2) VALUES (:f1, :f2)"),
            {"f1": user_id, "f2": friend_id}
        )
    
        db.session.commit()
        
    return redirect("/chats")

    
