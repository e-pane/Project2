from auctions.models import Listings

def get_current_bid(listing):
    current_bid = listing.bids.order_by('-timestamp').first()
    return current_bid.bid_amount if current_bid else listing.starting_bid

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
        "active_status": listing.active_status,
        "watchlist_status": listing.watchlist_status,
        "starting_bid": listing.starting_bid,
        "winner": listing.winner,
    }

