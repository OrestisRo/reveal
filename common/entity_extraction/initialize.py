import fb_info
from pymongo import MongoClient
import pprint

fb_info.token = ""
fb_info.graph = ""
def overlaps(access_token,uid):
		client = MongoClient('127.0.0.1')
		db = client.recommendation_db
		collection = db.friends
		user_coll = db.users
		fb_info.token=access_token
		user_movie_gens = {}
		user_music_gens = {}
		movie_results = []
		music_results = []
		user = collection.find_one({'id':uid})
		if not user:
			user_movie_gens, user_music_gens,user_movie_cat,user_music_cat = fb_info.createProfile()
		else:
			user_movie_gens = user['movie_genres']
			user_music_gens = user['music_genres']
			user_movie_cat = user['movie_categories']
			user_music_cat = user['music_categories']
			user['token'] = access_token
			user['has_lists'] = 0
			user['proc_posts'] = []
			user['time'] = 0
			user_coll.insert(user)
		uid=fb_info.calcOverlap(user_movie_gens,user_music_gens,user_movie_cat,user_music_cat)
		return uid

def init_lists(uid):
	fb_info.readStatusAndCreateLists(uid)
