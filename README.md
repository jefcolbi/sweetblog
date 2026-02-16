# Sweetblog

[![Django](https://img.shields.io/badge/Django-4.0%2B-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

**Sweetblog** is a Django application that simplifies blog creation and maintenance. It provides a clean, easy-to-use platform for running your own personal blog with minimal setup.

## Features

### Core Functionality
- **Markdown Support**: Write posts in Markdown with live preview in the admin interface
- **Collections**: Organize articles into collections (categories)
- **Tags**: Tag articles for better organization and discoverability
- **Comments System**: Built-in nested commenting system with reply functionality
- **Engagement**: Like/dislike system for articles
- **View Tracking**: Track article views and calculate reading time
- **Multiple Themes**: Support for Pico.css and Sakura.css frameworks

## Quick Start

### Installation

1. **Add Sweetblog to your Django project:**

```bash
# Using pip
pip install sweetblog

# Using uv
uv add sweetblog
```

2. **Configure Django settings:**

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
   'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Sweetblog
    'sweetblog',
   
    'meta',
    'treenode',
    'magic_notifier',
]
```

3. **Add Sweetblog settings:**

```python
# CSS Framework choice
CSS_FRAMEWORK = 'pico'  # Options: 'pico', 'sakura'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
```

4. **Include URLs:**

In your main `urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sweetblog.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

5. **Run migrations:**

```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser:**

```bash
python manage.py createsuperuser
```

7. **Collect static files:**

```bash
python manage.py collectstatic
```

8. **Run server:**

```bash
python manage.py runserver
```

## Usage

### Creating Blog Posts

1. Login to Django Admin at `/admin/`
2. Create a Collection (optional):
   - Go to Collections -> Add Collection
   - Enter name and description
   
3. Create an Article:
   - Go to Articles -> Add Article  
   - Write content in Markdown
   - Add tags and select collection
   - Upload thumbnail image
   - Save

### Markdown Support

Sweetblog supports standard Markdown syntax:

```markdown
# Heading 1
## Heading 2

**Bold** and *italic*

- Bullet lists
1. Numbered lists

[Links](https://example.com)
![Images](image.jpg)

`inline code`
```

### Available Views

- **HomeView**: Lists recent articles with pagination
- **CollectionDetailView**: Shows articles in a specific collection
- **ArticleDetailView**: Displays single article with comments
- **TagDetailView**: Lists articles with a specific tag

## Project Structure

```
sweetblog/
├── src/
│   └── sweetblog/
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       ├── admin.py
│       ├── serializers.py
│       ├── templates/
│       │   └── sweetblog/
│       │       ├── base_pico.html
│       │       ├── base_sakura.html
│       │       ├── home.html
│       │       └── article_detail.html
│       └── static/
│           └── sweetblog/
│               ├── css/
│               └── js/
│                   └── article.js
└── tests/
    └── testsweetblog/
        └── settings.py
```

## Configuration

### Basic Settings

```python
# Django settings
SECRET_KEY = 'your-secret-key'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Sweetblog theme
CSS_FRAMEWORK = 'pico'  # or 'sakura'
```

## Development

### Testing

```bash
python manage.py test sweetblog
```

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd sweetblog

# Install with uv
uv pip install -e .

# Run development server
python manage.py runserver
```

## Dependencies

- Django >= 4.0
- mistune (Markdown parser)
- Pillow (Image processing)

## Models

- **Category**: Article categories
- **Collection**: Groups of related articles
- **Article**: Base article model
- **MarkdownArticle**: Article with Markdown content
- **Device**: User device tracking
- **Comment**: Article comments

## Admin Features

- Live Markdown preview widget
- Automatic HTML generation from Markdown
- Support for multiple Markdown fields on same page

## License

See LICENSE file for details.