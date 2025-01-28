from collections import defaultdict
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from decimal import Decimal
from .helpers import get_listing_context, get_current_bid
from .models import User, Listings, Category, Bids, Comment


@login_required
def add_bid(request, listing_id): #add a bid to an active listing

    if request.method == "POST":
        try:
            bid_amount = Decimal(request.POST.get("bid_amount")) #fetch form data from listing.html form
        except (TypeError, ValueError):
            #call helper function to return a dictionary of the fields from Listings Model
            context = get_listing_context(listing_id) 
            #add a key of "bid_message" to the context dict 
            context["bid_message"] = "Bid amount must be a number greater than the starting and current bids"  # Add the message to the context
            return render(request, "auctions/listing.html", context)
        
        listing = Listings.objects.get(pk=listing_id) #get specific listing instance from Listings model
        current_bid = get_current_bid(listing) #call helper to return current_bid as a decimal value
        
        if bid_amount <= current_bid: # check if form submitted bid_amount is less than current_bid, if so
            context = get_listing_context(listing_id) #fetch context dict
            #add keys of "bid_message" and "bid_value" to the context dict with appropriate values 
            context["bid_message"] = "Bid amount must be greater than the current bid of: " 
            context["bid_value"] = current_bid
            return render(request, "auctions/listing.html", context)

        #if submitted bid_amount is greater than current_bid, instantiate an instance of the Bids class
        bid=Bids(listing=listing, bid_amount=bid_amount, bidder=request.user)
        bid.save()
        #fetch context dict again and add keys and values to the context dict
        context = get_listing_context(listing_id)
        context["bid_value"] = current_bid
        context["current_bid"] = bid_amount
        context["bid_value"] = bid_amount
        
        return render(request, "auctions/listing.html", context)
                
    return render(request, "auctions/listing.html", context)

@login_required
def add_comment(request, listing_id): #to add a comment to an individual listing
    if request.method == "POST":
        listing = Listings.objects.get(id=listing_id) #fetch the listing instance
        comment = (request.POST.get("comment")) #fetch the form data called "comment"
        #instantiate an instance of the Comment class
        comment = Comment(listing=listing, user=request.user, text=comment)
        comment.save()

        current_bid = get_current_bid(listing) #call helper to retrieve current_bid as a value

        context = get_listing_context(listing_id) #call helper to fetch context dict then add keys:values
        #specifically, use listing.comments to use foreign key to access comments for the given listing
        #then use .all on listing.comments to get all of the comments for that listing
        context['comments'] = listing.comments.all() 
        context['current_bid'] = current_bid
        #specifically watchlist is a ManytoMany field in the User model connecting User and Listings 
        # models, where one User can have many listings on their watchlist, and any Listing can be on 
        # many User's watchlist But instead of accessing the watchlist field of the User model, the User
        # model also has a decorator that returns watchlist_item_count as an attribute. So 
        # request.user.watchlist_item_count is the product of a decorator leaning on the manytomany
        # field called watchlist in the user model - linking the user and Listings models 
        context['watchlist_item_count'] = request.user.watchlist_item_count

        return render(request, "auctions/listing.html", context)

@login_required
def add_to_watchlist(request, listing_id):
    if request.method == "POST":
        try:
            listing = Listings.objects.get(id=listing_id) #fetch correct listing instance
            # use Python "not in" to say if the fetched instance isn't among all of the given user's
            #
            if listing not in request.user.watchlist.all():
                request.user.watchlist.add(listing)
            
            watchlist_item_count = request.user.watchlist.count()
            active_listings = Listings.objects.filter(active_status=True).distinct()

            listings_with_bids = []

            for listing in active_listings:
                current_bid = get_current_bid(listing)
                bid_value = current_bid if current_bid else None
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
        current_bid = get_current_bid(listing)
        current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder

        listing.winner = current_bidder
        listing.active_status = False
        listing.save()

        if listing in request.user.watchlist.all():
            request.user.watchlist.remove(listing)
            request.user.save()

        if request.user == current_bidder:
            return render(request, "auctions/listing.html", {
                "auction_message":f"Congratulations { current_bidder.username }, you won this auction!!",
                "listing": listing,
                "current_bid": current_bid,
                "bidder":current_bidder.username,
            })
        
        else:
            return render(request, "auctions/listing.html", {
                "auction_message":"This Auction is Closed!!!",
                "bidder":current_bidder.username,
                "current_bid":current_bid,
                "listing": listing,
            })

@login_required
def closed_listings(request):
    closed_listings = Listings.objects.filter(active_status=False).distinct()
    closed_listings_with_bids = []
    won_listings = closed_listings.filter(winner=request.user) if request.user.is_authenticated else []

    for listing in closed_listings:
                current_bid = get_current_bid(listing)
                if current_bid:
                    current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
                else:
                    current_bidder = None

                closed_listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "current_bidder": current_bidder,
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
                current_bid = get_current_bid(listing)
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
            current_bid = get_current_bid(listing)
            bid_value = current_bid if current_bid else None
            listings_with_bids.append({
                "listing":listing,
                "current_bid":current_bid if current_bid else None,
                "bid_value":bid_value,
            })
    
        seen_ids.add(listing.id)

    for listing in closed_listings:
        current_bid = get_current_bid(listing)  # Ensure correct bid is attached
        listing.current_bid = current_bid 

    return render(request, "auctions/index.html", {
        "listings_with_bids": listings_with_bids,
        "active_listings": active_listings,
    })

def individual_listing(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)

    if not listing.active_status:
        current_bid = get_current_bid(listing)
    
        if current_bid:
            current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
        else:
            current_bidder = None
    
        context = {
            "listing": listing,
            "current_bid": current_bid if current_bid else None,
            "current_bidder": current_bidder,
            "auction_message": "This auction has ended.",
        }

        return render(request, "auctions/listing.html", context)
    
    current_bid = get_current_bid(listing)
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
                current_bid = get_current_bid(listing)
                current_bidder = ( 
                    Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
                    if current_bid else None
                )
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": current_bid if current_bid and current_bidder == user else None,
                })

            for listing in closed_listings:
                current_bid = get_current_bid(listing)
                current_bidder = (
                Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
                if current_bid else None
                )
                
                closed_listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": current_bid if current_bid and current_bidder == user else None,
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
