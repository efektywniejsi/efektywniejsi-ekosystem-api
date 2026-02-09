"""
Tests for FakturowniaService - invoice generation via Fakturownia.pl API.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.packages.models.order import Order, OrderItem, PaymentProvider
from app.packages.services.fakturownia_service import (
    FakturowniaService,
    InvoiceResult,
    get_fakturownia_service,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def create_mock_order(
    email: str = "test@example.com",
    name: str = "Jan Kowalski",
    total: int = 9900,  # 99.00 PLN in grosz
    payment_provider: PaymentProvider = PaymentProvider.STRIPE,
    buyer_tax_no: str | None = None,
    buyer_company_name: str | None = None,
    buyer_street: str | None = None,
    buyer_post_code: str | None = None,
    buyer_city: str | None = None,
) -> Order:
    """Create a mock Order object for testing."""
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-TEST"
    order.email = email
    order.name = name
    order.total = total
    order.currency = "PLN"
    order.payment_provider = payment_provider
    order.buyer_tax_no = buyer_tax_no
    order.buyer_company_name = buyer_company_name
    order.buyer_street = buyer_street
    order.buyer_post_code = buyer_post_code
    order.buyer_city = buyer_city

    # Create mock items
    item1 = MagicMock(spec=OrderItem)
    item1.package_title = "Kurs Produktywności"
    item1.price = 4900  # 49.00 PLN

    item2 = MagicMock(spec=OrderItem)
    item2.package_title = "Pakiet Premium"
    item2.price = 5000  # 50.00 PLN

    order.items = [item1, item2]

    return order


def create_mock_settings(**overrides):
    """Create mock settings for Fakturownia."""
    defaults = {
        "FAKTUROWNIA_API_TOKEN": "test_api_token_12345",
        "FAKTUROWNIA_SUBDOMAIN": "testfirma",
        "FAKTUROWNIA_SELLER_NAME": "Test Firma Sp. z o.o.",
        "FAKTUROWNIA_SELLER_TAX_NO": "1234567890",
        "FAKTUROWNIA_SELLER_STREET": "ul. Testowa 1",
        "FAKTUROWNIA_SELLER_POST_CODE": "00-001",
        "FAKTUROWNIA_SELLER_CITY": "Warszawa",
        "FAKTUROWNIA_SELLER_COUNTRY": "PL",
        "FAKTUROWNIA_SELLER_BANK": "Test Bank",
        "FAKTUROWNIA_SELLER_BANK_ACCOUNT": "12 1234 5678 9012 3456 7890 1234",
    }
    defaults.update(overrides)

    mock_settings = MagicMock()
    for key, value in defaults.items():
        setattr(mock_settings, key, value)

    return mock_settings


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Configuration
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServiceConfiguration:
    """Tests for service configuration and initialization."""

    def test_is_configured_returns_true_when_all_settings_present(self):
        """Service should be configured when API token and subdomain are set."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            assert service.is_configured is True

    def test_is_configured_returns_false_when_token_missing(self):
        """Service should not be configured when API token is missing."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_API_TOKEN=""),
        ):
            service = FakturowniaService()
            assert service.is_configured is False

    def test_is_configured_returns_false_when_subdomain_missing(self):
        """Service should not be configured when subdomain is missing."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_SUBDOMAIN=""),
        ):
            service = FakturowniaService()
            assert service.is_configured is False

    def test_base_url_uses_subdomain(self):
        """Base URL should include the configured subdomain."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_SUBDOMAIN="mojafirma"),
        ):
            service = FakturowniaService()
            assert service.base_url == "https://mojafirma.fakturownia.pl"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: PDF URL Generation
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServicePdfUrl:
    """Tests for invoice PDF URL generation."""

    def test_get_invoice_pdf_url_returns_correct_format(self):
        """PDF URL should use the public token format."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_SUBDOMAIN="mojafirma"),
        ):
            service = FakturowniaService()
            url = service.get_invoice_pdf_url("ABC123XYZ")

            assert url == "https://mojafirma.fakturownia.pl/invoice/ABC123XYZ.pdf"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Invoice Data Building
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServiceBuildInvoiceData:
    """Tests for _build_invoice_data method."""

    def test_builds_correct_invoice_structure(self):
        """Invoice data should have correct structure and required fields."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            data = service._build_invoice_data(order)

            assert "api_token" in data
            assert "invoice" in data
            assert data["api_token"] == "test_api_token_12345"

            invoice = data["invoice"]
            assert invoice["kind"] == "vat"
            assert invoice["currency"] == "PLN"
            assert invoice["lang"] == "pl"
            assert invoice["status"] == "paid"

    def test_converts_grosz_to_pln_for_prices(self):
        """Prices should be converted from grosz to PLN (divided by 100)."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(total=9900)  # 99.00 PLN

            data = service._build_invoice_data(order)

            assert data["invoice"]["paid"] == "99.0"

            # Check positions
            positions = data["invoice"]["positions"]
            assert len(positions) == 2
            assert positions[0]["total_price_gross"] == 49.0  # 4900 grosz
            assert positions[1]["total_price_gross"] == 50.0  # 5000 grosz

    def test_uses_company_name_when_provided(self):
        """Buyer name should use company name if provided."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(
                name="Jan Kowalski",
                buyer_company_name="Kowalski Tech Sp. z o.o.",
            )

            data = service._build_invoice_data(order)

            assert data["invoice"]["buyer_name"] == "Kowalski Tech Sp. z o.o."

    def test_uses_personal_name_when_no_company(self):
        """Buyer name should use personal name when no company provided."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(
                name="Jan Kowalski",
                buyer_company_name=None,
            )

            data = service._build_invoice_data(order)

            assert data["invoice"]["buyer_name"] == "Jan Kowalski"

    def test_includes_buyer_tax_no_when_provided(self):
        """Buyer NIP should be included when provided."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(buyer_tax_no="9876543210")

            data = service._build_invoice_data(order)

            assert data["invoice"]["buyer_tax_no"] == "9876543210"

    def test_payment_type_card_for_stripe(self):
        """Payment type should be 'card' for Stripe orders."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(payment_provider=PaymentProvider.STRIPE)

            data = service._build_invoice_data(order)

            assert data["invoice"]["payment_type"] == "card"

    def test_payment_type_transfer_for_payu(self):
        """Payment type should be 'transfer' for PayU orders."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(payment_provider=PaymentProvider.PAYU)

            data = service._build_invoice_data(order)

            assert data["invoice"]["payment_type"] == "transfer"

    def test_includes_seller_info_from_settings(self):
        """Seller information should come from settings."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(
                FAKTUROWNIA_SELLER_NAME="Moja Super Firma",
                FAKTUROWNIA_SELLER_TAX_NO="1112223344",
            ),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            data = service._build_invoice_data(order)

            assert data["invoice"]["seller_name"] == "Moja Super Firma"
            assert data["invoice"]["seller_tax_no"] == "1112223344"

    def test_includes_order_reference(self):
        """Invoice should include order reference in description and oid."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            data = service._build_invoice_data(order)

            assert order.order_number in data["invoice"]["description"]
            assert data["invoice"]["oid"] == str(order.id)

    def test_always_sends_email(self):
        """send_email should always be True - invoice is sent via Fakturownia email."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            data = service._build_invoice_data(order)

            assert data["invoice"]["send_email"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Invoice Creation (API calls)
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServiceCreateInvoice:
    """Tests for create_invoice method with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_returns_failure_when_not_configured(self):
        """Should return failure result when service is not configured."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_API_TOKEN=""),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            result = await service.create_invoice(order)

            assert result.success is False
            assert result.error == "Fakturownia not configured"
            assert result.invoice_id is None

    @pytest.mark.asyncio
    async def test_successful_invoice_creation(self):
        """Should return success with invoice data when API call succeeds."""
        mock_response = {
            "id": 12345,
            "number": "FV/2026/02/001",
            "token": "ABC123XYZ",
        }

        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance

                mock_http_response = MagicMock()
                mock_http_response.json.return_value = mock_response
                mock_http_response.raise_for_status = MagicMock()
                mock_instance.post.return_value = mock_http_response

                result = await service.create_invoice(order)

                assert result.success is True
                assert result.invoice_id == 12345
                assert result.invoice_number == "FV/2026/02/001"
                assert result.invoice_token == "ABC123XYZ"
                assert result.error is None

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        """Should return failure when API returns HTTP error."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance

                # Simulate HTTP 401 error
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=mock_response,
                )
                mock_instance.post.return_value = mock_response

                result = await service.create_invoice(order)

                assert result.success is False
                assert "API error: 401" in result.error

    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        """Should return failure when connection to API fails."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_instance.post.side_effect = httpx.RequestError(
                    "Connection refused",
                    request=MagicMock(),
                )

                result = await service.create_invoice(order)

                assert result.success is False
                assert "Connection error" in result.error

    @pytest.mark.asyncio
    async def test_handles_unexpected_error(self):
        """Should return failure for unexpected errors without crashing."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_instance.post.side_effect = RuntimeError("Unexpected error")

                result = await service.create_invoice(order)

                assert result.success is False
                assert "Unexpected error" in result.error

    @pytest.mark.asyncio
    async def test_sends_correct_request_to_api(self):
        """Should send properly formatted request to Fakturownia API."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(FAKTUROWNIA_SUBDOMAIN="testfirma"),
        ):
            service = FakturowniaService()
            order = create_mock_order()

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance

                mock_response = MagicMock()
                mock_response.json.return_value = {"id": 1, "number": "FV/1", "token": "x"}
                mock_response.raise_for_status = MagicMock()
                mock_instance.post.return_value = mock_response

                await service.create_invoice(order)

                # Verify API call
                mock_instance.post.assert_called_once()
                call_args = mock_instance.post.call_args

                assert call_args[0][0] == "https://testfirma.fakturownia.pl/invoices.json"
                assert call_args[1]["headers"]["Content-Type"] == "application/json"
                assert call_args[1]["headers"]["Accept"] == "application/json"

                # Verify request body structure
                json_data = call_args[1]["json"]
                assert "api_token" in json_data
                assert "invoice" in json_data
                assert json_data["invoice"]["kind"] == "vat"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Singleton Pattern
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServiceSingleton:
    """Tests for get_fakturownia_service factory function."""

    def test_returns_same_instance(self):
        """Should return the same service instance on multiple calls."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            # Reset singleton
            import app.packages.services.fakturownia_service as module

            module._fakturownia_service = None

            service1 = get_fakturownia_service()
            service2 = get_fakturownia_service()

            assert service1 is service2


# ─────────────────────────────────────────────────────────────────────────────
# Tests: InvoiceResult Dataclass
# ─────────────────────────────────────────────────────────────────────────────


class TestInvoiceResult:
    """Tests for InvoiceResult dataclass."""

    def test_success_result(self):
        """Success result should have all invoice fields."""
        result = InvoiceResult(
            success=True,
            invoice_id=12345,
            invoice_number="FV/2026/02/001",
            invoice_token="ABC123",
        )

        assert result.success is True
        assert result.invoice_id == 12345
        assert result.invoice_number == "FV/2026/02/001"
        assert result.invoice_token == "ABC123"
        assert result.error is None

    def test_failure_result(self):
        """Failure result should have error message and no invoice fields."""
        result = InvoiceResult(
            success=False,
            error="API connection failed",
        )

        assert result.success is False
        assert result.error == "API connection failed"
        assert result.invoice_id is None
        assert result.invoice_number is None
        assert result.invoice_token is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: B2B Invoice with Full Billing Details
# ─────────────────────────────────────────────────────────────────────────────


class TestFakturowniaServiceB2BInvoice:
    """Tests for B2B invoices with full company details."""

    def test_includes_full_buyer_address(self):
        """B2B invoice should include full buyer address."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(
                buyer_company_name="Acme Corp Sp. z o.o.",
                buyer_tax_no="1234567890",
                buyer_street="ul. Biznesowa 10",
                buyer_post_code="00-123",
                buyer_city="Kraków",
            )

            data = service._build_invoice_data(order)

            assert data["invoice"]["buyer_name"] == "Acme Corp Sp. z o.o."
            assert data["invoice"]["buyer_tax_no"] == "1234567890"
            assert data["invoice"]["buyer_street"] == "ul. Biznesowa 10"
            assert data["invoice"]["buyer_post_code"] == "00-123"
            assert data["invoice"]["buyer_city"] == "Kraków"
            assert data["invoice"]["buyer_country"] == "PL"

    def test_handles_missing_address_fields_gracefully(self):
        """Should use empty strings for missing optional address fields."""
        with patch(
            "app.packages.services.fakturownia_service.settings",
            create_mock_settings(),
        ):
            service = FakturowniaService()
            order = create_mock_order(
                buyer_tax_no=None,
                buyer_street=None,
                buyer_post_code=None,
                buyer_city=None,
            )

            data = service._build_invoice_data(order)

            assert data["invoice"]["buyer_tax_no"] == ""
            assert data["invoice"]["buyer_street"] == ""
            assert data["invoice"]["buyer_post_code"] == ""
            assert data["invoice"]["buyer_city"] == ""
