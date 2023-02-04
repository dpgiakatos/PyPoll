from tqdm import tqdm
import pymongo
import bson


class MongoDB:
    def __init__(self, host, db_name, port=27017, username=None, password=None):
        self.client = pymongo.MongoClient(host, port, username=username, password=password)
        self.db = db_name
        self.create_index("metadata")

    def insert_many(self, collection, data):
        self.client[self.db][collection].insert_many(data)

    def count_documents(self, collection):
        return self.client[self.db][collection].count_documents({})

    def get_created_date(self, collection, order="ASC"):
        if order == "ASC":
            order_key = 1
        else:
            order_key = -1
        try:
            res = self.client[self.db][collection].aggregate([{"$sort": {"created_at": order_key}}, {"$limit": 1}]).next()["created_at"]
        except:
            res = None
        return res

    def update_metadata(self, username, cursor, next_cursor):
        self.client[self.db]["metadata"].update_one(
            {"username": username},
            {"$set": {
                "next_cursor": next_cursor,
                "cursor": cursor
            }},
            upsert=True
        )

    def get_cursor(self, username):
        res = self.client[self.db]["metadata"].find_one({"username": username})
        return res

    def create_index(self, collection):
        indexes = self.client[self.db][collection].index_information()
        if "username_1" in indexes:
            return False
        self.client[self.db][collection].create_index([("username", pymongo.ASCENDING)], unique=True)
        return True

    def get_all(self, collection):
        return self.client[self.db][collection].find({}).sort([("created_at", -1)]).allow_disk_use(True)

    def exist_username(self, collection, username):
        if self.client[self.db][collection].find_one({"username": username}):
            return True
        return False

    def get_tweet(self, collection, tweet_id):
        tweet = self.client[self.db][collection].find_one({"id": tweet_id})
        return tweet

    def dump(self, collection):
        count = self.count_documents(collection)
        print(f"Exporting collection `{collection}` with {count} ...")
        file = open(f"{collection}.bson", "wb+")
        cursor = self.get_all(collection)
        for doc in tqdm(cursor, total=count):
            file.write(bson.BSON.encode(doc))

    def restore(self, filename):
        if "/" in filename:
            collection = filename.split("/")[-1].replace(".bson", "")
        else:
            collection = filename.replace(".bson", "")
        print(f"Importing collection `{collection}` ...")
        file = open(filename, "rb+")
        docs = []
        for doc in tqdm(bson.decode_iter(file.read())):
            docs.append(doc)
            if len(doc) > 10000:
                self.client[self.db][collection].insert_many(docs)
                docs.clear()
        if len(docs):
            self.client[self.db][collection].insert_many(docs)
    def delete(self, collection):
        print(f"Deleting `{collection}` collection ...")
        self.client[self.db][collection].drop()

    def update(self, collection, find_rule, update_rule):
        self.client[self.db][collection].update_many(find_rule, update_rule)
