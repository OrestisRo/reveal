from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response,render
from django.views.generic import View
from recommender.models import *

from pymongo import MongoClient
from datetime import datetime,timedelta
import re,json,urllib.parse,requests,time,os
from common.entity_extraction import youtubeAPI
"""Both "index" and "handle_token" View,are obsolete as permissions in facebook's graph api have changed due to
    v2.x standarization and deprecation of v1.0. This proof-of-concept project developed considering v1.0,
    and thus is now inoperable. Still can be used for further study,changes and any implementation according to
    new v2.x API.
 """

 #Trivial function for facebook authorization
class index(View):
    def get(self,request):
        auth_request = requests.get('https://www.facebook.com/dialog/oauth?client_id=236883073170435&redirect_uri=https://apps.facebook.com/recommendsys/init/&scope=read_stream,user_status,user_likes,user_friends,friends_status,friends_likes,friends_actions.music,friends_actions.video&response_type=code',allow_redirects=True)
        oAuthRedirect = auth_request.url
        template = loader.get_template('pages/auth.html')
        context = RequestContext(request,{"auth":oAuthRedirect})
        return HttpResponse(template.render(context))


#Trivial function for exchanging facebook code fragment for access token
class handle_token(View):
    # db = MongoClient('127.0.0.1').recommendation_db
    # users_collection = db.users
    # friends_collection = db.friends
    app_id = '236883073170435'
    secret = '0ee7bfa0e9f036598e38d9b30a1c0f8f'

    def get(self,request):
        code = request.REQUEST['code']
        token = self.ask_token(code)
        uid = self.getUserId(token)
        # query = self.users_collection.find_one({'id':uid},{'id':'true','_id':False})
        query = User.objects(fid=uid).only('fid').first()
        if query: # Check if user exists
            request.session['id'] = query['id']
            return render(request,'pages/index.html',query)

        uid = self.overlaps(token,uid)
        request.session['id'] = uid #save session
        query = User.objects(fid=uid).exclude('music_genres','movie_genres','music_categories','movie_categories')
        # ({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
        user_info = query.to_json()

        template = loader.get_template('pages/recap.html')
        context = RequestContext(request,{"user_info":user_info})
        return HttpResponse(template.render(context))

    def ask_token(self,code):
        redirect = 'https://apps.facebook.com/recommendsys/init/'
        app_info = {'client_id':self.app_id, 'redirect_uri':redirect,'client_secret':self.secret,'code':code}
        token_request = requests.get('https://graph.facebook.com/oauth/access_token', params=app_info)
        response = token_request.text
        access_token = urllib.parse.parse_qs(response)
        try:
            token = access_token['access_token'][0]
        except(KeyError, e):
            print(e,"KEY ERROR")
            token = None
        return token

    def getUserId(self,token):
        app_token_info = {'client_id':self.app_id,'client_secret':self.secret,'grant_type':'client_credentials'}
        app_token_req = requests.get('https://graph.facebook.com/oauth/access_token?',params=app_token_info)
        app_token = urllib.parse.parse_qs(app_token_req.text)
        access_token = app_token['access_token'][0]
        debug_params = {'input_token':token,'access_token':access_token}
        debug_request = requests.get('https://graph.facebook.com/debug_token?',params=debug_params)
        parsed = json.loads(debug_request.text)
        uid = parsed['data']['user_id']
        return uid

    def overlaps(self,token,uid):
        user_movie_gens = {}
        user_music_gens = {}
        user = Friend.objects(fid=uid).first()#find_one({'id':uid}) #Search for new user, in friends of old users
        if not user:
            user_movie_gens, user_music_gens,user_movie_cat,user_music_cat = fb_info.createProfile(token)
        else:
            user = User()
            user['token'] = access_token
            user['has_lists'] = 0
            user['proc_posts'] = []
            user['time'] = 0
            user.save()
            # self.users_collection.insert(user)

        uid=fb_info.calcOverlap(user['movie_genres'],user['music_genres'],user['movie_categories'],user['music_categories'],token)
        return uid

class display_index(View):
    def get(self,request):
        return render(request,'pages/index.html')

class display_index_init(display_index):
    # db = MongoClient('127.0.0.1').recommendation_db
    # users_collection = db.users
    list_flag = 0

    def get(self,request):
        uid = '520078670'
        user_info = User.objects(fid=uid).exclude('music_genres','movie_genres','music_categories','movie_categories')
        # self.users_collection.find_one({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
        form = request.POST
        self.list_flag = user_info['has_lists']
        self.update_scores(uid,user_info['scores'],form)

        if not list_flag:
            fb_info.readStatusAndCreateLists(uid)
        return render(request,'pages/index.html')


    def update_scores(self,uid,friends_list,new_form):
        for friend in friends_list:
            cur_id = friend['facebook_id']
            new_movie = new_form.get('music_'+cur_id)
            new_music = new_form.get('movie_'+cur_id)
            if new_movie is not None:
                User.objects.filter(                Q(fid=uid)&Q(scores__facebook_id=cur_id)).update(**{'set__scores__$__movie_score__movie_friend_score':new_movie}
                )
                # self.users_collection.update({'id':uid,'scores.facebook_id':cur_id},{'$set':{'scores.$.movie_score.movie_friend_score':new_movie}})
            if new_music is not None:
                User.objects.filter(                Q(fid=uid)&Q(scores__facebook_id=cur_id)).update(**{'set__scores__$__music_score__music_friend_score':new_music}
                )
                # self.users_collection.update({'id':uid,'scores.facebook_id':cur_id},{'$set':{'scores.$.music_score.music_friend_score':new_music}})

class display_movies(View):
    time_window = 2
    time = 0
    db = MongoClient('127.0.0.1').recommendation_db
    users_collection = db.users

    def get(self,request):
        uid = '520078670'
        movies = User.objects(fid=uid).only('movies10').first()['movies10']
        # movies = self.users_collection.find_one({'id':uid},{'movies10':'true','_id':False})['movies10']
        ex = str(datetime.now() - timedelta(days=self.time_window))[:10]

        movies10 = filter(lambda x:x['created'] > ex,movies)
        movies10 = sorted(movies10, key=lambda k:k['score'])[::-1]
        if len(movies10) > 10:
            movies10 = movies10[:10]
        elif len(movies10) == 0:
            movies10 = self.get_movie(uid)
        return render(request,'pages/fb_movies.html',{'movies':movies10,'time':self.time})

    def get_movie(self,uid):
        movie_genres = User.objects(fid=uid).only('movie_genres').first()['movie_genres']
        # movie_genres = self.users_collection.find_one({'id':uid},{'movie_genres':'true','_id':False})['movie_genres']
        score1 = {}
        score2 = {}
        movies10 = []
        if movie_genres and len(movie_genres)>6:
            sorted_genres = sorted(movie_genres.items(),key=lambda x:x[1])[::-1][:6]
            score1 = dict(sorted_genres[:3])
            score2 = dict(sorted_genres[4:6])
            to_string1,to_string2 = " ".join(score1.keys())," ".join(score2.keys())
            search_term1 = "{0} movie trailer".format(to_string1)
            search_term2 = "{0} movie trailer".format(to_string2)
            title,url,description = youtubeAPI.getVideo(search_term1)
            if title:
                movies10.append({"name": "Your list was empty,\nso this recommendation was made automatically.","score":11,'title':title,'embed':url,'description':description})
            title,url,description = youtubeAPI.getVideo(search_term2)
            if title:
                movies10.append({"name": "Your list was empty,\nso this recommendation was made automatically.","score":11,'title':title,'embed':url,'description':description})

        return movies10



class display_movies_week(display_movies):
    time_window = 7
    time = 1



class display_movies_2(display_movies):
    time_window = 14
    time = 2

class display_music(View):
    time_window = 2
    time = 0
    db = MongoClient('127.0.0.1').recommendation_db
    users_collection = db.users

    def get(self,request):
        uid = '520078670'
        music = User.objects(fid=uid).only('music10').first()['music10']
        """
        ATT!!:removed as current data is old
        # ex = str(datetime.now() - timedelta(days=self.time_window))[:10]
        # music10 = filter(lambda x:x['created'] > ex,music)
        """
        music10 = sorted(music, key=lambda k:k['score'])[::-1][:10]
        if len(music10) > 10:
            music10 = music10[:10]
        elif len(music10) == 0:
            music10 = self.get_music(uid)
        template = loader.get_template('pages/fb_music.html')
        context = RequestContext(request,{"music":music10,"time":self.time})
        return HttpResponse(template.render(context))

    def get_music(uid):
        music_genres = User.objects(fid=uid).only('music_genres')['music_genres']
        # music_genres = self.users_collection.find_one({'id':uid},{'music_genres':'true','_id':False})['music_genres']
        score1 = {}
        score2 = {}
        music10 = []
        if music_genres and len(music_genres)>6:
            sorted_genres = sorted(music_genres.items(),key=lambda x:x[1])[::-1][:6]
            score1 = dict(sorted_genres[:3])
            score2 = dict(sorted_genres[4:6])
            to_string1,to_string2 = " ".join(score1.keys())," ".join(score2.keys())
            search_term1 = "{0}".format(to_string1)
            search_term2 = "{0}".format(to_string2)
            title,url,description = youtubeAPI.getVideo(search_term1)
            if title:
                music10.append({"name": "Your list was empty,\nso this recommendation was made automatically.","score":11,'title':title,'embed':url,'description':description})
            title,url,description = youtubeAPI.getVideo(search_term2)
            if title:
                music10.append({"name": "Your list was empty,\nso this recommendation was made automatically.","score":11,'title':title,'embed':url,'description':description})
        return music10

class display_music_week(display_music):
    time_window = 7
    time = 1


class display_music_2(display_music):
    time_window = 14
    time = 2




class display_scores(View):
    db = MongoClient('127.0.0.1').recommendation_db
    users_collection = db.users

    def get(self,request):
        uid = '520078670'
        query = User.objects(fid=uid).exclude('music_genres','music_categories','movie_genres','movie_categories')
        # query = self.users_collection.find_one({"id":uid},{'music_genres':False,'movie_genres':False,'music_categories':False,'movie_categories':False,'_id':False,'token':False})
        user_info = query.to_json()
        template = loader.get_template('pages/recap.html')
        context = RequestContext(request,{"user_info":user_info})
        return HttpResponse(template.render(context))

class rate(View):
    db = MongoClient('127.0.0.1').recommendation_db
    users_collection = db.users
    rating = 0
    boost = 0
    def get(self,request):
        uid = '520078670'
        genres = request.GET['genres']
        typ = request.GET['type']
        pid = request.GET['id']
        for genre in json.loads(genres):
            try:
                if typ == 'music':
                    User.objects.filter(Q(fid=uid) & Q(music10__post_id=pid)).update(**{'set__music10__$__rated':rating})
                    # self.users_collection.update({'id':uid,'music10.post_id':pid},{"$set":{'music10.$.rated':rating}})
                    whole = 'inc__music_genres__{0}'.format(genre)
                    User.objects(fid=uid).update(**{whole:boost})
                    # whole = 'music_genres.{0}'.format(genre)
                    # self.users_collection.update({'id':uid},{"$inc":{whole:boost}})
                elif typ == 'movie':
                    User.objects.filter(Q(fid=uid) & Q(movies10__post_id=pid)).update(**{'set__movies10__$__rated':rating})
                    # self.users_collection.update({'id':uid,'movies10.post_id':pid},{"$set":{'movies10.$.rated':rating}})
                    whole = 'inc__movie_genres__{0}'.format(genre)
                    User.objects(fid=uid).update(**{whole:boost})
                    # whole = 'movie_genres.{0}'.format(genre)
                    # self.users_collection.update({'id':uid},{"$inc":{whole:boost}})
            except Exception as e:
                print(e)
        return HttpResponse('OK')

class plus_rate(rate):
    rating = 1
    boost = 1
class minus_rate(rate):
    rating = -1
    boost = -1

class reset_rate_plus(rate):
    rating = 0
    boost = -1

class reset_rate_minus(rate):
    rating = 0
    boost = 1
