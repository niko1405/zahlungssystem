from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate
from typing import List, Optional

class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create_invoice(self, invoice: InvoiceCreate) -> Invoice:
        db_invoice = Invoice(
            id=invoice.id,
            supplier=invoice.supplier,
            amount=invoice.amount
        )
        self.db.add(db_invoice)
        self.db.commit()
        self.db.refresh(db_invoice)
        return db_invoice
    
    def get_invoice_by_id(self, invoice_id: str) -> Optional[Invoice]:
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    def get_all_invoices(self) -> List[Invoice]:
        return self.db.query(Invoice).all()
    
    def update_invoice(self, invoice_id: str, invoice_data: InvoiceCreate) -> Optional[Invoice]:
        db_invoice = self.get_invoice_by_id(invoice_id)
        if db_invoice:
            db_invoice.supplier = invoice_data.supplier
            db_invoice.amount = invoice_data.amount
            self.db.commit()
            self.db.refresh(db_invoice)
        return db_invoice
    
    def delete_invoice(self, invoice_id: str) -> bool:
        db_invoice = self.get_invoice_by_id(invoice_id)
        if db_invoice:
            self.db.delete(db_invoice)
            self.db.commit()
            return True
        return False
