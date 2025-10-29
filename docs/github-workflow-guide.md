# GitHub Workflow Implementation Guide

## Overview

This document provides a comprehensive guide for implementing the controlled commit and PR workflow for the MedellínBot project using GitHub's MCP tools.

## Prerequisites

### Required GitHub Access
To use the GitHub MCP tools, you need:

1. **GitHub Repository**: A valid repository URL (e.g., `https://github.com/username/medellinbot.git`)
2. **Personal Access Token**: A GitHub PAT with the following permissions:
   - `repo` (full control of private repositories)
   - `read:user` (read user profile data)
   - `user:email` (access user email addresses)

### Setting Up GitHub Access

1. **Generate Personal Access Token**:
   ```bash
   # Go to GitHub Settings > Developer settings > Personal access tokens
   # Generate new token with required permissions
   ```

2. **Configure MCP Tool**:
   ```json
   {
     "github_token": "your_github_pat_here",
     "repository_url": "https://github.com/username/medellinbot.git"
   }
   ```

## Controlled Workflow Implementation

### Step 1: Repository Verification

```python
# Verify repository exists
use_mcp_tool({
  "server_name": "GitHub",
  "tool_name": "search_repositories",
  "arguments": {
    "query": "medellinbot",
    "page": 1,
    "perPage": 5
  }
})
```

### Step 2: Project File Inventory

The MedellínBot project contains these key files that should be included in the initial commit:

**Core Files:**
- `README.md` - Project documentation and overview
- `LICENSE` - Project license information
- `requirements.txt` - Python dependencies

**Source Code:**
- `webhook/app.py` - Telegram webhook handler
- `orchestrator/app.py` - Main orchestration engine
- `agents/tramites/app.py` - Trámites agent implementation

**Configuration:**
- `deployment/deploy.sh` - Deployment script
- `deployment/migrate.sql` - Database migration script
- `cloud-run/*.yaml` - Cloud Run configuration files

**Documentation:**
- `docs/` - Comprehensive documentation
- `prompts/` - LLM prompt templates
- `monitoring/` - Monitoring and alerting configuration

### Step 3: Initial Commit Process

```python
# Create commit with essential files
use_mcp_tool({
  "server_name": "GitHub",
  "tool_name": "push_files",
  "arguments": {
    "owner": "username",
    "repo": "medellinbot",
    "branch": "main",
    "files": [
      {
        "path": "README.md",
        "content": "<content of README.md>"
      },
      {
        "path": "webhook/app.py",
        "content": "<content of webhook app>"
      },
      {
        "path": "orchestrator/app.py",
        "content": "<content of orchestrator app>"
      }
      # Add other essential files...
    ],
    "message": "Initial commit: Add core MedellínBot architecture and documentation"
  }
})
```

### Step 4: Pull Request Creation

```python
# Create PR from main to main (for workflow initiation)
use_mcp_tool({
  "server_name": "GitHub",
  "tool_name": "create_pull_request",
  "arguments": {
    "owner": "username",
    "repo": "medellinbot",
    "title": "🚀 Initial Project Setup - MedellínBot Core Architecture",
    "body": "## Summary\n\nThis PR introduces the foundational architecture for MedellínBot, an AI-powered citizen assistance system for the municipality of Medellín, Colombia.\n\n## Changes\n\n- Core webhook handler for Telegram integration\n- Orchestrator service for intent classification and routing\n- Trámites agent for municipal procedure handling\n- Comprehensive documentation and deployment scripts\n\n## Testing\n\n- Unit tests for all core components\n- Integration tests for service communication\n- Load testing configuration with Locust\n\n## Next Steps\n\n- [ ] Review and merge this PR to initiate the development workflow\n- [ ] Set up CI/CD pipeline for automated testing and deployment\n- [ ] Begin development of additional specialized agents\n- [ ] Implement comprehensive monitoring and observability\n\n## Checklist\n\n- [x] All core files included\n- [x] Documentation complete\n- [x] Testing framework established\n- [x] Deployment scripts ready",
    "head": "main",
    "base": "main",
    "draft": false,
    "maintainer_can_modify": true
  }
})
```

## Error Handling and Validation

### Common Issues and Solutions

1. **Permission Denied Errors**:
   ```python
   # Check if token has required permissions
   # Regenerate token with repo, read:user, user:email scopes
   ```

2. **Repository Not Found**:
   ```python
   # Verify repository URL is correct
   # Ensure repository exists and is accessible
   ```

3. **File Conflicts**:
   ```python
   # Check existing files before pushing
   # Use appropriate branch strategy
   ```

### Validation Steps

1. **Pre-commit Validation**:
   - Verify all essential files are included
   - Check file syntax and structure
   - Validate dependencies

2. **Post-commit Verification**:
   - Confirm commit was created successfully
   - Verify all files are present in repository
   - Check commit message format

3. **PR Validation**:
   - Ensure PR was created with correct title and description
   - Verify all required reviewers are assigned
   - Check that draft status is correct

## Best Practices

### Commit Message Standards
- Use clear, descriptive commit messages
- Follow conventional commit format when possible
- Include relevant issue references

### PR Management
- Use descriptive PR titles
- Include comprehensive PR descriptions
- Assign appropriate reviewers
- Set proper labels and milestones

### Security Considerations
- Never commit sensitive information
- Use GitHub Secrets for environment variables
- Regular security audits of dependencies

## Alternative Approaches

If GitHub MCP tools are not accessible, consider these alternatives:

1. **Local Git Operations**:
   ```bash
   # Initialize local repository
   git init
   git add .
   git commit -m "Initial commit"
   
   # Add remote and push
   git remote add origin https://github.com/username/medellinbot.git
   git push -u origin main
   ```

2. **Manual GitHub Operations**:
   - Create repository manually via GitHub web interface
   - Upload files through GitHub's web interface
   - Create PRs manually through GitHub web interface

3. **GitHub CLI**:
   ```bash
   # Install GitHub CLI
   gh auth login
   gh repo create medellinbot --public
   gh repo clone username/medellinbot
   # Add and commit files
   gh pr create --title "Initial commit" --body "Description"
   ```

## Monitoring and Maintenance

### Regular Tasks
- Monitor PR reviews and approvals
- Update documentation as code changes
- Maintain dependency security
- Track repository metrics and usage

### Automation Opportunities
- Set up GitHub Actions for CI/CD
- Configure automated security scanning
- Implement automated documentation generation
- Set up issue and PR templates

## Conclusion

This guide provides a comprehensive approach to implementing the controlled GitHub workflow for MedellínBot. The key to success is ensuring proper access credentials and following the step-by-step validation process to maintain code quality and security standards.

For questions or support, refer to the project documentation or contact the development team.