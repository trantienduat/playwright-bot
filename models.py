from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Seller(Base):  # Renamed from Provider
    __tablename__ = 'sellers'
    
    id = Column(Integer, primary_key=True)
    tax_code = Column(String(50), unique=True)  # Moved from Invoice
    name = Column(String(255))
    invoices = relationship("Invoice", back_populates="seller")  # Add relationship to Invoice

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
    invoice_number = Column(String(50))
    invoice_timestamp = Column(DateTime(timezone=True))
    tracking_code = Column(String(255))
    seller_id = Column(Integer, ForeignKey('sellers.id'))  # Renamed from provider_id
    tax_provider_id = Column(Integer, ForeignKey('tax_providers.id'))
    is_downloaded = Column(Integer, default=0)  # 0 = not downloaded, 1 = downloaded
    seller = relationship("Seller", back_populates="invoices")  # Add relationship to Seller

    # Add unique constraint
    __table_args__ = (
        UniqueConstraint('invoice_form', 'invoice_series', 'invoice_number', name='uix_invoice'),
    )

def init_db():
    engine = create_engine('sqlite:///vantoi.db')
    Base.metadata.create_all(engine)
