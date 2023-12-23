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
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        print(request.form.get("username") + " " + generate_password_hash(request.form.get("password")))
        db.execute("INSERT INTO users(username, password) VALUES(?,?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
        return redirect("/")

@app.route("/myprofile")
@login_required
def myprofile():
    return render_template("myprofile.html")