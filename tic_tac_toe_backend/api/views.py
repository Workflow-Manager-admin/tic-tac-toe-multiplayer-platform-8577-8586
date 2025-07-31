from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, logout
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Game, Move, LeaderboardEntry
from .serializers import (
    UserSerializer,
    GameSerializer,
    MoveSerializer,
    LeaderboardSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@api_view(['GET'])
def health(request):
    return Response({"message": "Server is up!"})

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Registers a new user. POST username, password."""
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response({"error": "Username and password required."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username)
    user.set_password(password)
    user.save()
    # Also create leaderboard entry
    LeaderboardEntry.objects.create(user=user)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """User login. POST username, password. Returns token."""
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        })
    else:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_game(request):
    """Authenticated user starts a new game; board is empty, status waiting."""
    current_user = request.user
    # Find if user has an open game as X (otherwise spam prevention)
    open_game = Game.objects.filter(player_x=current_user, status='waiting').first()
    if open_game:
        return Response(GameSerializer(open_game).data)
    game = Game.objects.create(player_x=current_user, status='waiting')
    return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED)

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_game(request):
    """Current user joins an open waiting game as O."""
    current_user = request.user
    open_game = Game.objects.filter(status='waiting').exclude(player_x=current_user).first()
    if not open_game:
        return Response({"error": "No open games available."}, status=status.HTTP_404_NOT_FOUND)
    open_game.player_o = current_user
    open_game.status = 'active'
    open_game.save()
    return Response(GameSerializer(open_game).data)

# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_move(request):
    """Authenticated user makes a move. POST: game_id, position (0-8)"""
    current_user = request.user
    game_id = request.data.get("game_id")
    position = request.data.get("position")
    if game_id is None or position is None:
        return Response({"error": "Missing game_id or position."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        position = int(position)
    except Exception:
        return Response({"error": "Position must be integer 0-8."}, status=status.HTTP_400_BAD_REQUEST)
    if not (0 <= position < 9):
        return Response({"error": "Position must be between 0 and 8."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response({"error": "Game not found."}, status=status.HTTP_404_NOT_FOUND)
    if game.status != 'active':
        return Response({"error": "Game not active."}, status=status.HTTP_400_BAD_REQUEST)
    # Determine which symbol this user is
    if current_user == game.player_x:
        symbol = "X"
    elif current_user == game.player_o:
        symbol = "O"
    else:
        return Response({"error": "You are not a player in this game."}, status=status.HTTP_403_FORBIDDEN)
    try:
        board = list(game.board_state)
        if board[position] != " ":
            return Response({"error": "Cell occupied."}, status=status.HTTP_400_BAD_REQUEST)
        board[position] = symbol
        game.board_state = "".join(board)
        game.save()
        Move.objects.create(game=game, player=current_user, position=position, move_symbol=symbol)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # After move, check for winner/draw
    win = game.check_winner()
    if win == "X":
        game.status = "finished"
        game.winner = game.player_x
        game.save()
        update_leaderboard(game.player_x, game.player_o, winner="X")
    elif win == "O":
        game.status = "finished"
        game.winner = game.player_o
        game.save()
        update_leaderboard(game.player_x, game.player_o, winner="O")
    elif win == "draw":
        game.status = "finished"
        game.winner = None
        game.save()
        update_leaderboard(game.player_x, game.player_o, winner="draw")
    return Response(GameSerializer(game).data)

# PUBLIC_INTERFACE
def update_leaderboard(player_x, player_o, winner):
    """Update statistics and rating in leaderboards."""
    entry_x, _ = LeaderboardEntry.objects.get_or_create(user=player_x)
    entry_o, _ = LeaderboardEntry.objects.get_or_create(user=player_o)
    entry_x.games_played += 1
    entry_o.games_played += 1
    if winner == "X":
        entry_x.games_won += 1
        entry_o.games_lost += 1
        entry_x.rating += 15
        entry_o.rating -= 10
    elif winner == "O":
        entry_o.games_won += 1
        entry_x.games_lost += 1
        entry_o.rating += 15
        entry_x.rating -= 10
    else:  # draw
        entry_x.games_drawn += 1
        entry_o.games_drawn += 1
        entry_x.rating += 2
        entry_o.rating += 2
    entry_x.save()
    entry_o.save()

# PUBLIC_INTERFACE
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_games(request):
    """Return all games for the current user."""
    user = request.user
    games = Game.objects.filter(Q(player_x=user) | Q(player_o=user)).order_by('-created_at')
    return Response(GameSerializer(games, many=True).data)

# PUBLIC_INTERFACE
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_game_detail(request, game_id):
    """Get a game detail with move history."""
    user = request.user
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response({"error": "Game not found."}, status=status.HTTP_404_NOT_FOUND)
    if user != game.player_x and user != game.player_o:
        return Response({"error": "Not your game."}, status=status.HTTP_403_FORBIDDEN)
    moves = Move.objects.filter(game=game).order_by('created_at')
    game_data = GameSerializer(game).data
    game_data['moves'] = MoveSerializer(moves, many=True).data
    return Response(game_data)

# PUBLIC_INTERFACE
@api_view(['GET'])
@permission_classes([AllowAny])
def leaderboard(request):
    """Returns the leaderboard with stats and rating."""
    entries = LeaderboardEntry.objects.select_related('user').all().order_by('-rating')[:20]
    return Response(LeaderboardSerializer(entries, many=True).data)
