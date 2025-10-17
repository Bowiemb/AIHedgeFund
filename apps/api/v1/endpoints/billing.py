"""Billing and Stripe webhook endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.auth import get_current_user
from apps.api.core.stripe_client import (
    create_checkout_session,
    create_customer_portal_session,
    verify_webhook_signature,
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
)
from apps.api.v1.schemas import APIResponse
from packages.db.models import User
from packages.db.session import get_session

router = APIRouter()


@router.post("/checkout", response_model=APIResponse)
async def create_checkout(
    plan: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create Stripe checkout session.

    Args:
        plan: Plan name (pro, enterprise)
        current_user: Authenticated user
        session: Database session

    Returns:
        Checkout URL
    """
    try:
        result = await create_checkout_session(current_user, plan, session)
        return APIResponse(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/portal", response_model=APIResponse)
async def customer_portal(
    current_user: User = Depends(get_current_user),
):
    """
    Get Stripe customer portal URL.

    Args:
        current_user: Authenticated user

    Returns:
        Portal URL
    """
    try:
        result = await create_customer_portal_session(current_user)
        return APIResponse(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Handle Stripe webhooks.

    Args:
        request: HTTP request
        session: Database session

    Returns:
        Success response
    """
    # Get payload and signature
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature",
        )

    # Verify signature
    event = verify_webhook_signature(payload, signature)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Handle event
    event_type = event["type"]
    event_data = event["data"]

    if event_type == "customer.subscription.created":
        await handle_subscription_created(event_data, session)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(event_data, session)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(event_data, session)

    return {"status": "success"}
