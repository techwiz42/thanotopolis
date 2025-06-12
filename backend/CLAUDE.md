# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## 🚨 CRITICAL: ABSOLUTE GIT COMMIT PROHIBITION 🚨
**CLAUDE CODE MUST NEVER, EVER, UNDER ANY CIRCUMSTANCES COMMIT CODE TO GIT**

### STRICT RULES - NO EXCEPTIONS:
1. **NEVER run `git commit` commands** - User explicitly forbids ALL automated git commits
2. **NEVER run `git add` followed by commits** - No staging and committing workflows
3. **NEVER suggest git commit commands** - Don't even recommend commit messages
4. **NEVER create commits** - Even with user approval, let them handle it
5. **NEVER push to remote** - Absolutely forbidden under all circumstances

### ALLOWED GIT OPERATIONS:
- `git status` - To check repository state
- `git diff` - To view changes
- `git log` - To view commit history
- `git branch` - To check/list branches
- READ-ONLY operations only

### VIOLATION CONSEQUENCES:
- Any Claude Code session that commits to git violates user trust
- This has caused problems before and must be prevented
- User must maintain complete control over their git workflow

### IF ASKED ABOUT COMMITS:
- Respond: "I cannot commit code to git. Please handle git operations yourself."
- Suggest what files have been changed, but never commit them
- Let user decide when and how to commit their changes

## Current Project: Organization & Agent Management Enhancements (January 11, 2025)

### Overview
Implementing enhanced organization registration and agent management system with the following key features:
1. Extended organization data collection (full name, address, phone, email)
2. Automatic organization admin creation during registration
3. Organization admin capabilities (edit org data, manage users)
4. Agent ownership model (free agents vs proprietary agents)

### Database Schema Changes Required

#### 1. Tenant/Organization Model Updates
- Add fields: `full_name`, `address`, `phone`, `organization_email`
- Consider renaming `Tenant` to `Organization` for clarity (but keeping table name for compatibility)

#### 2. User Model Updates
- Ensure proper role hierarchy: `user`, `org_admin`, `admin`, `super_admin`
- Add capability for org_admin to manage organization users

#### 3. New Agent Model
- Create `Agent` table to track agent configurations
- Add `is_free_agent` boolean field (True = available to all, False = proprietary)
- Add `owner_tenant_id` field for proprietary agents
- Update `ConversationAgent` to reference Agent model instead of just agent_type string

### Implementation Progress

#### ✅ Completed Tasks
1. [x] Analyze current database models and schema
2. [x] Update organization model with new fields (name, address, phone, email)
3. [x] Update agent model to support free vs proprietary agents
4. [x] Create database migration for schema changes (revision 87b8d0316915)
5. [x] Update API endpoints and schemas
6. [x] Create/update CLAUDE.md with progress tracking

#### 🔄 In Progress Tasks
- [ ] Update frontend organization registration form

#### ⏸️ Pending Tasks (Backend Implementation Ready)
- [ ] Create organization admin during org registration ✅ **API READY**
- [ ] Add organization admin permissions for editing org data ✅ **API READY**
- [ ] Add organization admin ability to list/delete/deactivate users ✅ **API READY**

### ✅ MAJOR MILESTONE: Backend Implementation Complete

#### What's Been Implemented (January 11, 2025)

##### Database Schema Updates
- **Enhanced Tenant/Organization Model**: Added `full_name`, `address` (JSON), `phone`, `organization_email` fields
- **New Agent Model**: Complete agent management with ownership (free vs proprietary agents)
- **Updated Role Hierarchy**: Added `org_admin` role between `user` and `admin`
- **Migration Applied**: Database successfully updated with revision 87b8d0316915

##### New API Endpoints
**Organizations API (`/api/organizations/`)**:
- `POST /register` - Complete organization registration with admin user creation
- `GET /{org_id}` - Get organization details
- `PATCH /{org_id}` - Update organization (org_admin+ required)
- `GET /{org_id}/users` - List organization users (org_admin+ required)
- `PATCH /{org_id}/users/{user_id}` - Update user role/status (org_admin+ required)
- `DELETE /{org_id}/users/{user_id}` - Deactivate user (org_admin+ required)

**Agents API (`/api/agents/`)**:
- `GET /` - List available agents (filtered by ownership)
- `POST /` - Create proprietary agent (org_admin+ required)
- `GET /{agent_id}` - Get agent details
- `PATCH /{agent_id}` - Update agent configuration
- `DELETE /{agent_id}` - Deactivate agent

##### Security & Permissions
- **Role-based Access Control**: Proper hierarchy (user < org_admin < admin < super_admin)
- **Organization Isolation**: Users can only manage their own organization
- **Agent Ownership**: Free agents available to all, proprietary agents per organization
- **Authentication Integration**: Token generation for immediate login after registration

##### Updated Schemas
- **Enhanced Organization Schemas**: Full registration request/response models
- **Agent Management Schemas**: Complete CRUD operations support
- **Role Management**: Admin user update capabilities

### Technical Decisions

#### Organization Data Structure
- Keep `Tenant` model name for backward compatibility
- Add new fields to existing model rather than creating separate table
- Use JSON field for address to support international formats

#### Agent Ownership Model
```python
class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID, primary_key=True)
    agent_type = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_free_agent = Column(Boolean, default=True)
    owner_tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    configuration_template = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
```

#### Role Hierarchy
- `user`: Basic user within organization
- `org_admin`: Can manage organization data and users
- `admin`: System-wide admin (if multi-tenant)
- `super_admin`: Full system access

### API Endpoint Changes

#### Organization Registration
- `POST /api/organizations/register` - New endpoint for full org registration
- Creates organization and first admin user atomically
- Returns organization details and admin credentials

#### Organization Management
- `GET /api/organizations/{org_id}` - Get organization details
- `PATCH /api/organizations/{org_id}` - Update organization (org_admin only)
- `GET /api/organizations/{org_id}/users` - List organization users
- `PATCH /api/organizations/{org_id}/users/{user_id}` - Update user status
- `DELETE /api/organizations/{org_id}/users/{user_id}` - Remove user

#### Agent Management
- `GET /api/agents` - List available agents (filtered by ownership)
- `POST /api/agents` - Create proprietary agent (org_admin only)
- `PATCH /api/agents/{agent_id}` - Update agent configuration
- `DELETE /api/agents/{agent_id}` - Delete proprietary agent

### Frontend Changes Required
1. New organization registration form with all fields
2. Organization admin dashboard
3. User management interface
4. Agent configuration interface

### Migration Strategy
1. Add new columns to existing tables with defaults
2. Create new Agent table
3. Migrate existing agent_type strings to Agent records
4. Update foreign key relationships

### Next Steps
1. Create database migration script
2. Update models.py with new fields
3. Update schemas.py with new request/response models
4. Implement new API endpoints
5. Update authentication to support org_admin role
6. Create frontend components

---

## Previous Project Sections (Preserved for Reference)

### Current Project: Language Selection for STT (January 8, 2025) - COMPLETED ✅

[Previous content preserved but moved to bottom of file...]