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

    def get_followers(self, username):
        if username is None or username == "":
            raise Exception("Handle cannot be none or empty")
        print(f"Fetching {username} ...")
        self.mongodb.create_index(username)
        print(f"`{username}` collection created.")
        user = dict(self.client.get_user(username=username, user_fields=["id", "name"]).data)
        print(f"{user}\nGetting followers of {user['name']} ...")
        params = {
            "id": user["id"],
            "user_fields": [
                "id", "name", "username", "created_at", "description", "entities", "location",
                "pinned_tweet_id", "profile_image_url", "protected", "public_metrics", "url",
                "verified",
                "withheld"
            ],
            "max_results": 1000
        }
        cursor = self.mongodb.get_cursor(username)
        if cursor is not None:
            cursor = cursor["next_cursor"]
            if cursor is None:
                print(f"The followers of {user['name']} have been collected.")
                print(f"Please delete the collections and start over if you want to update them.")
                return
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
            documents = []
            for item in res.data:
                documents.append(dict(item))
                documents[-1]["id"] = str(documents[-1]["id"])
            self.mongodb.insert_many(username, documents)
            meta = dict(res.meta)
            if "next_token" in meta:
                self.mongodb.update_metadata(username, str(cursor), str(meta["next_token"]))
                cursor = meta["next_token"]
            else:
                self.mongodb.update_metadata(username, str(cursor), None)
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
            raise Exception("Hashtag cannot be none and must be a string")
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
                documents[-1]["id"] = str(documents[-1]["id"])
                documents[-1]["conversation_id"] = str(documents[-1]["conversation_id"])
                documents[-1]["author_id"] = str(documents[-1]["author_id"])
                for user in res.includes["users"]:
                    if documents[-1]["author_id"] == str(dict(user)["id"]):
                        documents[-1]["author"] = dict(user)
                        documents[-1]["author"]["id"] = str(documents[-1]["author"]["id"])
            self.mongodb.insert_many(hashtag, documents)
            meta = dict(res.meta)
            if "next_token" in meta:
                # self.mongodb.update_metadata(hashtag, str(cursor), str(meta["next_token"]))
                cursor = meta["next_token"]
            else:
                break

    def get_all_tweets_count(self, hashtag, start_time=None, end_time=None):
        params = {
            "granularity": "day"
        }
        total_tweet_count = 0
        if hashtag is None or type(hashtag) != str:
            raise Exception("Hashtag cannot be none and must be a string")
        elif not hashtag.startswith("#"):
            raise Exception(f"The hashtag {hashtag} must start with `#`")
        print(f"Counting tweets containing {hashtag} ...")
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
                res = self.client.get_all_tweets_count(hashtag, **params)
                print(res)
            except Exception as e:
                print(f"Server error. {e} Sleeping for 10sec ...")
                sleep(10)
                continue
            meta = dict(res.meta)
            total_tweet_count += meta["total_tweet_count"]
            if "next_token" in meta:
                cursor = meta["next_token"]
            else:
                break
        return total_tweet_count
