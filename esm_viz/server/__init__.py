# Flask
from flask import Flask, render_template, request, session, redirect, url_for, escape
from simplepam import authenticate


# Queue stuff:


app = Flask(__name__)
app.secret_key = "!098abctheowlisfluffyxyz123+"


@app.route("/")
def index():
    if "username" in session:
        print(session)
        return "Logged in as %s" % escape(session["username"])
    return "You are not logged in"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if authenticate(str(username), str(password)):
            session["username"] = request.form["username"]
            return redirect(url_for("index"))
        else:
            return "Invalid username/password"
    return """
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    """


@app.route("/logout")
def logout():
    # remove the username from the session if it's there
    session.pop("username", None)
    return redirect(url_for("index"))


# TODO: This should just be part of the dashboard
@app.route("/queue")
def queue():
    return "This is the queue!!"

# With debug=True, Flask server will auto-reload
# when there are code changes
if __name__ == "__main__":
    app.run(port=8888, debug=True)
