import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///mlc.db")


@app.route("/")
def index():
    if session.get("user_id"):
        users = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])
        if len(users) == 0:
            session.clear()
            return render_template("index.html")
        return render_template("index.html", username=users[0]["username"])
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        if not request.form.get("username"):
            return render_template("login.html", massage="Please provide username")
        if not request.form.get("password"):
            return render_template("login.html", massage="Please provide password")

        user = db.execute("SELECT * FROM users WHERE username=?", request.form.get("username"))
        if len(user) == 0:
            return render_template("login.html", massage="Wrong username and/or password")

        if not check_password_hash(user[0]["password"], request.form.get("password")):
            return render_template("login.html", massage="Wrong username and/or password")
        
        session["user_id"] = user[0]["id"]
        return redirect("/")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        if not request.form.get("username"):
            return render_template("signup.html", massage="Please provide username")
        if not request.form.get("password") or not request.form.get("confirmation"):
            return render_template("signup.html", massage="Please provide password and confirm password")
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("signup.html", massage="Passwords are not identical")

        users = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("username"))
        print(users)
        if len(users) != 0:
            return render_template("signup.html", massage="Username is taken")

        print(request.form.get("username") + " " + generate_password_hash(request.form.get("password")))
        db.execute("INSERT INTO users(username, password) VALUES(?,?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
        users = db.execute("SELECT * FROM users WHERE username=?", request.form.get("username"))
        session["user_id"] = users[0]["id"]
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
    #if request.args.get("friend"):
    #    print(request.args.get("friend"))
    #    massages = db.execute("SELECT * FROM massages WHERE sender=? AND receiver=?", session["user_id"], request.args.get("friend"))
    #    return redirect("chat.html", friend1 = session["user_id"], friend2=request.args.get("friend"), massages=massages)
    #else:
        friends = db.execute("SELECT * FROM friends WHERE friend1=? or friend2=?", session["user_id"], session["user_id"])
        for row in friends:
            if row["friend2"] == session["user_id"]:
                row["friend2"], row["friend1"] = row["friend1"], row["friend2"]

        for row in friends:
            users = db.execute("SELECT * FROM users WHERE id=?", row["friend2"])
            row["friend_username"] = users[0]["username"]

        return render_template("chats.html", friends=friends)


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if not request.args.get("friend"):
        return redirect("/chats")
    else:
        massages = db.execute("SELECT * FROM massages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)", session["user_id"], request.args.get("friend"), request.args.get("friend"), session["user_id"])
        print(massages)
        print(request.args.get("friend"))
        #print(massages[len(massages)-1]["sender"])
        if request.form.get("massage") and (len(massages)==0 or massages[len(massages)-1]["massage"] != request.form.get("massage" or massages[len(massages)-1]["sender"] != request.args.grt("friend"))) :
            print(request.form.get("massage"))
            db.execute("INSERT INTO massages(sender,receiver,massage) VALUES(?,?,?)", session["user_id"], request.args.get("friend"), request.form.get("massage"))

        massages = db.execute("SELECT * FROM massages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)", session["user_id"], request.args.get("friend"), request.args.get("friend"), session["user_id"])
        print(massages)
        print(request.args.get("friend"))
        print(session["user_id"])
        friendname = db.execute("SELECT * FROM users WHERE id=?", request.args.get("friend"))[0]["username"]
        username = db.execute("SELECT * FROM users WHERE id=?", session["user_id"])[0]["username"]
        return render_template("chat.html", friend1_username=username, friend2_username=friendname, friend1=session["user_id"], friend2=request.args.get("friend"), massages=massages)



@app.route("/addfriend", methods=["POST", "GET"])
@login_required
def addfriend():
    if request.method == "GET":
        print("a")
        return render_template("addfriend.html")
    else:
        if not request.form.get("username"):
            return render_template("addfriend.html", massage="Provide friend's username")
        friends = db.execute("SELECT * FROM users WHERE username LIKE ? AND id!=?", "%" + request.form.get("username") + "%", session["user_id"])
        print(friends)
        return render_template("addfriend.html", friends=friends)
        

@app.route("/add")
def add():
    print("\n\n\n")
    print(request.args.get("friend"))
    db.execute("INSERT INTO friends(friend1, friend2) VALUES (?, ?)", session["user_id"], request.args.get("friend"))
    return redirect("/chats")

    
