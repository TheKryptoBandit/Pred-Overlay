# server.py
from flask import Flask, jsonify, render_template, request
import os
import sys

active_build = None

def run_server():
    """Function to create and run the Flask app."""
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        app = Flask(__name__, template_folder=template_folder)
    else:
        app = Flask(__name__)

    def overlay():
        return render_template('index.html')

    def get_build():
        if active_build:
            return jsonify(active_build)
        else:
            return jsonify({"hero": None, "items": [], "crest": None})

    def set_build():
        global active_build
        active_build = request.json
        if active_build and active_build.get('hero'):
             print(f"Received new build for: {active_build.get('hero').get('name')}")
        return jsonify({"status": "success"})

    app.add_url_rule('/', 'overlay', overlay)
    app.add_url_rule('/api/get_build', 'get_build', get_build)
    app.add_url_rule('/api/set_build', 'set_build', set_build, methods=['POST'])

    # Run the app in production mode (no debug messages)
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()