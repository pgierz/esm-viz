from flask import Flask, render_template, request, session, redirect, url_for, escape
from flask_login import LoginManager, login_required, login_user, logout_user
from simplepam import authenticate


# Holoviz
import panel as pn

# Bokeh Imports
from bokeh.embed import file_html
from bokeh.resources import CDN

# Python Standard Library
import json
import os


# from esm_viz.visualization.general import General

# Queue stuff:
# general = General(
#        user="a270077",
#        host="mistral.dkrz.de",
#        basedir="/work/ba0989/a270077/AWICM_PISM/LGM_011",
#        coupling=True,
#        storage_prefix="/isibhv/projects/paleo_work/pgierz/viz_test"
#        )

# TODO: This probably should go somewhere else...
def panel_to_html(panel_obj):
    return file_html(panel_obj.get_root(), CDN)


app = Flask(__name__, template_folder=os.path.abspath("static/templates"))
app.secret_key = "!098abctheowlisfluffyxyz123+"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(object):
    def __init__(self, username, password):
        self.authenticated = authenticate(username, password)
        self.id = self.name = username

    def is_authenticated(self):
        return self.authenticated

    def get_id(self):
        return self.id

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


@login_manager.user_loader
def user_loader(user_id):
    user = User(user_id, session["psw"])
    if user.is_authenticated():
        return user
    return None


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["uname"]
        password = request.form["psw"]
        user = User(username, password)

        if user.is_authenticated():
            login_user(user)
            session["psw"] = password
            return redirect(url_for("dashboard"))
    return render_template("login.html", bad_auth=True)


@app.route("/logout")
def logout():
    # remove the username from the session if it's there
    logout_user()
    return redirect(url_for("index"))


# TODO: This should just be part of the dashboard
@app.route("/queue")
def queue():
    return render_template("queue.html")


@app.route("/public_sims")
def public_sims():
    return render_template("public_sims.html")

# With debug=True, Flask server will auto-reload
# when there are code changes
if __name__ == "__main__":
    app.run(port=8888, debug=True)
