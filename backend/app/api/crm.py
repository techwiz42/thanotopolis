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
from app.auth.auth import get_current_user
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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

# ============================================================================
# EMAIL TESTING
# ============================================================================

from pydantic import BaseModel, EmailStr

class TestEmailRequest(BaseModel):
    to_email: EmailStr
    test_type: str = "simple"  # "simple" or "template"

@router.post("/test-email")
async def send_test_email(
    request: TestEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a test email to verify SendGrid configuration"""
    
    if not email_service.is_configured():
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured. Please set SENDGRID_API_KEY environment variable."
        )
    
    try:
        if request.test_type == "template":
            # Send template test email
            template_vars = {
                "contact_name": f"{current_user.first_name} {current_user.last_name}".strip() or "Test User",
                "organization_name": "Thanotopolis CRM",
                "business_name": "Test Organization",
                "contact_role": "Admin",
                "contact_email": request.to_email,
                "phone": "+1-555-123-4567"
            }
            
            welcome_template = DEFAULT_TEMPLATES["contact_welcome"]
            
            result = await email_service.send_template_email(
                to_email=request.to_email,
                subject_template=welcome_template["subject"],
                html_template=welcome_template["html_content"],
                template_variables=template_vars,
                text_template=welcome_template["text_content"],
                to_name=template_vars["contact_name"]
            )
        else:
            # Send simple test email
            subject = "Test Email from Thanotopolis CRM"
            html_content = f"""
            <html>
            <body>
                <h2>Test Email</h2>
                <p>Hello {current_user.first_name or 'Admin'},</p>
                <p>This is a test email from your Thanotopolis CRM system.</p>
                <p>If you're receiving this, it means your SendGrid integration is working correctly!</p>
                <hr>
                <p><strong>Email Service Details:</strong></p>
                <ul>
                    <li>Service: SendGrid</li>
                    <li>From: {email_service.from_email}</li>
                    <li>From Name: {email_service.from_name}</li>
                    <li>Sent by: {current_user.first_name} {current_user.last_name}</li>
                </ul>
                <p>Best regards,<br>Thanotopolis CRM Team</p>
            </body>
            </html>
            """
            
            result = await email_service.send_email(
                to_email=request.to_email,
                subject=subject,
                html_content=html_content,
                to_name=f"{current_user.first_name} {current_user.last_name}".strip()
            )
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Test email sent successfully to {request.to_email}",
                "status_code": result["status_code"],
                "message_id": result.get("message_id"),
                "test_type": request.test_type
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send test email: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test email: {str(e)}"
        )


# ============================================================================
# EMAIL TEMPLATES
# ============================================================================

@router.get("/email-templates", response_model=List[EmailTemplateResponse])
async def list_email_templates(
    current_user: User = Depends(get_current_user),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List email templates"""
    
    query = select(EmailTemplate).where(EmailTemplate.tenant_id == current_user.tenant_id)
    
    if not include_inactive:
        query = query.where(EmailTemplate.is_active == True)
    
    query = query.order_by(EmailTemplate.name)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [EmailTemplateResponse.model_validate(template) for template in templates]

@router.get("/email-templates/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get email template details"""
    
    template = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.id == template_id,
                EmailTemplate.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    return EmailTemplateResponse.model_validate(template)

@router.post("/email-templates", response_model=EmailTemplateResponse)
async def create_email_template(
    template_data: EmailTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new email template"""
    
    # Check for duplicate template name
    existing = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.tenant_id == current_user.tenant_id,
                EmailTemplate.name == template_data.name
            )
        )
    )
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Email template with name '{template_data.name}' already exists"
        )
    
    # Create template
    template = EmailTemplate(
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        **template_data.model_dump()
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    logger.info(f"Email template created: {template.name} by user {current_user.email}")
    
    return EmailTemplateResponse.model_validate(template)

@router.patch("/email-templates/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: UUID,
    template_data: EmailTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update email template"""
    
    template = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.id == template_id,
                EmailTemplate.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Check for duplicate name if name is being updated
    if template_data.name and template_data.name != template.name:
        existing = await db.scalar(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.tenant_id == current_user.tenant_id,
                    EmailTemplate.name == template_data.name,
                    EmailTemplate.id != template_id
                )
            )
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Email template with name '{template_data.name}' already exists"
            )
    
    # Update fields
    for field, value in template_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    
    return EmailTemplateResponse.model_validate(template)

@router.delete("/email-templates/{template_id}")
async def delete_email_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete email template"""
    
    template = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.id == template_id,
                EmailTemplate.tenant_id == current_user.tenant_id
            )
        )
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    await db.delete(template)
    await db.commit()
    
    logger.info(f"Email template deleted: {template.name} by user {current_user.email}")
    
    return {"message": "Email template deleted successfully"}

@router.post("/email-templates/upload")
async def upload_email_template(
    file: UploadFile = File(...),
    name: str = Query(..., description="Template name"),
    subject: str = Query(..., description="Email subject"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload email template from HTML file"""
    
    if not file.filename.endswith(('.html', '.htm')):
        raise HTTPException(status_code=400, detail="File must be HTML")
    
    # Check for duplicate template name
    existing = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.tenant_id == current_user.tenant_id,
                EmailTemplate.name == name
            )
        )
    )
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Email template with name '{name}' already exists"
        )
    
    # Read HTML content
    content = await file.read()
    html_content = content.decode('utf-8')
    
    # Extract variables from HTML (looking for {{variable}} patterns)
    import re
    variables = list(set(re.findall(r'\{\{([^}]+)\}\}', html_content)))
    
    # Create template
    template = EmailTemplate(
        tenant_id=current_user.tenant_id,
        created_by_user_id=current_user.id,
        name=name,
        subject=subject,
        html_content=html_content,
        variables=variables,
        is_active=True
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    logger.info(f"Email template uploaded: {template.name} by user {current_user.email}")
    
    return {
        "message": "Email template uploaded successfully",
        "template": EmailTemplateResponse.model_validate(template)
    }

# ============================================================================
# BULK EMAIL
# ============================================================================

@router.post("/bulk-email")
async def send_bulk_email(
    request: BulkEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send bulk email to multiple contacts using a template"""
    
    if not email_service.is_configured():
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured. Please set SENDGRID_API_KEY environment variable."
        )
    
    # Get email template
    template = await db.scalar(
        select(EmailTemplate).where(
            and_(
                EmailTemplate.id == request.template_id,
                EmailTemplate.tenant_id == current_user.tenant_id,
                EmailTemplate.is_active == True
            )
        )
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Get contacts
    contacts_query = select(Contact).where(
        and_(
            Contact.tenant_id == current_user.tenant_id,
            Contact.id.in_(request.contact_ids),
            Contact.contact_email.is_not(None),
            Contact.contact_email != ""
        )
    )
    
    contacts_result = await db.execute(contacts_query)
    contacts = contacts_result.scalars().all()
    
    if not contacts:
        raise HTTPException(status_code=400, detail="No valid contacts found with email addresses")
    
    # Get organization name for template variables
    tenant = await db.scalar(select(Tenant).where(Tenant.id == current_user.tenant_id))
    organization_name = tenant.name if tenant else "Unknown Organization"
    
    # Send emails
    results = BulkEmailResult(
        template_id=str(request.template_id),
        total_contacts=len(contacts),
        successful_sends=0,
        failed_sends=0,
        errors=[]
    )
    
    for contact in contacts:
        try:
            # Prepare template variables
            template_vars = {
                "contact_name": contact.contact_name,
                "business_name": contact.business_name,
                "organization_name": organization_name,
                "contact_role": contact.contact_role or "",
                "contact_email": contact.contact_email,
                "phone": contact.phone or "",
                "city": contact.city or "",
                "state": contact.state or "",
                "website": contact.website or "",
                "address": contact.address or "",
                **request.additional_variables  # Allow custom variables
            }
            
            # Send email
            result = await email_service.send_template_email(
                to_email=contact.contact_email,
                subject_template=template.subject,
                html_template=template.html_content,
                template_variables=template_vars,
                text_template=template.text_content,
                to_name=contact.contact_name
            )
            
            if result["success"]:
                results.successful_sends += 1
                
                # Log interaction
                interaction = ContactInteraction(
                    contact_id=contact.id,
                    user_id=current_user.id,
                    interaction_type=ContactInteractionType.EMAIL.value,
                    subject=f"Bulk Email: {template.subject}",
                    content=f"Sent email using template '{template.name}'",
                    interaction_date=datetime.now(timezone.utc),
                    metadata={"template_id": str(template.id), "bulk_email": True}
                )
                db.add(interaction)
            else:
                results.failed_sends += 1
                results.errors.append({
                    "contact_id": str(contact.id),
                    "contact_email": contact.contact_email,
                    "error": result.get("error", "Unknown error")
                })
                
        except Exception as e:
            results.failed_sends += 1
            results.errors.append({
                "contact_id": str(contact.id),
                "contact_email": contact.contact_email,
                "error": str(e)
            })
    
    # Commit interactions
    await db.commit()
    
    logger.info(f"Bulk email sent: {results.successful_sends} successful, {results.failed_sends} failed by user {current_user.email}")
    
    return results

@router.get("/contacts/search", response_model=PaginatedResponse)
async def search_contacts_advanced(
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    search_term: Optional[str] = Query(None, description="Search term"),
    search_fields: Optional[str] = Query(None, description="Comma-separated list of fields to search"),
    status: Optional[ContactStatus] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None, description="Filter contacts with/without email"),
    db: AsyncSession = Depends(get_db)
):
    """Advanced contact search with field selection"""
    
    tenant_id = current_user.tenant_id
    
    # Build query
    query = select(Contact).where(Contact.tenant_id == tenant_id)
    conditions = []
    
    # Search term with field selection
    if search_term and search_fields:
        fields = [field.strip() for field in search_fields.split(',')]
        search_conditions = []
        search_pattern = f"%{search_term}%"
        
        for field in fields:
            if field == 'business_name':
                search_conditions.append(Contact.business_name.ilike(search_pattern))
            elif field == 'contact_name':
                search_conditions.append(Contact.contact_name.ilike(search_pattern))
            elif field == 'contact_email':
                search_conditions.append(Contact.contact_email.ilike(search_pattern))
            elif field == 'contact_role':
                search_conditions.append(Contact.contact_role.ilike(search_pattern))
            elif field == 'phone':
                search_conditions.append(Contact.phone.ilike(search_pattern))
            elif field == 'city':
                search_conditions.append(Contact.city.ilike(search_pattern))
            elif field == 'state':
                search_conditions.append(Contact.state.ilike(search_pattern))
            elif field == 'notes':
                search_conditions.append(Contact.notes.ilike(search_pattern))
        
        if search_conditions:
            conditions.append(or_(*search_conditions))
    elif search_term:  # Fallback to all fields search
        search_pattern = f"%{search_term}%"
        conditions.append(
            or_(
                Contact.business_name.ilike(search_pattern),
                Contact.contact_name.ilike(search_pattern),
                Contact.contact_email.ilike(search_pattern),
                Contact.contact_role.ilike(search_pattern),
                Contact.phone.ilike(search_pattern),
                Contact.city.ilike(search_pattern),
                Contact.state.ilike(search_pattern),
                Contact.notes.ilike(search_pattern)
            )
        )
    
    # Other filters
    if status:
        conditions.append(Contact.status == status.value)
    
    if city:
        conditions.append(Contact.city.ilike(f"%{city}%"))
    
    if state:
        conditions.append(Contact.state.ilike(f"%{state}%"))
    
    if has_email is True:
        conditions.append(and_(Contact.contact_email.is_not(None), Contact.contact_email != ""))
    elif has_email is False:
        conditions.append(or_(Contact.contact_email.is_(None), Contact.contact_email == ""))
    
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
    
    # Add interaction counts
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
        
        contact_dict = ContactResponse.model_validate(contact).model_dump()
        contact_dict["interaction_count"] = interaction_count or 0
        contact_dict["last_interaction_date"] = last_interaction
        contact_responses.append(contact_dict)
    
    return PaginatedResponse(
        items=contact_responses,
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=((total or 0) + pagination.page_size - 1) // pagination.page_size
    )