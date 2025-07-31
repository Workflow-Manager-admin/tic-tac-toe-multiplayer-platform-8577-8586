from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="Health"),
    path("register/", views.register, name="Register"),
    path("login/", views.login_view, name="Login"),
    path("logout/", views.logout_view, name="Logout"),
    path("start/", views.start_game, name="StartGame"),
    path("join/", views.join_game, name="JoinGame"),
    path("move/", views.make_move, name="MakeMove"),
    path("games/", views.get_games, name="GetGames"),
    path("games/<int:game_id>/", views.get_game_detail, name="GameDetail"),
    path("leaderboard/", views.leaderboard, name="Leaderboard"),
]
