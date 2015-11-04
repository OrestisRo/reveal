import text_analysis_freebase
from datetime import datetime,timedelta
import re
import pymongo
from pprint import pprint
import math
from pymongo import MongoClient
from sentiment import analysis
import facebook as fb
import youtubeAPI,text_analysis
import time,re
from langid import classify





def getUserHistory(user):
	history_posts = []
	my_posts = []
	my_music_actions = []
	my_movie_actions = []
	token = user['token']
	ex = datetime.now() - timedelta(days=60)
	graph = fb.GraphAPI(token)
	fields = {'fields':'links.since('+str(ex)+').fields(link,id,name,created_time).limit(100),name,video.watches.fields(id,data,publish_time).limit(100)'}

	my_wall = graph.get_object('me',**fields)
	if 'links' in my_wall:
		my_posts = my_wall['links']['data']
	if 'video.watches' in my_wall:
		my_movie_actions = my_wall['video.watches']['data']
	#Deprecated
	# if 'music.listens' in my_wall:
	# 	my_music_actions = my_wall['music.listens']['data']

	for video in my_movie_actions:
		check = {}
		p_time = video['publish_time']
		if 'movie' in video['data']:
			entity = video['data']['movie']['title']
			post_id = video['id']
			check = text_analysis_freebase.search(entity,"movie")
			entity = check
			if bool(entity):
				for gen in entity['genres']:
					if (gen.lower() in user['movie_genres'].keys()):
						user['movie_genres'][gen.lower()] += 1
					else:
						user['movie_genres'][gen.lower()] = 1
				if title:
					user['movie_categories'].append({'like_name':entity['name'],'fb_id':post_id,'genres':entity['genres']})

	#Deprecated
	# for item in my_music_actions:
	# 	check = {}
	# 	p_time = item['publish_time']
	# 	if 'musician' in item['data']:
	# 		entity = item['data']['musician']['title']
	# 		post_id = item['id']
	# 		check = text_analysis_freebase.search(entity,"music")
	# 		entity = check
	# 		if bool(entity):
	# 			for gen in entity['genres']:
	# 				if (gen.lower() in user['movie_genres'].keys()):
	# 					user['music_genre_history'][gen.lower()] += 1
	# 				else:
	# 					user['music_genre_history'][gen.lower()] = 1
	# 			if title:
	# 				user['music_categories'].append({'like_name':entity['name'],'fb_id':post_id,'genres':entity['genres']})
	user,history_movie_entities,history_music_entities = processHistoryLink(my_posts,user)

	for mo_genres in user['movie_genres']:
		totalWeightOfUserMovieGenres+=user['movie_genres'][mo_genres] #this is a total weight consisting by the sum of each genre weight
	for mu_genres in user['music_genres']:
		totalWeightOfUserMusicGenres+=user['music_genres'][mu_genres]	#same applies for music genres
	user['total_movie_score'] = totalWeightOfUserMovieGenres
	user['total_music_score'] = totalWeightOfUserMusicGenres
	user['movie_likes_score'] = getScoreSum(user['movie_categories'], user['movie_genres'])
	user['music_likes_score'] = getScoreSum(user['music_categories'], user['music_genres'])

	return user


def processHistoryLink(history_posts,user):
	history_movie_entities,history_music_entities = [],[]
	ex = datetime.now() - timedelta(days=14)
	for item in history_posts:
		tids = []
		url = ""
		description = ""
		title = ""
		message = ""
		created = item['created_time'][:10]
		if 'name' in item:
			title = item['name']
		plink = item['link']
		post_id = item['id']
		if 'youtube' in plink or 'youtu.be' in plink:
			tids,url= youtubeAPI.getEntity(plink,title)
		check = {}
		if tids:
			for tid in tids:
				check = text_analysis_freebase.link_search(tid,title)
				if check:
					break
		entity = check
		if entity:
			if entity['type'] == 'movie' and entity['genres']:
				for gen in entity['genres']:
					if (gen in user['movie_genres'].keys()):
						user['movie_genres'][gen] += 1
					else:
						user['movie_genres'][gen] = 1
				user['movie_categories'].append({'like_name':entity['name'],'fb_id':post_id,'genres':entity['genres']})
			elif entity['type'] == 'music' and entity['genres']:
				for key in entity['genres']:
					if key in user['music_genres'].keys():
						user['music_genres'][key] += 1
					else:
						user['music_genres'][key] = 1
				user['music_categories'].append({'like_name':entity['name'],'fb_id':post_id,'genres':entity['genres']})

	return user,history_movie_entities,history_music_entities

def createProfile():
	db_client = MongoClient('127.0.0.1')
	recomm = db_client.recommendation_db
	ins = recomm.users
	movie_likes = []
	music_likes = []
	movie_genres = {}
	music_genres = {}
	totalWeightOfUserMovieGenres = 0 #depends on how many times a genre occurs,and an item of every genre gets the correspondent weight
	totalWeightOfUserMusicGenres = 0
	graph1 = fb.GraphAPI(token)
	user = graph1.get_object("me",fields='id,name')
	current = ins.find_one({'id':user['id']})
	if not current:
		user_likes = graph1.get_object("me/movies",fields='id,name,category,genre',limit=500)
		for like in user_likes['data']:
			if 'Movie' in like['category'] and 'character' not in like['category']:
				movie_likes.append({'id':like['id'],'name':like['name'].encode('utf8'),'category':like['category']})
		user_likes = graph1.get_object("me/music",fields='id,name,category,genre',limit=500)
		for like in user_likes['data']:
			if 'Musician/band' in like['category']:
				music_likes.append({'id':like['id'],'name':like['name'].encode('utf8'),'category':like['category']})

		movie_genres,full_movie_cat = movieGather(movie_likes)
		music_genres,full_music_cat = musicGather(music_likes)
		for mo_genres in movie_genres:
			totalWeightOfUserMovieGenres+=movie_genres[mo_genres] #this is a total weight consisting by the sum of each genre weight
		for mu_genres in music_genres:
			totalWeightOfUserMusicGenres+=music_genres[mu_genres]	#same applies for music genres

		user['movie_categories'] = full_movie_cat
		user['movie_genres'] = movie_genres
		user['music_categories'] = full_music_cat
		user['music_genres'] = music_genres
		user['total_movie_score'] = totalWeightOfUserMovieGenres
		user['total_music_score'] = totalWeightOfUserMusicGenres
		user['movie_likes_score'] = getScoreSum(full_movie_cat, movie_genres)
		user['music_likes_score'] = getScoreSum(full_music_cat, music_genres)
		user['token'] = token
		user['has_lists'] = 0
		user['proc_posts'] = []
		if len(full_music_cat)<10 or len(full_movie_cat) < 10:
			user = getUserHistory(user)
		ins.insert(user)
		return movie_genres,music_genres,full_movie_cat,full_music_cat
	else:
		return current['movie_genres'],current['music_genres'],current['movie_categories'],current['music_categories']


def getScoreSum(likes,genres): #Like's Average Score
	score = 0
	for like in likes:
		temp = 0
		for gen in like['genres']:
			temp += genres[gen]
		score += float(temp)/len(like['genres'])
	return score



def calcOverlap(user_movie_genres,user_music_genres,user_movie_cat,user_music_cat,token):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	friends = db.friends

	user = db.users
	results = []
	full_movie_cat = []					#array with like id,name,genres of the friends' movie likes
	full_music_cat = []
	friend_movie_genres = {}			#array with gens and scores of likes
	friend_music_genres = {}			#array with gens and scores of likes
	graph1 = fb.GraphAPI(token)
	me = graph1.get_object('me',fields='name,id')
	all_friends = graph1.get_object('me/friends',fields='id,name,picture') #,limit='100'
	user_buff = user.find_one({"id":me['id']},{'total_movie_score':'true','total_music_score':'true','movie_categories':'true','music_categories':'true','_id':'false','movie_likes_score':True,'music_likes_score':True})
	for f in all_friends['data']:
		friend = friends.find_one({'id':f['id']})
		if friend and friend['music_categories'] and friend['movie_categories']:
			print "friend existed already"
			full_movie_cat = friend['movie_categories']
			full_music_cat = friend['music_categories']
			friend_movie_genres = friend['movie_genres']
			friend_music_genres = friend['music_genres']
			profile_picture = friend['picture']
		else:
			profile_picture = f['picture']['data']['url']
			friend_movie_likes,friend_music_likes= filterLikes(f)
			friend_movie_genres,full_movie_cat = movieGather(friend_movie_likes)
			friend_music_genres,full_music_cat = musicGather(friend_music_likes)

		results = getFriendScores(user_buff,f,user_movie_genres,user_movie_cat,friend_movie_genres,full_movie_cat,user_music_genres,user_music_cat,friend_music_genres,full_music_cat,profile_picture,results)
	user.update({'id':me['id']},{'$set':{'scores':results}})
	return me['id']


def getFriendScores(user,f,user_movie_genres,user_movie_cat,friend_movie_genres,full_movie_cat,user_music_genres,user_music_cat,friend_music_genres,full_music_cat,profile_picture,results):
	movie_genres_score = 0
	music_genres_score = 0
	movie_similarity = {}
	music_similarity = {}
	movie_likes_score = getScoreSum(full_movie_cat, friend_movie_genres)
	music_likes_score = getScoreSum(full_music_cat, friend_music_genres)


	friend_entry = {}
	if friend_movie_genres:
		for mo_genres in friend_movie_genres:
			movie_genres_score+=friend_movie_genres[mo_genres]
	if friend_music_genres:
		for mu_genres in friend_music_genres:
			music_genres_score+=friend_music_genres[mu_genres]

	#Inserting friend document to db
	friend_todb = {}
	friend_todb['name'] = f['name']
	friend_todb['id'] = f['id']
	friend_todb['picture'] = profile_picture
	friend_todb['music_genres'] = friend_music_genres
	friend_todb['movie_genres'] = friend_movie_genres
	friend_todb['music_categories'] = full_music_cat
	friend_todb['movie_categories'] = full_movie_cat
	friend_todb['movie_likes_score'] = movie_likes_score
	friend_todb['music_likes_score'] = music_likes_score
	friend_todb['total_movie_score'] = movie_genres_score
	friend_todb['total_music_score'] = music_genres_score
	friend_todb['has_lists'] = 0
	friend_todb['proc_posts'] = []
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.friends
	collection.update({'id':f['id']},friend_todb,True)

	friend_entry['friend_name'] = f['name']
	friend_entry['facebook_id'] = f['id']
	friend_entry['picture'] = profile_picture

	if full_movie_cat:
		movie_similarity = getMovieSimilarity(user_movie_genres,user_movie_cat,friend_movie_genres,full_movie_cat,[f['id'],f['name'],profile_picture],user,movie_genres_score,movie_likes_score)
		if movie_likes_score!=0 and user['movie_likes_score']!=0:
			ovmovie_likes_score = movie_similarity['item_score']
		else:
			ovmovie_likes_score = 0
		ovmovie_genres_score = movie_similarity['genre_score']
		movie_friend_score = (float(2*ovmovie_genres_score + ovmovie_likes_score)) / 3
		movie_similarity['movie_friend_score'] = int(round(movie_friend_score*100,0))
	else:
		movie_similarity['movie_friend_score'] = 0

	if full_music_cat:
		music_similarity = getMusicSimilarity(user_music_genres,user_music_cat,friend_music_genres,full_music_cat,[f['id'],f['name'],profile_picture],user,music_genres_score,music_likes_score)
		if music_likes_score !=0 and user['music_likes_score']!=0:
			ovmusic_likes_score = music_similarity['item_score']
		else:
			ovmusic_likes_score =0
		ovmusic_genres_score = music_similarity['genre_score']
		music_friend_score = (float(2*ovmusic_genres_score + ovmusic_likes_score))/3
		music_similarity['music_friend_score'] = int(round(music_friend_score*100,0))
	else:
		music_similarity['music_friend_score'] = 0

	friend_entry['movie_score'] = movie_similarity
	friend_entry['music_score'] = music_similarity
	results.append(friend_entry)
	return results

def getMovieSimilarity(user_movie_genres,user_movie_cat,friend_movie_genres,friend_movie_cat,friend_name,user,fgscore,flscore):
	movie_results = {}
	genre_list = []
	item_list = []
	genre_score=0
	item_score=0
	genre_score, genre_list = getGenreOv(user_movie_genres,friend_movie_genres,user['total_movie_score'],fgscore) #new
	for movies in user_movie_cat:
		for item in friend_movie_cat:
			if movies['like_name'] == item['like_name']:
				item_score += getLikeOv(user_movie_genres,friend_movie_genres,item['genres'])
				item_list.append({'like_name':item['like_name'],'facebook_id':item['fb_id']}) #list of overlapping items
				break
	item_score = round(float(item_score)/(user['movie_likes_score']+flscore),3)	#new
	movie_results['genres'] = genre_list
	movie_results['genre_score'] = genre_score
	movie_results['items'] = item_list
	movie_results['item_score'] = item_score
	return movie_results

def getGenreOv(user_genres,friend_genres,uscore,fscore):
	score,final = 0,0
	genre_list = {}
	for genre in user_genres:
		if genre in friend_genres:
			score += user_genres[genre] + friend_genres[genre]
			genre_list[genre] = "{0} / {1}".format(str(friend_genres[genre]),str(fscore))
	final = round(float(score)/ (uscore+fscore),3)
	return final, genre_list


def getLikeOv(user_genres,friend_genres,like_genres): #Like's Overlapping Score
	score = 0
	utemp = 0
	ftemp = 0
	for gen in like_genres:
		utemp += user_genres[gen]
		ftemp += friend_genres[gen]
	score = round(((float(utemp)/len(like_genres))+(float(ftemp)/len(like_genres))),3)
	return score

#same kind of scoring applies here
def getMusicSimilarity(user_music_genres,user_music_cat,friend_music_genres,friend_music_cat,friend_name,user,fgscore,flscore):
	music_results = {}
	genre_list = []
	item_list = []
	genre_score = 0
	item_score = 0
	genre_score, genre_list = getGenreOv(user_music_genres,friend_music_genres,user['total_music_score'],fgscore) #n
	for music in user_music_cat:
		for item in friend_music_cat:
			if music['like_name'] == item['like_name']:
				item_score += getLikeOv(user_music_genres,friend_music_genres,item['genres'])
				item_list.append({'like_name':item['like_name'],'facebook_id':item['fb_id']})
			break


	item_score = round(float(item_score)/(user['music_likes_score']+flscore),3)	#new
	music_results['genres'] = genre_list
	music_results['genre_score'] = genre_score
	music_results['items'] = item_list
	music_results['item_score'] = item_score
	return music_results

def filterLikes(f):
	global token
	friend_movie_likes = []
	friend_music_likes = []
	graph1 = fb.GraphAPI(token)
	try:
		friend_likes = graph1.get_object(f['id']+'/music',fields='id,name,category,genre',limit=500)
	except Exception, e:
		print e
		friend_likes={'data':[]}
		friend_music_likes = []
	for like in friend_likes['data']:
		try:	#IGNORE NON ENGLISH(ASCII) CHARACTERS
			like['name'].encode('ascii')
		except (UnicodeDecodeError,UnicodeEncodeError):
			continue
		if 'Musician/band' in like['category']:
			friend_music_likes.append({'id':like['id'],'name':like['name'].encode('utf-8'),'category':like['category']})
	try:
		friend_likes = graph1.get_object(f['id']+'/movies',fields='id,name,genre,category',limit=500)
	except:
		friend_likes={'data':[]}
		friend_movie_likes = []
	for like in friend_likes['data']:
		try:	#IGNORE NON ENGLISH(ASCII) CHARACTERS
			like['name'].encode('ascii')
		except (UnicodeDecodeError,UnicodeEncodeError):
			continue
		if 'Movie' in like['category'] and 'character' not in like['category']:
			friend_movie_likes.append({'id':like['id'],'name':like['name'].encode('utf-8'),'category':like['category']})
	return friend_movie_likes, friend_music_likes

def movieGather(movie_likes):
	movie_genres={}
	full_movie_cat = []
	for like in movie_likes:
		like_check = re.sub("[\\W]"," ",like['name'].strip())
		entity = text_analysis_freebase.search(like_check,"movie")
		if entity:
			gens = entity['genres']
			try:
				full_movie_cat.append({'fb_id':like['id'],'like_name':entity['title'],'genres':entity['genres']})
			except Exception, e:
				print e
				print entity
				full_movie_cat.append({'fb_id':like['id'],'like_name':entity['name'],'genres':entity['genres']}) #CHECK THIS
			for gen in gens:
				if gen not in movie_genres.keys():
					movie_genres[gen] = 1
				else:
					movie_genres[gen] += 1
	return movie_genres,full_movie_cat



def musicGather(music_likes):
	music_genres = {}
	full_music_cat = []
	for like in music_likes:
		gens = []
		entity = text_analysis_freebase.search(like['name'],"music")
		if entity:
			gens = entity['genres']
			full_music_cat.append({'fb_id':like['id'],'like_name':entity['name'],'genres':gens})
			for gen in gens:
				if gen not in music_genres:
					music_genres[gen] = 1
				else:
					music_genres[gen] += 1
	return music_genres,full_music_cat


def readStatusAndCreateLists(uid):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	user_coll = db.users
	movies10 = []
	music10 = []
	friends_list = []
	query = user_coll.find_one({"id":uid})
	user = query
	acc_token = user['token']
	graph = fb.GraphAPI(acc_token)
	scores = user['scores']
	lim = len(scores)
	music_genres = user['music_genres']
	movie_genres = user['movie_genres']
	proc_posts = user['proc_posts']	#ore
	ex = datetime.now() - timedelta(days=14)
	fields = {"fields":'links.since('+str(ex)+').fields(comments.fields(id,from,message).limit(10),message,link,id,name,created_time,description),name,picture,statuses.since('+str(ex)+').fields(comments.fields(id,from,message).limit(10),message,id,updated_time),video.watches.fields(id,data,publish_time,message),music.listens.fields(id,data,publish_time,message)'}

	for i in range(0,lim):
		args = {}
		links_filtered = []
		statuses_filtered = []
		videos = []
		music = []
		if not scores[i]['music_score'] and not scores[i]['movie_score']:
			continue
		try:
			statuses = graph.get_object(scores[i]['facebook_id'],**fields)
		except:
			print str(scores[i]['friend_name'].encode('utf8')) + " - Graph error\n"
			continue

		if 'links' in statuses:
			links_filtered = statuses['links']['data']
		if 'statuses' in statuses:
			statuses_filtered = statuses['statuses']['data']
		if 'video.watches' in statuses:
			videos = statuses['video.watches']['data']
		if 'music.listens' in statuses:
			music = statuses['music.listens']['data']

		picture = statuses['picture']['data']['url']

		for video in videos:
			p_time = video['publish_time']
			if 'movie' in video['data'] and p_time > str(ex):
				entity = video['data']['movie']['title']
				post_id = video['id']
				if post_id not in proc_posts:
					proc_posts.append(post_id)
				else:
					continue
				check = text_analysis_freebase.search(entity,"movie")
				entity = check
				if bool(entity):
					ubuff = 0
					for gen in entity['genres']:
						if (gen in movie_genres.keys()):
								ubuff += movie_genres[gen]
					ubuff = float(ubuff)/len(entity['genres'])
					score_now = float(scores[i]['movie_score']['movie_friend_score'])*ubuff
					title,url,description = youtubeAPI.getVideo(entity)
					if title:
						exist_flag = 0
						for it in movies10: #TODO O markos to eixe valei se sxolia
							if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]: #edw paizei na prepei na be "or" analoga me to ama 8eloume genika na uparxei to 1 vid 1 fora mono.
								exist_flag = 1
						if (exist_flag == 0):
							movies10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,'picture':picture,'title':title,'embed':url,'description':description,'created':p_time[:10],'genres':entity['genres'],'rated':0})

		for item in music:
			p_time = item['publish_time']
			if 'musician' in item['data'] and p_time > str(ex):
				entity = item['data']['musician']['title']
				post_id = item['id']
				if post_id not in proc_posts:
					proc_posts.append(post_id)
				else:
					continue
				check = text_analysis_freebase.search(entity,"music")
				entity = check
				if bool(entity):
					ubuff=0
					for gen in entity['genres']:
						if (gen in movie_genres.keys()):
								ubuff += movie_genres[gen]
					ubuff = float(ubuff)/len(entity['genres'])
					score_now = float(scores[i]['movie_score']['movie_friend_score'])*ubuff
					title,url,description = youtubeAPI.getVideo(entity)
					if title:
						exist_flag = 0
						for it in music10:
							if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]: #edw paizei na prepei na be "or" analoga me to ama 8eloume genika na uparxei to 1 vid 1 fora mono.
								exist_flag = 1
						if exist_flag == 0:
							music10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,'picture':picture,'title':title,'embed':url,'description':description,'created':p_time[:10],'genres':entity['genres'],'rated':0})


		args['i'] = i
		args['scores'] = scores
		args['movie'] = movie_genres
		args['music'] = music_genres
		args['pic'] = picture
		for link in links_filtered:
			if 'link' in link:
				proc_posts, movies10, music10 = process_link(link,proc_posts,movies10,music10,args)

		for status in statuses_filtered:
			status_flag = 1
			if 'message' in status:
				lme = status['message']
				try:#ore
					lang = classify(lme)
					if lang[0]!='en':
						continue
				except Exception as e:
					print e
					continue

				split_buffer = status['message'].split(" ")
				for word in split_buffer:
					if 'http://' in word:
						link_buffer = {}
						link_buffer['id'] = status['id']
						link_buffer['link'] = word
						if 'updated_time' in status:
							link_buffer['created_time'] = status['updated_time']
						proc_posts, movies10, music10 = process_link(link_buffer,proc_posts,movies10,music10,args)
						status_flag = 0
						break
			if status_flag == 1:
				proc_posts, movies10, music10 = process_status(status,proc_posts,movies10,music10,args)

	movies10 = sorted(movies10, key=lambda k:k['created'])
	movies10 = movies10[::-1]
	music10 = sorted(music10, key=lambda k:k['created'])
	music10 = music10[::-1]
	user_coll.update({"id":uid},{"$set":{"movies10":movies10,"music10":music10,"has_lists":1,"proc_posts":proc_posts}})


def process_link(link,proc_posts,movies10,music10,args):
	i = args['i']
	scores = args['scores']
	movie_genres = args['movie']
	music_genres = args['music']
	picture = args['pic']
	description = " "
	title = " "
	score_now = 0
	post_id = link['id']
	if post_id not in proc_posts:
		proc_posts.append(post_id)
	else:
		return proc_posts,movies10,music10
	if 'message' in link:
		message = link['message']
	else:
		message = ''
	if 'comments' in link:
		comments = link['comments']['data']
	else:
		comments = ''
	created = link['created_time'][:10]
	if 'name' in link:
		title = link['name']
	if 'description' in link:
		description = link['description']
	plink = link['link']
	if 'youtube' in plink or 'youtu.be' in plink:
		tids,url= youtubeAPI.getEntity(plink,title)
		check = {}
		if bool(tids):
			f_score = 0 #final score
			m_score = analysis.sentiment_analysis(message.encode('utf-8')) #message score
			if m_score >=-0.1:
				f_score +=1
			else:
				f_score -=1
			for c in comments:
				if c['from']['id'] == scores[i]['facebook_id']:
					c_score = 0
					c_score = analysis.sentiment_analysis(c['message'].encode('utf8'))	#comment_score
					if c_score >=-0.1:
						f_score+=1
					else:
						f_score-=1
			if f_score < 0:
				return proc_posts,movies10,music10
			for tid in tids:
				check = text_analysis_freebase.link_search(tid,title)
				if check:
					break
		else:
			return proc_posts,movies10,music10
		entity = check
		if entity:
			ubuff = 0
			if entity['type'] == 'movie' and entity['genres']:
				for gen in entity['genres']:
					if (gen in movie_genres.keys()):
						ubuff += movie_genres[gen]
				ubuff = float(ubuff)/len(entity['genres'])
				score_now = float(scores[i]['movie_score']['movie_friend_score'])*ubuff
				score_now = int(round(score_now,0))
				exist_flag = 0
				for it in movies10:#EDW
					if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]:
						exist_flag = 1
				if (exist_flag == 0):
					movies10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,"message":message.encode('utf-8'),'link':plink,'picture':picture,"title":title,'description':description,'embed':url,'created':created,'genres':entity['genres'],'rated':0})
			elif entity['type'] == 'music' and entity['genres']:
				for key in entity['genres']:
					if key in music_genres.keys():
						ubuff += music_genres[key]
				ubuff = float(ubuff)/len(entity['genres'])
				score_now = float(scores[i]['music_score']['music_friend_score'])*ubuff
				score_now = int(round(score_now,0))
				exist_flag = 0
				for it in music10:
					if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]:
						exist_flag = 1
				if exist_flag == 0:
					music10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,"message":message.encode('utf-8'),"link":plink,'picture':picture,"title":title,'description':description,'embed':url,'created':created,'genres':entity['genres'],'rated':0})
	return proc_posts,movies10,music10

def process_status(status,proc_posts,movies10,music10,args):
	i = args['i']
	scores = args['scores']
	movie_genres = args['movie']
	music_genres = args['music']
	picture = args['pic']
	title=''
	embed=''
	description=''
	score_now = 0
	post_id = status['id']
	if post_id not in proc_posts:
		proc_posts.append(post_id)
	else:
		return proc_posts,movies10,music10
	created = status['updated_time'][:10]

	if 'message' in status:
		message = status['message']
	else:
		message = ''
	if 'comments' in status:
		comments = status['comments']['data']
	else:
		comments = ''
	f_score = 0 #final score
	m_score = analysis.sentiment_analysis(message.encode('utf-8')) #message score
	if m_score >=-0.1:
		f_score +=1
	else:
		f_score -=1
	for c in comments:
		if c['from']['id'] == scores[i]['facebook_id']:
			c_score = 0
			c_score = analysis.sentiment_analysis(c['message'].encode('utf8'))	#comment_score
			if c_score >=-0.1:
				f_score+=1
			else:
				f_score-=1
	if f_score < 0:
		return proc_posts,movies10,music10
	message = re.sub('\n',' ', message)
	message = re.split('[ .,!?]',message)
	message = ' '.join(message[:8])
	results = text_analysis_freebase.getResults(message.encode('utf-8'))
	for entity in results:
		ubuff = 0
		if bool(entity):
			if entity['type'] == 'movie' and entity['genres']:
				for gen in entity['genres']:
					if (gen in movie_genres.keys()):
						ubuff += movie_genres[gen]
				ubuff = float(ubuff)/len(entity['genres'])
				score_now = float(scores[i]['movie_score']['movie_friend_score'])*ubuff
				if score_now > 0:
					title,url,description = youtubeAPI.getVideo(entity)
					if title:
						exist_flag = 0
						for it in movies10:
							if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]:
								exist_flag = 1
						if (exist_flag == 0):
							movies10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,"message":message.encode('utf-8'),'picture':picture,'title':title,'embed':url,'description':description,'created':created,'genres':entity['genres'],'rated':0})
			elif entity['type'] == 'music' and entity['genres']:
				for key in entity['genres']:
					if key in music_genres.keys():
						ubuff += music_genres[key]
				ubuff = float(ubuff)/len(entity['genres'])
				score_now = float(scores[i]['music_score']['music_friend_score'])*ubuff
				if score_now>0.0:
					title,url,description = youtubeAPI.getVideo(entity)
					if title:
						exist_flag = 0
						for it in music10:
							if ((post_id == it["post_id"]) and (url == it["embed"])) or url == it["embed"]:
								exist_flag = 1
						if exist_flag == 0:
							music10.append({"name":scores[i]['friend_name'],"f_id":scores[i]['facebook_id'],"post_id":post_id,"score":score_now,"message":message.encode('utf-8'),'picture':picture,'title':title,'embed':url,'description':description,'created':created,'genres':entity['genres'],'rated':0})
	return proc_posts,movies10,music10
