# admin.py
from django.contrib import admin
from .models import *

admin.site.register(TouristicSite)
admin.site.register(UserProfile)
admin.site.register(Service)
admin.site.register(UserAction)
admin.site.register(EcoAction)
