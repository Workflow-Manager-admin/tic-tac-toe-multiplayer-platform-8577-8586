from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Game, Move, LeaderboardEntry

User = get_user_model()

# PUBLIC_INTERFACE
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'rating')

# PUBLIC_INTERFACE
class GameSerializer(serializers.ModelSerializer):
    player_x = UserSerializer(read_only=True)
    player_o = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)

    class Meta:
        model = Game
        fields = ('id', 'player_x', 'player_o', 'status', 'winner', 'created_at', 'updated_at', 'board_state')

# PUBLIC_INTERFACE
class MoveSerializer(serializers.ModelSerializer):
    player = UserSerializer(read_only=True)
    class Meta:
        model = Move
        fields = ('id', 'game', 'player', 'position', 'move_symbol', 'created_at')

# PUBLIC_INTERFACE
class LeaderboardSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = LeaderboardEntry
        fields = ('user', 'rating', 'games_played', 'games_won', 'games_lost', 'games_drawn')
