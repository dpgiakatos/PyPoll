from poll.dblib import MongoDB
import networkx as nx
from tqdm import tqdm
from scipy.sparse import identity
from scipy.sparse.linalg import inv
import numpy as np
import xml.etree.ElementTree as ET
from itertools import compress, combinations
from collections import Counter
import json


class Graph:
    def __init__(self):
        self.mongodb = None
        self.graph = nx.Graph()
        self.metadata = dict()

    def __add_node(self, user, follows_users, keep_all_users):
        node_created = False
        user_follows_user = []
        for follows_user in follows_users:
            user_follows_user.append(self.mongodb.exist_username(follows_user, user))
        follows_user_by_selector = list(compress(follows_users, user_follows_user))
        if len(follows_user_by_selector):
            self.graph.add_node(user, follows=",".join(follows_user_by_selector))
            node_created = True
        elif keep_all_users:
            self.graph.add_node(user, follows="none")
            node_created = True
        return node_created

    def create_mention_graph_from_mongodb(self, users, hashtag, mongodb, options):
        if type(mongodb) != MongoDB:
            raise Exception("The DB must be MongoDB")
        usernames = [item["username"] for item in users]
        self.mongodb: MongoDB = mongodb
        count_documents = mongodb.count_documents(hashtag)
        if "subgraph_from_latest" in options:
            percentage_of_subgraph = np.round(count_documents * options["subgraph_from_latest"])
        else:
            percentage_of_subgraph = count_documents
        cursor = self.mongodb.get_all(hashtag)
        for index, document in tqdm(enumerate(cursor)):
            if index >= percentage_of_subgraph:
                break
            if "entities" not in document or "mentions" not in document["entities"]:
                continue
            user_created = self.__add_node(document["author"]["username"], usernames, options["keep_all_users"])
            for mention_user in document["entities"]["mentions"]:
                mention_user_created = self.__add_node(mention_user["username"], usernames, options["keep_all_users"])
                if user_created and mention_user_created:
                    edge = (document["author"]["username"], mention_user["username"])
                    if self.graph.has_edge(*edge):
                        self.graph[edge[0]][edge[1]]["weight"] += 1
                    else:
                        self.graph.add_edge(edge[0], edge[1], weight=1)
        self.graph.remove_nodes_from(list(nx.isolates(self.graph)))
        self.graph = self.graph.subgraph(max(nx.connected_components(self.graph), key=len)).copy()
        if options["remove_leaf_nodes"]:
            self.graph.remove_nodes_from([node for node, degree in dict(self.graph.degree()).items() if degree == 1])
        self.metadata["source"] = {"number_of_documents": count_documents}
        self.metadata["entities"] = users
        self.metadata["date"] = {
            "from": mongodb.get_created_date(hashtag, "ASC").strftime("%Y-%m-%d"),
            "until": mongodb.get_created_date(hashtag, "DES").strftime("%Y-%m-%d")
        }

    def save_as(self, filename):
        filetype = filename.split(".")[-1]
        if filetype != "gexf":
            raise Exception("The file must be gexf type")
        nx.write_gexf(self.graph, filename, version="1.2draft")
        self.__metadata_save_as(filename)

    def __metadata_save_as(self, filename):
        metadata_filename = filename.split(".")
        metadata_filename[-1] = "metadata.json"
        metadata_file = open(".".join(metadata_filename), "w", encoding="utf8")
        json.dump(self.metadata, metadata_file, ensure_ascii=False)

    def load(self, filename):
        self.graph = nx.read_gexf(filename)
        metadata_filename = filename.split(".")
        metadata_filename[-1] = "metadata.json"
        metadata_file = open(".".join(metadata_filename), "r", encoding="utf8")
        self.metadata = json.load(metadata_file)

    def get_graph(self):
        return self.graph

    def get_number_of_nodes(self):
        return self.graph.number_of_nodes()

    def get_number_of_edges(self):
        return self.graph.number_of_edges()

    def get_polarization_index(self, user_A, user_B):
        internal_opinion = []
        for node in self.graph.nodes(data=True):
            if node[1]["follows"] == user_A:
                internal_opinion.append([1])
            elif node[1]["follows"] == user_B:
                internal_opinion.append([-1])
            else:
                internal_opinion.append([0])
        laplacian = nx.laplacian_matrix(self.graph)
        identity_matrix = identity(self.get_number_of_nodes())
        inverse = inv(laplacian + identity_matrix)
        expressed_opinion = inverse.dot(internal_opinion)
        return np.power(np.linalg.norm(expressed_opinion), 2) / self.get_number_of_nodes()

    def set_metadata(self, source, title):
        if source == "Twitter":
            self.metadata["source"]["name"] = source
            self.metadata["source"]["label_of_documents"] = "Tweets"
        self.metadata["graph_properties"] = {
            "nodes": self.get_number_of_nodes(),
            "edges": self.get_number_of_edges(),
            "polarization_index": dict()
        }
        pairs = list(combinations([item["username"] for item in self.metadata["entities"]], 2))
        for pair in pairs:
            self.metadata["graph_properties"]["polarization_index"]["|".join(pair)] = self.get_polarization_index(
                pair[0], pair[1])
        self.metadata["title"] = title

    def set_metadata_entities(self, entities):
        self.metadata["entities"] = entities

    def __set_combinations_to_metadata_entities(self, follows_color):
        usernames = [self.metadata["entities"][i]["username"] for i in range(len(self.metadata["entities"]))]
        full_names = {self.metadata["entities"][i]["username"]: self.metadata["entities"][i]["full_name"] for i in
                      range(len(self.metadata["entities"]))}
        for key in follows_color:
            if key in usernames:
                usernames.remove(key)
            else:
                self.metadata["entities"].append({
                    "username": key,
                    "full_name": ",".join([full_names[username] for username in key.split(",")]),
                    "color": follows_color[key]
                })

    def create_layout(self, save_to_file: str, node_size="2.0", scale=1000):
        filetype = save_to_file.split(".")[-1]
        if filetype != "gexf":
            raise Exception("The file must be gexf type")
        print("Creating layout...")
        follows_combinations = []
        follows_color = {item["username"]: item["color"] for item in self.metadata["entities"]}
        for i in range(2, len(follows_color) + 1):
            follows_combinations += list(combinations(follows_color.keys(), i))
        for item in follows_combinations:
            color = {"r": 0, "g": 0, "b": 0, "a": 0}
            for key in item:
                color = dict(Counter(color) + Counter(follows_color[key]))
            for i in color:
                color[i] /= len(item)
                if i == "a":
                    color[i] = round(color[i], 1)
                else:
                    color[i] = round(color[i])
            follows_color[",".join(item)] = color.copy()
        self.__set_combinations_to_metadata_entities(follows_color)
        for key in follows_color:
            follows_color[key] = {k: str(v) for k, v in follows_color[key].items()}
        pos = nx.spring_layout(self.graph, scale=scale)
        gexf = [line for line in nx.generate_gexf(self.graph, version="1.2draft")]
        tree = ET.ElementTree(ET.fromstringlist(gexf))
        attributes = []
        namespace = "http://www.gexf.net/1.2draft"
        for element in tqdm(tree.iter()):
            if f"{'{' + namespace + '}'}gexf" == element.tag:
                element.set("xmlns:viz", "http://gexf.net/1.3/viz")
            elif f"{'{' + namespace + '}'}attribute" == element.tag:
                attributes.append(element.attrib)
            elif f"{'{' + namespace + '}'}node" == element.tag:
                el_attr = list(list(element)[0])
                for obj in attributes:
                    if obj.get("title") == "follows":
                        get_el_attr = el_attr[int(obj.get("id"))]
                        color = follows_color.get(get_el_attr.attrib.get("value"))
                element.append(element.makeelement("viz:size", dict(value=node_size)))
                node_pos = pos.get(element.attrib.get("id"))
                element.append(element.makeelement("viz:position", dict(x=str(node_pos[0]), y=str(node_pos[1]))))
                element.append(element.makeelement("viz:color", color))
        ET.register_namespace("", namespace)
        tree.write(save_to_file)
        self.__metadata_save_as(save_to_file)
