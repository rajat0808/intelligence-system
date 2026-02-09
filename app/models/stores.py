from sqlalchemy import Column, Integer, String

from app.database.base import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)


__all__ = ["Store"]
