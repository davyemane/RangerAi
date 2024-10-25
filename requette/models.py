# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class TouristicSite(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=50, choices=[
        ('MONUMENT', 'Monument'),
        ('MUSEUM', 'Musée'),
        ('NATURE', 'Site Naturel'),
    ])
    latitude = models.FloatField()
    longitude = models.FloatField()
    image = models.ImageField(upload_to='sites/')
    eco_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

class Service(models.Model):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=[
        ('HOTEL', 'Hôtel'),
        ('RESTAURANT', 'Restaurant'),
        ('OTHER', 'Autre'),
    ])
    description = models.TextField()
    eco_friendly = models.BooleanField(default=False)
    latitude = models.FloatField()
    longitude = models.FloatField()
    site = models.ForeignKey(TouristicSite, on_delete=models.CASCADE, related_name='services')

class EcoAction(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    eco_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    completed_actions = models.ManyToManyField(EcoAction, through='UserAction')

class UserAction(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    action = models.ForeignKey(EcoAction, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
