from app.database import Base
from sqlalchemy import  Column,Integer,String,Float,ForeignKey,Boolean
from sqlalchemy.orm import relationship

class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String,nullable=False)
    slug = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)

