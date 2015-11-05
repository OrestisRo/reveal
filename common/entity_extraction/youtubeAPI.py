import requests,re
from pprint import pprint
import json
import urllib.parse
from pymongo import MongoClient
import Levenshtein as lev


#Given a youtube's video ID or a whole youtube url, return the possible entity from inside the title OR None.
def getEntity(vid,titled):
	key = "AIzaSyArhDVJIN3ogIeR1NqLfNDm-UEUtj6qZyk"
	embed=" "
	topics=None
	try:
		if 'youtube' in vid:
			dat = urlparse.urlparse(vid)
			frag = urlparse.parse_qs(dat.query)
			vid = frag['v'][0]
		elif 'youtu.be' in vid:
			dat = urlparse.urlparse(vid)
			dirty = dat.path
			vid = re.sub('[/]',"",dirty)
		elif 'gdata' in vid and 'youtube' in vid:
			spl = re.split('/',vid)
			vid = spl[-1]
	except:
		return None,None
	embed = 'https://www.youtube.com/embed/'+str(vid)
	client = MongoClient('127.0.0.1')
	db = client.entities
	youtube = db.youtube
	topics = youtube.find_one({"vid":vid})

	if topics and 'tid' in topics:
		topics = topics['tid']
	return topics,embed


def compareVideos(entity,items):
	name = None
	lev_score = 0
	best_match = {}
	best_match['score'] = 0
	buff = [0,0,0,0]
	if entity['type']=='music':
		name = entity['name'].lower().strip()
		buff[0] = name
		buff[1] = name + " official"
		buff[2] = name + " trailer"
		buff[3] = name + buff[1] + buff[2]
	elif entity['type']=='movie':
		name = entity['title'].lower().strip()
		buff[0] = name
		buff[1] = name + " official"
		buff[2] = name + " video"
		buff[3] = name + buff[1] + buff[2]
	if name:
		for item in items:
			for i in range(0,4):
				lev_score = lev.ratio(buff[i], item['title'])
				if lev_score > best_match['score']:
					best_match = item
					best_match['score'] = lev_score
	return best_match['title'],best_match['embed'],best_match['description']



def checkViews(results):
	maxViews = 0
	best = None
	for video in results:
		url = "https://www.googleapis.com/youtube/v3/videos?part=statistics&id={0}&maxResults=1&key=AIzaSyArhDVJIN3ogIeR1NqLfNDm-UEUtj6qZyk".format(video['id'])
		response = requests.get(url).json()
		if ('items' in response) and response['items'] != []:
			statistics = response['items'][0]['statistics']
			if int(statistics['viewCount']) > maxViews:
				best = video
				maxViews = int(statistics['viewCount'])
	if best:
		return best['title'], best['embed'], best['description']
	else:
		return None,None,None


def getVideo(entity):
	search_term,embed,title,description = None,None,None,None
	results = []
	if not isinstance(entity, str):
		pass
	else:
		search_term = entity
	if title==None:
		urls = []
		if search_term==None and entity['type']=='movie' and 'title' in entity:
			search_term = entity['title'] + " official trailer"
		if 'tid' in entity:
			for tid in entity['tid']:
				url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&q=&type=video&order=relevance&maxResults=1&key=AIzaSyArhDVJIN3ogIeR1NqLfNDm-UEUtj6qZyk&topicId={0}'.format(tid)
				urls.append(url)
		else:
			url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&q=&type=video&order=relevance&maxResults=1&key=AIzaSyArhDVJIN3ogIeR1NqLfNDm-UEUtj6qZyk&topicId={0}'.format(search_term)
			urls.append(url)
		for url in urls:
			try:
				test = requests.get(url).json()
			except ConnectionError:
				print ("Connection Error in getVideo.")
			if 'items' in test:
				if test['items']:
					item = test['items'][0]
					buff = {}
					# try:
					lang = item['snippet']['title']
						# if lang[0]!='en':
							# continue
					# except e:
						# print (e)
					embed = 'https://www.youtube.com/embed/{0}'.format(item['id']['videoId'])
					title = item['snippet']['title']
					description = item['snippet']['description']
					buff['title'] = title.lower().strip()
					buff['description'] = description
					buff['embed'] = embed
					buff['id'] = item['id']['videoId']
					results.append(buff)

	title, embed, description = checkViews(results)
	return title,embed,description
