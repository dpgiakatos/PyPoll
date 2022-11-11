import pymongo


class MongoDB:
    def __init__(self, host, db_name, port=27017, username=None, password=None):
        self.client = pymongo.MongoClient(host, port, username=username, password=password)
        self.db = db_name

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

    def get_all(self, collection):
        return self.client[self.db][collection].find({}).sort([("created_at", -1)]).allow_disk_use(True)

    def exist_username(self, collection, username):
        if self.client[self.db][collection].find_one({"username": username}):
            return True
        return False
