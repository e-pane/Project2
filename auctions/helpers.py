from auctions.models import Listings



def get_listing_context(listing_id):
    listing = Listings.objects.get(id=listing_id)
    return {
        "listing": listing,
        "title": listing.title,
        "photo_url": listing.photo_url,
        "item_detail": listing.item_detail,
        "current_bid": listing.bids.order_by('-timestamp').first().bid_amount if listing.bids.exists() else None,
        "listed_by": listing.listed_by,
        "category": listing.category,
        "bid_count": listing.bids.count(),
        "watchlist_status": listing.watchlist_status,
        "starting_bid": listing.starting_bid,
    }

