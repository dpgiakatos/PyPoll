# poll
A python library for polarization. [Political lighthouse](https://political-lighthouse.netlify.com/) created by using this library.

### Installation
```commandline
pip install git+https://github.com/dpgiakatos/PyPoll.git
```

### Get started
Import the libraries.

```python
from pypoll import Twitter, MongoDB, Graph, GraphPlot
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

Create #υποκλοπες graph using the Tweets and the followers that we collected previously.
```python
graph = Graph()
options = {
        "edge_type": "mention",
        "giant_component": False,
        "remove_leaf_nodes": False,
        "users": {"kmitsotakis", "atsipras"}
    }
graph.create_graph("#υποκλοπες", db, options)
graph.save_as("#υποκλοπες.gexf")
```

Create polarized layout for #υποκλοπες graph.
```python
graph.load("#υποκλοπες.gexf")
options = {
        "scale": 1e+10,
        "node_size": 2,
        "users": {
            "kmitsotakis": {
                "full_name": "Kyriakos Mitsotakis",
                "color": {"r": 27, "g": 92, "b": 199, "a": 1}
            },
            "atsipras": {
                "full_name": "Alexis Tsipras",
                "color": {"r": 238, "g": 128, "b": 143, "a": 1}
            }
        }
    }
graph.create_layout("kmitsotakis_atsipras_#υποκλοπες.gexf", options)
```

Visualize the #υποκλοπες polarized graph.
```python
plot = GraphPlot()
plot.show("kmitsotakis_atsipras_#υποκλοπες.gexf")
```

### Documentation
For more information about poll you can read the documentation on ...