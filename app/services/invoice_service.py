from sqlalchemy.orm import Session
from app.repository.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from typing import List, Optional

class InvoiceService:
    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)
    
    def create_invoice(self, invoice: InvoiceCreate) -> InvoiceResponse:
        existing_invoice = self.repository.get_invoice_by_id(invoice.id)
        if existing_invoice:
            raise ValueError(f"Invoice with ID {invoice.id} already exists")
        
        db_invoice = self.repository.create_invoice(invoice)
        return InvoiceResponse.from_orm(db_invoice)
    
    def get_invoice_by_id(self, invoice_id: str) -> Optional[InvoiceResponse]:
        db_invoice = self.repository.get_invoice_by_id(invoice_id)
        if db_invoice:
            return InvoiceResponse.from_orm(db_invoice)
        return None
    
    def get_all_invoices(self) -> List[InvoiceResponse]:
        db_invoices = self.repository.get_all_invoices()
        return [InvoiceResponse.from_orm(invoice) for invoice in db_invoices]
    
    def update_invoice(self, invoice_id: str, invoice_data: InvoiceCreate) -> Optional[InvoiceResponse]:
        db_invoice = self.repository.update_invoice(invoice_id, invoice_data)
        if db_invoice:
            return InvoiceResponse.from_orm(db_invoice)
        return None
    
    def delete_invoice(self, invoice_id: str) -> bool:
        return self.repository.delete_invoice(invoice_id)
