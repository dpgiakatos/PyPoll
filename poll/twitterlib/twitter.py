import tweepy
from time import sleep
from poll.dblib import MongoDB
from datetime import timedelta


class Twitter:
    def __init__(self, bearer_token, mongodb):
        if bearer_token is None:
            raise Exception("Bearer token is none")
        if type(mongodb) != MongoDB:
            raise Exception("The DB must be MongoDB")
        self.client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
        self.mongodb: MongoDB = mongodb

    def get_followers(self, handle):
        if handle is None or handle == "":
            raise Exception("Handle cannot be none or empty")
        print(f"Fetching {handle} ...")
        user = dict(self.client.get_user(username=handle, user_fields=["id", "name"]).data)
        print(f"{user}\nGetting followers of {user['name']} ...")
        params = {
            "id": user["id"],
            "user_fields": [
                "id", "name", "username", "created_at", "description", "entities", "location",
                "pinned_tweet_id", "profile_image_url", "protected", "public_metrics", "url",
                "verified",
                "withheld"
            ],
            "max_results": 100
        }
        cursor = None
        while True:
            try:
                if cursor is None:
                    if "pagination_token" in params:
                        del params["pagination_token"]
                else:
                    params["pagination_token"] = cursor
                res = self.client.get_users_followers(**params)
                print(res)
            except Exception as e:
                print(f"Server error. {e} Sleeping for 10sec ...")
                sleep(10)
                continue
            self.mongodb.insert_many(handle, [dict(item) for item in res.data])
            meta = dict(res.meta)
            if "next_token" in meta:
                self.mongodb.update_metadata(handle, str(cursor), str(meta["next_token"]))
                cursor = meta["next_token"]
            else:
                break

    def get_tweets_by_hashtag(self, hashtag, start_time=None, end_time=None):
        params = {
            "tweet_fields": [
                "id", "text", "attachments", "author_id", "context_annotations", "conversation_id",
                "created_at", "entities", "geo", "in_reply_to_user_id", "lang", "public_metrics",
                "referenced_tweets", "reply_settings", "source", "withheld"
            ],
           "expansions": ["author_id"],
            "user_fields": [
                "id", "name", "username", "created_at", "description",
                "entities", "location",
                "pinned_tweet_id", "profile_image_url", "protected",
                "public_metrics", "url",
                "verified", "withheld"
            ],
          "max_results": 100
        }
        if hashtag is None or type(hashtag) != str:
            raise Exception("Hashtag cannor be none and must be a string")
        elif not hashtag.startswith("#"):
            raise Exception(f"The hashtag {hashtag} must start with `#`")
        print(f"Getting tweets containing {hashtag} ...")
        if start_time is None:
            start_time = self.mongodb.get_created_date(hashtag, "DES")
            if start_time is None:
                pass
            else:
                start_time += timedelta(seconds=1)
                params["start_time"] = start_time.isoformat() + "Z"
        else:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time
        cursor = None
        while True:
            try:
                if cursor is None:
                    if "next_token" in params:
                        del params["next_token"]
                else:
                    params["next_token"] = cursor
                res = self.client.search_all_tweets(hashtag, **params)
                print(res)
            except Exception as e:
                print(f"Server error. {e} Sleeping for 10sec ...")
                sleep(10)
                continue
            documents = []
            for item in res.data:
                documents.append(dict(item))
                for user in res.includes["users"]:
                    if documents[-1]["author_id"] == dict(user)["id"]:
                        documents[-1]["author"] = dict(user)
            self.mongodb.insert_many(hashtag, documents)
            meta = dict(res.meta)
            if "next_token" in meta:
                # self.mongodb.update_metadata(hashtag, str(cursor), str(meta["next_token"]))
                cursor = meta["next_token"]
            else:
                break
