# Web Scraping Service Operations Runbook
## MedellínBot - Day-to-Day Operations Guide

### Table of Contents
1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [Incident Response](#incident-response)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Performance Monitoring](#performance-monitoring)
6. [Security Operations](#security-operations)
7. [Backup and Recovery](#backup-and-recovery)
8. [Scaling Operations](#scaling-operations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Contact Information](#contact-information)

---

## Overview

This runbook provides step-by-step procedures for the day-to-day operations of the Web Scraping Service for MedellínBot. It is designed for operations engineers, DevOps engineers, and on-call personnel responsible for maintaining the service.

### Service Overview

- **Service Name**: Web Scraping Service
- **Environment**: Production
- **URL**: `https://web-scraping-service-[PROJECT_ID].a.run.app`
- **Uptime SLA**: 99.9%
- **Response Time SLA**: < 3 seconds for 95% of requests
- **Data Freshness**: < 1 hour for critical data

### Key Components

- **Cloud Run Service**: Main application container
- **Cloud SQL**: PostgreSQL database for structured data
- **Cloud Storage**: Object storage for raw data and files
- **Cloud Scheduler**: Automated job scheduling
- **Cloud Monitoring**: Metrics and alerting
- **Secret Manager**: Secure configuration storage

---

## Daily Operations

### Morning Check (8:00 AM)

#### 1. Service Health Check
```bash
# Check service status
gcloud run services describe web-scraping-service --platform=managed --region=us-central1

# Test health endpoints
curl -f https://web-scraping-service-[PROJECT_ID].a.run.app/health
curl -f https://web-scraping-service-[PROJECT_ID].a.run.app/ready

# Check recent logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=web-scraping-service' --limit=10 --format="table(timestamp,severity,jsonPayload.message)"
```

#### 2. Monitor Key Metrics
- [ ] Check Grafana dashboard for service health
- [ ] Verify error rate < 1%
- [ ] Confirm data quality scores > 0.8
- [ ] Review scraper performance metrics
- [ ] Check database connection health

#### 3. Review Overnight Jobs
```bash
# Check scheduled job execution
gcloud scheduler jobs describe web-scraping-scheduler

# Review job execution logs
gcloud logging read 'resource.type=cloud_scheduler_job AND resource.labels.job_id=web-scraping-scheduler' --limit=5
```

### Afternoon Check (2:00 PM)

#### 1. Data Quality Review
```bash
# Check latest scraped data
curl https://web-scraping-service-[PROJECT_ID].a.run.app/api/v1/data/latest

# Review data quality metrics
curl https://web-scraping-service-[PROJECT_ID].a.run.app/api/v1/metrics/quality
```

#### 2. Resource Utilization
- [ ] Check CPU usage < 70%
- [ ] Verify memory usage < 80%
- [ ] Review storage utilization
- [ ] Monitor database performance

#### 3. Alert Review
- [ ] Check for any active alerts in Cloud Monitoring
- [ ] Review alert history from the past 24 hours
- [ ] Verify no false positives in alerting

### Evening Check (6:00 PM)

#### 1. End-of-Day Summary
```bash
# Generate daily metrics summary
gcloud monitoring time-series query 'metric.type="run.googleapis.com/request_count" AND resource.labels.service_name="web-scraping-service"' --interval=24h
```

#### 2. Prepare for Next Day
- [ ] Review scheduled maintenance windows
- [ ] Check for any pending deployments
- [ ] Verify backup completion status

---

## Incident Response

### Incident Classification

#### P1 - Critical (Response Time: 15 minutes)
- Service completely down
- Data corruption detected
- Security breach
- Database connection failure

#### P2 - High (Response Time: 1 hour)
- Partial service degradation
- High error rates (> 5%)
- Performance degradation (> 50% slower)
- Data quality issues

#### P3 - Medium (Response Time: 4 hours)
- Individual scraper failures
- Non-critical alert escalations
- Minor performance issues

#### P4 - Low (Response Time: 24 hours)
- Feature requests
- Minor configuration changes
- Documentation updates

### Incident Response Procedure

#### Step 1: Detection and Alerting
1. **Monitor alerts** in Cloud Monitoring
2. **Check dashboards** for异常 patterns
3. **Review logs** for error patterns
4. **Verify** if it's a real incident or false positive

#### Step 2: Initial Response
```bash
# Acknowledge the incident
# Create incident ticket in tracking system
# Notify on-call engineer
# Begin investigation
```

#### Step 3: Investigation
```bash
# Check service health
gcloud run services describe web-scraping-service --platform=managed --region=us-central1

# Review recent logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=web-scraping-service' --limit=50

# Check metrics
gcloud monitoring dashboards describe web-scraping-dashboard
```

#### Step 4: Mitigation
- **Service Down**: Check deployment status, restart if needed
- **High Errors**: Review error logs, identify root cause
- **Performance Issues**: Check resource utilization, scale if needed
- **Database Issues**: Verify connections, check query performance

#### Step 5: Resolution
1. **Implement fix** based on root cause analysis
2. **Verify resolution** with monitoring
3. **Update stakeholders** on status
4. **Document incident** in tracking system

#### Step 6: Post-Incident Review
- [ ] Conduct post-mortem within 48 hours
- [ ] Document root cause and resolution
- [ ] Identify preventive measures
- [ ] Update runbook if needed

### Common Incident Scenarios

#### Scenario 1: Service Down
**Symptoms**: Health checks failing, 5xx errors
**Actions**:
```bash
# Check deployment status
gcloud run services describe web-scraping-service --platform=managed --region=us-central1

# Check recent deployments
gcloud run revisions list --service=web-scraping-service --platform=managed --region=us-central1

# If needed, rollback to previous revision
gcloud run services update-traffic web-scraping-service --platform=managed --region=us-central1 --to-revisions=PREVIOUS_REVISION --remove-traffic=latest
```

#### Scenario 2: High Error Rate
**Symptoms**: Error rate > 5%, increasing error logs
**Actions**:
```bash
# Check error logs
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR AND resource.labels.service_name=web-scraping-service' --limit=20

# Check for specific error patterns
gcloud logging read 'jsonPayload.message:"database connection failed"'

# Verify external dependencies
curl -f https://target-website.com
```

#### Scenario 3: Performance Degradation
**Symptoms**: Response times > 10 seconds, high CPU/memory
**Actions**:
```bash
# Check resource usage
gcloud monitoring metrics list --filter="resource.type=gae_instance AND metric.type=compute.googleapis.com/instance/cpu/utilization"

# Review concurrent requests
# Consider scaling up if needed
```

---

## Maintenance Procedures

### Weekly Maintenance (Every Monday 9:00 AM)

#### 1. Log Review
```bash
# Review last week's logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=web-scraping-service' --since="7d" --format="json" > weekly_logs.json

# Check for error patterns
grep -i error weekly_logs.json | wc -l
```

#### 2. Performance Analysis
- [ ] Review response time trends
- [ ] Analyze resource utilization patterns
- [ ] Check data quality trends
- [ ] Review scraper performance

#### 3. Security Review
- [ ] Check for any security alerts
- [ ] Review access logs
- [ ] Verify secret rotation status

#### 4. Backup Verification
```bash
# Verify database backups
gcloud sql backups list --instance=web-scraping-db --limit=5

# Check storage backup status
gsutil ls gs://web-scraping-data-bucket/
```

### Monthly Maintenance (First Friday 10:00 AM)

#### 1. Dependency Review
```bash
# Check for dependency updates
pip list --outdated

# Review container image vulnerabilities
gcloud artifacts docker images list-vulnerabilities $REGION-docker.pkg.dev/[PROJECT_ID]/web-scraping-repo/web-scraping-service:latest
```

#### 2. Capacity Planning
- [ ] Review storage growth trends
- [ ] Analyze database performance
- [ ] Plan for scaling needs
- [ ] Review cost optimization opportunities

#### 3. Security Audit
- [ ] Review IAM permissions
- [ ] Check for unused service accounts
- [ ] Verify encryption settings
- [ ] Review network security

#### 4. Documentation Update
- [ ] Update runbook with new procedures
- [ ] Document any changes made
- [ ] Review and update checklists

### Quarterly Maintenance

#### 1. Disaster Recovery Test
```bash
# Test database restore from backup
gcloud sql backups restore BACKUP_ID --instance=test-restore-instance

# Verify data integrity
# Test service deployment to alternate region
```

#### 2. Performance Optimization
- [ ] Review and optimize database queries
- [ ] Analyze and optimize scraping schedules
- [ ] Review and update monitoring dashboards
- [ ] Performance tuning of application

#### 3. Security Assessment
- [ ] Penetration testing (if applicable)
- [ ] Vulnerability assessment
- [ ] Security configuration review
- [ ] Incident response procedure testing

---

## Performance Monitoring

### Key Performance Indicators (KPIs)

#### Service Metrics
- **Uptime**: Target > 99.9%
- **Response Time**: Target < 3 seconds for 95% of requests
- **Error Rate**: Target < 1%
- **Throughput**: Requests per second

#### Data Quality Metrics
- **Data Freshness**: Time since last update
- **Data Completeness**: Percentage of expected data captured
- **Data Accuracy**: Validation success rate
- **Data Consistency**: Cross-source consistency

#### Infrastructure Metrics
- **CPU Utilization**: Target < 70%
- **Memory Utilization**: Target < 80%
- **Database Performance**: Query response times
- **Storage Utilization**: Growth trends

### Monitoring Commands

```bash
# Check current metrics
gcloud monitoring metrics list --filter="web_scraping"

# View time series data
gcloud monitoring time-series query 'metric.type="web_scraping_requests_total"' --interval=1h

# Check alerting policies
gcloud monitoring policies list

# View dashboards
gcloud monitoring dashboards list
```

### Performance Tuning

#### Database Optimization
```bash
# Check slow queries
gcloud sql instances describe web-scraping-db --format="value(settings.databaseFlags)"

# Review connection pool
# Optimize indexes if needed
```

#### Application Optimization
- Review scraper concurrency settings
- Optimize data processing pipelines
- Tune caching strategies
- Review rate limiting configuration

#### Infrastructure Optimization
- Adjust Cloud Run settings (CPU, memory)
- Optimize container image size
- Review network configuration
- Consider regional deployment options

---

## Security Operations

### Daily Security Tasks

#### 1. Security Monitoring
- [ ] Review security alerts in Cloud Security Command Center
- [ ] Check for unusual access patterns
- [ ] Monitor for vulnerability alerts
- [ ] Review firewall logs

#### 2. Access Management
```bash
# Check recent access
gcloud logging read 'protoPayload.methodName="google.iam.admin.serviceaccount.ListServiceAccountKeys"'

# Review active service accounts
gcloud iam service-accounts list
```

### Weekly Security Tasks

#### 1. Vulnerability Assessment
```bash
# Check container vulnerabilities
gcloud artifacts docker images list-vulnerabilities $REGION-docker.pkg.dev/[PROJECT_ID]/web-scraping-repo/web-scraping-service:latest

# Review dependency vulnerabilities
pip-audit
```

#### 2. Access Review
- [ ] Review IAM permissions
- [ ] Check for unused service accounts
- [ ] Verify secret rotation schedule
- [ ] Review audit logs

### Monthly Security Tasks

#### 1. Security Configuration Review
- [ ] Review firewall rules
- [ ] Check encryption settings
- [ ] Verify backup encryption
- [ ] Review network security

#### 2. Compliance Check
- [ ] Verify data protection compliance
- [ ] Check logging compliance
- [ ] Review access control compliance
- [ ] Document security posture

### Security Incident Response

#### Step 1: Detection
- Monitor security alerts
- Check for unusual activity
- Verify security tool alerts

#### Step 2: Containment
```bash
# Isolate affected systems if needed
# Block malicious IPs
# Disable compromised accounts
```

#### Step 3: Investigation
```bash
# Collect forensic data
# Review security logs
# Analyze attack patterns
```

#### Step 4: Recovery
- [ ] Implement security fixes
- [ ] Restore affected systems
- [ ] Update security controls
- [ ] Document lessons learned

---

## Backup and Recovery

### Backup Schedule

#### Daily Backups
- **Database**: Automated Cloud SQL backups
- **Configuration**: Git repository backups
- **Logs**: Cloud Logging retention

#### Weekly Backups
- **Data Files**: Cloud Storage snapshots
- **Container Images**: Artifact Registry backups
- **Documentation**: Repository backups

### Backup Verification

```bash
# Check database backup status
gcloud sql backups list --instance=web-scraping-db --limit=5

# Verify storage backups
gsutil ls gs://web-scraping-data-bucket/

# Check backup integrity
gcloud sql backups describe BACKUP_ID --instance=web-scraping-db
```

### Recovery Procedures

#### Database Recovery
```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID --instance=web-scraping-db

# Verify data integrity
# Update application configuration if needed
```

#### Service Recovery
```bash
# Redeploy from container registry
gcloud run deploy web-scraping-service --image=$REGION-docker.pkg.dev/[PROJECT_ID]/web-scraping-repo/web-scraping-service:latest

# Verify service health
# Test functionality
```

#### Data Recovery
```bash
# Restore from Cloud Storage
gsutil cp gs://web-scraping-data-bucket/backup/ ./restore/

# Verify data integrity
# Update database if needed
```

### Disaster Recovery Testing

#### Quarterly DR Tests
1. **Database Restore Test**: Restore from backup to test instance
2. **Service Deployment Test**: Deploy to alternate region
3. **Data Recovery Test**: Restore data files from backup
4. **Failover Test**: Test traffic redirection

---

## Scaling Operations

### When to Scale

#### Scale Up Indicators
- CPU utilization > 80% sustained
- Memory utilization > 90% sustained
- Response times > 5 seconds sustained
- Error rate > 3% sustained

#### Scale Out Indicators
- High request volume
- Long queue times
- Resource constraints
- Performance degradation

### Scaling Procedures

#### Cloud Run Scaling
```bash
# Update service configuration
gcloud run services update web-scraping-service \
    --platform=managed \
    --region=us-central1 \
    --memory=8Gi \
    --cpu=4 \
    --concurrency=100
```

#### Database Scaling
```bash
# Check current configuration
gcloud sql instances describe web-scraping-db

# Scale if needed
gcloud sql instances patch web-scraping-db --tier=db-custom-2-7680
```

#### Storage Scaling
- Monitor storage growth
- Adjust bucket lifecycle policies
- Consider multi-region storage if needed

### Cost Optimization

#### Regular Cost Review
```bash
# Check monthly costs
gcloud billing accounts list

# Analyze cost breakdown
gcloud billing budgets list

# Identify optimization opportunities
```

#### Optimization Strategies
- Right-size Cloud Run configurations
- Optimize database instance size
- Implement storage lifecycle policies
- Review and clean up unused resources

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Service Not Responding
**Symptoms**: Health checks failing, 5xx errors
**Diagnosis**:
```bash
# Check service status
gcloud run services describe web-scraping-service --platform=managed --region=us-central1

# Check recent deployments
gcloud run revisions list --service=web-scraping-service --platform=managed --region=us-central1
```
**Solution**:
- Restart service if needed
- Rollback to previous revision
- Check resource constraints

#### Issue 2: High Error Rate
**Symptoms**: Increasing error logs, failed requests
**Diagnosis**:
```bash
# Check error logs
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' --limit=20

# Check external dependencies
curl -f https://target-website.com
```
**Solution**:
- Fix configuration issues
- Update scraper logic for target changes
- Implement retry logic

#### Issue 3: Performance Degradation
**Symptoms**: Slow response times, high resource usage
**Diagnosis**:
```bash
# Check resource usage
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"

# Review concurrent requests
# Check database performance
```
**Solution**:
- Scale resources
- Optimize queries
- Review scraping schedules

#### Issue 4: Data Quality Issues
**Symptoms**: Low quality scores, missing data
**Diagnosis**:
```bash
# Check data quality metrics
curl https://web-scraping-service-[PROJECT_ID].a.run.app/api/v1/metrics/quality

# Review scraper logs
# Check target website changes
```
**Solution**:
- Update scraper logic
- Fix data validation rules
- Review data processing pipeline

### Escalation Procedures

#### When to Escalate
- Issue affects multiple components
- Root cause not identified within 30 minutes
- Issue impacts users significantly
- Security concern identified

#### Escalation Contacts
1. **Senior DevOps Engineer**: devops-lead@medellinbot.com
2. **Database Administrator**: dba-lead@medellinbot.com
3. **Security Team**: security-lead@medellinbot.com
4. **Engineering Manager**: engineering-manager@medellinbot.com

---

## Contact Information

### On-Call Schedule

#### Primary On-Call
- **Name**: [Current On-Call Engineer]
- **Phone**: +1-555-ONCALL
- **Email**: oncall@medellinbot.com
- **Rotation**: Weekly

#### Secondary On-Call
- **Name**: [Backup Engineer]
- **Phone**: +1-555-BACKUP
- **Email**: backup-oncall@medellinbot.com
- **Rotation**: Weekly

### Team Contacts

#### DevOps Team
- **Lead**: devops-lead@medellinbot.com
- **Team**: devops-team@medellinbot.com

#### Database Team
- **Lead**: dba-lead@medellinbot.com
- **Team**: database-team@medellinbot.com

#### Security Team
- **Lead**: security-lead@medellinbot.com
- **Team**: security-team@medellinbot.com

#### Engineering Management
- **Manager**: engineering-manager@medellinbot.com
- **Director**: engineering-director@medellinbot.com

### Emergency Contacts

#### Critical Issues (P1/P2)
- **PagerDuty**: https://medellinbot.pagerduty.com
- **Slack**: #alerts-critical
- **Phone**: +1-555-EMERGENCY

#### Non-Critical Issues (P3/P4)
- **Jira**: https://medellinbot.atlassian.net
- **Slack**: #devops-general
- **Email**: devops-team@medellinbot.com

### External Contacts

#### Google Cloud Support
- **Support Portal**: https://cloud.google.com/support
- **Emergency**: 1-800-GCP-0123

#### Vendor Contacts
- **Database Vendor**: [Contact Information]
- **Security Vendor**: [Contact Information]
- **Monitoring Vendor**: [Contact Information]

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-29 | DevOps Team | Initial operations runbook |

---

*This runbook should be reviewed and updated monthly. All team members should be familiar with the procedures outlined herein.*