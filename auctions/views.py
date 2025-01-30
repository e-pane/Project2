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
            # request.user is pulling the correct instance from the user table based on the incoming
            #http request  - .watchlist is a related manager automatically created by Django bc we linked
            #the user table to the listing table via a manytomany field called watchlist - so watchlist
            #is a related manager (object) that's going to grant access to the Listings table via the 
            #manytomany - so .all is a method the related manager (.watchlist) will use to access the 
            #Listings table.  But - and here's the trick part.... Bc of the manytomany field linking user
            #table and listings table, django is automatically making a join table called user_watchlist
            #that's storing all the listings that a user added at least once to their watchlist (via the
            #Add to Watchlist button on listings.html).  Even if a user removed a listing from their
            #watchlist, it will still show in the user_watchlist join table.  So .all method applied to 
            #the join table will use the manytomany to head to the listings table and pull all listings
            #for that user that have been added to their watchlist.  And right below that, after we've
            #checked that a listing in not in that join table, we'll add it to that join table with
            #the .add method applied to the watchlist related manager.  .add must take an instance as 
            #a parameter, so listing is that passed parameter to be added to the join table. remembering
            #that watchlist is a related manager SPECIFIC to the one authenticated user only
            if listing not in request.user.watchlist.all():
                request.user.watchlist.add(listing)
            #if the listing is in the join table, we'll use the property decorator (in the User model
            # to directly access the watchlist_item_count attribute, which is the number of listings in 
            # the user_watchlist join table Django makes behind the scenes.  So it's a count of listings
            # in the join table for just this user where the listing has been added at one point or 
            # another to their watchlist.  Note that the property decorator method watchlist_item_count
            # is just using the .count() method of the watchlist related manager to do the counting in 
            # the user_watchlist join table!!  
            watchlist_item_count = request.user.watchlist_item_count
            #now filter ALL users for active listings by the True filter and keep them unique
            active_listings = Listings.objects.filter(active_status=True).distinct()
            # initialize an empty list
            listings_with_bids = []
            #loop through queryset of listing instances
            for listing in active_listings:
                #return most current_bid value for each listing with helper function
                current_bid = get_current_bid(listing)
                #set bid_value to that current_bid value
                bid_value = current_bid if current_bid else None
                #for each iteration, adding a dict with 3 key:value pairs to the list
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": bid_value,
                })
            #rendering to the template a value, list and instance, respectively
            return render(request, "auctions/index.html", {
                'watchlist_item_count': watchlist_item_count,
                "listings_with_bids": listings_with_bids,
                "active_listings": active_listings,
            })
        
        except Listings.DoesNotExist:
            raise Http404("Listing not found.")
    else:
        return HttpResponse("Invalid request.")
    
def categories(request): # simple get request to render a queryset of all instances of Category table
    return render(request, "auctions/categories.html", {"categories": Category.objects.all()})

@login_required
def close_auction(request, listing_id): # if the listing shown was listed by the authenticated user
    #the user can close the auction with a button
    if request.method == "POST":
        #get the correct Listings instance using the form data id
        listing = Listings.objects.get(pk=listing_id)
        #get current bid from the helper function
        current_bid = get_current_bid(listing)
        #fetch the current bidder by querying the Bids table, filtering on the listing and bid_amount
        #fields (columns) of the table to get just the one bid instance for this user with the most recent
        #bid and access the .bidder field to get an instance for that user since user and bids models 
        # are linked with a one to many field. Note: if the bidder field were just a normal field, .bidder
        #would return a value (string, integer, datetime). but the bidder field is a foreign key field
        #so it will head over to the user model and return a complete instance
        current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
        #access the winner field of the fetched listing instnace and set to current_bidder
        listing.winner = current_bidder
        #toggle active_status field of the listing instance to False and save it. 
        listing.active_status = False
        listing.save()
        #complex use of request.user.watchlist.all to access all the listings in the user_watchlist
        #join table for just his user and check if this particular listing instance is in that queryset
        if listing in request.user.watchlist.all():
            #if if is, remove the listing from the join table. Note that this is not the same as "removing"
            #from the watchlist!  This is removing the entry from the join table
            request.user.watchlist.remove(listing)
            request.user.save()
        #bc request.user retrieves an instance from the user model, and current_bidder is already an 
        #instance from the user model.... 
        if request.user == current_bidder:
            #context rendered will be a formatted string, instance, value, and value respectively, with
            #that last value bc current_bidder is an instance of the user table, but .username accesses 
            #the string field (Charfield) of the actual name of the user from the instance
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
def closed_listings(request): #to render only closed listings upon get request from layout.html header link
    #get a filtered and unique queryset from listings table
    closed_listings = Listings.objects.filter(active_status=False).distinct()
    #initiate an empty list
    closed_listings_with_bids = []
    #filter down even further on the returned query set to pull just the closed listings that the
    #authentic user won.  Again, filtering on request.user, which has to be an instance of the user table
    # equal to winner, which is a field in the listing table, but bc it's a foreign key to the user table
    #winner will be an instance of the user table.  If winner.username, then we'd get the name of winner
    won_listings = closed_listings.filter(winner=request.user) if request.user.is_authenticated else []
    #loop through the closed_listings queryset
    for listing in closed_listings:
        #fetch current bid for each listing iteration with helper function
        current_bid = get_current_bid(listing)
        if current_bid:
            #get the current_bidder instance from the user table via the Bids table via the bidder
            #foreign key field in the Bids table and filter to get just the instance that matches
            #the iterated listing and where the bid_amount field in the Bids table is a decimal
            #value and current_bid is a value returned with the helper function
            current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
        else:
            current_bidder = None
        #to the list, append a dict for each iteration with an instance, value and instance,
        #respectively
        closed_listings_with_bids.append({
            "listing": listing,
            "current_bid": current_bid if current_bid else None,
            "current_bidder": current_bidder,
        })
    #render a list and queryset, respectively
    return render(request, "auctions/index.html", {
        "closed_listings_with_bids": closed_listings_with_bids,
        "won_listings": won_listings,
    })

@login_required
def create_listing(request): #to make a new listing via a link in layout.html header
    if request.method == "POST":
        #go to work retrieving all the form data from create_listing template
        title = request.POST.get("title")
        category = request.POST.get("category")
        description = request.POST.get("description")
        #convert starting_bid to a decimal bc all form data is in string form
        starting_bid = Decimal(request.POST.get("starting_bid"))
        photo_url = request.POST.get("photo_url")
        #form data is coming in with either a value of "Other" or a name of the category selected from
        #a drop-down menu in the template.  Since it's a dropdown, we're dealing in incoming "values"
        if category == "Other":
            #if "Other" is the selected incoming value from dropdown, a textarea will deliver a name 
            # attribute called "other_category" containing the text we need in string form
            other_category = request.POST.get("other_category")
            #filter on the name field of the category table equaling the string value of other_category
            #and retrieve the correct instance from the Category table based on name
            category_instance = Category.objects.create(name=other_category)

        else:
            #do the same if the incoming string value is the name of the category (bc the template form
            #is set up to send in the name of the category as a string when it's selected from drop-down)
            category_instance = Category.objects.get(name=category)
        #instantiate the new instance of the Listings table adding in the form data pulled from the 
        #submission - including the conditional category_instance string value.  Note that there are 10
        #fields in the Listings table and we only have 6 here.  watchlist_status and active_status are 
        #defaulted to False and True, respectively in the Model, and creation_time is auto-set by Django
        #that leaves just winner, which doesn't need direct instantiation bc it has a Null=True attribute 
        #in the Field, so the winner "instance" will default to Null if no instance is given here (which it
        #isn't).  winner field has to be an instance b/c it's a foreign key. Same for listed_by and 
        #category, which are both given below as instances
        listing = Listings(
            title=title, 
            category=category_instance, 
            item_detail=description, 
            starting_bid=starting_bid,
            photo_url=photo_url,
            listed_by=request.user,
            )
        
        listing.save()
        #instantiate an instance of the Bids table with .create  listing field needs an instance, since
        #it's a foreign key to the listing table. and bidder must be an instance, since it's a foreign
        #key to the user table.  timestamp is the 4th field of Bids, but Django will autopopulate 
        Bids.objects.create(
            listing=listing,
            bid_amount=starting_bid,
            bidder=request.user,  # The user creating the listing is the starting bidder
        )
        #pull a queryset from Listings of only active listings
        listings = Listings.objects.filter(active_status=True)
        #initiate an empty list
        listings_with_bids = []
        #loop through each instance in the queryset
        for listing in listings:
            #get current_bid for each instance from the helper
            current_bid = get_current_bid(listing)
            #append a dict to the list for each row with 2 keys an instance and a value, respectively
            listings_with_bids.append({
                "listing": listing,
                "current_bid": current_bid if current_bid else None,
            })

        return render(request, "auctions/index.html", {
            "listings_with_bids": listings_with_bids,
        })
    
    return render(request, "auctions/create_listing.html", {"categories": Category.objects.all()})

def index(request): #to show the user's "home page" - with both active and closed listings
    #fetch unique and filtered instances from listings table
    active_listings = Listings.objects.filter(active_status=True).distinct()

    listings_with_bids = []
    #loop through each instance in the queryset
    for listing in active_listings:
        #get value of current_bid from helper
        current_bid = get_current_bid(listing)
        #set bid_value to current_bid
        bid_value = current_bid if current_bid else None
        #for each iteration, add dict of instance, value, value, respectively, to the list 
        listings_with_bids.append({
            "listing":listing,
            "current_bid":current_bid if current_bid else None,
            "bid_value":bid_value,
        })

    #render to the template a list and an instance
    return render(request, "auctions/index.html", {
        "listings_with_bids": listings_with_bids,
        "active_listings": active_listings,
    })

def individual_listing(request, listing_id): #to show an individual listing from index.html hyperlink
    #fetch correct instance
    listing = Listings.objects.get(pk=listing_id)  
    #get current_bid value from helper  
    current_bid = get_current_bid(listing)
    #fetch current_bidder as an instance
    if current_bid:
        current_bidder = Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
    else:
        current_bidder = None
    #fetch context as dict with helper function
    context = get_listing_context(listing_id)
    #add 5 keys to the dict for value, instance, value, bool, and queryset, respectively
    context['current_bid'] = current_bid
    context['current_bidder'] = current_bidder
    #watchlist_item_count will be a value here as the @property decorator functions as an attribute
    context['watchlist_item_count'] = request.user.watchlist_item_count
    #here, request.user.watchlist.filter(active_status=True) will have the related manager "watchlist"
    #apply the .filter method to the listings table and pull only the user's listings from the join table
    #where active_status is true in the Listings table, then listing in is a Bool test that will 
    #evaluate to true if the listing in question is both in the join user_watchlist table and active_status
    #is True in listings table.context value "listing in request.user.watchlist.filter(active_status=True)"
    #will evaluate to False if the listing is not BOTH in the join table and active_status is True in 
    #the Listing table.  In listing.html will be a conditional "if watchlist_status" that will check
    #if the rendered Bool is true or fals.
    context['watchlist_status'] = listing in request.user.watchlist.filter(active_status=True)
    #and a queryset here of all instances of the comments table for this listing, via a foreign key field
    #in the comments table referencing this specific listing
    context['comments'] = listing.comments.all()

    return render(request, "auctions/listing.html", context)

def listings_by_category(request, category_id): #from a hyperlink click on a category, return listings
    #fetch the correct instance from Category table
    category = Category.objects.get(id=category_id)
    #return a queryset of all instances of listings that have this specific category - note that the
    # category field of the Listings table is a foreign key linking to the category table 
    listings = category.listings.all()

    return render(request,"auctions/listings_by_category.html", {
        "category": category,
        "listings": listings
    })

def login_view(request):
    if request.method == "POST":  # when user clicks on "log in" button after entering username and pword
        #pull creds from form data
        username = request.POST["username"]
        password = request.POST["password"]
        #use authenticate method from django.contrib.auth - it returns a user instance if successful
        #and None if fail
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            #use the login method from django.contrib.auth, pass it the user instance (subclass) and the
            #request object (from browser's http request and it will return a session 
            # (dict like structure) for this user
            login(request, user)
            #fetch querysets of instances of active and closed listings filtering on active_status
            active_listings = Listings.objects.filter(active_status=True).distinct()
            closed_listings = Listings.objects.filter(active_status=False).distinct()
            #filter to an even tighter query set on whether the winner instance equals the request.user
            #instance - note that django made the request.user instance by first storing the user's session
            #as a dictlike structure with a key of id, then each incoming request, django's middleware retrieves
            #the id value and with that user id queries the user table to get the request.user instance
            #from the user table
            won_listings = closed_listings.filter(winner=request.user) if request.user.is_authenticated else []
            listings_with_bids = []
            closed_listings_with_bids = []
            #loop through the active_listings q-set for each instance
            for listing in active_listings:
                #use helper to get current_bid of this listing as a value
                current_bid = get_current_bid(listing)
                #fetch current_bidder as an instance of the user table, looking for the instance with this 
                #specific listing and the current_bid is the bid_amount field value.  using .get 
                #here bc we expect only 1 instance returned.  .filter would be used if we were expecting
                #a q-set of instances
                current_bidder = ( 
                    Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
                    if current_bid else None
                )
                #add listing instance, and current_bid value (twice!)
                listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "bid_value": current_bid if current_bid and current_bidder == user else None,
                })
            #loop through the closed_listings q-set for each instance
            for listing in closed_listings:
                current_bid = get_current_bid(listing)
                current_bidder = (
                Bids.objects.get(listing=listing, bid_amount=current_bid).bidder
                if current_bid else None
                )
                # add to the list, including adding the current_bidder instance and only adding the 
                #current_bid value if the current_bidder instance equals the user instance that django's
                #authenticate method gave us (i.e. to tell us this particular user is the current 
                #highest bidder)
                closed_listings_with_bids.append({
                    "listing": listing,
                    "current_bid": current_bid if current_bid else None,
                    "current_bidder": current_bidder,
                    "bid_value": current_bid if current_bid and current_bidder == user else None,
                })
            # use the @property decorator to access the watchlist_item_count value of the request.user
            # object, as the decorator uses the watchlist related manager to wield the .count method to
            # count the instances in the join table.  BUT... here's where it gets very tricky... the join
            # table includes all listings once added to the watchlist, and even those subsequently
            # removed from the watchlist will stay in the join table.  But somehow, the watchlist related
            # manager knows that a listing once added but since removed from the watchlist stays in the
            # join table, but the "relationship" is "broken" and django's ORM abstracting applies a 
            # filter like watchlist_status=True to the join table, so the line below somehow only pulls
            # the instances from the join table where the listing is still actively on the watchlist!!!
            watchlist_item_count = request.user.watchlist_item_count

            return render(request, "auctions/index.html", {
                "listings_with_bids": listings_with_bids,
                "closed_listings_with_bids": closed_listings_with_bids,
                "won_listings": won_listings,
                "watchlist_item_count": watchlist_item_count,
            })
        #if creds fail, send a message
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    #if a get request (user clicked on log-in link), give them the login page
    else:
        return render(request, "auctions/login.html")


def logout_view(request): #when user clicks log out hyperlink, redirect to index.html
    logout(request)
    #note the redirect here as no context needs to be passed, so reverse redirect is fine
    return HttpResponseRedirect(reverse("index"))


def register(request):  #to get a potential user registered with creds
    if request.method == "POST":
        #pull creds from incoming form data
        username = request.POST["username"]
        email = request.POST["email"]
        #pull pword creds from form data and ensure they match
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            #this is django using the abstractuser subclass of user class to instantiate an instance
            # of the user table for us, filling in the required fields for us 
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
def remove_from_watchlist(request, listing_id):  # to remove a listing from a user's watchlist
    if request.method == "POST":
        try:
            # fetch the correct instance
            listing = Listings.objects.get(id=listing_id)

            # again, that complex use of the request.user object having a related manager called 
            #watchlist that can use the .all method to read the whole user_watchlist join table to see
            #if our specific listing instance is in that table.  If it is, use the watchlist related
            #manager to call the .remove method to remove this listing from the join table
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
        #again, the watchlist related manager will query the join table and pull all instances for this
        #user, somehow also applying a filter like watchlist_status=True to the query behind the scenes
        #so that watchlist will be a q-set with only instances where watchlist_status=True
        watchlist = request.user.watchlist.all()
    #and again, how to get the count from the join table, while also filtering for watchlist_status=True
    #with django doing that filtering behind the scenes for us!!
    watchlist_item_count = request.user.watchlist_item_count

    return render(request, "auctions/watchlist.html", {
        "watchlist": watchlist,
        "watchlist_item_count": watchlist_item_count,
    })
