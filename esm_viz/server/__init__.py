from flask import Flask, render_template, request, session, redirect, url_for, escape
from flask_login import LoginManager, login_required, login_user, logout_user
from simplepam import authenticate


# Holoviz
import panel as pn

# Bokeh Imports
from bokeh.embed import file_html, components
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

def panel_to_components(panel_obj):
    return components(panel_obj.get_root())


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
@app.route("/queue", methods=["GET", "POST"])
def queue():
    # TODO: Retrieve previously generated queues from db
    if request.method == "POST":
        batch_sys = request.form["batch_sys"]
        is_remote = request.form["is_remote"]
        username = request.form["uname"] if is_remote else None
        host = request.form["host"] if is_remote else None
        queue = models.QueueModel(batch_sys, is_remote, username, host)

    batch_sys_widget = pn.widgets.Select(name="Batch System", options=["slurm",])
    is_remote_widget = pn.widgets.Checkbox(name="Remote")
    uname_widget = pn.widgets.TextInput(name='Username', placeholder='User', disabled=(not is_remote_widget.value))
    host_widget = pn.widgets.TextInput(name='Compute Host', placeholder='Host', disabled=(not is_remote_widget.value))
    submit_widget = pn.widgets.Button(name="Submit")
    form = pn.Column(batch_sys_widget, is_remote_widget, uname_widget, host_widget, submit_widget)
    script, div = panel_to_components(form)
    return render_template("queue.html", form=div)#, script=script)


@app.route("/public_sims")
def public_sims():
    return render_template("public_sims.html")

# With debug=True, Flask server will auto-reload
# when there are code changes
if __name__ == "__main__":
    app.run(port=8888, debug=True)
