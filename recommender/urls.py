from django.conf.urls import patterns, url

from recommender import views

urlpatterns = patterns('',
    url(r'^$', views.index.as_view(), name='index'),
    url(r'^init/$', views.handle_token.as_view(), name='handle_token'),
    url(r'^main/$', views.display_index.as_view(), name='display_index'),
    url(r'^movies/$', views.display_movies.as_view(), name='display_movies'),
    url(r'^movies_week/$', views.display_movies_week.as_view(), name='display_movies_week'),
    url(r'^movies_2_weeks/$', views.display_movies_2.as_view(), name='display_movies_2'),
    url(r'^music/$', views.display_music.as_view(), name='display_music'),
    url(r'^music_week/$', views.display_music_week.as_view(), name='display_music_week'),
    url(r'^music_2_weeks/$', views.display_music_2.as_view(), name='display_music_2'),
    url(r'^init_main/$', views.display_index_init.as_view(), name='display_index_init'),
    url(r'^scores/$', views.display_scores.as_view(), name='display_scores'),
    url(r'^plus_rated/$', views.plus_rate.as_view(), name='plus_rate'),
    url(r'^minus_rated/$', views.minus_rate.as_view(), name='minus_rate'),
    url(r'^reset_minus/$', views.reset_rate_minus.as_view(), name='reset_rate_minus'),
    url(r'^reset_plus/$', views.reset_rate_plus.as_view(), name='reset_rate_plus'),
)
