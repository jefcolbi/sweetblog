from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.forms import ModelForm
from django.contrib.auth import get_user_model
from imagekit.templatetags.imagekit import thumbnail

from .models import MarkdownArticle, SweetblogProfile, MarkdownPage
from .widgets import MarkdownWidget
from dal_select2_taggit.widgets import TaggitSelect2

User = get_user_model()


class MarkdownArticleForm(ModelForm):
    class Meta:
        model = MarkdownArticle
        fields = ['title', 'description', 'keywords', 'tags', 'image', 'status', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter article title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a brief description of your article'
            }),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO keywords, comma-separated'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'onchange': 'previewImage(this)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            # 'content': MarkdownWidget(attrs={
            #     'class': 'form-control markdown-content-editor',
            #     'placeholder': 'Write your article content in Markdown format'
            # }),
            'tags': TaggitSelect2(
                'tag_autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                }
            ),
        }
        labels = {
            'title': 'Title',
            'description': 'Description',
            'keywords': 'Keywords',
            'tags': 'Tags',
            'image': 'Featured Image',
            'status': 'Status',
            'content': 'Content'
        }
        help_texts = {
            'title': 'The title of your article',
            'description': 'A brief summary that will appear in article listings',
            'keywords': 'Enter SEO keywords separated by commas',
            'tags': 'Select relevant tags for your article',
            'image': 'Upload a featured image for your article',
            'status': 'Select whether to publish or save as draft',
            'content': 'Write your article content using Markdown formatting'
        }

    def save(self, commit=True):
        thumbnail = None

        if 'image' in self.cleaned_data:
            original_image: InMemoryUploadedFile = self.cleaned_data['image']
            if isinstance(original_image, InMemoryUploadedFile):
                content = BytesIO(original_image.read())
                thumbnail = InMemoryUploadedFile(file=content, field_name='thumbnail',
                                                 name=original_image.name, content_type=original_image.content_type,
                                                 size=original_image.size, charset=original_image.charset)
                original_image.seek(0)

        res = super().save(commit=commit)
        if thumbnail:
            res.thumbnail = thumbnail
            res.save()
        return


class EmailForm(forms.Form):
    """Form for email authentication."""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True
        }),
        help_text='Enter your email address to sign in or create an account'
    )


class CodeForm(forms.Form):
    """Form for verifying authentication code."""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True
        })
    )
    code = forms.CharField(
        label='Verification Code',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code',
            'autofocus': True,
            'maxlength': '6',
            'pattern': '[0-9]{6}'
        }),
        help_text='Enter the 6-digit code sent to your email'
    )


class ProfileForm(forms.ModelForm):
    """Form for user profile."""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True
        })
    )
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        help_text='Choose a unique username for your profile'
    )
    
    class Meta:
        model = SweetblogProfile
        fields = ['receive_newsletter']
        widgets = {
            'receive_newsletter': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'receive_newsletter': 'Receive Newsletter'
        }
        help_texts = {
            'receive_newsletter': 'Check this box if you want to receive newsletter updates'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email
            self.fields['username'].initial = self.user.username
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user and commit:
            # Update user's username
            self.user.username = self.cleaned_data['username']
            self.user.save()
            profile.save()
        return profile


class MarkdownPageForm(ModelForm):
    class Meta:
        model = MarkdownPage
        fields = ['title', 'description', 'keywords', 'status', 'show_site_nav', 'show_page_title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter page title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a brief description of your page'
            }),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO keywords, comma-separated'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'show_site_nav': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_page_title': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'content': MarkdownWidget(attrs={
                'class': 'form-control markdown-content-editor',
                'placeholder': 'Write your page content in Markdown format'
            })
        }
        labels = {
            'title': 'Title',
            'description': 'Description',
            'keywords': 'Keywords',
            'status': 'Status',
            'show_site_nav': 'Show Site Navigation',
            'show_page_title': 'Show Page Title',
            'content': 'Content'
        }
        help_texts = {
            'title': 'The title of your page',
            'description': 'A brief summary for SEO purposes',
            'keywords': 'Enter SEO keywords separated by commas',
            'status': 'Select whether to publish or save as draft',
            'show_site_nav': 'Display site navigation on this page',
            'show_page_title': 'Display the page title at the top of the content',
            'content': 'Write your page content using Markdown formatting'
        }