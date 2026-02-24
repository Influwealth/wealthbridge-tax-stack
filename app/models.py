from sqlalchemy import Column, Integer, Float, String
from app.database import Base

class TaxRecord(Base):
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String, index=True)
    tax_year = Column(Integer, index=True)
    income = Column(Float)
    expenses = Column(Float)
    tax_due = Column(Float)
