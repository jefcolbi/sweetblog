from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.conf import settings
from . import views, api_views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('collections/', views.CollectionListView.as_view(), name='collection_list'),
    path('collection/<str:name>/', views.CollectionDetailView.as_view(), name='collection_detail'),
    path('article/<str:title>-<str:type>-<str:aid>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('add-article/', login_required(views.AddMarkdownArticleView.as_view()), name='article_add'),
    path('edit-article/<str:aid>/', login_required(views.EditMarkdownArticleView.as_view()), name='article_edit'),
    path('add-page/', login_required(views.AddMarkdownPageView.as_view()), name='page_add'),
    path('edit-page/<str:canonical_title>/', login_required(views.EditMarkdownPageView.as_view()), name='page_edit'),
    path('tags/', views.TagListView.as_view(), name='tag_list'),
    path('tag/<slug:slug>/', views.TagDetailView.as_view(), name='tag_detail'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('dal/', views.TagAutocomplete.as_view(), name="tag_autocomplete"),
    
    # Authentication URLs
    path('auth/connect/', views.ConnectionView.as_view(), name='sweetblog_connection'),
    path('auth/code/', views.CodeView.as_view(), name='sweetblog_code'),
    path('auth/profile/', views.ProfileView.as_view(), name='sweetblog_profile'),
    
    # API endpoints
    path('api/mistune/', api_views.MistuneView.as_view(), name='mistune_api'),
    path('api/mark-as-read/', views.MarkArticleAsReadView.as_view(), name='mark_as_read'),
    path('api/like-dislike/', views.LikeDislikeView.as_view(), name='like_dislike'),
    path('api/submit-comment/', views.CommentView.as_view(), name='submit_comment'),

    path('<str:canonical_title>/', views.MarkdownPageView.as_view(), name='page_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)