# Hello, Flask!
from flask import Flask, render_template, request


# Queue stuff:


app = Flask(__name__)

# Index page, no args
@app.route('/')
def index():
    name = request.args.get("name")
    if name == None:
        name = "Paul"
        return render_template("index.html", name=name)


@app.route('/queue')
def queue():
    return "This is the queue!!"

# With debug=True, Flask server will auto-reload 
# when there are code changes
if __name__ == '__main__':
    app.run(port=8888, debug=True)
