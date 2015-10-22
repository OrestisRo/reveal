from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response,render

from recommender.models import *
#FIX PATHS TO UTILITY SCRIPTS
from extraction import youtubeAPI
import extraction.initialize as init

from pymongo import MongoClient
from datetime import datetime,timedelta
import re,json,urlparse,requests,time,os

"""Both "index" and "handle_token" views,are obsolete as permissions in facebook's graph api have changed due to
    v2.x standarization and deprecation of v1.0. This proof-of-concept project developed considering v1.0,
    and thus is now inoperable. Still can be used for further study,changes and any implementation according to
    new v2.x API.
 """

 #Trivial function for facebook authorization
def index(request):
	auth_request = requests.get('https://www.facebook.com/dialog/oauth?client_id=236883073170435&redirect_uri=https://apps.facebook.com/recommendsys/init/&scope=read_stream,user_status,user_likes,user_friends,friends_status,friends_likes,friends_actions.music,friends_actions.video&response_type=code',allow_redirects=True)
	oAuthRedirect = auth_request.url
	template = loader.get_template('pages/auth.html')
	context = RequestContext(request,{"auth":oAuthRedirect})
	return HttpResponse(template.render(context))


#Trivial function for exchanging facebook code fragment for access token
def handle_token(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	users_collection = db.users

	app_id = '236883073170435'
	redirect = 'https://apps.facebook.com/recommendsys/init/'
	secret = '0ee7bfa0e9f036598e38d9b30a1c0f8f'
	code = request.REQUEST['code']
	app_info = {'client_id':app_id, 'redirect_uri':redirect,'client_secret':secret,'code':code}
	token_request = requests.get('https://graph.facebook.com/oauth/access_token', params=app_info)
	response = token_request.text
	access_token = urlparse.parse_qs(response)
	try:
		access = access_token['access_token'][0]
	except KeyError, e:
		print "----Access token key error here----"
		print e

	app_token_info = {'client_id':app_id,'client_secret':secret,'grant_type':'client_credentials'}
	app_token_req = requests.get('https://graph.facebook.com/oauth/access_token?',params=app_token_info)
	app_token = urlparse.parse_qs(app_token_req.text)
	debug_params = {'input_token':access_token['access_token'][0],'access_token':app_token['access_token'][0]}
	debug_request = requests.get('https://graph.facebook.com/debug_token?',params=debug_params)
	parsed = json.loads(debug_request.text)
	uid = parsed['data']['user_id']

	query = users_collection.find_one({'id':uid},{'id':'true','_id':False})
	if query: # Check if user exists
		request.session['id'] = query['id']
		return render(request,'pages/index.html',query)

	uid = init.overlaps(access,uid)
	request.session['id'] = uid
	query = users_collection.find_one({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
	user_info = query

	template = loader.get_template('pages/recap.html')
	context = RequestContext(request,{"user_info":user_info})
	return HttpResponse(template.render(context))

def display_index(request):
	print request.session['id']
	return render(request,'pages/index.html')

def display_index_init(request):
	uid = request.session['id']
	list_flag = 0
	changes_flag = 0

	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	users_collection = db.users
	user_info = users_collection.find_one({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
	form = request.POST
	list_flag = user_info['has_lists']

	for friend in user_info['scores']:
		cur_id = friend['facebook_id']
		new_movie = form.get('music_'+cur_id)
		new_music = form.get('movie_'+cur_id)
		if new_movie is not None:
			users_collection.update({'id':uid,'scores.facebook_id':cur_id},{'$set':{'scores.$.movie_score.movie_friend_score':new_movie}})
		if new_music is not None:
			users_collection.update({'id':uid,'scores.facebook_id':cur_id},{'$set':{'scores.$.music_score.music_friend_score':new_music}})

	if list_flag == 0:
		init.init_lists(uid)


	return render(request,'pages/index.html')

def display_movies(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	uid = request.session['id']
	movies = collection.find_one({'id':uid},{'movies10':'true','_id':False})['movies10']
	ex = str(datetime.now() - timedelta(days=2))[:10]

	movies10 = []
	for item in movies:
		if item['created'] > ex:
			movies10.append(item)
		else:
			break
	movies10 = sorted(movies10, key=lambda k:k['score'])
	movies10 = movies10[::-1]
	if len(movies10) > 10:
		movies10 = movies10[:10]
	elif len(movies10) == 0:
		movies10 = get_movie(uid)
	time = 0
	return render(request,'pages/fb_movies.html',{'movies':movies10,'time':time})


def display_movies_week(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	uid = request.session['id']
	movies = collection.find_one({'id':uid},{'movies10':'true','_id':False})['movies10']
	ex = str(datetime.now() - timedelta(days=7))[:10]

	movies10 = []
	for item in movies:
		if item['created'] > ex:
			movies10.append(item)
		else:
			break
	movies10 = sorted(movies10, key=lambda k:k['score'])
	movies10 = movies10[::-1]
	if len(movies10) > 10:
		movies10 = movies10[:10]
	elif len(movies10) == 0:
		movies10 = get_movie(uid)
	time = 1
	return render(request,'pages/fb_movies.html',{'movies':movies10,'time':time})



def display_movies_2(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users

	uid = request.session['id']
	movies = collection.find_one({'id':uid},{'movies10':'true','_id':False})['movies10']
	ex = str(datetime.now() - timedelta(days=14))[:10]

	movies10 = []
	for item in movies:
		if item['created'] > ex:
			movies10.append(item)
		else:
			break
	movies10 = sorted(movies10, key=lambda k:k['score'])
	movies10 = movies10[::-1]
	if len(movies10) > 10:
		movies10 = movies10[:10]
	elif len(movies10) == 0:
		movies10 = get_movie(uid)
	time = 2
	return render(request,'pages/fb_movies.html',{'movies':movies10,'time':time})



def display_music(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	uid = request.session['id']
	music = collection.find_one({'id':uid},{'music10':'true','_id':False})['music10']
	ex = str(datetime.now() - timedelta(days=2))[:10]

	music10 = []
	for item in music:
		if item['created'] > ex:
			music10.append(item)
		else:
			break
	music10 = sorted(music10, key=lambda k:k['score'])
	music10 = music10[::-1]
	if len(music10) > 10:
		music10 = music10[:10]
	elif len(music10) == 0:
		music10 = get_music(uid)
	template = loader.get_template('pages/fb_music.html')
	time = 0
	context = RequestContext(request,{"music":music10,"time":time})
	return HttpResponse(template.render(context))


def display_music_week(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	uid = request.session['id']
	music = collection.find_one({'id':uid},{'music10':'true','_id':False})['music10']
	ex = str(datetime.now() - timedelta(days=7))[:10]

	music10 = []
	for item in music:
		if item['created'] > ex:
			music10.append(item)
		else:
			break
	music10 = sorted(music10, key=lambda k:k['score'])
	music10 = music10[::-1]
	if len(music10) > 10:
		music10 = music10[:10]
	elif len(music10) == 0:
		music10 = get_music(uid)
	template = loader.get_template('pages/fb_music.html')
	time = 1
	context = RequestContext(request,{"music":music10,"time":time})
	return HttpResponse(template.render(context))


def display_music_2(request):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	uid = request.session['id']
	music = collection.find_one({'id':uid},{'music10':'true','_id':False})['music10']
	ex = str(datetime.now() - timedelta(days=14))[:10]

	music10 = []
	for item in music:
		if item['created'] > ex:
			music10.append(item)
		else:
			break
	music10 = sorted(music10, key=lambda k:k['score'])
	music10 = music10[::-1]
	if len(music10) > 10:
		music10 = music10[:10]
	elif len(music10) == 0:
		music10 = get_music(uid)
	template = loader.get_template('pages/fb_music.html')
	time = 2
	context = RequestContext(request,{"music":music10,"time":time})
	return HttpResponse(template.render(context))



def get_movie(uid):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	movie_genres = collection.find_one({'id':uid},{'movie_genres':'true','_id':False})['movie_genres']
	best = None
	best2 = None
	score = 0
	movies10 = []
	if movie_genres:
		score = max(movie_genres.values())
	for genre in movie_genres:
		if movie_genres[genre]==score:
			best = genre
	heap = {best:score}
	if best:
		to_string = " ".join(heap.keys())
		search_term = "{0} movie trailer".format(to_string)
		title,url,description = youtubeAPI.getVideo(search_term)
		if title:
			movies10.append({"name": "Your list was empty,\nso we make this recommendation.","score":11,'title':title,'embed':url,'description':description})
		for genre in movie_genres:
			if len(heap) >1:
				break
			elif movie_genres[genre] == score and genre != best:
				best2 = genre
				heap[genre] = movie_genres[genre]
		if len(heap) == 1:
			score-=1
			for genre in movie_genres:
				if len(heap) >1:
					break
				elif movie_genres[genre] == score:
					best2 = genre
					heap[genre] = movie_genres[genre]
		if len(heap) > 1:
			to_string = best2
			search_term = "{0} movie trailer".format(to_string)
			title,url,description = youtubeAPI.getVideo(search_term)
			if title:
				movies10.append({"name": "Your list was empty,\nso we make this recommendation.","score":11,'title':title,'embed':url,'description':description})
			to_string = " ".join(heap.keys())
			search_term = "{0} movie trailer".format(to_string)
			title,url,description = youtubeAPI.getVideo(search_term)
			if title:
				movies10.append({"name": "Your list was empty,\nso we make this recommendation.","score":10,'title':title,'embed':url,'description':description})
	return movies10


def get_music(uid):
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	collection = db.users
	music_genres = collection.find_one({'id':uid},{'music_genres':'true','_id':False})['music_genres']
	best = None
	best2 = None
	score = 0
	music10 = []
	if music_genres:
		score = max(music_genres.values())
	for genre in music_genres:
		if music_genres[genre]==score:
			best = genre
	heap = {best:score}
	if best:
		to_string = " ".join(heap.keys())
		search_term = "{0}".format(to_string)
		title,url,description = youtubeAPI.getVideo(search_term)
		if title:
			music10.append({"name": "Your list was empty,\nso we make this recommendation.","score":11,'title':title,'embed':url,'description':description})
		for genre in music_genres:
			if len(heap) >1:
				break
			elif music_genres[genre] == score and genre != best:
				best2 = genre
				heap[genre] = music_genres[genre]
		if len(heap) == 1:
			score-=1
			for genre in music_genres:
				if len(heap) >1:
					break
				elif music_genres[genre] == score:
					best2 = genre
					heap[genre] = music_genres[genre]
		if len(heap) > 1:
			to_string = best2
			search_term = "{0}".format(to_string)
			title,url,description = youtubeAPI.getVideo(search_term)
			if title:
				music10.append({"name": "Your list was empty,\nso we make this recommendation.","score":10,'title':title,'embed':url,'description':description})
			to_string = " ".join(heap.keys())
			search_term = "{0}".format(to_string)
			title,url,description = youtubeAPI.getVideo(search_term)
			if title:
				music10.append({"name": "Your list was empty,\nso we make this recommendation.","score":9,'title':title,'embed':url,'description':description})
	return music10

def display_scores(request):
	uid = request.session['id']
	client = MongoClient('127.0.0.1')
	db = client.recommendation_db
	users_collection = db.users
	query = users_collection.find_one({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
	user_info = query

	template = loader.get_template('pages/recap.html')
	context = RequestContext(request,{"user_info":user_info})
	return HttpResponse(template.render(context))

def plus_rate(request):
	uid = request.session['id']
	genres = request.GET['genres']
	typ = request.GET['type']
	pid = request.GET['id']
	rating = request.GET['rated']
	cl = MongoClient('127.0.0.1')
	db = cl.recommendation_db
	coll = db.users
	for genre in json.loads(genres):
		try:
			if typ == 'music':
				coll.update({'id':uid,'music10.post_id':pid},{"$set":{'music10.$.rated':1}})
				whole = 'music_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:1}})
			elif typ == 'movie':
				coll.update({'id':uid,'movies10.post_id':pid},{"$set":{'movies10.$.rated':1}})
				whole = 'movie_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:1}})
		except Exception as e:
			print e
	return HttpResponse('OK')

def minus_rate(request):
	uid = request.session['id']
	genres = request.GET['genres']
	typ = request.GET['type']
	pid = request.GET['id']
	cl = MongoClient('127.0.0.1')
	db = cl.recommendation_db
	coll = db.users
	for genre in json.loads(genres):
		try:
			if typ == 'music':
				coll.update({'id':uid,'music10.post_id':pid},{"$set":{'music10.$.rated':-1}})
				whole = 'music_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:-1}})
			elif typ == 'movie':
				coll.update({'id':uid,'movies10.post_id':pid},{"$set":{'movies10.$.rated':-1}})
				whole = 'movie_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:-1}})
		except Exception as e:
			print e
	return HttpResponse('OK')

def reset_rate_plus(request):
	uid = request.session['id']
	genres = request.GET['genres']
	typ = request.GET['type']
	pid = request.GET['id']
	cl = MongoClient('127.0.0.1')
	db = cl.recommendation_db
	coll = db.users
	for genre in json.loads(genres):
		try:
			if typ == 'music':
				coll.update({'id':uid,'music10.post_id':pid},{"$set":{'music10.$.rated':0}})
				whole = 'music_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:-1}})
			elif typ=='movie':
				coll.update({'id':uid,'movies10.post_id':pid},{"$set":{'movies10.$.rated':0}})
				whole = 'movie_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:-1}})
		except Exception as e:
			print e
	return HttpResponse('OK')

def reset_rate_minus(request):
	uid = request.session['id']
	genres = request.GET['genres']
	typ = request.GET['type']
	pid = request.GET['id']
	cl = MongoClient('127.0.0.1')
	db = cl.recommendation_db
	coll = db.users
	for genre in json.loads(genres):
		try:
			if typ == 'music':
				coll.update({'id':uid,'music10.post_id':pid},{"$set":{'music10.$.rated':0}})
				whole = 'music_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:+1}})
			elif typ== 'movie':
				coll.update({'id':uid,'movies10.post_id':pid},{"$set":{'movies10.$.rated':0}})
				whole = 'movie_genres.{0}'.format(genre)
				coll.update({'id':uid},{"$inc":{whole:+1}})
		except Exception as e:
			print e
	return HttpResponse('OK')
