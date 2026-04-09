from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.invoice_service import InvoiceService
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from typing import List

router = APIRouter(prefix="/invoices", tags=["invoices"])

def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)

@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service)
):
    try:
        return service.create_invoice(invoice)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service)
):
    invoice = service.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice

@router.get("/", response_model=List[InvoiceResponse])
async def get_all_invoices(
    service: InvoiceService = Depends(get_invoice_service)
):
    return service.get_all_invoices()

@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service)
):
    invoice = service.update_invoice(invoice_id, invoice_data)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service)
):
    if not service.delete_invoice(invoice_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return {"message": "Invoice deleted successfully"}
