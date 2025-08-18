"""
Management command to send newsletters to subscribed users.

Usage examples:
    # Send newsletter with latest articles
    python manage.py send_newsletter --latest-articles

    # Send custom newsletter
    python manage.py send_newsletter --subject "Weekly Update" --content "Custom content here"

    # Send newsletter with specific articles and collections
    python manage.py send_newsletter --subject "Featured Content" --article-ids 1,2,3 --collection-ids 1,2
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from sweetblog.utils import send_newsletter_emails, send_newsletter_for_new_articles, send_custom_newsletter
from sweetblog.models import MarkdownArticle, Collection


class Command(BaseCommand):
    help = 'Send newsletter emails to subscribed users'

    def add_arguments(self, parser):
        # Newsletter type options
        parser.add_argument(
            '--latest-articles',
            action='store_true',
            help='Send newsletter with latest published articles'
        )
        
        parser.add_argument(
            '--custom',
            action='store_true',
            help='Send custom newsletter (requires --subject and --content)'
        )
        
        # Content options
        parser.add_argument(
            '--subject',
            type=str,
            help='Email subject line'
        )
        
        parser.add_argument(
            '--content',
            type=str,
            help='Custom newsletter content (HTML allowed)'
        )
        
        parser.add_argument(
            '--article-ids',
            type=str,
            help='Comma-separated list of article IDs to include'
        )
        
        parser.add_argument(
            '--collection-ids',
            type=str,
            help='Comma-separated list of collection IDs to include'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of latest articles to include (default: 5)'
        )
        
        # Dry run option
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails'
        )

    def handle(self, *args, **options):
        """Execute the newsletter sending command."""
        
        # Validate arguments
        if not any([options['latest_articles'], options['custom'], options['subject']]):
            raise CommandError(
                'You must specify either --latest-articles, --custom, or provide --subject'
            )
        
        if options['custom'] and not (options['subject'] and options['content']):
            raise CommandError(
                '--custom requires both --subject and --content'
            )
        
        # Handle dry run
        if options['dry_run']:
            self.handle_dry_run(options)
            return
        
        # Send appropriate newsletter type
        if options['latest_articles']:
            result = self.send_latest_articles_newsletter(options)
        elif options['custom']:
            result = self.send_custom_newsletter(options)
        else:
            result = self.send_general_newsletter(options)
        
        # Output results
        self.stdout.write(
            self.style.SUCCESS(
                f"Newsletter operation completed: {result['message']}"
            )
        )
        
        if result['sent_count'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully sent to {result['sent_count']} subscribers")
            )
        
        if result['failed_count'] > 0:
            self.stdout.write(
                self.style.ERROR(f"Failed to send to {result['failed_count']} recipients")
            )

    def handle_dry_run(self, options):
        """Handle dry run mode - show what would be sent."""
        from sweetblog.models import SweetblogProfile
        
        # Get subscriber count
        subscriber_count = SweetblogProfile.objects.filter(
            receive_newsletter=True,
            user__is_active=True
        ).count()
        
        self.stdout.write(
            self.style.WARNING(f"DRY RUN MODE - No emails will be sent")
        )
        self.stdout.write(f"Subscribers: {subscriber_count}")
        
        if options['latest_articles']:
            articles = MarkdownArticle.objects.filter(
                status=MarkdownArticle.PUBLISHED
            ).order_by('-created_at')[:options['limit']]
            self.stdout.write(f"Would include {articles.count()} latest articles")
            
        if options['subject']:
            self.stdout.write(f"Subject: {options['subject']}")
            
        if options['content']:
            content_preview = options['content'][:100] + '...' if len(options['content']) > 100 else options['content']
            self.stdout.write(f"Content preview: {content_preview}")

    def send_latest_articles_newsletter(self, options):
        """Send newsletter with latest articles."""
        self.stdout.write("Sending newsletter with latest articles...")
        return send_newsletter_for_new_articles(limit=options['limit'])

    def send_custom_newsletter(self, options):
        """Send custom newsletter."""
        self.stdout.write("Sending custom newsletter...")
        return send_custom_newsletter(
            subject=options['subject'],
            content=options['content']
        )

    def send_general_newsletter(self, options):
        """Send general newsletter with specified content."""
        self.stdout.write("Sending general newsletter...")
        
        # Parse article IDs
        articles = None
        if options['article_ids']:
            try:
                article_ids = [int(x.strip()) for x in options['article_ids'].split(',')]
                articles = MarkdownArticle.objects.filter(
                    id__in=article_ids,
                    status=MarkdownArticle.PUBLISHED
                )
                if not articles.exists():
                    self.stdout.write(
                        self.style.WARNING("No published articles found with specified IDs")
                    )
            except ValueError:
                raise CommandError("Invalid article IDs format")
        
        # Parse collection IDs
        collections = None
        if options['collection_ids']:
            try:
                collection_ids = [int(x.strip()) for x in options['collection_ids'].split(',')]
                collections = Collection.objects.filter(id__in=collection_ids)
                if not collections.exists():
                    self.stdout.write(
                        self.style.WARNING("No collections found with specified IDs")
                    )
            except ValueError:
                raise CommandError("Invalid collection IDs format")
        
        # Use provided subject or generate default
        subject = options['subject'] or f"Updates from {getattr(settings, 'BLOG_NAME', 'SweetBlog')}"
        
        return send_newsletter_emails(
            subject=subject,
            content=options.get('content'),
            articles=articles,
            collections=collections
        )