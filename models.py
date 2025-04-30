from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Provider(Base):
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    tax_code = Column(String(50), unique=True)
    name = Column(String(255))
    invoices = relationship("Invoice", back_populates="provider")

class TaxProvider(Base):
    __tablename__ = 'tax_providers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    search_url = Column(String(255))
    invoices = relationship("Invoice", back_populates="tax_provider")

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_form = Column(String(50))  # khmshdon
    invoice_series = Column(String(50))  # khhdon
    invoice_number = Column(Integer)  # shdon 
    invoice_timestamp = Column(DateTime(timezone=True))  # Store ISO timestamp with timezone
    tracking_code = Column(String(255))  # Add tracking_code column
    provider_id = Column(Integer, ForeignKey('providers.id'))
    provider = relationship("Provider", back_populates="invoices")
    tax_provider_id = Column(Integer, ForeignKey('tax_providers.id'))
    tax_provider = relationship("TaxProvider", back_populates="invoices")

def init_db():
    engine = create_engine('sqlite:///vantoi.db')
    Base.metadata.create_all(engine)
