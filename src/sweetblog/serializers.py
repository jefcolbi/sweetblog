from rest_framework import serializers
from .models import Category, Collection, MarkdownArticle
from taggit.serializers import TagListSerializerField, TaggitSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at']


class CollectionSerializer(serializers.ModelSerializer):
    tags = TagListSerializerField()
    
    class Meta:
        model = Collection
        fields = [
            'id', 
            'name', 
            'description', 
            'normalized_name', 
            'image', 
            'thumbnail', 
            'tags', 
            'created_at', 
            'updated_at'
        ]


class ArticleSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    collection_name = serializers.CharField(source='collection.name', read_only=True)
    writer_name = serializers.CharField(source='writer.get_full_name', read_only=True)
    
    class Meta:
        model = MarkdownArticle
        fields = [
            'id',
            'title',
            'keywords',
            'tags',
            'image',
            'thumbnail',
            'thumbnail_height',
            'version',
            'description',
            'content',
            'generated_html',
            'status',
            'created_at',
            'updated_at',
            'writer',
            'writer_name',
            'collection',
            'collection_name'
        ]