# serializers.py
from rest_framework import serializers
from .models import TouristicSite, Service, EcoAction, UserProfile, UserAction

class TouristicSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TouristicSite
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class EcoActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoAction
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class UserActionSerializer (serializers.ModelSerializer):
    class Meta:
        model = UserAction
        fields = '__all__'