# backend/app/models/rewards.py
from datetime import datetime

from .. import db


class RewardItem(db.Model):
    """Redeemable reward in the points shop (e.g. gym pass, treadmill time)."""

    __tablename__ = "reward_items"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    points_cost = db.Column(db.Integer, nullable=False)
    redeem_message = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "points_cost": int(self.points_cost or 0),
            "redeem_message": self.redeem_message,
            "is_active": bool(self.is_active),
        }


class RewardShopSettings(db.Model):
    """Singleton-style shop config (default redeem toast, etc.)."""

    __tablename__ = "reward_shop_settings"

    id = db.Column(db.Integer, primary_key=True)
    default_redeem_message = db.Column(
        db.String(255),
        nullable=False,
        default="Go to the counter to redeem the reward",
    )


class RewardRedemption(db.Model):
    """History of a user spending points on a reward item."""

    __tablename__ = "reward_redemptions"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    reward_item_id = db.Column(db.Integer, db.ForeignKey("reward_items.id"), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    redeemed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref="reward_redemptions")
    reward_item = db.relationship("RewardItem", backref="redemptions")

    def to_dict(self):
        item = self.reward_item
        return {
            "id": self.id,
            "reward_item_id": self.reward_item_id,
            "code": item.code if item else None,
            "name": item.name if item else "Reward",
            "points_spent": int(self.points_spent or 0),
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
        }
