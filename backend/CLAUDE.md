# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## CRITICAL: Verify Assumptions Before Making Breaking Changes
**ALWAYS VERIFY BUSINESS LOGIC ASSUMPTIONS WITH THE USER BEFORE IMPLEMENTING**
- DO NOT assume default behavior for security-critical features
- ASK THE USER to clarify intended behavior when logic is ambiguous
- Example: Agent filtering logic assumed agents without OWNER_DOMAINS should be unavailable
- This broke the entire chat application when most agents lacked this property
- VERIFY with user whether undefined properties should default to restrictive or permissive behavior
- When in doubt about application-breaking changes, ASK FIRST

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
