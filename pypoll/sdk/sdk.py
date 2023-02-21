from urllib.parse import urlparse
from http.client import HTTPConnection, HTTPSConnection
from tabulate import tabulate
import requests
import json


class SDK:
    def __init__(self, host):
        if self.__check_https_url(host):
            self.host = f'https://{host}'
        elif self.__check_http_url(host):
            self.host = f'http://{host}'
        else:
            raise Exception("Both HTTP and HTTPS did not load the website, check whether your url is malformed.")
        self.bearer_token = None

    @staticmethod
    def __check_https_url(host):
        HTTPS_URL = f'https://{host}'
        try:
            HTTPS_URL = urlparse(HTTPS_URL)
            connection = HTTPSConnection(HTTPS_URL.netloc, timeout=0.01)
            connection.request('HEAD', HTTPS_URL.path)
            if connection.getresponse():
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    def __check_http_url(host):
        HTTP_URL = f'http://{host}'
        try:
            HTTP_URL = urlparse(HTTP_URL)
            connection = HTTPConnection(HTTP_URL.netloc, timeout=0.01)
            connection.request('HEAD', HTTP_URL.path)
            if connection.getresponse():
                return True
            else:
                return False
        except:
            return False

    def sign_up(self, email, password, first_name, last_name):
        body = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
        res = requests.post(f"{self.host}/auth/signup", json=body)
        print(res.text)

    def sign_in(self, email, password):
        body = {
            "email": email,
            "password": password
        }
        res = requests.post(f"{self.host}/auth/signin", json=body)
        if res.status_code == 200:
            self.bearer_token = f"Bearer {res.json()['access_token']}"
        else:
            print(res.status_code, res.text)

    def get_user_info(self):
        headers = {
            "Authorization": self.bearer_token
        }
        res = requests.get(f"{self.host}/user/get", headers=headers)
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.status_code, res.text)

    def get_all_graphs(self, page=0, items_per_page=10):
        headers = {
            "Authorization": self.bearer_token
        }
        count = requests.get(f"{self.host}/graph/count", headers=headers)
        if items_per_page == "all":
            page = 0
            items_per_page = count.json()["number_of_graphs"]
        body = {
            "page": page,
            "items": items_per_page
        }
        res = requests.get(f"{self.host}/graph/get/all", headers=headers, json=body)
        if res.status_code == 200:
            data = {
                "Id": [],
                "Filename": [],
                "Description": [],
                "Source": [],
                "Graph nodes": [],
                "Graph edges": [],
                "Uploaded date": []
            }
            for item in res.json()["data"]:
                data["Id"].append(item["_id"])
                data["Filename"].append(item["filename"])
                data["Description"].append(item["description"])
                data["Source"].append(item["source"])
                data["Graph nodes"].append(item["graph_properties"]["nodes"])
                data["Graph edges"].append(item["graph_properties"]["edges"])
                data["Uploaded date"].append(item["uploadDate"])
            print(tabulate(data, headers="keys"))
        else:
            print(res.status_code, res.text)

    def get_graph(self, graph_id):
        res = requests.get(f"{self.host}/graph/get/{graph_id}")
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.status_code, res.text)

    def delete_graph(self, graph_id):
        headers = {
            "Authorization": self.bearer_token
        }
        res = requests.get(f"{self.host}/graph/delete/{graph_id}", headers=headers)
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.status_code, res.text)

    def upload_graph(self, filename):
        headers = {
            "Authorization": self.bearer_token
        }
        files = {
            "file": open(filename, "rb")
        }
        metadata_filename = filename.split(".")
        metadata_filename[-1] = "metadata.json"
        metadata_file = open(".".join(metadata_filename), "r", encoding="utf8")
        body = json.load(metadata_file)
        for key in body:
            body[key] = str(body[key])
        res = requests.post("http://localhost:8000/graph/upload", files=files, params=body, headers=headers)
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.status_code, res.text)
