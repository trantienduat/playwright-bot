from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Provider(Base):
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    tax_code = Column(String(50), unique=True)
    name = Column(String(255))

class TaxProvider(Base):
    __tablename__ = 'tax_providers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    search_url = Column(String(255))
    status = Column(String(50), default='TBD')  # RESOLVED or TBD
    note = Column(String(500), nullable=True)

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_form = Column(String(50))
    invoice_series = Column(String(50))
    invoice_number = Column(Integer)
    invoice_timestamp = Column(DateTime(timezone=True))
    tracking_code = Column(String(255))
    provider_id = Column(Integer, ForeignKey('providers.id'))
    tax_provider_id = Column(Integer, ForeignKey('tax_providers.id'))

def init_db():
    engine = create_engine('sqlite:///vantoi.db')
    Base.metadata.create_all(engine)
