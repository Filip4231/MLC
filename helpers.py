def loggin_required(func):
    def wrapper():
        if session.get("user_id") is None:
            return redirect("/login")