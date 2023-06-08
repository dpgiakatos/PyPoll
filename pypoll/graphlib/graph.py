from pypoll.dblib import MongoDB
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
        self.graph = nx.DiGraph()
        self.metadata = dict()

    def __add_node(self, user, options):
        user_follows_user = []
        if "public_metrics" in user:
            followers = user["public_metrics"]["followers_count"]
            following = user["public_metrics"]["following_count"]
            tweet = user["public_metrics"]["tweet_count"]
            listed = user["public_metrics"]["listed_count"]
        else:
            followers = 0
            following = 0
            tweet = 0
            listed = 0
        if "users" in options:
            for follows_user in options["users"]:
                user_follows_user.append(self.mongodb.exist_username(follows_user, user["username"]))
            follows_user_by_selector = list(compress(list(options["users"]), user_follows_user))
            if len(follows_user_by_selector):
                self.graph.add_node(user["username"], follows=",".join(follows_user_by_selector), followers=followers, following=following, tweet=tweet, listed=listed)
            else:
                self.graph.add_node(user["username"], follows="none", followers=followers, following=following, tweet=tweet, listed=listed)
        else:
            self.graph.add_node(user["username"], followers=followers, following=following, tweet=tweet, listed=listed)

    def __add_edge(self, u_of_edge, v_of_edge, created_at):
        edge = (u_of_edge, v_of_edge)
        if self.graph.has_edge(*edge):
            self.graph[edge[0]][edge[1]]["weight"] += 1
        else:
            self.graph.add_edge(edge[0], edge[1], weight=1, created_at=created_at.strftime("%Y-%m-%d %H:%M:%S"))

    def __add_node_from_tweet(self, hashtag, tweet_id, user, options,):
        tweet = self.mongodb.get_tweet(hashtag, tweet_id)
        if tweet is not None:
            self.__add_node(tweet["author"], options)
            self.__add_edge(user, tweet["author"]["username"], tweet["created_at"])

    def create_graph(self, hashtag, mongodb, options):
        if type(mongodb) != MongoDB:
            raise Exception("The DB must be MongoDB")
        self.mongodb: MongoDB = mongodb
        count_documents = mongodb.count_documents(hashtag)
        cursor = self.mongodb.get_all(hashtag)
        for index, document in tqdm(enumerate(cursor), total=count_documents):
            self.__add_node(document["author"], options)
            if options["edge_type"] == "mention":
                if "entities" not in document or "mentions" not in document["entities"]:
                    continue
                for mention_user in document["entities"]["mentions"]:
                    self.__add_node(mention_user, options)
                    self.__add_edge(document["author"]["username"], mention_user["username"], document["created_at"])
            elif options["edge_type"] == "retweet":
                if "referenced_tweets" not in document:
                    continue
                for retweet in document["referenced_tweets"]:
                    if retweet["type"] == "retweeted":
                        self.__add_node_from_tweet(hashtag, retweet["id"], document["author"]["username"], options)
            elif options["edge_type"] == "quote":
                if "referenced_tweets" not in document:
                    continue
                for quote in document["referenced_tweets"]:
                    if quote["type"] == "quoted":
                        self.__add_node_from_tweet(hashtag, quote["id"], document["author"]["username"], options)
            else:
                raise Exception("")
        if options["giant_component"]:
            self.graph.remove_nodes_from(list(nx.isolates(self.graph)))
            self.graph = self.graph.subgraph(max(nx.connected_components(self.graph.to_undirected()), key=len)).copy()
        if options["remove_leaf_nodes"]:
            self.graph.remove_nodes_from([node for node, degree in dict(self.graph.degree()).items() if degree == 1])
        self.metadata["source"] = "Twitter"
        if "users" in options:
            options["users"] = {index: value for index, value in enumerate(options["users"])}
        self.metadata["options"] = options
        self.metadata["graph_properties"] = {
            "nodes": self.get_number_of_nodes(),
            "edges": self.get_number_of_edges(),
        }
        self.metadata["description"] = f"From {self.mongodb.get_created_date(hashtag, 'ASC').strftime('%Y-%m-%d')} until {self.mongodb.get_created_date(hashtag, 'DES').strftime('%Y-%m-%d')}"

    def save_as(self, filename):
        filetype = filename.split(".")[-1]
        if filetype == "gexf":
            nx.write_gexf(self.graph, filename, version="1.2draft")
        elif filetype == "gml":
            nx.write_gml(self.graph, filename)
        elif filetype == "json":
            graph_file = open(filename, "w", encoding="utf8")
            json.dump(nx.node_link_data(self.graph), graph_file, ensure_ascii=False)
        elif filetype == "gpickle":
            nx.write_gpickle(self.graph, filename)
        else:
            raise Exception("")
        self.__metadata_save_as(filename)

    def __metadata_save_as(self, filename):
        metadata_filename = filename.split(".")
        metadata_filename[-1] = "metadata.json"
        metadata_file = open(".".join(metadata_filename), "w", encoding="utf8")
        json.dump(self.metadata, metadata_file, ensure_ascii=False)

    def load(self, filename):
        filetype = filename.split(".")[-1]
        if filetype == "gexf":
            self.graph = nx.read_gexf(filename)
        elif filetype == "gml":
            self.graph = nx.read_gml(filename)
        elif filetype == "json":
            graph_file = open(filename, "r", encoding="utf8")
            self.graph = nx.node_link_graph(json.load(graph_file))
        elif filetype == "gpickle":
            self.graph = nx.read_gpickle(filename)
        else:
            raise Exception("")
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

    def fj(self, user_A, user_B):
        undirected_graph = self.graph.to_undirected()
        internal_opinion = []
        for node in undirected_graph.nodes(data=True):
            if node[1]["follows"] == user_A:
                internal_opinion.append([1])
            elif node[1]["follows"] == user_B:
                internal_opinion.append([-1])
            else:
                internal_opinion.append([0])
        laplacian = nx.laplacian_matrix(undirected_graph)
        identity_matrix = identity(undirected_graph.number_of_nodes())
        inverse = inv(laplacian + identity_matrix)
        expressed_opinion = inverse.dot(internal_opinion)
        return np.power(np.linalg.norm(expressed_opinion), 2) / undirected_graph.number_of_nodes()

    def get_polarization(self, methods):
        self.metadata["graph_properties"]["polarization"] = {method: dict() for method in methods}
        pairs = list(combinations([self.metadata["options"]["users"][item] for item in self.metadata["options"]["users"]], 2))
        for method in methods:
            for pair in tqdm(pairs, total=len(pairs)):
                if method == "fj":
                    self.metadata["graph_properties"]["polarization"][method]["|".join(pair)] = self.fj(pair[0], pair[1])
                elif method == "rwc":
                    self.metadata["graph_properties"]["polarization"][method]["|".join(pair)] = self.rwc(pair[0], pair[1])
                else:
                    raise Exception("")
        return self.metadata["graph_properties"]["polarization"]

    def __set_combinations_to_metadata_entities(self, follows_color):
        usernames = [i for i in self.metadata["users"]]
        full_names = {item: self.metadata["users"][item]["full_name"] for item in self.metadata["users"]}
        for key in follows_color:
            if key in usernames:
                usernames.remove(key)
            else:
                self.metadata["users"][key] = {
                    "full_name": ",".join([full_names[username] for username in key.split(",")]),
                    "color": follows_color[key]
                }

    def create_layout(self, save_to_file: str, options):
        filetype = save_to_file.split(".")[-1]
        if filetype != "gexf":
            raise Exception("The file must be gexf type")
        print("Creating layout...")
        self.metadata["options"]["users"] = options["users"]
        follows_color = {item: self.metadata["options"]["users"][item]["color"] for item in self.metadata["options"]["users"]}
        follows_color["none"] = {"r": 210, "g": 210, "b": 210, "a": 1}
        pos = nx.spring_layout(self.graph, scale=options["scale"])
        gexf = [line for line in nx.generate_gexf(self.graph, version="1.2draft")]
        tree = ET.ElementTree(ET.fromstringlist(gexf))
        attributes = []
        namespace = "http://www.gexf.net/1.2draft"
        for element in tqdm(tree.iter(), total=len(gexf)):
            if f"{'{' + namespace + '}'}gexf" == element.tag:
                element.set("xmlns:viz", "http://gexf.net/1.3/viz")
            elif f"{'{' + namespace + '}'}attribute" == element.tag:
                attributes.append(element.attrib)
            elif f"{'{' + namespace + '}'}node" == element.tag:
                el_attr = list(list(element)[0])
                for obj in attributes:
                    if obj.get("title") == "follows":
                        get_el_attr = el_attr[int(obj.get("id"))]
                        if get_el_attr.attrib.get("value") in self.metadata["options"]["users"]:
                            color = follows_color.get(get_el_attr.attrib.get("value"))
                        else:
                            color = follows_color["none"]
                        color = {i: str(color[i]) for i in color}
                element.append(element.makeelement("viz:size", dict(value=str(options["node_size"]))))
                node_pos = pos.get(element.attrib.get("id"))
                element.append(element.makeelement("viz:position", dict(x=str(node_pos[0]), y=str(node_pos[1]))))
                element.append(element.makeelement("viz:color", color))
        ET.register_namespace("", namespace)
        tree.write(save_to_file)
        self.__metadata_save_as(save_to_file)

    def __random_walk(self, start_node, end_nodes):
        first_node = start_node
        while True:
            neighbors = list(self.graph.neighbors(start_node))
            random_num = random.randint(0, len(neighbors) - 1)
            start_node = neighbors[random_num]
            if start_node == first_node:
                continue
            if start_node in end_nodes:
                break
        return (first_node, self.graph.nodes[first_node]), (start_node, self.graph.nodes[start_node])

    def rwc(self, user_A, user_B, k=None):
        central_nodes = sorted(self.graph.degree, key=lambda x: x[1], reverse=True)
        central_l_nodes = []
        central_r_nodes = []
        for node in central_nodes:
            follows = self.graph.nodes(data="follows")[node[0]]
            if follows == user_A:
                central_l_nodes.append(node[0])
            elif follows == user_B:
                central_r_nodes.append(node[0])
        if k is not None:
            central_l_nodes = central_l_nodes[:k]
            central_r_nodes = central_r_nodes[:k]
        end_nodes = central_l_nodes + central_r_nodes
        start_user_A = [node for node, att in self.graph.nodes(data=True) if att["follows"] == user_A]
        start_user_B = [node for node, att in self.graph.nodes(data=True) if att["follows"] == user_B]
        walks = []
        for _ in range(10000):
            walks.append(self.__random_walk(random.choice(start_user_A), end_nodes))
            walks.append(self.__random_walk(random.choice(start_user_B), end_nodes))
        c_ll = 0
        c_rr = 0
        c_lr = 0
        c_rl = 0
        c_ln = 0
        c_rn = 0
        for walk in walks:
            start = walk[0]
            end = walk[1]
            if start[1]["follows"] == user_A and end[0] in central_l_nodes:
                c_ll += 1
            elif start[1]["follows"] == user_B and end[0] in central_r_nodes:
                c_rr += 1
            elif start[1]["follows"] == user_A and end[0] in central_r_nodes:
                c_lr += 1
            elif start[1]["follows"] == user_B and end[0] in central_l_nodes:
                c_rl += 1
            elif start[1]["follows"] == user_A and end[1]["follows"] not in [user_A, user_B]:
                c_ln += 1
            elif start[1]["follows"] == user_B and end[1]["follows"] not in [user_A, user_B]:
                c_rn += 1
        p_ll = c_ll / (c_ll + c_rl)
        p_rr = c_rr / (c_rr + c_lr)
        p_lr = c_lr / (c_lr + c_rr)
        p_rl = c_rl / (c_rl + c_ll)
        rwc = p_ll * p_rr - p_lr * p_rl
        return rwc
