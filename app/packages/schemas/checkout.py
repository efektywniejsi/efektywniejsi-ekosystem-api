"""
Pydantic schemas for checkout.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.packages.models.order import PaymentProvider
from app.packages.schemas.order import OrderResponse


class CheckoutInitiateRequest(BaseModel):
    """Request to initiate checkout."""

    package_ids: list[str] | None = Field(
        default=None,
        description="List of package UUIDs to purchase",
    )
    implementation_package_ids: list[str] | None = Field(
        default=None,
        description="List of implementation package UUIDs to purchase",
    )
    email: EmailStr = Field(..., description="Customer email")
    name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    payment_provider: PaymentProvider = Field(..., description="Selected payment provider")

    # Optional invoice/billing information (for B2B)
    wants_invoice: bool = Field(default=False, description="Whether customer wants a VAT invoice")
    buyer_tax_no: str | None = Field(
        default=None,
        max_length=20,
        description="Buyer NIP/VAT number (required if wants_invoice=True for companies)",
    )
    buyer_company_name: str | None = Field(
        default=None,
        max_length=200,
        description="Company name for invoice",
    )
    buyer_street: str | None = Field(default=None, max_length=200)
    buyer_post_code: str | None = Field(default=None, max_length=20)
    buyer_city: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def at_least_one_product(self) -> "CheckoutInitiateRequest":
        has_packages = self.package_ids and len(self.package_ids) > 0
        has_impl_packages = (
            self.implementation_package_ids and len(self.implementation_package_ids) > 0
        )
        if not has_packages and not has_impl_packages:
            raise ValueError("Musisz wybrać co najmniej jeden produkt do zakupu")
        return self

    @model_validator(mode="after")
    def validate_invoice_fields(self) -> "CheckoutInitiateRequest":
        if self.wants_invoice:
            if not self.buyer_tax_no or not self.buyer_tax_no.strip():
                raise ValueError("NIP jest wymagany dla faktury VAT")
            if not self.buyer_company_name or not self.buyer_company_name.strip():
                raise ValueError("Nazwa firmy jest wymagana dla faktury VAT")
        return self


class AuthenticatedCheckoutRequest(BaseModel):
    """Request to initiate checkout for authenticated dashboard users."""

    package_ids: list[str] | None = Field(
        default=None,
        description="List of package UUIDs to purchase",
    )
    implementation_package_ids: list[str] | None = Field(
        default=None,
        description="List of implementation package UUIDs to purchase",
    )
    payment_provider: PaymentProvider = Field(..., description="Selected payment provider")

    # Optional invoice/billing information (for B2B)
    wants_invoice: bool = Field(default=False, description="Whether customer wants a VAT invoice")
    buyer_tax_no: str | None = Field(
        default=None,
        max_length=20,
        description="Buyer NIP/VAT number (required if wants_invoice=True for companies)",
    )
    buyer_company_name: str | None = Field(
        default=None,
        max_length=200,
        description="Company name for invoice",
    )
    buyer_street: str | None = Field(default=None, max_length=200)
    buyer_post_code: str | None = Field(default=None, max_length=20)
    buyer_city: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def at_least_one_product(self) -> "AuthenticatedCheckoutRequest":
        has_packages = self.package_ids and len(self.package_ids) > 0
        has_impl_packages = (
            self.implementation_package_ids and len(self.implementation_package_ids) > 0
        )
        if not has_packages and not has_impl_packages:
            raise ValueError("Musisz wybrać co najmniej jeden produkt do zakupu")
        return self

    @model_validator(mode="after")
    def validate_invoice_fields(self) -> "AuthenticatedCheckoutRequest":
        if self.wants_invoice:
            if not self.buyer_tax_no or not self.buyer_tax_no.strip():
                raise ValueError("NIP jest wymagany dla faktury VAT")
            if not self.buyer_company_name or not self.buyer_company_name.strip():
                raise ValueError("Nazwa firmy jest wymagana dla faktury VAT")
        return self


class CheckoutInitiateResponse(BaseModel):
    """Response from checkout initiation."""

    payment_url: str = Field(..., description="URL to redirect user for payment")
    order_id: uuid.UUID = Field(..., description="Created order ID")


class OrderStatusResponse(BaseModel):
    """Response for order status check.

    Contains the full order with items, plus webhook_processed flag for polling.
    Note: Invoice is sent automatically via Fakturownia email,
    not accessible from our platform.
    """

    order: OrderResponse
    webhook_processed: bool
