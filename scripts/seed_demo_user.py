#!/usr/bin/env python3
"""Create demo user testing123 / password with workouts, stats, friends, achievements."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_USERNAME = "testing123"
DEMO_EMAIL = "testing123@fitquest.local"
DEMO_PASSWORD = "password"
DEMO_DISPLAY = "Test Player"

FRIEND_USERS = [
    {"username": "fitquest_ana", "email": "ana@fitquest.local", "display_name": "Ana Quest"},
    {"username": "fitquest_miko", "email": "miko@fitquest.local", "display_name": "Miko Fit"},
]

WORKOUT_TEMPLATES = [
    ("pushup", "Push-ups", "medium", 180, 45, 120),
    ("squat", "Squats", "easy", 240, 60, 150),
    ("plank", "Plank Hold", "medium", 120, 0, 80),
    ("situp", "Sit-ups", "easy", 200, 40, 100),
    ("burpees", "Burpees", "hard", 300, 25, 200),
    ("lunges", "Lunges", "medium", 220, 50, 130),
]


def _upsert_leaderboard(user) -> None:
    from app import db
    from app.models.social import GlobalLeaderboard

    row = GlobalLeaderboard.query.get(user.id)
    if not row:
        row = GlobalLeaderboard(user_id=user.id)
        db.session.add(row)
    row.username = user.username
    row.display_name = user.display_name
    row.avatar_url = user.avatar_url
    row.total_points = user.total_points
    row.level = user.level
    row.current_streak_days = user.current_streak_days
    row.longest_streak_days = user.longest_streak_days


def main() -> None:
    from app import create_app, db
    from app.models.rewards import RewardItem, RewardRedemption
    from app.models.social import (
        Achievement,
        Challenge,
        ChallengeParticipant,
        Friendship,
        GlobalLeaderboard,
        UserAchievement,
    )
    from app.models.user import User
    from app.models.user_daily_stats import UserDailyStats
    from app.models.workout import Workout
    from app.routes.rewards_routes import seed_achievements, seed_reward_catalog

    app = create_app()
    with app.app_context():
        seed_achievements()
        seed_reward_catalog()

        demo = User.query.filter_by(username=DEMO_USERNAME).first()
        if not demo:
            demo = User(
                email=DEMO_EMAIL,
                username=DEMO_USERNAME,
                display_name=DEMO_DISPLAY,
            )
            demo.set_password(DEMO_PASSWORD)
            db.session.add(demo)
            db.session.flush()
            print(f"Created user {DEMO_USERNAME} (id={demo.id})")
        else:
            demo.set_password(DEMO_PASSWORD)
            print(f"Updated password for {DEMO_USERNAME} (id={demo.id})")

        # Clear old demo-linked rows so re-run is idempotent
        Workout.query.filter_by(user_id=demo.id).delete()
        UserDailyStats.query.filter_by(user_id=demo.id).delete()
        UserAchievement.query.filter_by(user_id=demo.id).delete()
        RewardRedemption.query.filter_by(user_id=demo.id).delete()
        Friendship.query.filter(
            (Friendship.requester_id == demo.id) | (Friendship.addressee_id == demo.id)
        ).delete(synchronize_session=False)
        for ch in Challenge.query.filter_by(created_by=demo.id).all():
            ChallengeParticipant.query.filter_by(challenge_id=ch.id).delete()
            db.session.delete(ch)
        GlobalLeaderboard.query.filter_by(user_id=demo.id).delete()

        today = date.today()
        demo.display_name = DEMO_DISPLAY
        demo.gender = "male"
        demo.birth_date = date(1998, 6, 15)
        demo.height_cm = 175
        demo.weight_kg = 75
        demo.target_weight_kg = 70
        demo.fitness_level = "intermediate"
        demo.fitness_goal = "lose_weight"
        demo.has_completed_onboarding = True
        demo.current_streak_days = 5
        demo.longest_streak_days = 7
        demo.last_active_date = today

        total_points = 0
        total_reps = 0
        daily: dict[date, dict] = {}

        for day_offset in range(13, -1, -1):
            if day_offset % 2 == 1 and day_offset > 0:
                continue
            wdate = today - timedelta(days=day_offset)
            tpl = WORKOUT_TEMPLATES[(13 - day_offset) % len(WORKOUT_TEMPLATES)]
            ex_id, title, diff, duration, reps, pts = tpl
            started = datetime.combine(wdate, datetime.min.time()).replace(
                hour=9 + (day_offset % 5), minute=15
            )
            ended = started + timedelta(seconds=duration)

            w = Workout(
                user_id=demo.id,
                title=title,
                workout_date=wdate,
                started_at=started,
                ended_at=ended,
                total_duration_seconds=duration,
                total_points_earned=pts,
                calories_estimate=max(50, duration // 3),
                exercise_id=ex_id,
                difficulty=diff,
                preset_id=f"{ex_id}-demo-1",
                target_sets=3,
                target_reps=max(reps, 10) if reps else None,
                total_reps=reps,
            )
            db.session.add(w)

            total_points += pts
            total_reps += reps
            bucket = daily.setdefault(
                wdate,
                {"points": 0, "workouts": 0, "reps": 0, "duration": 0},
            )
            bucket["points"] += pts
            bucket["workouts"] += 1
            bucket["reps"] += reps
            bucket["duration"] += duration

        for stat_date, agg in daily.items():
            db.session.add(
                UserDailyStats(
                    user_id=demo.id,
                    stat_date=stat_date,
                    total_points=agg["points"],
                    total_workouts=agg["workouts"],
                    total_reps=agg["reps"],
                    total_duration_seconds=agg["duration"],
                )
            )

        demo.total_points = total_points + 175
        demo.level = max(1, (demo.total_points // 1000) + 1)

        unlock_codes = ["first_workout", "workouts_5", "reps_100", "streak_3", "points_500"]
        for code in unlock_codes:
            ach = Achievement.query.filter_by(code=code).first()
            if ach:
                db.session.add(
                    UserAchievement(
                        user_id=demo.id,
                        achievement_id=ach.id,
                        unlocked_at=datetime.utcnow() - timedelta(days=2),
                    )
                )

        shake = RewardItem.query.filter_by(code="protein_shake").first()
        if shake and demo.total_points >= shake.points_cost:
            db.session.add(
                RewardRedemption(
                    user_id=demo.id,
                    reward_item_id=shake.id,
                    points_spent=shake.points_cost,
                    redeemed_at=datetime.utcnow() - timedelta(days=1),
                )
            )
            demo.total_points -= shake.points_cost

        friend_ids = []
        for spec in FRIEND_USERS:
            fu = User.query.filter_by(username=spec["username"]).first()
            if not fu:
                fu = User(
                    email=spec["email"],
                    username=spec["username"],
                    display_name=spec["display_name"],
                )
                fu.set_password("password")
                fu.has_completed_onboarding = True
                fu.total_points = 1200 + len(friend_ids) * 400
                fu.level = 2
                fu.current_streak_days = 3
                fu.longest_streak_days = 5
                db.session.add(fu)
                db.session.flush()
            friend_ids.append(fu.id)
            _upsert_leaderboard(fu)

            db.session.add(
                Friendship(
                    requester_id=demo.id,
                    addressee_id=fu.id,
                    status="accepted",
                    created_at=datetime.utcnow() - timedelta(days=10),
                )
            )

        challenge = Challenge(
            name="7-Day Push-up Sprint",
            description="Most push-up reps this week wins bragging rights.",
            created_by=demo.id,
            start_date=today - timedelta(days=3),
            end_date=today + timedelta(days=4),
            metric_type="reps",
            exercise_id="pushup",
            difficulty="medium",
            target_value=200,
            is_active=True,
        )
        db.session.add(challenge)
        db.session.flush()

        db.session.add(
            ChallengeParticipant(
                challenge_id=challenge.id,
                user_id=demo.id,
                progress_value=142,
            )
        )
        if friend_ids:
            db.session.add(
                ChallengeParticipant(
                    challenge_id=challenge.id,
                    user_id=friend_ids[0],
                    progress_value=118,
                )
            )

        _upsert_leaderboard(demo)
        db.session.commit()

        print("")
        print("Demo account ready:")
        print(f"  Username : {DEMO_USERNAME}")
        print(f"  Email    : {DEMO_EMAIL}")
        print(f"  Password : {DEMO_PASSWORD}")
        print(f"  Points   : {demo.total_points}  Level: {demo.level}")
        print(f"  Workouts : {Workout.query.filter_by(user_id=demo.id).count()}")
        print(f"  Friends  : {len(friend_ids)}")
        print("")


if __name__ == "__main__":
    main()
