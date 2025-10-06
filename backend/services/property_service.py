"""
Property CRUD Service
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from models.property import Property, PropertyFinancials, RentRoll
from schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyFinancialsCreate,
    RentRollCreate
)


class PropertyService:
    """Service for property operations"""
    
    @staticmethod
    def create(db: Session, property_data: PropertyCreate) -> Property:
        """Create new property"""
        property_obj = Property(**property_data.model_dump())
        db.add(property_obj)
        db.commit()
        db.refresh(property_obj)
        return property_obj
    
    @staticmethod
    def get_by_id(db: Session, property_id: UUID) -> Optional[Property]:
        """Get property by ID"""
        return db.query(Property).filter(Property.id == property_id).first()
    
    @staticmethod
    def get_by_loan(db: Session, loan_id: UUID) -> Optional[Property]:
        """Get property by loan application ID"""
        return db.query(Property).filter(
            Property.loan_application_id == loan_id
        ).first()
    
    @staticmethod
    def update(
        db: Session,
        property_id: UUID,
        property_data: PropertyUpdate
    ) -> Optional[Property]:
        """Update property"""
        property_obj = PropertyService.get_by_id(db, property_id)
        if not property_obj:
            return None
        
        update_data = property_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(property_obj, field, value)
        
        db.commit()
        db.refresh(property_obj)
        return property_obj
    
    @staticmethod
    def delete(db: Session, property_id: UUID) -> bool:
        """Delete property"""
        property_obj = PropertyService.get_by_id(db, property_id)
        if not property_obj:
            return False
        
        db.delete(property_obj)
        db.commit()
        return True
    
    @staticmethod
    def calculate_ltv(property_obj: Property, loan_amount: Decimal) -> Optional[Decimal]:
        """Calculate LTV for a property"""
        property_value = property_obj.appraised_value or property_obj.purchase_price
        if not property_value or property_value <= 0:
            return None
        
        ltv = (loan_amount / property_value) * 100
        return ltv.quantize(Decimal('0.01'))


class PropertyFinancialsService:
    """Service for property financials operations"""
    
    @staticmethod
    def create(
        db: Session,
        financials_data: PropertyFinancialsCreate
    ) -> PropertyFinancials:
        """Create new property financials"""
        financials = PropertyFinancials(**financials_data.model_dump())
        
        # Auto-calculate NOI if not provided
        if not financials.net_operating_income:
            egi = financials.effective_gross_income or Decimal('0')
            opex = financials.total_operating_expenses or Decimal('0')
            financials.net_operating_income = egi - opex
        
        db.add(financials)
        db.commit()
        db.refresh(financials)
        return financials
    
    @staticmethod
    def get_by_property(db: Session, property_id: UUID) -> List[PropertyFinancials]:
        """Get all financials for a property"""
        return db.query(PropertyFinancials).filter(
            PropertyFinancials.property_id == property_id
        ).order_by(PropertyFinancials.year.desc()).all()
    
    @staticmethod
    def get_latest(db: Session, property_id: UUID) -> Optional[PropertyFinancials]:
        """Get most recent financials for a property"""
        return db.query(PropertyFinancials).filter(
            PropertyFinancials.property_id == property_id
        ).order_by(PropertyFinancials.year.desc()).first()


class RentRollService:
    """Service for rent roll operations"""
    
    @staticmethod
    def create(db: Session, rent_roll_data: RentRollCreate) -> RentRoll:
        """Create new rent roll entry"""
        rent_roll = RentRoll(**rent_roll_data.model_dump())
        db.add(rent_roll)
        db.commit()
        db.refresh(rent_roll)
        return rent_roll
    
    @staticmethod
    def get_by_property(db: Session, property_id: UUID) -> List[RentRoll]:
        """Get all rent roll entries for a property"""
        return db.query(RentRoll).filter(
            RentRoll.property_id == property_id
        ).all()
    
    @staticmethod
    def get_occupied_units(db: Session, property_id: UUID) -> List[RentRoll]:
        """Get occupied units for a property"""
        return db.query(RentRoll).filter(
            RentRoll.property_id == property_id,
            RentRoll.occupancy_status == 'occupied'
        ).all()
    
    @staticmethod
    def calculate_occupancy_rate(db: Session, property_id: UUID) -> Optional[Decimal]:
        """Calculate occupancy rate for a property"""
        all_units = RentRollService.get_by_property(db, property_id)
        if not all_units:
            return None
        
        occupied_units = len([u for u in all_units if u.occupancy_status == 'occupied'])
        total_units = len(all_units)
        
        if total_units == 0:
            return None
        
        occupancy_rate = (Decimal(occupied_units) / Decimal(total_units)) * 100
        return occupancy_rate.quantize(Decimal('0.01'))
