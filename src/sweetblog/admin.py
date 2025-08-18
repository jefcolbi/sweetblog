from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import messages
from treenode.admin import TreeNodeModelAdmin
from treenode.forms import TreeNodeForm

from .models import Category, Collection, MarkdownArticle, MarkdownPage, ArticleRead, TempCode, Comment
from .widgets import MarkdownWidget
from .utils import send_newsletter_emails


class MarkdownArticleAdminForm(forms.ModelForm):
    class Meta:
        model = MarkdownArticle
        fields = '__all__'
        widgets = {
            'content': MarkdownWidget(),
        }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    ordering = ['name']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'normalized_name', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['normalized_name', 'created_at', 'updated_at']
    ordering = ['name']


@admin.register(MarkdownArticle)
class MarkdownArticleAdmin(admin.ModelAdmin):
    form = MarkdownArticleAdminForm
    list_display = ['edit_link', 'title', 'created_by', 'collection', 'status', 'created_at', 'article_link']
    list_filter = ['status', 'collection', 'created_at']
    search_fields = ['title', 'description', 'content']
    readonly_fields = ['generated_html', 'created_at', 'updated_at']
    filter_horizontal = ['tags']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'keywords', 'status', 'version')
        }),
        ('Content', {
            'fields': ('content', 'generated_html')
        }),
        ('Media', {
            'fields': ('image', 'thumbnail',)
        }),
        ('Organization', {
            'fields': ('collection', 'tags',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def edit_link(self, obj):
        if obj.id:
            url = reverse('article_edit', kwargs={'aid': obj.get_hex_id()})
            return format_html(
                '<a href="{}" target="_blank" title="Edit in external editor">✏️ Edit</a>',
                url
            )
        return '-'
    edit_link.short_description = 'Edit'
    
    def article_link(self, obj):
        if obj.id:
            url = obj.get_url()
            return format_html(
                '<input type="text" value="{}" readonly style="width: 300px;" '
                'onclick="this.select(); document.execCommand(\'copy\'); '
                'this.nextElementSibling.style.display=\'inline\'; '
                'setTimeout(() => this.nextElementSibling.style.display=\'none\', 2000);" '
                'title="Click to copy" />'
                '<span style="display:none; color: green; margin-left: 5px;">Copied!</span>',
                url
            )
        return '-'
    article_link.short_description = 'Article Link'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['add_url'] = reverse('article_add')
        return super().changelist_view(request, extra_context=extra_context)
    
    actions = ['send_newsletter_with_selected_articles']
    
    def send_newsletter_with_selected_articles(self, request, queryset):
        """
        Admin action to send newsletter with selected articles.
        """
        # Filter only published articles
        published_articles = queryset.filter(status=MarkdownArticle.PUBLISHED)
        
        if not published_articles.exists():
            self.message_user(
                request, 
                "No published articles selected. Please select published articles only.", 
                messages.ERROR
            )
            return
        
        # Generate subject
        from django.conf import settings
        blog_name = getattr(settings, 'BLOG_NAME', 'SweetBlog')
        article_count = published_articles.count()
        
        if article_count == 1:
            subject = f"New article: {published_articles.first().title}"
        else:
            subject = f"{article_count} new articles from {blog_name}"
        
        # Send newsletter
        try:
            result = send_newsletter_emails(
                subject=subject,
                articles=published_articles
            )
            
            if result['sent_count'] > 0:
                self.message_user(
                    request,
                    f"Newsletter sent successfully to {result['sent_count']} subscribers!",
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    f"Newsletter not sent: {result['message']}",
                    messages.WARNING
                )
                
        except Exception as e:
            self.message_user(
                request,
                f"Failed to send newsletter: {str(e)}",
                messages.ERROR
            )
    
    send_newsletter_with_selected_articles.short_description = "📧 Send newsletter with selected articles"


class MarkdownPageAdminForm(forms.ModelForm):
    class Meta:
        model = MarkdownPage
        fields = '__all__'
        widgets = {
            'content': MarkdownWidget(),
        }


@admin.register(MarkdownPage)
class MarkdownPageAdmin(admin.ModelAdmin):
    form = MarkdownPageAdminForm
    list_display = ['title', 'normalized_title', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description', 'content']
    readonly_fields = ['normalized_title', 'generated_html', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'keywords', 'status', 'version', 'show_page_title', 'show_site_nav')
        }),
        ('Content', {
            'fields': ('content', 'generated_html')
        }),
        ('Metadata', {
            'fields': ('normalized_title', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['add_url'] = reverse('page_add')
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ArticleRead)
class ArticleReadAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_read', 'ended_read', 'device',)


@admin.register(TempCode)
class TempCodeAmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'code', 'is_used', 'created_at')


@admin.register(Comment)
class CommentAdmin(TreeNodeModelAdmin):
    treenode_display_mode = TreeNodeModelAdmin.TREENODE_DISPLAY_MODE_BREADCRUMBS
    ordering = ("created_at",)
    # form = TreeNodeForm
