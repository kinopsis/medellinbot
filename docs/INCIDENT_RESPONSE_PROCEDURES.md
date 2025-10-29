# MedellínBot Incident Response Procedures
## Comprehensive Incident Management Guide

### Table of Contents
1. [Introduction](#introduction)
2. [Incident Classification](#incident-classification)
3. [Incident Response Team](#incident-response-team)
4. [Incident Response Process](#incident-response-process)
5. [Escalation Procedures](#escalation-procedures)
6. [Communication Plan](#communication-plan)
7. [Post-Incident Activities](#post-incident-activities)
8. [Training and Preparedness](#training-and-preparedness)
9. [Tools and Resources](#tools-and-resources)
10. [Appendices](#appendices)

---

## Introduction

This document outlines the comprehensive incident response procedures for MedellínBot, the AI-powered citizen assistance platform for Medellín. These procedures ensure rapid, effective response to incidents that could impact service availability, data integrity, or user experience.

### Purpose
- Establish clear incident response procedures
- Minimize service disruption and impact
- Ensure consistent communication during incidents
- Facilitate rapid resolution and recovery
- Enable continuous improvement through post-incident analysis

### Scope
Applies to all technical incidents affecting MedellínBot services including:
- Webhook service
- Orchestrator service
- Specialized agents (Trámites, PQRSD, Programas, Notificaciones)
- Database systems
- External integrations
- Infrastructure components

---

## Incident Classification

### Severity Levels

#### P1 - Critical (Response Time: 15 minutes)
**Impact**: Complete service outage or critical functionality failure
**Examples**:
- Service completely down (all endpoints unreachable)
- Database connection failure affecting all services
- Security breach or data compromise
- Critical data corruption
- Complete loss of Telegram integration

**Response Requirements**:
- Immediate escalation to all stakeholders
- All hands on deck
- Hourly status updates
- Executive notification required

#### P2 - High (Response Time: 1 hour)
**Impact**: Significant service degradation affecting multiple users
**Examples**:
- Partial service outage (some endpoints down)
- High error rates (>5%)
- Performance degradation (>50% slower than baseline)
- Individual service failures with cascading effects
- Data quality issues affecting critical functionality

**Response Requirements**:
- Immediate investigation
- Daily status updates
- Management notification required

#### P3 - Medium (Response Time: 4 hours)
**Impact**: Limited service impact affecting specific functionality
**Examples**:
- Individual scraper failures
- Non-critical alert escalations
- Minor performance issues
- Feature-specific failures
- Non-critical integration failures

**Response Requirements**:
- Standard investigation procedures
- Status updates as needed
- Team lead notification

#### P4 - Low (Response Time: 24 hours)
**Impact**: Minimal service impact, primarily informational
**Examples**:
- Feature requests
- Minor configuration changes
- Documentation updates
- Non-critical monitoring alerts
- Performance optimization opportunities

**Response Requirements**:
- Standard ticketing procedures
- Regular business hours response

---

## Incident Response Team

### Core Response Team

#### Incident Commander (IC)
- **Role**: Overall incident management and coordination
- **Responsibilities**:
  - Declare incident severity
  - Coordinate response efforts
  - Manage communication flow
  - Make escalation decisions
  - Close incident when resolved
- **Primary**: Engineering Manager
- **Secondary**: Senior DevOps Engineer

#### Technical Lead
- **Role**: Technical investigation and resolution
- **Responsibilities**:
  - Lead technical investigation
  - Implement technical fixes
  - Coordinate with subject matter experts
  - Validate resolution
- **Primary**: Senior DevOps Engineer
- **Secondary**: Database Administrator

#### Communications Lead
- **Role**: Internal and external communication
- **Responsibilities**:
  - Draft incident communications
  - Update status pages
  - Coordinate stakeholder notifications
  - Manage external communications
- **Primary**: Product Manager
- **Secondary**: Operations Lead

### Subject Matter Experts

#### DevOps Engineer
- Infrastructure monitoring and scaling
- Deployment and rollback procedures
- Container and orchestration issues

#### Database Administrator
- Database performance and connectivity
- Data integrity and recovery
- Query optimization

#### Security Engineer
- Security incident investigation
- Vulnerability assessment
- Compliance and forensics

#### Application Engineers
- Service-specific troubleshooting
- Code deployment and rollback
- Feature-specific issues

---

## Incident Response Process

### Step 1: Detection and Alerting

#### Automated Detection
```bash
# Monitoring systems automatically detect issues
- Prometheus alerts for service health
- Cloud Monitoring for infrastructure metrics
- Custom application metrics
- Log-based alerting for errors

# Alert escalation rules
- P1: Immediate page + Slack + Email
- P2: Slack + Email within 15 minutes
- P3: Email within 1 hour
- P4: Ticket creation during business hours
```

#### Manual Detection
- User reports via Telegram
- Internal team observations
- Partner notifications
- Social media monitoring

### Step 2: Initial Response

#### Incident Declaration
1. **Acknowledge Alert**: Respond to monitoring alerts within defined timeframes
2. **Gather Initial Information**:
   ```bash
   # Collect initial data
   - Service status and health checks
   - Recent deployment history
   - Error logs and metrics
   - User impact assessment
   ```
3. **Declare Incident**: Assign severity level based on impact assessment
4. **Assemble Response Team**: Notify appropriate team members

#### Initial Assessment Template
```
INCIDENT DECLARATION
==================
Incident ID: [AUTO-GENERATED]
Timestamp: [YYYY-MM-DD HH:MM:SS UTC]
Declared By: [Name]
Severity: [P1/P2/P3/P4]
Services Affected: [List]
Initial Impact: [Description]
Initial Root Cause: [If known]
Response Team: [List of notified members]
```

### Step 3: Investigation and Diagnosis

#### Systematic Investigation
1. **Service Health Check**:
   ```bash
   # Check service status
   curl -f https://medellinbot-webhook-[PROJECT_ID].a.run.app/health
   curl -f https://medellinbot-orchestrator-[PROJECT_ID].a.run.app/health
   
   # Check recent logs
   gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' --limit=50
   
   # Check metrics
   gcloud monitoring metrics list --filter="web_scraping"
   ```

2. **Recent Changes Review**:
   - Last deployment timestamps
   - Configuration changes
   - Dependency updates
   - External service changes

3. **Impact Assessment**:
   - Number of affected users
   - Geographic impact
   - Business process impact
   - Data integrity concerns

#### Investigation Tools
- **Monitoring Dashboard**: Real-time service metrics
- **Log Analysis**: Structured log searching
- **Tracing**: Request flow analysis
- **Database Tools**: Query performance and connectivity
- **Network Tools**: Connectivity and latency testing

### Step 4: Mitigation and Resolution

#### Immediate Mitigation
1. **Service Restoration**:
   ```bash
   # Common mitigation steps
   - Restart affected services
   - Scale resources if needed
   - Rollback recent deployments
   - Enable maintenance mode if necessary
   ```

2. **Communication**:
   - Update internal channels
   - Notify affected users
   - Post status updates

#### Root Cause Resolution
1. **Implement Fix**:
   - Apply configuration changes
   - Deploy code fixes
   - Resolve infrastructure issues
   - Coordinate with external vendors

2. **Validation**:
   - Verify service restoration
   - Monitor for stability
   - Confirm user impact resolution

### Step 5: Incident Closure

#### Resolution Verification
1. **Service Validation**:
   ```bash
   # Verify all services are healthy
   - All health checks passing
   - Error rates below thresholds
   - Performance within normal ranges
   - User functionality confirmed
   ```

2. **Documentation**:
   - Update incident timeline
   - Document root cause
   - Record resolution steps
   - Note lessons learned

#### Incident Closure Template
```
INCIDENT RESOLUTION
==================
Incident ID: [NUMBER]
Resolution Timestamp: [YYYY-MM-DD HH:MM:SS UTC]
Resolved By: [Name]
Root Cause: [Detailed description]
Resolution Steps: [Step-by-step actions taken]
Verification: [How resolution was confirmed]
Prevention: [Steps to prevent recurrence]
```

---

## Escalation Procedures

### Automatic Escalation

#### Time-Based Escalation
- **P1**: Escalate every 15 minutes until resolved
- **P2**: Escalate every 30 minutes until resolved
- **P3**: Escalate every 2 hours until resolved
- **P4**: Escalate daily until resolved

#### Severity-Based Escalation

##### P1 Escalation Path
1. **Immediate**: All response team members + Engineering Director
2. **15 minutes**: VP of Engineering + Product Director
3. **30 minutes**: CTO + CEO
4. **1 hour**: Executive team + External stakeholders

##### P2 Escalation Path
1. **Immediate**: Response team + Engineering Manager
2. **1 hour**: Engineering Director
3. **4 hours**: Product Director
4. **8 hours**: VP of Engineering

### Manual Escalation

#### When to Escalate
- Incident impact increases
- Root cause not identified within timeframe
- Resolution attempts unsuccessful
- External coordination required
- Media or public attention

#### Escalation Request Template
```
ESCALATION REQUEST
==================
Incident ID: [NUMBER]
Current Severity: [P1/P2/P3/P4]
Escalation Reason: [Reason for escalation]
Requested Escalation: [Who to involve]
Additional Resources Needed: [Specific resources]
```

---

## Communication Plan

### Internal Communication

#### Communication Channels
- **Slack**: #incidents channel for real-time updates
- **Email**: Formal notifications for stakeholders
- **Status Page**: Public service status updates
- **Phone**: Critical escalation calls

#### Communication Templates

##### Initial Incident Notification
```
🚨 INCIDENT DECLARED
===================
Severity: [P1/P2/P3/P4]
Services Affected: [List]
Impact: [Description]
Declared By: [Name]
Response Team: [List]
Initial Assessment: [Brief description]
Next Update: [Time]
```

##### Status Update
```
 INCIDENT UPDATE
===============
Incident ID: [NUMBER]
Timestamp: [YYYY-MM-DD HH:MM:SS UTC]
Current Status: [Status description]
Progress: [What has been done]
Next Steps: [Planned actions]
ETA to Resolution: [If available]
```

##### Resolution Notification
```
✅ INCIDENT RESOLVED
===================
Incident ID: [NUMBER]
Resolution Time: [YYYY-MM-DD HH:MM:SS UTC]
Root Cause: [Brief description]
Resolution: [What was done]
Verification: [How it was confirmed]
Follow-up: [Next steps if any]
```

### External Communication

#### User Communication
- **Telegram Bot**: Automated status updates
- **Website**: Status page updates
- **Social Media**: Public announcements for major incidents
- **Email**: Direct notifications for critical issues

#### Stakeholder Communication
- **Municipal Partners**: Direct notifications for service impacts
- **External Vendors**: Coordination for integration issues
- **Regulatory Bodies**: Required notifications for data incidents

---

## Post-Incident Activities

### Post-Incident Review (PIR)

#### PIR Timeline
- **P1 Incidents**: Within 48 hours
- **P2 Incidents**: Within 1 week
- **P3 Incidents**: Within 2 weeks
- **P4 Incidents**: As part of regular review cycle

#### PIR Participants
- Incident Commander
- Technical Lead
- Communications Lead
- Subject Matter Experts
- Affected Stakeholders
- Management (for P1/P2)

#### PIR Template
```
POST-INCIDENT REVIEW
====================
Incident ID: [NUMBER]
Date: [YYYY-MM-DD]
Severity: [P1/P2/P3/P4]
Duration: [Start time - End time]

EXECUTIVE SUMMARY
=================
Brief description of what happened and impact.

TIMELINE
========
[Detailed timeline of events, actions, and communications]

ROOT CAUSE ANALYSIS
===================
Primary Cause: [Main cause]
Contributing Factors: [Additional factors]
Detection: [How and when was it detected]
Response: [Response effectiveness]

IMPACT ASSESSMENT
=================
User Impact: [Number and type of users affected]
Business Impact: [Operational and financial impact]
Reputation Impact: [Public and stakeholder impact]
Data Impact: [Any data loss or corruption]

RESPONSE ASSESSMENT
===================
Detection Time: [Time to detect]
Response Time: [Time to respond]
Resolution Time: [Time to resolve]
Communication: [Effectiveness of communication]
Coordination: [Team coordination effectiveness]

LESSONS LEARNED
===============
What Went Well: [Positive aspects]
What Could Be Improved: [Areas for improvement]
Action Items: [Specific improvements to make]

PREVENTION MEASURES
===================
Monitoring Improvements: [Better detection]
Process Improvements: [Better response]
Technical Improvements: [Better resolution]
Training Needs: [Skill development required]

ACTION ITEMS
============
[Specific action items with owners and due dates]
```

### Follow-up Actions

#### Action Item Tracking
- **Owner**: Person responsible
- **Due Date**: Completion deadline
- **Status**: In progress/completed/blocked
- **Priority**: High/medium/low

#### Regular Review
- Weekly action item review
- Monthly incident trend analysis
- Quarterly process improvement
- Annual procedure review

---

## Training and Preparedness

### Training Program

#### New Team Member Training
- Incident response procedures
- Tool usage and access
- Communication protocols
- Role-specific training

#### Regular Training
- **Monthly**: Tabletop exercises
- **Quarterly**: Full incident simulation
- **Annually**: Procedure review and update

#### Training Materials
- Incident response playbooks
- Tool documentation
- Communication templates
- Case studies

### Preparedness Activities

#### Drills and Exercises
1. **Tabletop Exercises**:
   - Scenario-based discussions
   - Role-playing different incident types
   - Communication practice

2. **Technical Drills**:
   - Tool usage practice
   - Escalation procedure testing
   - Communication channel testing

3. **Full Simulation**:
   - Realistic incident scenarios
   - Cross-team coordination
   - External communication practice

#### Readiness Assessment
- **Tool Access**: All team members have required access
- **Documentation**: Current and accessible
- **Contact Information**: Up to date
- **Escalation Paths**: Tested and verified

---

## Tools and Resources

### Monitoring and Alerting
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Cloud Monitoring**: Google Cloud metrics
- **PagerDuty**: Alerting and escalation
- **Slack**: Real-time communication

### Communication
- **Slack**: Team communication
- **Email**: Formal notifications
- **Status Page**: Public updates
- **Phone**: Critical escalation
- **Video Conferencing**: Team coordination

### Investigation
- **Cloud Logging**: Log analysis
- **Cloud Trace**: Request tracing
- **Database Tools**: Query analysis
- **Network Tools**: Connectivity testing
- **Git**: Change tracking

### Documentation
- **Confluence**: Procedure documentation
- **Google Drive**: File storage
- **GitHub**: Code and configuration
- **Runbooks**: Step-by-step guides
- **Incident Tracking**: Jira/ServiceNow

---

## Appendices

### Appendix A: Contact Information

#### On-Call Schedule
- **Primary On-Call**: [Name, Phone, Email]
- **Secondary On-Call**: [Name, Phone, Email]
- **Rotation Schedule**: [Link to rotation]

#### Emergency Contacts
- **Engineering Manager**: [Contact Info]
- **Product Manager**: [Contact Info]
- **Security Lead**: [Contact Info]
- **External Vendors**: [Contact Info]

### Appendix B: Runbooks

#### Service-Specific Runbooks
- Webhook Service Runbook
- Orchestrator Service Runbook
- Database Runbook
- Infrastructure Runbook

#### Common Procedures
- Service Restart Procedure
- Deployment Rollback Procedure
- Database Recovery Procedure
- Security Incident Procedure

### Appendix C: External Resources

#### Vendor Contacts
- Google Cloud Support: [Contact Info]
- Database Vendor: [Contact Info]
- Security Vendor: [Contact Info]

#### Emergency Services
- IT Emergency Services: [Contact Info]
- Data Recovery Services: [Contact Info]
- Security Incident Response: [Contact Info]

### Appendix D: Legal and Compliance

#### Regulatory Requirements
- Data Protection Regulations
- Incident Reporting Requirements
- Service Level Agreements

#### Documentation Requirements
- Incident Logs
- Communication Records
- Resolution Documentation
- Compliance Reports

---

*This document should be reviewed and updated quarterly. All team members should be familiar with the procedures outlined herein.*

**Document Version**: 1.0  
**Last Updated**: 2025-10-29  
**Next Review**: 2026-01-29  
**Owner**: Engineering Manager