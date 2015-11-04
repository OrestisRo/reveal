from pattern.en import parse,tag,tokenize,conjugate,mood
from pattern.vector import stem,LEMMA,PORTER
from pymongo import MongoClient
import nltk
import Levenshtein as lev
import string,math,time,os,yaml,pprint,re,HTMLParser

global count
count = 0

def dictionary_tag(sentence):
	client = MongoClient('127.0.0.1')
	db = client.dictionaries
	collection = db.sfu
	emots = db.emoticons
	for word in sentence:
		qu = emots.find_one({'word':word[0].encode('utf-8').strip(),'pos':'em'})
		if qu:
			word[1] = 'em'
			word.append(qu['polarity'])
			continue
		qu = word[0].encode('utf-8').strip().lower()
		qu = re.sub(":"," ",qu)
		if 'n\'t' in qu or 'not' in qu or qu == 'not' or qu == 'n\'t' or qu == 'no':
			word[1] = 'neg'
			word.append("")
			continue
		single = None
		single = collection.find_one({'word':qu,'pos':word[1][:2].lower()})
		if single:	#word as it is
			word[1] = single['pos']
			word.append(single['polarity'])
		else: #convert to 1 person present tense
			qu = conjugate(qu,'1sg')
			single = collection.find_one({'word':qu,'pos':word[1][:2].lower()})
			if single:
				word[1] = single['pos']
				word.append(single['polarity'])
			else:
				word.append('')
	return sentence

def sentiment_score(sentence):
	summ = 0.0
	cl = MongoClient('127.0.0.1')
	db = cl.dictionaries
	coll = db.sfu
	ranks = ['jj','rb','nn','vb']
	for index,word in enumerate(sentence):
		token_score = 0.0
		if word[1]=='em':
			token_score = float(word[2])
		elif word[1] in ranks:
			rec = 1
			token_score=float(word[2])
			while index-rec>=0 and sentence[index-rec][1] != 'CC' and 'VB' not in sentence[index-rec][1] and sentence[index-rec][0] not in ['.','!']:
				bef = sentence[index-rec]
				intens = coll.find_one({'word':bef[0],'pos':'int'})
				if intens:
					if bef[2]:
						summ-=float(bef[2])
					token_score*= 1+float(intens['polarity'])
				elif bef[1] == "neg":
					token_score-=4*cmp(token_score,0)
				rec+=1
			word[2]=token_score
		else:
			token_score=0.0
		if cmp(token_score,0) == -1:
			token_score = token_score / 1.5
		summ+= token_score
	summ = round(summ,1)
	return summ

def sentiment_analysis(message):
	actual_range = 2
	final = []
	message = re.sub("(@[A-Za-z0-9]+)|( RT)|( rt)|(\w+:\/\/\S+)"," ",message).strip() #filter usernames,urls
	message = re.sub('#',"",message)
	message = filter(lambda x: x in string.printable, message) #filter non printable characters
	message = HTMLParser.HTMLParser().unescape(message) #unescape html
	tokenized = tokenize(message,puctuation='.!?:')
	tokenized = filter(bool,tokenized)
	tok1=[]
	for index,it in enumerate(tokenized):
		mod = mood(it)
		if '?' in it or mod=='conditional':
			continue
		tok1.append(it.strip())
	score = 0.0
	possed = [re.split(' ',sentence)for sentence in tok1]
	possed = [nltk.pos_tag(sentence) for sentence in possed]
	final = []
	for sentence in possed:
		check = []
		for entry in sentence:
			check.append(list(entry))
		final.append(check)
	range_count=0
	for sentence in final:
		sentence = dictionary_tag(sentence)
		score = score + sentiment_score(sentence)
	return score



















#FOR URBAN
		# cursor = collection.find({ '$text': { '$search': qu,'$language':'en' } },{ 'score': { '$meta': "textScore" },'_id':False})
		# cursor.sort([('score', {'$meta': 'textScore'})]).limit(15)
		# elif cursor.count() != 0:
		# 	for item in cursor:
		# 		if item['score'] <1 and item['word']!=best_match['word']:
		# 			score = lev.distance(item['word'].lower().strip(),word[0].lower().strip())
		# 			if score >= best_score:
		# 				best_match = item
		# 				best_score = score
		# if 'JJ' in word[1] or 'RB' in word[1] or 'UH' in word[1] and best_match is not None:
		# 	urban_single = None
		# 	urban_single = urban.find_one({'word':word[0].encode('utf8')})
		# 	if urban_single:
		# 		best_match = urban_single
		# 		best_score = 0
		# 	else:
		# 		cursor2 = urban.find({ '$text': { '$search': word[0].encode('utf-8'),'$language':'en' } },{ 'score': { '$meta': "textScore" },'_id':False})
		# 		cursor2.sort([('score', {'$meta': 'textScore'})]).limit(15)
		# 		if cursor2.count()!=0:
		# 			for item in cursor2:
		# 				if item['score'] >=1:
		# 					score = lev.distance(item['word'].lower().strip().encode('utf-8'),word[0].lower().strip().encode('utf-8'))
		# 					if score < best_score and item['word']!=best_match['word']:
		# 						best_match = item
		# 						best_score = score>>>>>>> destination
