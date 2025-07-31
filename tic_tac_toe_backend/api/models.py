from django.db import models
from django.contrib.auth.models import AbstractUser

# PUBLIC_INTERFACE
class User(AbstractUser):
    """Custom user for multiplayer tic-tac-toe."""
    rating = models.IntegerField(default=1000, help_text="Elo-style rating for leaderboard.")

    def __str__(self):
        return self.username

class Game(models.Model):
    """Tracks a game between 2 users (or one user with open slot)."""
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('active', 'Active'),
        ('finished', 'Finished'),
    )
    player_x = models.ForeignKey(User, related_name='games_as_x', on_delete=models.CASCADE)
    player_o = models.ForeignKey(User, related_name='games_as_o', on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    winner = models.ForeignKey(User, related_name='games_won', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    board_state = models.CharField(
        max_length=9, default=" " * 9,
        help_text="Flat string representation of board, 9 chars (X/O/space)."
    )

    def __str__(self):
        return f"Game {self.id}: {self.player_x} vs {self.player_o or 'TBD'}"

    # PUBLIC_INTERFACE
    def make_move(self, player, position):
        """Attempt a move; player's symbol is 'X' or 'O' depending on user."""
        if self.status != "active":
            raise ValueError("Game is not active.")
        symbol = 'X' if player == self.player_x else 'O'
        board = list(self.board_state)
        if board[position] != " ":
            raise ValueError("Cell already occupied.")
        board[position] = symbol
        self.board_state = "".join(board)
        self.save()
        return board

    # PUBLIC_INTERFACE
    def check_winner(self):
        """Returns 'X', 'O', or None if no winner yet."""
        combos = [
            [0,1,2],[3,4,5],[6,7,8],
            [0,3,6],[1,4,7],[2,5,8],
            [0,4,8],[2,4,6],
        ]
        b = self.board_state
        for line in combos:
            chars = {b[i] for i in line}
            if chars == {"X"}:
                return "X"
            if chars == {"O"}:
                return "O"
        if " " not in b:
            return "draw"
        return None

class Move(models.Model):
    """Tracks a single move."""
    game = models.ForeignKey(Game, related_name='moves', on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    move_symbol = models.CharField(max_length=1)  # 'X' or 'O'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Move {self.position} by {self.player} in game {self.game.id}"

# PUBLIC_INTERFACE
class LeaderboardEntry(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=1000)
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    games_lost = models.IntegerField(default=0)
    games_drawn = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Leaderboard Entry"
        verbose_name_plural = "Leaderboard Entries"
        ordering = ['-rating']

    def __str__(self):
        return f"{self.user.username}: {self.rating}"
