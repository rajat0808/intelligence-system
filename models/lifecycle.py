from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from app.database import Base


class LifecycleHistory(Base):
    __tablename__ = "lifecycle_history"

    id = Column(Integer, primary_key=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"))

    old_price = Column(Float)
    new_price = Column(Float)

    rr_applied_on = Column(Date)
    closed_on = Column(Date)
