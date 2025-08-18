from django.db import models


class ArticleManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related("created_by", "updated_by").prefetch_related('tags')


class CollectionManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset()


class TaggedWhateverManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('tag')
