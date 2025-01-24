from django.contrib import admin
from .models import Listings, Category, User, Bids

# Register your models here.
admin.site.register(Listings)
admin.site.register(Category)
admin.site.register(User)
admin.site.register(Bids)
