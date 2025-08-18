import os
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from faker import Faker
from PIL import Image, ImageDraw, ImageFont
import io
from mdgen import MarkdownGenerator
from sweetblog.models import Category, Collection, MarkdownArticle, MarkdownPage

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates fake data for Category, Collection, and MarkdownArticle models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories',
            type=int,
            default=10,
            help='Number of categories to create (default: 10)'
        )
        parser.add_argument(
            '--collections',
            type=int,
            default=5,
            help='Number of collections to create (default: 5)'
        )
        parser.add_argument(
            '--articles',
            type=int,
            default=30,
            help='Number of articles to create (default: 30)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=5,
            help='Number of pages to create (default: 5)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data'
        )

    def create_placeholder_image(self, size, text):
        """Create a placeholder image with text."""
        image = Image.new('RGB', size, color=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)))
        draw = ImageDraw.Draw(image)
        
        # Try to use a default font, fallback to PIL default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            font = ImageFont.load_default()
        
        # Get text bounding box
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Center the text
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    def handle(self, *args, **options):
        fake = Faker()
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            MarkdownArticle.objects.all().delete()
            MarkdownPage.objects.all().delete()
            Collection.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create or get a user for the articles
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'testuser@example.com',
                'first_name': 'Test',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

        # Create Categories
        self.stdout.write(self.style.SUCCESS(f'Creating {options["categories"]} categories...'))
        categories = []
        category_names = [
            'Technology', 'Science', 'Health', 'Travel', 'Food',
            'Sports', 'Music', 'Art', 'Business', 'Education',
            'Fashion', 'Gaming', 'Photography', 'Nature', 'History',
            'Politics', 'Economics', 'Philosophy', 'Psychology', 'Literature'
        ]
        
        for i in range(min(options['categories'], len(category_names))):
            name = category_names[i]
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    'slug': fake.slug(),
                    'created_by': user,
                    'updated_by': user,
                }
            )
            if created:
                categories.append(category)
                self.stdout.write(f'  Created category: {category.name}')
            else:
                categories.append(category)
                self.stdout.write(f'  Category already exists: {category.name}')

        # Create Collections
        self.stdout.write(self.style.SUCCESS(f'\nCreating {options["collections"]} collections...'))
        collections = []
        
        for i in range(options['collections']):
            collection_name = f"{fake.catch_phrase()} Collection"
            
            # Generate collection image and thumbnail
            collection_image = self.create_placeholder_image((512, 512), f"Collection {i+1}")
            collection_thumbnail = self.create_placeholder_image((128, 128), f"C{i+1}")
            
            collection = Collection.objects.create(
                name=collection_name,
                description=fake.paragraph(nb_sentences=5),
                created_by=user,
                updated_by=user,
            )
            
            # Save images
            collection.image.save(
                f'collection_{i}.jpg',
                ContentFile(collection_image),
                save=False
            )
            collection.thumbnail.save(
                f'collection_thumb_{i}.jpg',
                ContentFile(collection_thumbnail),
                save=False
            )
            collection.save()
            
            collections.append(collection)
            self.stdout.write(f'  Created collection: {collection.name}')

        # Create Articles
        self.stdout.write(self.style.SUCCESS(f'\nCreating {options["articles"]} articles...'))
        
        statuses = [MarkdownArticle.PUBLISHED, MarkdownArticle.DRAFT]
        md_gen = MarkdownGenerator()
        
        for i in range(options['articles']):
            # Generate article title
            title = fake.sentence(nb_words=random.randint(4, 8)).rstrip('.')
            
            # Generate rich markdown content
            content_parts = []
            
            # Add a main heading
            content_parts.append(f"# {title}")
            content_parts.append("")
            
            # Add introduction paragraph
            content_parts.append(fake.paragraph(nb_sentences=4))
            content_parts.append("")
            
            # Add sections with various markdown elements
            for section in range(random.randint(2, 4)):
                # Section heading
                section_title = fake.sentence(nb_words=random.randint(3, 6)).rstrip('.')
                content_parts.append(f"## {section_title}")
                content_parts.append("")
                
                # Add some paragraphs
                for _ in range(random.randint(1, 3)):
                    content_parts.append(fake.paragraph(nb_sentences=random.randint(3, 6)))
                    content_parts.append("")
                
                # Randomly add markdown elements
                element_choice = random.choice(['list', 'code', 'quote', 'table', 'link'])
                
                if element_choice == 'list':
                    # Add a list
                    content_parts.append("### Key Points:")
                    for _ in range(random.randint(3, 6)):
                        content_parts.append(f"- {fake.sentence()}")
                    content_parts.append("")
                
                elif element_choice == 'code':
                    # Add a code block
                    content_parts.append("### Example Code:")
                    content_parts.append("```python")
                    content_parts.append("def example_function():")
                    content_parts.append(f'    return "{fake.word()}"')
                    content_parts.append("```")
                    content_parts.append("")
                
                elif element_choice == 'quote':
                    # Add a blockquote
                    content_parts.append(f"> {fake.paragraph(nb_sentences=2)}")
                    content_parts.append(f"> - {fake.name()}")
                    content_parts.append("")
                
                elif element_choice == 'table':
                    # Add a simple table
                    content_parts.append("### Data Overview:")
                    content_parts.append("| Feature | Value |")
                    content_parts.append("|---------|-------|")
                    for _ in range(3):
                        content_parts.append(f"| {fake.word().title()} | {fake.word()} |")
                    content_parts.append("")
                
                elif element_choice == 'link':
                    # Add some links
                    content_parts.append(f"For more information, visit [our website]({fake.url()}) or check out [this resource]({fake.url()}).")
                    content_parts.append("")
            
            # Join all content parts
            content = "\n".join(content_parts)
            
            # Generate article image and thumbnail
            article_image = self.create_placeholder_image((1024, 768), f"Article {i+1}")
            article_thumbnail = self.create_placeholder_image((400, 300), f"A{i+1}")
            
            # Create article
            article = MarkdownArticle(
                title=title,
                keywords=', '.join(fake.words(nb=random.randint(3, 6))),
                description=fake.paragraph(nb_sentences=2),
                content=content,
                status=random.choice(statuses),
                writer=user,
                created_by=user,
                updated_by=user,
                version="1.0",
            )
            
            # Assign to a random collection (or none)
            if collections and random.random() > 0.3:  # 70% chance to be in a collection
                article.collection = random.choice(collections)
            
            # Save images
            article.image.save(
                f'article_{i}.jpg',
                ContentFile(article_image),
                save=False
            )
            article.thumbnail.save(
                f'article_thumb_{i}.jpg',
                ContentFile(article_thumbnail),
                save=False
            )
            
            # Save article first
            article.save()
            
            # Add random tags
            selected_tags = random.sample(categories, k=random.randint(1, min(4, len(categories))))
            article.tags.add(*selected_tags)
            
            self.stdout.write(f'  Created article: {article.title} (Status: {article.status})')

        # Create Pages
        self.stdout.write(self.style.SUCCESS(f'\nCreating {options["pages"]} pages...'))
        
        page_titles = [
            'About Us',
            'Contact',
            'Terms of Service',
            'Privacy Policy',
            'FAQ',
            'Documentation',
            'Getting Started',
            'API Reference',
            'Support',
            'Partners'
        ]
        
        for i in range(min(options['pages'], len(page_titles))):
            title = page_titles[i] if i < len(page_titles) else f"Page {i+1}"
            
            # Generate rich markdown content for pages
            content_parts = []
            
            # Add main heading
            content_parts.append(f"# {title}")
            content_parts.append("")
            
            # Add introduction
            content_parts.append(fake.paragraph(nb_sentences=5))
            content_parts.append("")
            
            # Add sections based on page type
            if title == 'About Us':
                content_parts.append("## Our Mission")
                content_parts.append(fake.paragraph(nb_sentences=4))
                content_parts.append("")
                content_parts.append("## Our Team")
                content_parts.append(fake.paragraph(nb_sentences=3))
                content_parts.append("")
                content_parts.append("## Our Values")
                for _ in range(3):
                    content_parts.append(f"- **{fake.word().title()}**: {fake.sentence()}")
                content_parts.append("")
                
            elif title == 'Contact':
                content_parts.append("## Get in Touch")
                content_parts.append(fake.paragraph(nb_sentences=2))
                content_parts.append("")
                content_parts.append("### Contact Information")
                content_parts.append(f"- **Email**: {fake.email()}")
                content_parts.append(f"- **Phone**: {fake.phone_number()}")
                content_parts.append(f"- **Address**: {fake.address()}")
                content_parts.append("")
                
            elif title == 'FAQ':
                content_parts.append("## Frequently Asked Questions")
                content_parts.append("")
                for q in range(5):
                    content_parts.append(f"### {fake.sentence().rstrip('.')}?")
                    content_parts.append(fake.paragraph(nb_sentences=3))
                    content_parts.append("")
                    
            else:
                # Generic page content
                for section in range(random.randint(2, 4)):
                    section_title = fake.sentence(nb_words=random.randint(3, 5)).rstrip('.')
                    content_parts.append(f"## {section_title}")
                    content_parts.append("")
                    content_parts.append(fake.paragraph(nb_sentences=random.randint(4, 6)))
                    content_parts.append("")
            
            # Join content
            content = "\n".join(content_parts)
            
            # Create page
            page = MarkdownPage.objects.create(
                title=title,
                keywords=', '.join(fake.words(nb=random.randint(3, 5))),
                description=fake.paragraph(nb_sentences=2),
                content=content,
                status=MarkdownPage.PUBLISHED,  # Pages are usually published
                version="1.0",
                created_by=user,
                updated_by=user,
            )
            
            self.stdout.write(f'  Created page: {page.title}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\nData creation completed!'))
        self.stdout.write(self.style.SUCCESS(f'Total Categories: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total Collections: {Collection.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total Articles: {MarkdownArticle.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Published: {MarkdownArticle.objects.filter(status=MarkdownArticle.PUBLISHED).count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Draft: {MarkdownArticle.objects.filter(status=MarkdownArticle.DRAFT).count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total Pages: {MarkdownPage.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Published: {MarkdownPage.objects.filter(status=MarkdownPage.PUBLISHED).count()}'))
        self.stdout.write(self.style.SUCCESS(f'  - Draft: {MarkdownPage.objects.filter(status=MarkdownPage.DRAFT).count()}'))