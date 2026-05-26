# Import all models so db.create_all() registers every table (PostgreSQL on Render).
from .user import User
from .user_daily_stats import UserDailyStats
from .workout import Workout
from .social import (
    Achievement,
    Challenge,
    ChallengeItem,
    ChallengeParticipant,
    Exercise,
    ExerciseSession,
    Friendship,
    GlobalLeaderboard,
    PoseMetric,
    UserAchievement,
)
from .rewards import RewardItem, RewardRedemption, RewardShopSettings

__all__ = [
    "User",
    "UserDailyStats",
    "Workout",
    "Achievement",
    "UserAchievement",
    "Friendship",
    "Challenge",
    "ChallengeItem",
    "ChallengeParticipant",
    "Exercise",
    "ExerciseSession",
    "PoseMetric",
    "GlobalLeaderboard",
    "RewardItem",
    "RewardRedemption",
    "RewardShopSettings",
]
