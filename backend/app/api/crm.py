"""
CRM API endpoints for contact management, custom fields, and email integration
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import csv
import io
import logging

from app.db.database import get_db
from app.auth.auth import get_current_user, require_admin_user
from app.models.models import (
    User, Tenant, Contact, ContactInteraction, CustomField, EmailTemplate,
    ContactStatus, ContactInteractionType, CustomFieldType
)
from app.models.stripe_models import StripeCustomer, StripeSubscription
from app.schemas.schemas import (
    ContactCreate, ContactUpdate, ContactResponse,
    ContactInteractionCreate, ContactInteractionUpdate, ContactInteractionResponse,
    CustomFieldCreate, CustomFieldUpdate, CustomFieldResponse,
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    ContactImportRequest, ContactImportResult,
    BulkEmailRequest, BulkEmailResult,
    CRMDashboardResponse, CRMDashboardStats,
    PaginationParams, PaginatedResponse
)
from app.services.email_service import email_service, DEFAULT_TEMPLATES

router = APIRouter(prefix="/crm", tags=["crm"])
logger = logging.getLogger(__name__)

# Helper function to get billing status for contacts
async def get_contact_billing_status(contact: Contact, db: AsyncSession) -> tuple[Optional[str], Optional[str]]:
    """Get billing and subscription status for a contact"""
    if not contact.stripe_customer_id:
        return None, None
    
    try:
        # Get Stripe customer record
        stripe_customer = await db.scalar(
            select(StripeCustomer).where(
                StripeCustomer.stripe_customer_id == contact.stripe_customer_id
            )
        )
        
        if not stripe_customer:
            return None, None
        
        # Get active subscription
        subscription = await db.scalar(
            select(StripeSubscription).where(
                and_(
                    StripeSubscription.customer_id == stripe_customer.id,
                    StripeSubscription.status.in_(['active', 'past_due', 'trialing'])
                )
            ).order_by(desc(StripeSubscription.created_at))
        )
        
        billing_status = "linked" if stripe_customer else None
        subscription_status = subscription.status if subscription else "no_subscription"
        
        return billing_status, subscription_status
        
    except Exception as e:
        logger.error(f"Error getting billing status for contact {contact.id}: {str(e)}")
        return None, None

# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=CRMDashboardResponse)
async def get_crm_dashboard(
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get CRM dashboard with stats and recent data"""
    
    tenant_id = current_user.tenant_id
    
    # Get contact counts by status
    status_query = select(
        Contact.status,
        func.count(Contact.id).label('count')
    ).where(
        Contact.tenant_id == tenant_id
    ).group_by(Contact.status)
    
    status_result = await db.execute(status_query)
    contacts_by_status = {row.status: row.count for row in status_result.all()}
    
    # Get total contacts
    total_contacts = sum(contacts_by_status.values())
    
    # Get recent interactions (last 10)
    recent_interactions_query = select(ContactInteraction).where(
        ContactInteraction.contact_id.in_(
            select(Contact.id).where(Contact.tenant_id == tenant_id)
        )
    ).order_by(desc(ContactInteraction.created_at)).limit(10)
    
    recent_interactions_result = await db.execute(recent_interactions_query)
    recent_interactions = recent_interactions_result.scalars().all()
    
    # Get upcoming tasks (interactions marked as tasks for future dates)
    upcoming_tasks_query = select(ContactInteraction).where(
        and_(
            ContactInteraction.contact_id.in_(
                select(Contact.id).where(Contact.tenant_id == tenant_id)
            ),
            ContactInteraction.interaction_type == ContactInteractionType.TASK.value,
            ContactInteraction.interaction_date > datetime.now(timezone.utc)
        )
    ).order_by(ContactInteraction.interaction_date).limit(10)
    
    upcoming_tasks_result = await db.execute(upcoming_tasks_query)
    upcoming_tasks = upcoming_tasks_result.scalars().all()
    
    # Get contact growth (last 30 days by week)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    growth_query = select(
        func.date_trunc('week', Contact.created_at).label('week'),
        func.count(Contact.id).label('count')
    ).where(
        and_(
            Contact.tenant_id == tenant_id,
            Contact.created_at >= start_date
        )
    ).group_by('week').order_by('week')
    
    growth_result = await db.execute(growth_query)
    contact_growth = {
        str(row.week.date()): row.count for row in growth_result.all()
    }
    
    # Get recent contacts (last 10)
    recent_contacts_query = select(Contact).where(
        Contact.tenant_id == tenant_id
    ).order_by(desc(Contact.created_at)).limit(10)
    
    recent_contacts_result = await db.execute(recent_contacts_query)
    recent_contacts = recent_contacts_result.scalars().all()
    
    # Get custom fields
    custom_fields_query = select(CustomField).where(
        and_(
            CustomField.tenant_id == tenant_id,
            CustomField.is_active == True
        )
    ).order_by(CustomField.display_order)
    
    custom_fields_result = await db.execute(custom_fields_query)
    custom_fields = custom_fields_result.scalars().all()
    
    # Build dashboard stats
    stats = CRMDashboardStats(
        total_contacts=total_contacts,
        contacts_by_status=contacts_by_status,
        recent_interactions=[ContactInteractionResponse.model_validate(interaction) for interaction in recent_interactions],
        upcoming_tasks=[ContactInteractionResponse.model_validate(task) for task in upcoming_tasks],
        contact_growth=contact_growth
    )
    
    return CRMDashboardResponse(
        stats=stats,
        recent_contacts=[ContactResponse.model_validate(contact) for contact in recent_contacts],
        custom_fields=[CustomFieldResponse.model_validate(field) for field in custom_fields]
    )

# ============================================================================
# CONTACTS
# ============================================================================

@router.get("/contacts", response_model=PaginatedResponse)
async def list_contacts(
    current_user: User = Depends(require_admin_user),
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search in business name, contact name, or email"),
    status: Optional[ContactStatus] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List contacts with filtering and search"""
    
    tenant_id = current_user.tenant_id
    
    # Build query
    query = select(Contact).where(Contact.tenant_id == tenant_id)
    conditions = []
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Contact.business_name.ilike(search_term),
                Contact.contact_name.ilike(search_term),
                Contact.contact_email.ilike(search_term)
            )
        )
    
    if status:
        conditions.append(Contact.status == status.value)
    
    if city:
        conditions.append(Contact.city.ilike(f"%{city}%"))
    
    if state:
        conditions.append(Contact.state.ilike(f"%{state}%"))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size).order_by(desc(Contact.created_at))
    
    result = await db.execute(query)
    contacts = result.scalars().all()
    
    # Add interaction counts and billing status
    contact_responses = []
    for contact in contacts:
        interaction_count = await db.scalar(
            select(func.count(ContactInteraction.id)).where(
                ContactInteraction.contact_id == contact.id
            )
        )
        
        last_interaction = await db.scalar(
            select(func.max(ContactInteraction.interaction_date)).where(
                ContactInteraction.contact_id == contact.id
            )
        )
        
        # Get billing status
        billing_status, subscription_status = await get_contact_billing_status(contact, db)
        
        contact_dict = ContactResponse.model_validate(contact).model_dump()
        contact_dict["interaction_count"] = interaction_count or 0
        contact_dict["last_interaction_date"] = last_interaction
        contact_dict["billing_status"] = billing_status
        contact_dict["subscription_status"] = subscription_status
        contact_responses.append(contact_dict)
    
    return PaginatedResponse(
        items=contact_responses,
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=((total or 0) + pagination.page_size - 1) // pagination.page_size
    )

@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get contact details"""
    
    contact = await db.scalar(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Add interaction count, last interaction date, and billing status
    interaction_count = await db.scalar(
        select(func.count(ContactInteraction.id)).where(
            ContactInteraction.contact_id == contact.id
        )
    )
    
    last_interaction = await db.scalar(
        select(func.max(ContactInteraction.interaction_date)).where(
            ContactInteraction.contact_id == contact.id
        )
    )
    
    # Get billing status
    billing_status, subscription_status = await get_contact_billing_status(contact, db)
    
    contact_dict = ContactResponse.model_validate(contact).model_dump()
    contact_dict["interaction_count"] = interaction_count or 0
    contact_dict["last_interaction_date"] = last_interaction
    contact_dict["billing_status"] = billing_status
    contact_dict["subscription_status"] = subscription_status
    
    return ContactResponse(**contact_dict)

@router.post("/contacts", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new contact"""
    
    # Check for duplicate email within tenant
    if contact_data.contact_email:
        existing = await db.scalar(
            select(Contact).where(
                and_(
                    Contact.tenant_id == current_user.tenant_id,
                    Contact.contact_email == contact_data.contact_email
                )
            )
        )
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Contact with email {contact_data.contact_email} already exists"
            )
    
    # Create contact
    contact = Contact(
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        **contact_data.model_dump()
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    logger.info(f"Contact created: {contact.business_name} by user {current_user.email}")
    
    return ContactResponse.model_validate(contact)

@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    contact_data: ContactUpdate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update contact"""
    
    contact = await db.scalar(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Check for duplicate email if email is being updated
    if contact_data.contact_email and contact_data.contact_email != contact.contact_email:
        existing = await db.scalar(
            select(Contact).where(
                and_(
                    Contact.tenant_id == current_user.tenant_id,
                    Contact.contact_email == contact_data.contact_email,
                    Contact.id != contact_id
                )
            )
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Contact with email {contact_data.contact_email} already exists"
            )
    
    # Update fields
    for field, value in contact_data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    
    await db.commit()
    await db.refresh(contact)
    
    return ContactResponse.model_validate(contact)

@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: UUID,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete contact"""
    
    contact = await db.scalar(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    await db.delete(contact)
    await db.commit()
    
    logger.info(f"Contact deleted: {contact.business_name} by user {current_user.email}")
    
    return {"message": "Contact deleted successfully"}

# ============================================================================
# CONTACT INTERACTIONS
# ============================================================================

@router.get("/contacts/{contact_id}/interactions", response_model=List[ContactInteractionResponse])
async def list_contact_interactions(
    contact_id: UUID,
    current_user: User = Depends(require_admin_user),
    interaction_type: Optional[ContactInteractionType] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List interactions for a contact"""
    
    # Verify contact exists and belongs to tenant
    contact = await db.scalar(
        select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Build query
    query = select(ContactInteraction).where(ContactInteraction.contact_id == contact_id)
    
    if interaction_type:
        query = query.where(ContactInteraction.interaction_type == interaction_type.value)
    
    query = query.order_by(desc(ContactInteraction.interaction_date))
    
    result = await db.execute(query)
    interactions = result.scalars().all()
    
    # Add user names
    interaction_responses = []
    for interaction in interactions:
        user = await db.scalar(select(User).where(User.id == interaction.user_id))
        interaction_dict = ContactInteractionResponse.model_validate(interaction).model_dump()
        interaction_dict["user_name"] = f"{user.first_name} {user.last_name}".strip() if user else "Unknown"
        interaction_responses.append(ContactInteractionResponse(**interaction_dict))
    
    return interaction_responses

@router.post("/interactions", response_model=ContactInteractionResponse)
async def create_interaction(
    interaction_data: ContactInteractionCreate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new interaction"""
    
    # Verify contact exists and belongs to tenant
    contact = await db.scalar(
        select(Contact).where(
            and_(
                Contact.id == interaction_data.contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Create interaction
    interaction = ContactInteraction(
        user_id=current_user.id,
        **interaction_data.model_dump()
    )
    
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    
    # Add user name
    interaction_dict = ContactInteractionResponse.model_validate(interaction).model_dump()
    interaction_dict["user_name"] = f"{current_user.first_name} {current_user.last_name}".strip()
    
    return ContactInteractionResponse(**interaction_dict)

# ============================================================================
# CSV IMPORT
# ============================================================================

@router.post("/contacts/import", response_model=ContactImportResult)
async def import_contacts_csv(
    file: UploadFile = File(...),
    field_mapping: str = Query(..., description="JSON string mapping CSV headers to contact fields"),
    update_existing: bool = Query(False, description="Update existing contacts based on email"),
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Import contacts from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        import json
        mapping = json.loads(field_mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid field mapping JSON")
    
    # Read CSV content
    content = await file.read()
    csv_data = content.decode('utf-8')
    
    # Process CSV
    csv_file = io.StringIO(csv_data)
    reader = csv.DictReader(csv_file)
    
    results = ContactImportResult(
        total_rows=0,
        successful_imports=0,
        failed_imports=0,
        errors=[],
        created_contacts=[],
        updated_contacts=[]
    )
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
        results.total_rows += 1
        
        try:
            # Map CSV fields to contact fields
            contact_data = {}
            for csv_field, contact_field in mapping.items():
                if csv_field in row and row[csv_field]:
                    contact_data[contact_field] = row[csv_field].strip()
            
            # Validate required fields
            if not contact_data.get('business_name'):
                raise ValueError("business_name is required")
            if not contact_data.get('contact_name'):
                raise ValueError("contact_name is required")
            
            # Set default status if not provided
            if 'status' not in contact_data:
                contact_data['status'] = ContactStatus.LEAD.value
            
            # Check for existing contact by email
            existing_contact = None
            if contact_data.get('contact_email'):
                existing_contact = await db.scalar(
                    select(Contact).where(
                        and_(
                            Contact.tenant_id == current_user.tenant_id,
                            Contact.contact_email == contact_data['contact_email']
                        )
                    )
                )
            
            if existing_contact and update_existing:
                # Update existing contact
                for field, value in contact_data.items():
                    setattr(existing_contact, field, value)
                
                await db.commit()
                await db.refresh(existing_contact)
                
                results.updated_contacts.append(existing_contact.id)
                results.successful_imports += 1
                
            elif not existing_contact:
                # Create new contact
                contact = Contact(
                    tenant_id=current_user.tenant_id,
                    created_by_user_id=current_user.id,
                    **contact_data
                )
                
                db.add(contact)
                await db.commit()
                await db.refresh(contact)
                
                results.created_contacts.append(contact.id)
                results.successful_imports += 1
                
            else:
                # Skip existing contact
                results.failed_imports += 1
                results.errors.append({
                    "row": row_num,
                    "error": f"Contact with email {contact_data['contact_email']} already exists",
                    "data": contact_data
                })
        
        except Exception as e:
            results.failed_imports += 1
            results.errors.append({
                "row": row_num,
                "error": str(e),
                "data": row
            })
    
    logger.info(f"CSV import completed: {results.successful_imports} successful, {results.failed_imports} failed")
    
    return results

# ============================================================================
# CUSTOM FIELDS
# ============================================================================

@router.get("/custom-fields", response_model=List[CustomFieldResponse])
async def list_custom_fields(
    current_user: User = Depends(require_admin_user),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List custom fields"""
    
    query = select(CustomField).where(CustomField.tenant_id == current_user.tenant_id)
    
    if not include_inactive:
        query = query.where(CustomField.is_active == True)
    
    query = query.order_by(CustomField.display_order, CustomField.field_label)
    
    result = await db.execute(query)
    fields = result.scalars().all()
    
    return [CustomFieldResponse.model_validate(field) for field in fields]

@router.post("/custom-fields", response_model=CustomFieldResponse)
async def create_custom_field(
    field_data: CustomFieldCreate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom field"""
    
    # Check for duplicate field name
    existing = await db.scalar(
        select(CustomField).where(
            and_(
                CustomField.tenant_id == current_user.tenant_id,
                CustomField.field_name == field_data.field_name
            )
        )
    )
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Custom field with name '{field_data.field_name}' already exists"
        )
    
    # Create field
    field = CustomField(
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        **field_data.model_dump()
    )
    
    db.add(field)
    await db.commit()
    await db.refresh(field)
    
    return CustomFieldResponse.model_validate(field)

# Add more endpoints for email templates, bulk operations, etc...
# This is a substantial start to the CRM API