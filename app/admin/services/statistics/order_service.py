"""Order statistics service."""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    OrderDetailItem,
    OrderDetailResponse,
    OrderDetailsListResponse,
    OrderProviderCount,
    OrdersKPI,
    OrderStatisticsResponse,
    OrderStatusCount,
)
from app.admin.services.statistics.base import get_period_boundaries
from app.packages.models.order import Order, OrderItem, OrderStatus


class OrderStatisticsService:
    """Service for order-related statistics."""

    @staticmethod
    def get_kpis(db: Session, today_start: datetime, month_start: datetime) -> OrdersKPI:
        """Get order KPIs for dashboard.

        Args:
            db: Database session.
            today_start: Start of today.
            month_start: Start of current month.

        Returns:
            OrdersKPI with today's orders, pending, completed, and failed counts.
        """
        today_orders = db.query(Order).filter(Order.created_at >= today_start).count()
        pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
        completed_month = (
            db.query(Order)
            .filter(
                Order.status == OrderStatus.COMPLETED,
                Order.payment_completed_at >= month_start,
            )
            .count()
        )
        failed_month = (
            db.query(Order)
            .filter(Order.status == OrderStatus.FAILED, Order.created_at >= month_start)
            .count()
        )

        return OrdersKPI(
            today=today_orders,
            pending=pending_orders,
            completed_this_month=completed_month,
            failed_this_month=failed_month,
        )

    @staticmethod
    def get_statistics(
        db: Session, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> OrderStatisticsResponse:
        """Get order statistics with breakdowns.

        Args:
            db: Database session.
            start_date: Optional period start filter.
            end_date: Optional period end filter.

        Returns:
            OrderStatisticsResponse with status/provider breakdowns and recent orders.
        """
        query = db.query(Order)
        if start_date:
            query = query.filter(Order.created_at >= start_date)
        if end_date:
            query = query.filter(Order.created_at <= end_date)

        total_orders = query.count()

        # By status
        status_counts = (
            query.with_entities(Order.status, func.count(Order.id)).group_by(Order.status).all()
        )
        by_status = [
            OrderStatusCount(
                status=s.value if hasattr(s, "value") else str(s),
                count=c,
                percentage=round((c / total_orders) * 100, 2) if total_orders > 0 else 0,
            )
            for s, c in status_counts
        ]

        # By provider
        provider_stats = (
            query.filter(Order.status == OrderStatus.COMPLETED)
            .with_entities(
                Order.payment_provider,
                func.count(Order.id),
                func.sum(Order.total),
            )
            .group_by(Order.payment_provider)
            .all()
        )
        completed_total = sum(p[1] for p in provider_stats)
        by_provider = [
            OrderProviderCount(
                provider=p.value if hasattr(p, "value") else str(p),
                count=c,
                percentage=round((c / completed_total) * 100, 2) if completed_total > 0 else 0,
                revenue=r or 0,
            )
            for p, c, r in provider_stats
        ]

        # Recent orders
        recent = db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
        recent_orders: list[dict[str, Any]] = [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "email": o.email,
                "status": o.status.value,
                "total": o.total,
                "created_at": o.created_at.isoformat(),
            }
            for o in recent
        ]

        return OrderStatisticsResponse(
            total_orders=total_orders,
            by_status=by_status,
            by_provider=by_provider,
            recent_orders=recent_orders,
        )

    @staticmethod
    def get_order_details(
        db: Session,
        period: str | None = "this_month",
        status: str | None = None,
        limit: int = 50,
    ) -> OrderDetailsListResponse:
        """Get detailed order list with items for the modal view.

        Args:
            db: Database session.
            period: Time period filter.
            status: Optional status filter.
            limit: Maximum number of orders to return.

        Returns:
            OrderDetailsListResponse with orders, total count, and revenue.
        """
        query = db.query(Order)
        start: datetime | None = None
        end: datetime | None = None

        if period:
            start, end = get_period_boundaries(period)
            query = query.filter(
                Order.created_at >= start,
                Order.created_at <= end,
            )

        if status:
            query = query.filter(Order.status == status)

        total_count = query.count()

        # Total revenue (completed only within the same filters)
        revenue_query = db.query(func.sum(Order.total)).filter(
            Order.status == OrderStatus.COMPLETED,
        )
        if period and start and end:
            revenue_query = revenue_query.filter(
                Order.created_at >= start,
                Order.created_at <= end,
            )
        total_revenue = revenue_query.scalar() or 0

        orders = query.order_by(Order.created_at.desc()).limit(limit).all()

        order_responses = []
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            order_responses.append(
                OrderDetailResponse(
                    id=str(order.id),
                    order_number=order.order_number,
                    email=order.email,
                    name=order.name,
                    status=order.status.value
                    if hasattr(order.status, "value")
                    else str(order.status),
                    total=order.total,
                    created_at=order.created_at,
                    items=[
                        OrderDetailItem(package_title=item.package_title, price=item.price)
                        for item in items
                    ],
                )
            )

        return OrderDetailsListResponse(
            orders=order_responses,
            total_count=total_count,
            total_revenue=total_revenue,
        )
