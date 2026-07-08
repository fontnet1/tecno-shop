from django.db import models
class Size(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Color(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class Product(models.Model):

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    image = models.ImageField(upload_to='products')
    size = models.ManyToManyField(Size, related_name='sizes',blank=True,null=True)
    color = models.ManyToManyField(Color, related_name='colors',blank=True,null=True)

    def __str__(self):
        return self.title