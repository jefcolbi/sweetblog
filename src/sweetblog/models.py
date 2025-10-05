from uuid import uuid4

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from meta.models import ModelMeta
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill, ResizeToFit
from django.contrib.auth import get_user_model
from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase
from django.conf import settings
from unidecode import unidecode
import re
from sweetblog.managers import TaggedWhateverManager, CollectionManager, ArticleManager
from django.utils.translation import gettext as _
from sweetblog.utils import to_hex
from sweetblog.fields import MarkdownField
import mistune
from datetime import timedelta
from django.utils import timezone
import secrets
from treenode.models import TreeNodeModel

User = get_user_model()

rgx_normalize = re.compile(r"[\W]")

BASE_URL = getattr(settings, "BASE_URL", "http://localhost:8000")


class TrackingMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by",
    )

    class Meta:
        abstract = True


class Category(TrackingMixin, TagBase):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_url(self):
        return reverse('tag_detail', kwargs={'slug':self.slug})

    def save(self, *args, **kwargs):
        self.name = self.name.title()
        return super().save(*args, **kwargs)


class TaggedWhatever(GenericTaggedItemBase):
    # TaggedWhatever can also extend TaggedItemBase or a combination of
    # both TaggedItemBase and GenericTaggedItemBase. GenericTaggedItemBase
    # allows using the same tag for different kinds of objects, in this
    # example Food and Drink.
    objects = TaggedWhateverManager()


    # Here is where you provide your custom Tag class.
    tag = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )


class Collection(ModelMeta, TrackingMixin, models.Model):
    objects = CollectionManager()

    _metadata = {
        'title': 'name',
        'description': 'description',
        'image': 'get_image',
        'url': 'get_url',
        'keywords': 'get_keywords',
        'author': 'get_author',
    }

    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=255)
    description = models.TextField()
    normalized_name = models.CharField(max_length=255, null=True, blank=True,
                                       editable=False)
    image = ProcessedImageField(upload_to='collections', processors=[ResizeToFill(512, 512)], format='JPEG',
                               options={'quality': 90})
    thumbnail = ProcessedImageField(upload_to='collection', processors=[ResizeToFit(128, upscale=False)], format='JPEG',
                                    options={'quality': 90})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        norm_name = unidecode(self.name)
        self.normalized_name = rgx_normalize.sub("-", norm_name)
        self.normalized_name = self.normalized_name.lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_image(self):
        return self.thumbnail.url

    def get_url(self):
        return reverse('collection_detail', kwargs={'name':self.normalized_name})

    def get_keywords(self):
        author = getattr(settings, "BLOG_AUTHOR", "admin")
        blog_name = getattr(settings, "BLOG_NAME", "SweetBlog")
        return [_(f"{blog_name} {self.name} collection"),
                _(f"{author} {self.name} collection"),]

    def get_author(self):
        return getattr(settings, "BLOG_AUTHOR", "admin")


class AbstractArticle(ModelMeta, TrackingMixin, models.Model):
    _metadata = {
        'title': 'title',
        'description': 'description',
        'image': 'get_image',
        'url': 'get_url',
        'keywords': 'get_keywords',
        'author': 'get_author',
    }

    objects = ArticleManager()

    PUBLISHED = "Published"
    DRAFT = "Draft"
    STATUSES = [(PUBLISHED, _("Published")), (DRAFT, _("Draft"))]

    title = models.CharField(max_length=255)
    keywords = models.CharField(max_length=255, help_text=_("Enter SEO keywords"))
    tags = TaggableManager(through=TaggedWhatever, )
    image = ProcessedImageField(upload_to='articles', processors=[ResizeToFit(1024, upscale=False)], format='JPEG',
                                options={'quality': 90})
    thumbnail = ProcessedImageField(upload_to='thumbnails', processors=[ResizeToFit(300, upscale=False)], format='JPEG',
                                options={'quality': 90})
    version = models.CharField(max_length=255, default="1")
    description = models.TextField(help_text=_("Enter a small description for your article."))
    generated_html = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default=DRAFT, choices=STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    collection = models.ForeignKey(Collection, models.CASCADE, blank=True, null=True,
                                   help_text=_("Select a collection"),
                                   related_name='articles')

    class Meta:
        abstract = True

    def get_dashboard_edit_url(self):
        return reverse('dashboard_article_edit', kwargs={'aid':self.id})

    def get_url(self):
        norm_title = unidecode(self.title)
        norm_title = rgx_normalize.sub("-", norm_title)
        art_url = reverse('article_detail', kwargs={'title':norm_title.lower(),
                                                    'type': 'md', 'aid': to_hex(self.id)})
        print(f"article url {art_url}")
        return BASE_URL + art_url

    def get_image(self):
        return f"{BASE_URL}{self.image.url}"

    def get_keywords(self):
        return self.keywords.split(',')

    def get_author(self):
        return self.created_by.get_full_name()

    def get_hex_id(self):
        return to_hex(self.id)

    def generate_html(self):
        raise NotImplementedError

    def save(self, **kwargs):
        self.generated_html = self.generate_html()
        return super().save(**kwargs)


class MarkdownArticle(AbstractArticle):
    content = MarkdownField(help_text=_("Enter your article content in Markdown format."))

    def generate_html(self):
        from sweetblog.utils import markdown
        return markdown(self.content)

    def get_hidden_first_comment(self) -> 'Comment':
        content_type = ContentType.objects.get(model="markdownarticle")
        comment = Comment.objects.filter(
                article_ct=content_type,
                article_id=self.id,
            tn_parent=None
            ).first()
        if not comment:
            comment = Comment.objects.create(
                article_ct=content_type,
                article_id=self.id,
            )
        return comment


class AbstractPage(ModelMeta, TrackingMixin, models.Model):
    _metadata = {
        'title': 'title',
        'description': 'description',
        'image': 'get_image',
        'url': 'get_url',
        'keywords': 'get_keywords',
    }

    PUBLISHED = "Published"
    DRAFT = "Draft"
    STATUSES = [(PUBLISHED, _("Published")), (DRAFT, _("Draft"))]

    title = models.CharField(max_length=255)
    normalized_title = models.CharField(max_length=255, null=True, blank=True,
                                       editable=False)
    keywords = models.CharField(max_length=255, help_text=_("Enter SEO keywords"))
    version = models.CharField(max_length=255, default="1")
    description = models.TextField(help_text=_("Enter a small description for your page."))
    generated_html = models.TextField(null=True, blank=True)
    show_site_nav = models.BooleanField(default=False)
    show_page_title = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default=DRAFT, choices=STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def get_dashboard_edit_url(self):
        return reverse('dashboard_article_edit', kwargs={'aid':self.id})

    def get_url(self):
        norm_title = unidecode(self.title)
        norm_title = rgx_normalize.sub("-", norm_title)
        art_url = reverse('page_detail', kwargs={'title':norm_title.lower(),
                                                    'type': 'md', 'aid': to_hex(self.id)})
        print(f"article url {art_url}")
        return BASE_URL + art_url

    def get_image(self):
        return f"{BASE_URL}{settings.LOGO_URL}"

    def get_keywords(self):
        return self.keywords.split(',')

    def generate_html(self):
        raise NotImplementedError

    def save(self, **kwargs):
        norm_title = unidecode(self.title)
        self.normalized_title = rgx_normalize.sub("-", norm_title)
        self.normalized_title = self.normalized_title.lower()

        self.generated_html = self.generate_html()
        super().save(**kwargs)


class MarkdownPage(AbstractPage):
    content = models.TextField(help_text=_("Enter your page content in Markdown format."))

    def generate_html(self):
        from sweetblog.utils import markdown
        return markdown(self.content)


class Device(models.Model):
    uuid = models.UUIDField(default=uuid4)
    user = models.ForeignKey(User, models.SET_NULL, null=True, blank=True, related_name='devices')
    # Request metadata
    method = models.CharField(max_length=10)
    path = models.TextField()
    full_path = models.TextField()

    # Client info
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    remote_host = models.CharField(max_length=255, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    referer = models.TextField(null=True, blank=True)
    accept_language = models.CharField(max_length=255, null=True, blank=True)

    # Cookies
    cookies = models.JSONField(null=True, blank=True)

    # Query parameters
    query_params = models.JSONField(null=True, blank=True)

    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.uuid} from {self.remote_addr or 'unknown'}"

    @classmethod
    def from_request(cls, request):
        """
        Create a Device instance from a Django HttpRequest object.
        """
        # Get IP (supports common proxy header)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            remote_addr = x_forwarded_for.split(',')[0].strip()
        else:
            remote_addr = request.META.get('REMOTE_ADDR')

        return cls.objects.create(
            user=request.user if request.user.is_authenticated else None,
            method=request.method,
            path=request.path,
            full_path=request.get_full_path(),
            remote_addr=remote_addr,
            remote_host=request.META.get('REMOTE_HOST'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            referer=request.META.get('HTTP_REFERER'),
            accept_language=request.META.get('HTTP_ACCEPT_LANGUAGE'),
            cookies=request.COOKIES or None,
            query_params=request.GET.dict() if request.GET else None,
        )

    @classmethod
    def for_bot(cls):
        """
        Create a Device instance from a Django HttpRequest object.
        """

        try:
            return cls.objects.get(path="bot")
        except Exception as e:
            return cls.objects.create(
                method="bot",
                path="/",
                full_path="/",
            )


class TempCode(models.Model):
    """Model for storing temporary authentication codes."""
    email = models.EmailField()
    code = models.CharField(max_length=6)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['email', 'code']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.code}"
    
    @classmethod
    def generate_code(cls):
        """Generate a 6-digit code."""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    def is_valid(self):
        """Check if the code is still valid (not expired and not used)."""
        if self.is_used:
            return False
        # Code expires after 10 minutes
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() < expiry_time
    
    @classmethod
    def cleanup_expired(cls):
        """Delete expired codes."""
        expiry_time = timezone.now() - timedelta(minutes=10)
        cls.objects.filter(created_at__lt=expiry_time).delete()


class SweetblogProfile(models.Model):
    """Extended profile for blog users."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='sweetblog_profile'
    )
    receive_newsletter = models.BooleanField(
        default=False,
        help_text=_("Check if you want to receive newsletter updates")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.email}"
    
    def is_device_linked(self, device_id):
        """Check if a device is linked to this profile."""
        return device_id in self.linked_devices
    
    def link_device(self, device_id):
        """Link a device to this profile."""
        if device_id and device_id not in self.linked_devices:
            self.linked_devices.append(device_id)
            self.save()


class ArticleRead(models.Model):
    article_ct = models.ForeignKey(ContentType,
                         on_delete=models.CASCADE,
                         )
    article_id = models.PositiveIntegerField()
    article = GenericForeignKey('article_ct', 'article_id')
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True)
    started_read = models.DateTimeField(auto_now_add=True)
    ended_read = models.DateTimeField(blank=True, null=True)
    liked = models.BooleanField(null=True, blank=True)
    disliked = models.BooleanField(null=True, blank=True)


class Comment(TreeNodeModel):
    article_ct = models.ForeignKey(ContentType,
                                   on_delete=models.CASCADE,
                                   )
    article_id = models.PositiveIntegerField()
    article = GenericForeignKey('article_ct', 'article_id')
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(TreeNodeModel.Meta):
        ordering = ('created_at',)

    def __get_node_order_str(self):
        print(f"i am called")
        priority_max = 9999999999
        priority_len = len(str(priority_max))
        priority_val = priority_max - min(self.tn_priority, priority_max)
        priority_key = str(priority_val).zfill(priority_len)
        alphabetical_val = slugify(str(self))
        alphabetical_key = alphabetical_val.ljust(priority_len, "z")
        alphabetical_key = alphabetical_key[0:priority_len]

        pk_val = str(int(self.created_at.timestamp()))

        pk_key = str(pk_val).zfill(priority_len)
        s = f"{priority_key}{alphabetical_key}{pk_key}"
        s = s.upper()
        return s
