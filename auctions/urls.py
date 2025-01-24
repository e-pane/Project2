from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("categories", views.categories, name="categories"),
    path("categories/<int:category_id>/", views.listings_by_category, name = "listings_by_category"),
    path("closed_listings", views.closed_listings, name="closed_listings"),
    path("create_listing", views.create_listing, name="create_listing"),
    path("listing/<int:listing_id>/", views.individual_listing, name = "individual_listing"),
    path("listing/<int:listing_id>/add_bid/", views.add_bid, name="add_bid"),
    path("listing/<int:listing_id>/add_comment/", views.add_comment, name="add_comment"),
    path("listing/<int:listing_id>/add_to_watchlist/", views.add_to_watchlist, name="add_to_watchlist"),
    path("listing/<int:listing_id>/close_auction/", views.close_auction, name="close_auction"), 
    path("listing/<int:listing_id>/remove_from_watchlist/", views.remove_from_watchlist, name="remove_from_watchlist"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("watchlist", views.watchlist, name="watchlist"),
]
