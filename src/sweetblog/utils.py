import mistune
from mistune.directives import FencedDirective, RSTDirective
from mistune.directives import Admonition, TableOfContents

markdown = mistune.create_markdown(plugins=[
    'math',
    'footnotes',
    'strikethrough',
    'table',
    'url',
    'task_lists',
    'def_list',
    'abbr',
    'mark',
    'insert',
    'superscript',
    'subscript',
    'math',
    'spoiler',
    RSTDirective([
        Admonition(),
        TableOfContents(),
    ]),
])


def to_hex(num):
    """Convert number to hexadecimal string with minimum 5 characters"""
    hex_str = hex(num)[2:]  # Remove '0x' prefix
    return hex_str if len(hex_str) >= 5 else hex_str.zfill(5)

def from_hex(hex_str):
    """Convert hexadecimal string back to number"""
    return int(hex_str, 16)


def send_newsletter_emails(subject, content=None, articles=None, collections=None, 
                          unsubscribe_url=None, **extra_context):
    """
    Send newsletter emails to all users who have opted in for newsletters.
    
    Args:
        subject (str): Email subject line
        content (str, optional): Custom newsletter content (HTML allowed)
        articles (QuerySet, optional): QuerySet of articles to include
        collections (QuerySet, optional): QuerySet of collections to include
        unsubscribe_url (str, optional): URL for unsubscribing
        **extra_context: Additional context variables for templates
    
    Returns:
        dict: Statistics about sent emails (sent_count, failed_count, etc.)
    """
    from magic_notifier.notifier import notify
    from django.utils import timezone
    from django.conf import settings
    from .models import SweetblogProfile
    
    # Get all users who have opted in for newsletters
    newsletter_profiles = SweetblogProfile.objects.filter(
        receive_newsletter=True,
        user__is_active=True
    ).select_related('user')
    
    newsletter_users = [profile.user for profile in newsletter_profiles]
    
    if not newsletter_users:
        return {
            'sent_count': 0,
            'failed_count': 0,
            'message': 'No users subscribed to newsletter'
        }
    
    # Prepare template context
    context = {
        'newsletter_date': timezone.now(),
        'newsletter_content': content,
        'articles': articles,
        'collections': collections,
        'unsubscribe_url': unsubscribe_url,
        'blog_name': getattr(settings, 'BLOG_NAME', 'SweetBlog'),
        'blog_author': getattr(settings, 'BLOG_AUTHOR', 'Blog Team'),
        'current_year': timezone.now().year,
        **extra_context
    }
    
    try:
        # Send newsletter using magic-notifier
        notify(
            channels=["email"],
            subject=subject,
            receivers=newsletter_users,
            template="newsletter",
            context=context
        )
        
        return {
            'sent_count': len(newsletter_users),
            'failed_count': 0,
            'message': f'Newsletter sent to {len(newsletter_users)} subscribers'
        }
        
    except Exception as e:
        return {
            'sent_count': 0,
            'failed_count': len(newsletter_users),
            'message': f'Failed to send newsletter: {str(e)}'
        }


def send_newsletter_for_new_articles(limit=5):
    """
    Send a newsletter with the latest published articles.
    
    Args:
        limit (int): Number of latest articles to include
        
    Returns:
        dict: Statistics about sent emails
    """
    from .models import MarkdownArticle, Collection
    from django.urls import reverse
    from django.conf import settings
    
    # Get latest published articles
    latest_articles = MarkdownArticle.objects.filter(
        status=MarkdownArticle.PUBLISHED
    ).order_by('-created_at')[:limit]
    
    if not latest_articles.exists():
        return {
            'sent_count': 0,
            'failed_count': 0,
            'message': 'No published articles found'
        }
    
    # Get featured collections (optional)
    featured_collections = Collection.objects.all()[:3]
    
    # Generate unsubscribe URL (you might want to implement this view)
    unsubscribe_url = f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/auth/profile/"
    
    subject = f"Latest updates from {getattr(settings, 'BLOG_NAME', 'SweetBlog')}"
    
    return send_newsletter_emails(
        subject=subject,
        articles=latest_articles,
        collections=featured_collections if featured_collections.exists() else None,
        unsubscribe_url=unsubscribe_url
    )


def send_custom_newsletter(subject, content, **kwargs):
    """
    Send a custom newsletter with specific content.
    
    Args:
        subject (str): Email subject
        content (str): Custom content (HTML allowed)
        **kwargs: Additional arguments for send_newsletter_emails
        
    Returns:
        dict: Statistics about sent emails
    """
    from django.conf import settings
    
    # Generate unsubscribe URL
    unsubscribe_url = kwargs.get('unsubscribe_url') or \
                     f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/auth/profile/"
    
    return send_newsletter_emails(
        subject=subject,
        content=content,
        unsubscribe_url=unsubscribe_url,
        **kwargs
    )
