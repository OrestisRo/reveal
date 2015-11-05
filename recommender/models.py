from django.db import models
from mongoengine import *
# Create your models here.
class User(Document):
    name =   StringField(max_length=255)
    fid =   StringField(max_length=255)
    token =   StringField(max_length=255)
    total_weight =  FloatField()
    movie_categories = ListField()
    movie_genres = DictField()
    movies_scores=  FloatField()
    music_categories = ListField()
    music_genres = DictField()
    music_scores =  FloatField()
    music10 = ListField()
    movies10 = ListField()

class Friend(Document):
    name =   StringField(max_length=255)
    fb_id =   StringField(max_length=255)
    total_friend_weight =  FloatField()
    movie_genres = DictField()
    music_genres = DictField()
    music_list = ListField()
    movies_list = ListField()
