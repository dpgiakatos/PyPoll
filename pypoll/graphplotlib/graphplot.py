from http.server import SimpleHTTPRequestHandler
import waitress
import flask
from flask import Flask
from flask_cors import cross_origin
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtWebEngineWidgets import *
import socketserver
import os
import sys
import subprocess
import threading


TCP_PORT = 18940
FLASK_PORT = 18941


class HTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TCPServer:
    def __init__(self):
        self.httpd = ThreadedTCPServer(("", TCP_PORT), HTTPRequestHandler)

    def serve_forever(self):
        os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "build"))
        self.httpd.serve_forever()

    def shutdown(self):
        self.httpd.shutdown()


class Plot(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Plot, self).__init__(*args, **kwargs)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(f"http://localhost:{TCP_PORT}/"))
        self.setCentralWidget(self.browser)


class FlaskServer:
    def __init__(self, graph_file):
        self.app = Flask(__name__)
        self.graph_file = graph_file
        self.endpoints()
        self.server = waitress.create_server(self.app, port=FLASK_PORT)

    def endpoints(self):
        @self.app.route("/")
        @cross_origin()
        def hello_world():
            return flask.send_file(self.graph_file)

    def serve_forever(self):
        self.server.run()

    def shutdown(self):
        self.server.close()


class GraphPlot:
    def __init__(self):
        pass

    def show(self, filename=None):
        cwd = os.getcwd()
        flask_server = FlaskServer(os.path.abspath(filename))
        serve = threading.Thread(target=flask_server.serve_forever)
        serve.daemon = True
        serve.start()
        tcp_server = TCPServer()
        plot = threading.Thread(target=tcp_server.serve_forever)
        plot.daemon = True
        plot.start()
        subprocess.call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphplot.py")])
        tcp_server.shutdown()
        flask_server.shutdown()
        os.chdir(cwd)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Plot()
    window.show()
    app.exec()
