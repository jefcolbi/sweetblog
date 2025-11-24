from gettext import gettext
from pprint import pprint

import requests.adapters
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, TemplateView
from django.conf import settings
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.db.models import F, Avg, ExpressionWrapper, fields
from datetime import timedelta
from meta.views import Meta
from random_username.generate import generate_username
import hashlib
from sweetblog.models import (MarkdownArticle, Collection, Category,
                              MarkdownPage, TempCode, SweetblogProfile,
                              ArticleRead, Comment)
from sweetblog.forms import MarkdownArticleForm, EmailForm, CodeForm, ProfileForm, MarkdownPageForm
from taggit.models import Tag
from dal import autocomplete
from crawlerdetect import CrawlerDetect

User = get_user_model()


class BlogSettingsMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        css_framework_theme = getattr(settings, 'CSS_FRAMEWORK_THEME', None)
        blog_name = getattr(settings, 'BLOG_NAME', 'SweetBlog')

        if css_framework_theme:
            base_template = f"sweetblog/{css_framework}/base-{css_framework_theme}.html"
        else:
            base_template = f'sweetblog/{css_framework}/base.html'

        context['css_framework'] = css_framework
        context['base_template'] = base_template
        context['css_framework_theme'] = css_framework_theme
        context['blog_name'] = blog_name
        context['meta'] = self.get_meta()
        return context

    def get_meta(self):
        """Returns a Meta's object"""
        return


class BaseListView(BlogSettingsMixin, ListView):
    paginate_by = 20
    context_object_name = 'articles'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        return context


class HomeView(BaseListView):
    model = MarkdownArticle
    template_name = 'home.html'
    
    def get_queryset(self):
        return MarkdownArticle.objects.filter(
            status=MarkdownArticle.PUBLISHED
        ).order_by('-created_at')

    def get_meta(self):
        return Meta(author=getattr(settings, "BLOG_AUTHOR", "admin"),
                    title=getattr(settings, "BLOG_NAME", "SweetBlog"),
                    description=getattr(settings, "BLOG_DESCRIPTION", ""),
                    keywords=[_(key) for key in getattr(settings, "META_DEFAULT_KEYWORDS", [])])


class CollectionDetailView(BaseListView):
    template_name = 'collection_detail.html'
    
    def get_queryset(self):
        self.collection = get_object_or_404(
            Collection, 
            normalized_name=self.kwargs['name']
        )
        return MarkdownArticle.objects.filter(
            collection=self.collection,
            status=MarkdownArticle.PUBLISHED
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.collection
        context['meta'] = self.collection.as_meta(self.request)
        return context


class ArticleDetailView(BlogSettingsMixin, DetailView):
    model = MarkdownArticle
    template_name = 'article_detail.html'
    context_object_name = 'article'
    
    def get_object(self):
        return get_object_or_404(
            MarkdownArticle,
            id=int(self.kwargs['aid'], 16),
            status=MarkdownArticle.PUBLISHED
        )
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{self.template_name}']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        
        if self.object.collection:
            context['related_articles'] = MarkdownArticle.objects.filter(
                collection=self.object.collection,
                status=MarkdownArticle.PUBLISHED
            ).exclude(id=self.object.id)[:5]
        else:
            context['related_articles'] = []

        context['meta'] = self.object.as_meta(self.request)

        try:
            user_id = self.request.user.id
        except:
            user_id = None

        article_read: ArticleRead = ArticleRead.objects.filter(article_id=self.object.id,
                                device=self.request.device).first()
        if not article_read:
            article_read = ArticleRead.objects.create(article=self.object, device=self.request.device)
        
        context['article_read'] = article_read
        context['liked'] = article_read.liked if article_read.liked else False
        context['disliked'] = article_read.disliked if article_read.disliked else False
        
        # Get like and dislike counts
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self.object)
        context['like_count'] = ArticleRead.objects.filter(
            article_ct=content_type,
            article_id=self.object.id,
            liked=True
        ).count()
        context['dislike_count'] = ArticleRead.objects.filter(
            article_ct=content_type,
            article_id=self.object.id,
            disliked=True
        ).count()
        
        # Get comments for the article
        # Get or create the hidden root comment
        root_comment: Comment = self.object.get_hidden_first_comment()
        
        # if not root_comment:
        #     # Create the hidden root comment if it doesn't exist
        #     root_comment = Comment.objects.create(
        #         article_ct=content_type,
        #         article_id=self.object.id,
        #         device=None,
        #         content='',
        #         tn_parent=None
        #     )
        
        # Get all comments for this article (excluding the root)
        comments_tree = root_comment.get_descendants_tree(cache=False)
        pprint(comments_tree)

        print(root_comment.get_descendants_tree_display())
        
        # Build comment tree structure
        # comment_tree = []
        # for comment in comments:
        #     # Add username to each comment
        #     if comment.device and comment.device.user:
        #         comment.username = comment.device.user.get_full_name() or comment.device.user.username
        #     else:
        #         comment.username = 'Anonymous'
        #
        #     # Calculate display level (subtract 1 for hidden root)
        #     comment.display_level = comment.tn_level - 1
        #
        #     # Add flag to identify first-level comments (for Facebook-style threading)
        #     comment.is_first_level = comment.tn_level == 1
        #
        #     comment_tree.append(comment)
        
        context['comments'] = comments_tree
        context['comment_count'] = root_comment.get_descendants_count()

        average_duration_minutes = ArticleRead.objects.filter(ended_read__isnull=False).annotate(
            duration_seconds=ExpressionWrapper(
                F('ended_read') - F('started_read'),
                output_field=fields.DurationField()
            )
        ).aggregate(
            avg_duration_minutes=Avg(ExpressionWrapper(
                F('duration_seconds'),
                output_field=fields.DurationField()
            ))
        )
        avg_read_duration: timedelta = average_duration_minutes['avg_duration_minutes']
        if avg_read_duration:
            context['avg_read_duration'] = round(avg_read_duration.total_seconds() / 60)
        else:
            context['avg_read_duration'] = 0
        
        return context


class TagDetailView(BaseListView):
    template_name = 'tag_detail.html'
    
    def get_queryset(self):
        self.tag = get_object_or_404(Category, slug=self.kwargs['slug'])
        return MarkdownArticle.objects.filter(
            tags__slug=self.tag.slug,
            status=MarkdownArticle.PUBLISHED
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context

    def get_meta(self):
        return Meta(author=getattr(settings, "BLOG_AUTHOR", "admin"),
                    title=_(f"{self.tag.name} Tag"),
                    description=_("List of articles with tag") + f" {self.tag.name}",
                    keywords=[_(key) for key in getattr(settings, "META_DEFAULT_KEYWORDS", [])])


class CollectionListView(BaseListView):
    model = Collection
    template_name = 'collection_list.html'
    context_object_name = 'collections'
    paginate_by = 20
    
    def get_template_names(self):
        return [f'sweetblog/{self.template_name}']
    
    def get_meta(self):
        return Meta(author=getattr(settings, "BLOG_AUTHOR", "admin"),
                    title=_("Collections List"),
                    description=_("List of my blog's collections"),
                    keywords=[_(key) for key in getattr(settings, "META_DEFAULT_KEYWORDS", [])])


class TagListView(BaseListView):
    model = Category
    template_name = 'tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def get_template_names(self):
        return [f'sweetblog/{self.template_name}']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add article count for each tag
        for tag in context['tags']:
            tag.article_count = MarkdownArticle.objects.filter(
                tags__slug=tag.slug,
                status=MarkdownArticle.PUBLISHED
            ).count()
        return context

    def get_meta(self):
        return Meta(author=getattr(settings, "BLOG_AUTHOR", "admin"),
                    title=_("Tags List"),
                    description=_("List of my blog's tags"),
                    keywords=[_(key) for key in getattr(settings, "META_DEFAULT_KEYWORDS", [])])


class MarkdownPageView(BlogSettingsMixin, DetailView):
    model = MarkdownPage
    template_name = 'markdown_page.html'
    context_object_name = 'page'
    
    def get_object(self):
        return get_object_or_404(
            MarkdownPage,
            normalized_title=self.kwargs['canonical_title'],
            status=MarkdownPage.PUBLISHED
        )
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        return context


class SearchView(BaseListView):
    template_name = 'search.html'
    context_object_name = 'results'
    paginate_by = 20
    
    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            self.query = query
            
            # Search in Articles
            articles = MarkdownArticle.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query),
                status=MarkdownArticle.PUBLISHED
            )
            
            # Search in Collections
            collections = Collection.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
            
            # Search in Categories
            categories = Category.objects.filter(
                Q(name__icontains=query)
            )
            
            # Combine results
            results = []
            
            for article in articles:
                results.append({
                    'type': 'article',
                    'object': article,
                    'title': article.title,
                    'url': article.get_url(),
                    'description': article.description[:200] + '...' if len(article.description) > 200 else article.description
                })
            
            for collection in collections:
                results.append({
                    'type': 'collection',
                    'object': collection,
                    'title': collection.name,
                    'url': collection.get_url(),
                    'description': collection.description[:200] + '...' if len(collection.description) > 200 else collection.description
                })
            
            for category in categories:
                article_count = MarkdownArticle.objects.filter(
                    tags__slug=category.slug,
                    status=MarkdownArticle.PUBLISHED
                ).count()
                results.append({
                    'type': 'category',
                    'object': category,
                    'title': category.name,
                    'url': category.get_url(),
                    'description': f"{article_count} article{'s' if article_count != 1 else ''}"
                })
            
            return results
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = getattr(self, 'query', '')
        return context


class MarkdownArticleFormView(BlogSettingsMixin):
    model = MarkdownArticle
    form_class = MarkdownArticleForm
    template_name = 'article_form.html'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def form_valid(self, form):
        self.is_new = self.object is None
        if self.is_new:
            form.instance.created_by = self.request.user if self.request.user.is_authenticated else None
        form.instance.updated_by = self.request.user if self.request.user.is_authenticated else None
        
        return super().form_valid(form)

    def get_success_url(self):
        # Handle different submit actions
        action = self.request.POST.get('action', 'save')
        if action == 'save':
            return reverse('admin:sweetblog_markdownarticle_changelist')
        elif action == 'save_continue':
            if self.is_new:
                return reverse('sweetblog-article_add')
            else:
                return reverse('sweetblog-article_edit', kwargs={"aid":self.object.get_hex_id()})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        is_edit = hasattr(self, 'object') and self.object is not None
        context['page_title'] = 'Edit Article' if is_edit else 'Add New Article'
        context['is_edit'] = is_edit
        return context


class AddMarkdownArticleView(MarkdownArticleFormView, CreateView):
    pass


class EditMarkdownArticleView(MarkdownArticleFormView, UpdateView):
    def get_object(self):
        return get_object_or_404(
            MarkdownArticle,
            id=int(self.kwargs['aid'], 16)
        )


class TagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Category.objects.none()

        qs = Category.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


def get_device_id(request):
    """Generate a unique device ID based on request information."""
    meta = getattr(request, 'META', {}) or {}
    user_agent = meta.get('HTTP_USER_AGENT', '')
    remote_addr = meta.get('REMOTE_ADDR') or '127.0.0.1'
    
    # Create a hash of user agent and IP address
    device_string = f"{user_agent}:{remote_addr}"
    device_id = hashlib.sha256(device_string.encode()).hexdigest()[:32]
    
    return device_id


class ConnectionView(BlogSettingsMixin, FormView):
    """View for email authentication."""
    form_class = EmailForm
    template_name = 'auth/connection.html'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def get_success_url(self):
        next_url = self.request.GET.get('next', '/')
        return reverse('sweetblog_code') + f'?next={next_url}&email={self.email}'
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        self.email = email
        device_id = get_device_id(self.request)
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
            profile, created = SweetblogProfile.objects.get_or_create(user=user)

            if profile.is_device_linked(device_id):
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(self.request, user)
                next_url = self.request.GET.get('next', '/')
                return redirect(next_url)

            if self.request.device.user == user:
                next_url = self.request.GET.get('next', '/')
                return redirect(next_url)
            else:
                # Device not linked, send code
                code = TempCode.generate_code()
                TempCode.objects.create(
                    email=email,
                    code=code,
                    device_id=device_id
                )

                # Send email with code
                self._send_code_email(email, code)
                messages.info(self.request, 'A verification code has been sent to your email.')
            return super().form_valid(form)
                
        except User.DoesNotExist:
            # User doesn't exist, create new user
            username = generate_username()[0]
            while User.objects.filter(username=username).exists():
                username = generate_username()[0]
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=None
            )
            
            # Create profile
            profile = SweetblogProfile.objects.create(user=user)
            
            # Generate and send code
            code = TempCode.generate_code()
            TempCode.objects.create(
                email=email,
                code=code,
                device_id=device_id
            )
            
            self._send_code_email(email, code)
            messages.info(self.request, 'A verification code has been sent to your email.')
            return super().form_valid(form)
    
    def _send_code_email(self, email, code):
        """
        Send verification code email using django-magic-notifier.
        Uses professional email templates with MJML support.
        """
        from magic_notifier.notifier import notify
        from django.utils import timezone
        
        # Get or create a temporary user object for the email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create a minimal user-like object for template context
            class TempUser:
                def __init__(self, email):
                    self.email = email
                    self.username = email.split('@')[0]
                    self.first_name = ''
                    
            user = TempUser(email)
        
        # Prepare context for the email template
        context = {
            'code': code,
            'blog_name': getattr(settings, 'BLOG_NAME', 'SweetBlog'),
            'current_year': timezone.now().year,
        }
        
        # Send email using magic-notifier with the verification_code template
        notify(
            ["email"],
            subject=f'Your {getattr(settings, "BLOG_NAME", "SweetBlog")} verification code',
            receivers=[user],
            template="verification_code",
            context=context
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '/')
        return context


class CodeView(BlogSettingsMixin, FormView):
    """View for verifying authentication code."""
    form_class = CodeForm
    template_name = 'auth/code.html'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def get_initial(self):
        initial = super().get_initial()
        initial['email'] = self.request.GET.get('email', '')
        return initial
    
    def get_success_url(self):
        next_url = self.request.GET.get('next', '/')
        return next_url
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        code = form.cleaned_data['code']
        device_id = get_device_id(self.request)
        
        # Verify code
        temp_code = TempCode.objects.filter(
            email=email,
            code=code,
            is_used=False
        ).order_by('-created_at').first()
        
        if temp_code and temp_code.is_valid():
            # Mark code as used
            temp_code.is_used = True
            temp_code.save()
            
            # Get user and link device
            user = User.objects.get(email=email)
            profile = user.sweetblog_profile
            profile.link_device(device_id)

            # Log the user in
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(self.request, user)
            
            messages.success(self.request, 'Successfully logged in!')
            return super().form_valid(form)
        else:
            form.add_error('code', 'Invalid or expired code.')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '/')
        context['email'] = self.request.GET.get('email', '')
        return context


class ProfileView(LoginRequiredMixin, BlogSettingsMixin, UpdateView):
    """View for user profile."""
    model = SweetblogProfile
    form_class = ProfileForm
    template_name = 'auth/profile.html'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def get_object(self, queryset=None):
        profile, created = SweetblogProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        next_url = self.request.GET.get('next', '/')
        messages.success(self.request, 'Profile updated successfully!')
        return next_url
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '/')
        return context


class MarkdownPageFormView(BlogSettingsMixin):
    model = MarkdownPage
    form_class = MarkdownPageForm
    template_name = 'page_form.html'
    
    def get_template_names(self):
        css_framework = getattr(settings, 'CSS_FRAMEWORK', 'pico')
        return [f'sweetblog/{css_framework}/{self.template_name}',
                f'sweetblog/{self.template_name}']
    
    def form_valid(self, form):
        self.is_new = self.object is None
        if self.is_new:
            form.instance.created_by = self.request.user if self.request.user.is_authenticated else None
        form.instance.updated_by = self.request.user if self.request.user.is_authenticated else None
        
        return super().form_valid(form)

    def get_success_url(self):
        # Handle different submit actions
        action = self.request.POST.get('action', 'save')
        if action == 'save':
            return reverse('admin:sweetblog_markdownpage_changelist')
        elif action == 'save_continue':
            if self.is_new:
                return reverse('sweetblog-page_add')
            else:
                return reverse('sweetblog-page_edit', kwargs={"canonical_title": self.object.normalized_title})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        is_edit = hasattr(self, 'object') and self.object is not None
        context['page_title'] = 'Edit Page' if is_edit else 'Add New Page'
        context['is_edit'] = is_edit
        return context


class AddMarkdownPageView(MarkdownPageFormView, CreateView):
    pass


class EditMarkdownPageView(MarkdownPageFormView, UpdateView):
    def get_object(self):
        return get_object_or_404(
            MarkdownPage,
            normalized_title=self.kwargs['canonical_title']
        )


class MarkArticleAsReadView(TemplateView):
    def post(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.utils import timezone
        from django.contrib.contenttypes.models import ContentType
        import json
        
        try:
            data = json.loads(request.body)
            article_id = data.get('article_id')
            article_type = data.get('article_type', 'markdownarticle')  # Default to MarkdownArticle
            
            if not article_id:
                return JsonResponse({'error': 'Article ID is required'}, status=400)
            
            # Get device from middleware (set by DeviceMiddleware)
            if not hasattr(request, 'device') or not request.device:
                return JsonResponse({'error': 'Device not found'}, status=400)
            
            # Get content type for the article
            try:
                content_type = ContentType.objects.get(model=article_type.lower())
            except ContentType.DoesNotExist:
                return JsonResponse({'error': 'Invalid article type'}, status=400)
            
            # Find the ArticleRead instance
            article_read = ArticleRead.objects.filter(
                article_ct=content_type,
                article_id=article_id,
                device=request.device
            ).first()
            
            if not article_read:
                return JsonResponse({'error': 'Article read record not found'}, status=404)
            
            # Mark as read if not already marked
            if not article_read.ended_read:
                article_read.ended_read = timezone.now()
                article_read.save()
                
            return JsonResponse({'success': True, 'message': 'Article marked as read'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class LikeDislikeView(TemplateView):
    def post(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.contrib.contenttypes.models import ContentType
        import json
        
        try:
            data = json.loads(request.body)
            article_id = data.get('article_id')
            article_type = data.get('article_type', 'markdownarticle')
            action = data.get('action')  # 'like' or 'dislike'
            
            if not article_id:
                return JsonResponse({'error': 'Article ID is required'}, status=400)
            
            if action not in ['like', 'dislike']:
                return JsonResponse({'error': 'Invalid action'}, status=400)
            
            # Get device from middleware
            if not hasattr(request, 'device') or not request.device:
                return JsonResponse({'error': 'Device not found'}, status=400)
            
            # Get content type for the article
            try:
                content_type = ContentType.objects.get(model=article_type.lower())
            except ContentType.DoesNotExist:
                return JsonResponse({'error': 'Invalid article type'}, status=400)
            
            # Find or create the ArticleRead instance
            article_read, created = ArticleRead.objects.get_or_create(
                article_ct=content_type,
                article_id=article_id,
                device=request.device,
                defaults={'liked': False, 'disliked': False}
            )
            
            # Handle like/dislike logic (they are mutually exclusive)
            if action == 'like':
                if article_read.liked:
                    # Toggle off if already liked
                    article_read.liked = False
                    article_read.disliked = False
                else:
                    # Set like and remove dislike
                    article_read.liked = True
                    article_read.disliked = False
            else:  # action == 'dislike'
                if article_read.disliked:
                    # Toggle off if already disliked
                    article_read.disliked = False
                    article_read.liked = False
                else:
                    # Set dislike and remove like
                    article_read.disliked = True
                    article_read.liked = False
            
            article_read.save()
            
            # Get updated counts
            like_count = ArticleRead.objects.filter(
                article_ct=content_type,
                article_id=article_id,
                liked=True
            ).count()
            dislike_count = ArticleRead.objects.filter(
                article_ct=content_type,
                article_id=article_id,
                disliked=True
            ).count()
            
            return JsonResponse({
                'success': True,
                'liked': article_read.liked,
                'disliked': article_read.disliked,
                'like_count': like_count,
                'dislike_count': dislike_count
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CommentView(TemplateView):
    """
    View to handle comment submissions for articles.
    Supports both top-level comments and replies to existing comments.
    """
    def post(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.contrib.contenttypes.models import ContentType
        import json

        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Not logged in'}, status=401)
        
        try:
            # Parse request data
            data = json.loads(request.body)
            article_id = data.get('article_id')
            article_type = data.get('article_type', 'markdownarticle')
            content = data.get('content', '').strip()
            parent_id = data.get('parent_id')  # ID of parent comment for replies
            
            # Validate required fields
            if not article_id:
                return JsonResponse({'error': 'Article ID is required'}, status=400)
            
            if not content:
                return JsonResponse({'error': 'Comment content is required'}, status=400)
            
            # Check device from middleware
            if not hasattr(request, 'device') or not request.device:
                return JsonResponse({'error': 'Device not found'}, status=400)
            
            # Get content type for the article
            try:
                content_type = ContentType.objects.get(model=article_type.lower())
            except ContentType.DoesNotExist:
                return JsonResponse({'error': 'Invalid article type'}, status=400)
            
            # Get or create the hidden root comment for the article
            root_comment = Comment.objects.filter(
                article_ct=content_type,
                article_id=article_id,
                tn_parent=None,
            ).first()
            
            if not root_comment:
                # Create the hidden root comment
                root_comment = Comment.objects.create(
                    article_ct=content_type,
                    article_id=article_id,
                    tn_parent=None
                )
            
            # Determine the parent for the new comment
            if parent_id:
                # This is a reply to an existing comment
                try:
                    parent_comment = Comment.objects.get(id=parent_id)
                    # Verify the parent belongs to the same article
                    if (parent_comment.article_ct != content_type or 
                        parent_comment.article_id != int(article_id)):
                        return JsonResponse({'error': 'Invalid parent comment'}, status=400)
                except Comment.DoesNotExist:
                    return JsonResponse({'error': 'Parent comment not found'}, status=404)
            else:
                # This is a top-level comment, use the root comment as parent
                parent_comment = root_comment
            
            # Create the new comment
            new_comment = Comment.objects.create(
                article_ct=content_type,
                article_id=article_id,
                device=request.device,
                content=content,
                tn_parent=parent_comment
            )
            
            # Get username for the response
            username = request.device.user.username
            
            # Return the created comment data
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': new_comment.id,
                    'content': new_comment.content,
                    'username': username,
                    'created_at': new_comment.created_at.strftime('%B %d, %Y at %I:%M %p'),
                    'parent_id': parent_comment.id if parent_id else None,
                    'level': new_comment.tn_level - 1  # Subtract 1 because root is hidden
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
