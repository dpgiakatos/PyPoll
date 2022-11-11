# my-lib
A python library for political polarization. [Political lighthouse](https://political-lighthouse.netlify.com/) created by using this library.

### Installation
```commandline
pip install poll
```

### Get started
Import the libraries.

```python
from poll import Twitter, MongoDB, Graph, GraphPlot
from dotenv import load_dotenv
import os
```

Load the twitter bearer token and MongoDB credentials.
```python
load_dotenv()
twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
mongodb_host = os.getenv("MONGODB_HOST")
mongodb_port = int(os.getenv("MONGODB_PORT"))
mongodb_username = os.getenv("MONGODB_USERNAME")
mongodb_password = os.getenv("MONGODB_PASSWORD")
```

Get the followers of Kyriakos Mitsotakis, Alexis Tsipras and the Tweets than contains the hashtag #υποκλοπες.
```python
db = MongoDB(mongodb_host, "polarization", mongodb_port, mongodb_username, mongodb_password)
api = Twitter(twitter_bearer_token, db)
api.get_followers("kmitsotakis")
api.get_followers("atsipras")
api.get_tweets_by_hashtag("#υποκλοπες")
```

Create #υποκλοπες polarized graph using the Tweets and the followers that we collected previously.
```python
graph = Graph()
options = {"keep_all_users": False, "remove_leaf_nodes": False}
users = [
    {"username": "kmitsotakis", "full_name": "Kyriakos Mitsotakis", "color": {"r": 89, "g": 191, "b": 252, "a": 1}},
    {"username": "atsipras", "full_name": "Alexis Tsipras", "color": {"r": 252, "g": 52, "b": 129, "a": 1}}
]
graph.create_mention_graph_from_mongodb(users, "#υποκλοπες", db, options)
graph.set_metadata("Twitter", "#υποκλοπες")
graph.create_layout("kmitsotakis_atsipras_#υποκλοπες.gexf", scale=1e+10)
```

Visualize the #υποκλοπες polarized graph.
```python
plot = GraphPlot()
plot.show("kmitsotakis_atsipras_#υποκλοπες.gexf")
```

### Documentation
For more information about poll you can read the documentation on ...