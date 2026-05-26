# backend/app/routes/rewards_routes.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from .. import db
from ..models.user import User
from ..models.social import Achievement, UserAchievement
from ..models.rewards import RewardItem, RewardRedemption, RewardShopSettings

rewards_bp = Blueprint("rewards", __name__)

DEFAULT_REDEEM_MESSAGE = "Go to the counter to redeem the reward"

DEFAULT_ACHIEVEMENTS = [
    {
        "code": "first_workout",
        "name": "First Quest",
        "description": "Complete your first workout session.",
        "points_reward": 50,
        "condition_type": "first_workout",
        "condition_value": 1,
    },
    {
        "code": "workouts_5",
        "name": "Regular Athlete",
        "description": "Complete 5 workout sessions.",
        "points_reward": 100,
        "condition_type": "total_workouts",
        "condition_value": 5,
    },
    {
        "code": "workouts_25",
        "name": "Quest Grinder",
        "description": "Complete 25 workout sessions.",
        "points_reward": 200,
        "condition_type": "total_workouts",
        "condition_value": 25,
    },
    {
        "code": "reps_100",
        "name": "Rep Machine",
        "description": "Log 100 total reps across all workouts.",
        "points_reward": 75,
        "condition_type": "total_reps",
        "condition_value": 100,
    },
    {
        "code": "reps_500",
        "name": "Rep Legend",
        "description": "Log 500 total reps across all workouts.",
        "points_reward": 150,
        "condition_type": "total_reps",
        "condition_value": 500,
    },
    {
        "code": "points_500",
        "name": "Point Collector",
        "description": "Earn 500 total points.",
        "points_reward": 50,
        "condition_type": "total_points",
        "condition_value": 500,
    },
    {
        "code": "points_1000",
        "name": "Point Hunter",
        "description": "Earn 1,000 total points.",
        "points_reward": 100,
        "condition_type": "total_points",
        "condition_value": 1000,
    },
    {
        "code": "streak_3",
        "name": "On a Roll",
        "description": "Train 3 days in a row.",
        "points_reward": 75,
        "condition_type": "streak_days",
        "condition_value": 3,
    },
    {
        "code": "streak_7",
        "name": "Week Warrior",
        "description": "Train 7 days in a row.",
        "points_reward": 200,
        "condition_type": "streak_days",
        "condition_value": 7,
    },
]


DEFAULT_REWARD_ITEMS = [
    {
        "code": "gym_day_pass",
        "name": "Gym Day Pass",
        "description": "One full day access to partner gym facilities.",
        "points_cost": 1000,
        "redeem_message": "Go to the counter to redeem the reward",
        "sort_order": 1,
    },
    {
        "code": "treadmill_1hr",
        "name": "1 hr Treadmill",
        "description": "One hour on the treadmill at a partner gym.",
        "points_cost": 500,
        "redeem_message": "Go to the counter to redeem the reward",
        "sort_order": 2,
    },
    {
        "code": "protein_shake",
        "name": "Protein Shake",
        "description": "Redeem a post-workout protein shake.",
        "points_cost": 250,
        "redeem_message": "Go to the counter to redeem the reward",
        "sort_order": 3,
    },
]


def ensure_reward_schema():
    """Add new reward columns/tables on existing PostgreSQL DBs (safe to re-run)."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(db.engine)
        if "reward_items" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("reward_items")}
            if "redeem_message" not in cols:
                db.session.execute(
                    text(
                        "ALTER TABLE reward_items "
                        "ADD COLUMN redeem_message VARCHAR(255)"
                    )
                )
                db.session.commit()
    except Exception:
        db.session.rollback()


def get_default_redeem_message() -> str:
    row = RewardShopSettings.query.get(1)
    if row and row.default_redeem_message:
        return row.default_redeem_message.strip()
    return DEFAULT_REDEEM_MESSAGE


def resolve_redeem_message(item: RewardItem) -> str:
    custom = (item.redeem_message or "").strip()
    if custom:
        return custom
    return get_default_redeem_message()


def seed_reward_shop_settings():
    row = RewardShopSettings.query.get(1)
    if not row:
        db.session.add(
            RewardShopSettings(
                id=1,
                default_redeem_message=DEFAULT_REDEEM_MESSAGE,
            )
        )
        db.session.commit()


def seed_achievements():
    """Insert default achievement definitions if missing (by code)."""
    changed = False
    for row in DEFAULT_ACHIEVEMENTS:
        if Achievement.query.filter_by(code=row["code"]).first():
            continue
        db.session.add(Achievement(**row))
        changed = True
    if changed:
        db.session.commit()


def seed_reward_catalog():
    """Ensure default shop items exist and sync redeem messages from seed data."""
    ensure_reward_schema()
    seed_reward_shop_settings()

    changed = False
    for row in DEFAULT_REWARD_ITEMS:
        existing = RewardItem.query.filter_by(code=row["code"]).first()
        if existing:
            if not existing.redeem_message and row.get("redeem_message"):
                existing.redeem_message = row["redeem_message"]
                changed = True
            continue
        db.session.add(RewardItem(**row))
        changed = True

    if changed:
        db.session.commit()


def _item_to_catalog_dict(item: RewardItem) -> dict:
    data = item.to_dict()
    data["redeem_message"] = resolve_redeem_message(item)
    return data


def _sync_user_level(user: User) -> None:
    """Keep user.level in sync with total_points (1000 pts per level)."""
    pts = int(user.total_points or 0)
    user.level = max(1, (pts // 1000) + 1)


def _compute_next_level_points(level: int) -> int:
    """
    Simple level progression:
      - Level 1 -> 1000 pts
      - Level 2 -> 2000 pts total
      - Level 3 -> 3000 pts total
    You can swap this for something steeper later if you like.
    """
    if level < 1:
        level = 1
    return level * 1000


@rewards_bp.route("/overview", methods=["GET"])
@jwt_required()
def rewards_overview():
    """
    Returns:
    {
      "user": { ... user.to_dict() ... },
      "summary": {
        "total_points": 1200,
        "level": 5,
        "unlocked_achievements_count": 3,
        "total_achievements_count": 10,
        "next_level_points": 6000
      },
      "unlocked": [
        {
          "id": 1,
          "code": "first_workout",
          "name": "First Quest",
          "description": "...",
          "points_reward": 50,
          "unlocked_at": "2025-11-21T10:05:00"
        },
        ...
      ],
      "locked": [
        {
          "id": 3,
          "code": "workouts_25",
          "name": "Quest Grinder",
          "description": "...",
          "points_reward": 200
        },
        ...
      ]
    }
    """
    seed_achievements()

    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "user not found"}), 404

    _sync_user_level(user)
    db.session.commit()

    total_points = user.total_points or 0
    level = user.level or 1
    next_level_points = _compute_next_level_points(level)

    # ------------------------------
    # 1) Unlocked achievements
    # ------------------------------
    ua_rows = (
        db.session.query(UserAchievement, Achievement)
        .join(Achievement, UserAchievement.achievement_id == Achievement.id)
        .filter(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.unlocked_at.desc())
        .all()
    )

    unlocked = []
    unlocked_achievement_ids = []

    for ua, ach in ua_rows:
        unlocked_achievement_ids.append(ach.id)
        unlocked.append(
            {
                "id": ach.id,
                "code": ach.code,
                "name": ach.name,
                "description": ach.description,
                "points_reward": ach.points_reward,
                "unlocked_at": ua.unlocked_at.isoformat()
                if ua.unlocked_at
                else None,
            }
        )

    unlocked_count = len(unlocked)

    # ------------------------------
    # 2) Locked achievements
    # ------------------------------
    active_ach_q = Achievement.query.filter(Achievement.is_active.is_(True))
    total_achievements_count = active_ach_q.count()

    if unlocked_achievement_ids:
        locked_q = active_ach_q.filter(
            ~Achievement.id.in_(unlocked_achievement_ids)
        )
    else:
        locked_q = active_ach_q

    locked_rows = locked_q.order_by(Achievement.id.asc()).all()

    locked = []
    for ach in locked_rows:
        locked.append(
            {
                "id": ach.id,
                "code": ach.code,
                "name": ach.name,
                "description": ach.description,
                "points_reward": ach.points_reward,
            }
        )

    # ------------------------------
    # 3) Summary block
    # ------------------------------
    summary = {
        "total_points": int(total_points),
        "level": int(level),
        "unlocked_achievements_count": int(unlocked_count),
        "total_achievements_count": int(total_achievements_count),
        "next_level_points": int(next_level_points),
    }

    return (
        jsonify(
            {
                "user": user.to_dict(),
                "summary": summary,
                "unlocked": unlocked,
                "locked": locked,
            }
        ),
        200,
    )


@rewards_bp.route("/catalog", methods=["GET"])
@jwt_required()
def rewards_catalog():
    seed_reward_catalog()
    items = (
        RewardItem.query.filter(RewardItem.is_active.is_(True))
        .order_by(RewardItem.sort_order.asc(), RewardItem.id.asc())
        .all()
    )
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    default_message = get_default_redeem_message()
    return jsonify(
        {
            "items": [_item_to_catalog_dict(i) for i in items],
            "total_points": int(user.total_points or 0) if user else 0,
            "default_redeem_message": default_message,
        }
    ), 200


@rewards_bp.route("/redemptions", methods=["GET"])
@jwt_required()
def rewards_redemptions():
    user_id = int(get_jwt_identity())
    rows = (
        RewardRedemption.query.filter_by(user_id=user_id)
        .order_by(RewardRedemption.redeemed_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"redemptions": [r.to_dict() for r in rows]}), 200


@rewards_bp.route("/redeem", methods=["POST"])
@jwt_required()
def rewards_redeem():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "user not found"}), 404

    data = request.get_json(silent=True) or {}
    item_id = data.get("reward_item_id")
    if not item_id:
        return jsonify({"message": "reward_item_id is required"}), 400

    item = RewardItem.query.filter_by(id=int(item_id), is_active=True).first()
    if not item:
        return jsonify({"message": "reward not found"}), 404

    cost = int(item.points_cost or 0)
    balance = int(user.total_points or 0)
    if balance < cost:
        return (
            jsonify(
                {
                    "message": "Not enough points",
                    "total_points": balance,
                    "points_cost": cost,
                }
            ),
            400,
        )

    user.total_points = balance - cost
    _sync_user_level(user)
    toast_message = resolve_redeem_message(item)
    redemption = RewardRedemption(
        user_id=user.id,
        reward_item_id=item.id,
        points_spent=cost,
    )
    db.session.add(redemption)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Reward redeemed",
                "toast_message": toast_message,
                "redemption": redemption.to_dict(),
                "total_points": int(user.total_points or 0),
                "level": int(user.level or 1),
            }
        ),
        201,
    )
