from pattern.en import parsetree
import pattern.search
import math,time,re
from pymongo import MongoClient
import json
import Levenshtein as lev


entity_names = []
normal_nouns = []
results = []
flag_entity = 0
kinds_of_nouns = ['JJ','NN','NNP','NNP-PERS','NNS','VBN','VBG'] #TODO Be sure about NNP,VBG,NNS,VBN
numbers = ["IN","CD"]

def search(entry,cat):
	sep_flag = 0
	result = {}
	if type(entry) is 'list':
		" ".join(entry)
	else:
		extra = entry.strip()
		entry = re.sub('\(official\)','',entry.lower())
	mongo = MongoClient('127.0.0.1')
	db = mongo['entities']
	collection = db['freebase']
	try:
		qu = "\"{0}\"".format(entry.lower().strip())
	except:
		return result
	if cat:
		if "music" in cat.lower():
			cursor = collection.find({'$text': {'$search': qu},"type":"music"},{'score': {'$meta': 'textScore'}})
		elif "movie" in cat.lower():
			cursor = collection.find({'$text': {'$search': qu},"type":"movie"},{'score': {'$meta': 'textScore'}})
	else:
		cursor = collection.find({'$text': {'$search': qu}},{'score': {'$meta': 'textScore'}})
	if cursor.count() <= 0:
		sep_flag = 1
		if cat:
			if "music" in cat.lower():
				cursor = collection.find({'$text': {'$search': entry},"type":"music"},{'score': {'$meta': 'textScore'}})
			elif "movie" in cat.lower():
				cursor = collection.find({'$text': {'$search': entry},"type":"movie"},{'score': {'$meta': 'textScore'}})
		else:
			cursor = collection.find({'$text': {'$search': entry}},{'score': {'$meta': 'textScore'}})
	cursor.sort([('score', {'$meta': 'textScore'})]).limit(25)
	if cursor.count() <= 0 and cat:
		result = collection.find_one({'name':extra.strip(),'type':cat.lower()})
		if not result:
			result = {}
	else:
		best_match = {}
		best_score = 0
		for item in cursor:
			if item['score'] >=1:
				try:
					score = lev.ratio(str(item['name'].lower().strip().encode('utf8')),str(entry.lower().strip()))
				except:
					return result
				if score >= best_score:
					best_match = item
					best_score = score
		if best_match and best_score>0.7:
			if sep_flag == 0:
				if 'music' in best_match['type'].lower():
					result = {"type":"music","name":best_match['name'],"genres":best_match['genres'],"tid":best_match["mid"]}
				elif 'movie' in best_match['type'].lower():
					result = {"type":"movie","title":best_match['name'],"genres":best_match['genres'],"tid":best_match["mid"]}
			else:
				if best_score>0.9:
					if 'music' in best_match['type'].lower():
						result = {"type":"music","name":best_match['name'],"genres":best_match['genres'],"tid":best_match["mid"]}
					elif 'movie' in best_match['type'].lower():
						result = {"type":"movie","title":best_match['name'],"genres":best_match['genres'],"tid":best_match["mid"]}
	mongo.close()
	return result

def link_search(topic_id,title):
	mongo = MongoClient('127.0.0.1')
	db = mongo['entities']
	collection = db['freebase']
	response = collection.find_one({"mid":{"$in":[topic_id]} })
	result = {}
	if response:
		if 'music' in response['type'].lower():
			result = {"type":"music","name":response['name'],"genres":response['genres'],"tid":response["mid"]}
		elif 'movie' in response['type'].lower():
			result = {"type":"movie","title":response['name'],"genres":response['genres'],"tid":response["mid"]}

	return result

def extract_normal_nouns(tree):
	normal_nouns = []
	buff = []
	case_buff = []
	entry_types = []
	cc_flag = 0
	global count,kinds_of_nouns, brown_mapping1, entity_names, numbers
	for sentence in tree:
		for word in sentence:
			if word.string.lower() == 'music' or word.string.lower() == 'movie':
				pass
			elif word:
				if (word.tag in kinds_of_nouns) or (word.tag == 'CC') or (word.tag == 'DT') or (word.tag in numbers):
					if(word.tag == 'CC') and (cc_flag==0) and (buff != []):
						cc_flag = 1
						buff.append(word.string)
						entry_types.append(word.tag)
					elif (word.tag == 'DT'):
						dt_flag = 1
						buff.append(word.string)
						entry_types.append(word.tag)
					elif (word.tag in numbers):
						normal_nouns.append(buff)
						buff.append(word.string)
						normal_nouns.append(buff)
					elif (word.tag in kinds_of_nouns):
						buff.append(word.string)
						entry_types.append(word.tag)
					else:
						cc_flag = 0
				else:
					if len(buff):
						for b in range(0,len(buff)):
							if buff[b].lower() == 'and' and b!=0:
								pass
							else:
								normal_nouns.append(buff[b:])
						buff = []
						entry_types = []
		if len(buff):
			for b in range(0,len(buff)):
				if buff[b].lower() == 'and' and b!=0:
					pass
				else:
					normal_nouns.append(buff[b:])

	return normal_nouns

def getResults(text):
	global normal_nouns,flag_entity,flag_noun,results
	results = []
	tagged_text = parsetree(text, relations = True, lemmata = True)
	count=0
	candidates = extract_normal_nouns(tagged_text)
	for entry in candidates:
		entry = ' '.join(entry)
		check = search(entry,None)
		if check:
			results.append(check)
	return results
