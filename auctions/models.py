from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.conf import settings

class Bids(models.Model):
    listing = models.ForeignKey("Listings", on_delete=models.CASCADE, related_name="bids")
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    bidder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids")

    
class Category(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name
    

class Comment(models.Model):
    listing = models.ForeignKey("Listings", related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Correct reference to custom user model
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.listing.title}"


class Listings(models.Model):
    title = models.CharField(max_length= 128)
    category = models.ForeignKey("Category", on_delete=models.CASCADE, related_name="listings")
    item_detail = models.CharField(max_length=512) 
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2)
    photo_url = models.URLField(max_length=200, default="")
    listed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    creation_time = models.DateTimeField(auto_now_add=True)
    active_status = models.BooleanField(default=True)
    watchlist_status = models.BooleanField(default=False)
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="won_listings")

    def __str__(self):
        most_recent_bid = self.bids.order_by('-timestamp').first()
        if most_recent_bid:
            return f"{self.title} in the {self.category} Category has a current bid price of {most_recent_bid.bid_amount}"
        else:
            return f"{self.title} in the {self.category} Category has no bids yet."
        
class User(AbstractUser):
    watchlist = models.ManyToManyField(Listings, related_name = "watchlist", blank=True)

    @property
    def watchlist_item_count(self):
        return self.watchlist.count()