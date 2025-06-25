# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## CRITICAL: Agent Ownership and Availability Logic
**CLARIFIED: Agent filtering logic for organization access**

### Agent Availability Rules:
1. **Free Agents (Available to ALL organizations):**
   - `OWNER_DOMAINS = []` (empty list) - Explicit free agents
   - `OWNER_DOMAINS = None` or undefined - Legacy free agents (normalized to empty list)
   - Invalid `OWNER_DOMAINS` types (e.g., string) - Treated as legacy free agents

2. **Proprietary Agents (Available to SPECIFIC organizations only):**
   - `OWNER_DOMAINS = ["demo", "premium"]` - Only available to listed organizations

3. **Telephony-Only Agents:**
   - Excluded from chat context unless explicitly requested via `include_telephony_only=True`

### Implementation Notes:
- Legacy agents without `OWNER_DOMAINS` are treated as free agents for backward compatibility
- Invalid `OWNER_DOMAINS` types are normalized to `None` and treated as legacy free agents
- The fallback behavior on database errors returns only free agents as a safe default

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

## Current Project: Integration Test Suite Deployment (June 23, 2025)

### Overview
Preparing the integration test suite for comprehensive deployment across the Thanotopolis backend system. Focus on creating a robust testing infrastructure that ensures system reliability, API compatibility, and consistent behavior across different components.

### New Test Coverage Areas
- Full WebSocket connection lifecycle testing
- Telephony audio format conversion validation
- Organization and tenant isolation verification
- Agent discovery and filtering mechanisms
- Authentication token management

### Test Infrastructure Improvements
- Implement async database fixtures
- Create mock service layers for controlled testing
- Develop comprehensive error scenario tests
- Add logging and tracing for test diagnostics

### Priority Test Scenarios
1. Test WebSocket connection establishment and teardown
2. Validate audio conversion pipelines
3. Verify organization-level agent filtering
4. Test authentication token refresh mechanisms
5. Simulate complex conversation workflows

### Technical Approach
- Use pytest for test orchestration
- Implement async test runners
- Create reusable test fixtures
- Add detailed logging for test diagnostics

### Next Immediate Steps
1. Complete async database test fixtures
2. Develop WebSocket connection test suite
3. Create audio conversion validation tests
4. Implement organization isolation tests
