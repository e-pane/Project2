from django.conf import settings
from .models import Listings

def watchlist_item_count(request):
    if request.user.is_authenticated:
        count = Listings.objects.filter(watchlist_status=True).count()
    else:
        count = 0
    return {
        'watchlist_item_count': count
    }