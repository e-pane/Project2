from collections import defaultdict
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from decimal import Decimal
from .helpers import get_listing_context
from .models import User, Listings, Category, Bids, Comment


@login_required
def add_bid(request, listing_id):

    if request.method == "POST":
        try:
            bid_amount = Decimal(request.POST.get("bid_amount"))

        except (TypeError, ValueError):
            context = get_listing_context(listing_id)  
            context["bid_message"] = "Bid amount must be a number greater than the starting and current bids"  # Add the message to the context
            return render(request, "auctions/listing.html", context)
        
        listing = Listings.objects.get(pk=listing_id)
        starting_bid = listing.starting_bid 
        current_bid = listing.bids.order_by('-timestamp').first()

        if current_bid is None:
            current_bid = starting_bid
        else:
            current_bid = current_bid.bid_amount
        
        if bid_amount <= current_bid: 
            context = get_listing_context(listing_id)
            context["bid_message"] = "Bid amount must be greater than the current bid of: " 
            context["bid_value"] = current_bid
            return render(request, "auctions/listing.html", context)

        bid=Bids(listing=listing, bid_amount=bid_amount, bidder=request.user)
        bid.save()

        current_bid = listing.bids.order_by('-timestamp').first()

        context = get_listing_context(listing_id)
        context["bid_value"] = current_bid.bid_amount
        context["current_bid"] = current_bid
        
        return render(request, "auctions/listing.html", context)
                
    return render(request, 'auctions/listing.html', get_listing_context(listing_id))

@login_required
def add_comment(request, listing_id):
    if request.method == "POST":
        listing = Listings.objects.get(id=listing_id)
        comment = (request.POST.get("comment"))
        Comment.objects.create(listing=listing, user=request.user, text=comment)

        current_bid = listing.bids.order_by('-timestamp').first()

        context = get_listing_context(listing_id)
        context['comments'] = listing.comments.all()
        context['current_bid'] = current_bid
        context['watchlist_item_count'] = request.user.watchlist.count()

        return render(request, "auctions/listing.html", context)

@login_required
def add_to_watchlist(request, listing_id):
    if request.method == "POST":
        try:
            # Ensure the listing exists
            listing = Listings.objects.get(id=listing_id)

            
            if listing not in request.user.watchlist.all():
                request.user.watchlist.add(listing)
            
            watchlist_item_count = request.user.watchlist.count()
            active_listings = Listings.objects.filter(active_status=True).distinct()

            listings_with_bids = []

            for listing in active_listings:
                current_bid = listing.bids.order_by('-timestamp').first()
                bid_value = current_bid.bid_amount if current_bid else None
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": bid_value,
                })

            return render(request, "auctions/index.html", {
                'watchlist_item_count': watchlist_item_count,
                "listings_with_bids": listings_with_bids,
                "active_listings": active_listings,
            })
        
        except Listings.DoesNotExist:
            raise Http404("Listing not found.")
    else:
        return HttpResponse("Invalid request.")
    
def categories(request):
    return render(request, "auctions/categories.html", {"categories": Category.objects.all()})

@login_required
def close_auction(request, listing_id):
    if request.method == "POST":
        listing = Listings.objects.get(pk=listing_id)
        current_bid = listing.bids.order_by('-timestamp').first()

        if current_bid is None:
            current_bid = listing.starting_bid

        bidder = current_bid.bidder.username
        listing.winner = current_bid.bidder
        listing.active_status = False
        listing.save()

        if listing in request.user.watchlist.all():
            request.user.watchlist.remove(listing)
            request.user.save()

        if request.user.username == bidder:
            return render(request, "auctions/listing.html", {
                "auction_message":f"Congratulations { bidder }, you won this auction!!",
                "listing": listing,
                "current_bid": current_bid,
                "bidder":bidder,
            })
        
        else:
            return render(request, "auctions/listing.html", {
                "auction_message":"This Auction is Closed!!!",
                "bidder":bidder, 
                "current_bid":current_bid,
                "listing": listing,
            })

@login_required
def closed_listings(request):
    closed_listings = Listings.objects.filter(active_status=False).distinct()
    closed_listings_with_bids = []
    won_listings = closed_listings.filter(winner=request.user) if request.user.is_authenticated else []

    for listing in closed_listings:
                current_bid = listing.bids.order_by('-timestamp').first()
                closed_listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                })

    return render(request, "auctions/index.html", {
        "closed_listings_with_bids": closed_listings_with_bids,
        "won_listings": won_listings,
    })

@login_required
def create_listing(request):
    if request.method == "POST":
        # have new listing instantiated as a row and a class instance of Listings table
        title = request.POST.get("title")
        category = request.POST.get("category")
        description = request.POST.get("description")
        starting_bid = Decimal(request.POST.get("starting_bid"))
        photo_url = request.POST.get("photo_url")

        if category == "Other": 
            other_category = request.POST.get("other_category")
            category_instance = Category.objects.create(name=other_category)

        else:
            category_instance = Category.objects.get(name=category)

        listing = Listings(
            title=title, 
            category=category_instance, 
            item_detail=description, 
            starting_bid=starting_bid,
            photo_url=photo_url,
            listed_by=request.user,
            )
        
        listing.save()

        Bids.objects.create(
            listing=listing,
            bid_amount=starting_bid,
            bidder=request.user,  # The user creating the listing is the starting bidder
        )

        listings = Listings.objects.filter(active_status=True)

        listings_with_bids = []
        seen_ids = defaultdict(bool)

        for listing in listings:
            if listing.id not in seen_ids:
                seen_ids[listing.id] = True
                current_bid = listing.bids.order_by('-timestamp').first()
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                })

        return render(request, "auctions/index.html", {
            "listings_with_bids": listings_with_bids,
        })
    
    return render(request, "auctions/create_listing.html", {"categories": Category.objects.all()})

def index(request):
    active_listings = Listings.objects.filter(active_status=True).distinct()
    closed_listings = Listings.objects.filter(active_status=False).distinct()

    listings_with_bids = []
    seen_ids = set()

    for listing in active_listings:
        if listing.id not in seen_ids:
            current_bid = listing.bids.order_by('-timestamp').first()
            bid_value = current_bid.bid_amount if current_bid else None
            listings_with_bids.append({
                "listing":listing,
                "current_bid":current_bid if current_bid else None,
                "bid_value":bid_value,
            })
    
        seen_ids.add(listing.id)

    for listing in closed_listings:
        current_bid = listing.bids.order_by('-timestamp').first()  # Ensure correct bid is attached
        listing.current_bid = current_bid 

    return render(request, "auctions/index.html", {
        "listings_with_bids": listings_with_bids,
        "active_listings": active_listings,
    })

def individual_listing(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)

    current_bid = listing.bids.order_by('-timestamp').first()
    
    if current_bid is None:
        current_bid = listing.starting_bid
    
    context = get_listing_context(listing_id)
    context['current_bid'] = current_bid
    context['watchlist_item_count'] = request.user.watchlist.count()
    context['watchlist_status'] = listing in request.user.watchlist.all()
    context['comments'] = listing.comments.all()

    return render(request, "auctions/listing.html", context)

def listings_by_category(request, category_id):
    category = Category.objects.get(id=category_id)
    listings = category.listings.all()

    return render(request,"auctions/listings_by_category.html", {
        "category": category,
        "listings": listings
    })

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)

            active_listings = Listings.objects.filter(active_status=True).distinct()
            closed_listings = Listings.objects.filter(active_status=False).distinct()
            
            won_listings = closed_listings.filter(winner=request.user) if request.user.is_authenticated else []
            listings_with_bids = []
            closed_listings_with_bids = []

            for listing in active_listings:
                current_bid = listing.bids.order_by('-timestamp').first()
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": current_bid.bid_amount if current_bid and current_bid.bidder == user else None,
                })

            for listing in closed_listings:
                current_bid = listing.bids.order_by('-timestamp').first()
                closed_listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": current_bid.bid_amount if current_bid and current_bid.bidder == user else None,
                })

            watchlist_item_count = request.user.watchlist.count()
            print(watchlist_item_count)

            return render(request, "auctions/index.html", {
                "listings_with_bids": listings_with_bids,
                "closed_listings_with_bids": closed_listings_with_bids,
                "won_listings": won_listings,
                "watchlist_item_count": watchlist_item_count,
            })
        
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required   
def remove_from_watchlist(request, listing_id):
    if request.method == "POST":
        try:
            # Ensure the listing exists
            listing = Listings.objects.get(id=listing_id)

            # Update watchlist status
            if listing in request.user.watchlist.all():
                request.user.watchlist.remove(listing)

            # Redirect to the watchlist page or the index page after the update
            return redirect('index')  # Or redirect('watchlist')
        except Listings.DoesNotExist:
            raise Http404("Listing not found.")
    else:
        return HttpResponse("Invalid request.")

@login_required 
def watchlist(request):
    if request.method == "GET":
        watchlist = request.user.watchlist.all()
    
    watchlist_item_count = request.user.watchlist.count()

    return render(request, "auctions/watchlist.html", {
        "watchlist": watchlist,
        "watchlist_item_count": watchlist_item_count,
    })
