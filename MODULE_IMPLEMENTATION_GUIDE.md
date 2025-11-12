# Module Implementation Guide

## Quick Start: Implementing High-Priority Modules

This guide provides implementation steps for the top 3 recommended modules.

---

## Module 1: Compliance Dashboard & Analytics

### Backend Implementation

**File Structure:**
```
Complytics Backend/
├── routes/
│   └── analytics.py          # New file
├── schemas/
│   └── analytics.py          # New file
└── utils/
    └── analytics_engine.py   # New file
```

**Key Endpoints to Implement:**

```python
# routes/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from schemas.users import UserInDB
from routes.auth import get_current_user
from db import database
from datetime import datetime, timedelta
from typing import List, Dict

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_compliance_dashboard(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """Get comprehensive compliance dashboard data"""
    # Aggregate data from:
    # - compliance_chat_history
    # - azure_checker results
    # - document analysis results
    # - scheduled scans
    
    dashboard_data = {
        "overall_compliance_score": calculate_overall_score(),
        "framework_scores": get_framework_scores(),
        "recent_activities": get_recent_activities(),
        "alerts": get_active_alerts(),
        "trends": get_compliance_trends()
    }
    return dashboard_data

@router.get("/scorecard")
async def get_compliance_scorecard(
    framework: str = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get compliance scorecard for specific framework or overall"""
    pass

@router.get("/trends")
async def get_compliance_trends(
    days: int = 30,
    framework: str = None,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get compliance trends over time"""
    pass
```

### Frontend Implementation

**New Component:**
```jsx
// src/components/team/ComplianceDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';

const ComplianceDashboard = () => {
  const { authToken } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/analytics/dashboard', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  };

  return (
    <div className="compliance-dashboard">
      {/* Dashboard UI with charts, metrics, etc. */}
    </div>
  );
};
```

---

## Module 2: Compliance Risk Assessment

### Backend Implementation

**File Structure:**
```
Complytics Backend/
├── routes/
│   └── risk_assessment.py    # New file
├── schemas/
│   └── risk.py               # New file
└── utils/
    └── risk_calculator.py    # New file
```

**Key Implementation:**

```python
# routes/risk_assessment.py
from fastapi import APIRouter, Depends
from schemas.users import UserInDB
from routes.auth import get_current_user
from db import database
from typing import List, Dict
from datetime import datetime

router = APIRouter(prefix="/api/risk-assessment", tags=["risk-assessment"])

@router.post("/analyze")
async def analyze_risks(
    assessment_config: dict,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """Run comprehensive risk assessment"""
    # 1. Collect compliance data
    # 2. Identify gaps
    # 3. Calculate risk scores
    # 4. Categorize risks
    # 5. Store results
    
    risks = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }
    
    # Risk calculation logic
    overall_risk_score = calculate_risk_score(risks)
    
    return {
        "risk_score": overall_risk_score,
        "risks": risks,
        "recommendations": generate_recommendations(risks)
    }

@router.get("/dashboard")
async def get_risk_dashboard(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get risk assessment dashboard"""
    pass
```

**Risk Calculation Logic:**
```python
# utils/risk_calculator.py
def calculate_risk_score(risks: Dict) -> float:
    """Calculate overall risk score (0-100)"""
    weights = {
        "critical": 1.0,
        "high": 0.7,
        "medium": 0.4,
        "low": 0.1
    }
    
    total_score = 0
    for severity, risk_list in risks.items():
        total_score += len(risk_list) * weights[severity] * 10
    
    # Normalize to 0-100
    return min(100, total_score)
```

---

## Module 3: Compliance Gap Analysis & Remediation Planner

### Backend Implementation

**File Structure:**
```
Complytics Backend/
├── routes/
│   └── gap_analysis.py        # New file
├── schemas/
│   └── gap_analysis.py        # New file
└── utils/
    └── gap_analyzer.py        # New file
```

**Key Implementation:**

```python
# routes/gap_analysis.py
from fastapi import APIRouter, Depends
from schemas.users import UserInDB
from routes.auth import get_current_user
from db import database
from typing import List

router = APIRouter(prefix="/api/gap-analysis", tags=["gap-analysis"])

@router.post("/analyze")
async def analyze_gaps(
    framework: str,
    scope: dict,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(lambda: database.db)
):
    """Identify compliance gaps for a framework"""
    # 1. Get framework requirements
    # 2. Check current compliance status
    # 3. Identify gaps
    # 4. Classify gap severity
    # 5. Generate remediation plan
    
    gaps = identify_gaps(framework, scope)
    remediation_plan = generate_remediation_plan(gaps)
    
    return {
        "framework": framework,
        "gaps": gaps,
        "remediation_plan": remediation_plan,
        "estimated_completion": estimate_completion(remediation_plan)
    }

@router.post("/remediation-plan")
async def generate_remediation_plan(
    gap_ids: List[str],
    current_user: UserInDB = Depends(get_current_user)
):
    """Generate detailed remediation plan for gaps"""
    pass

@router.get("/progress")
async def track_remediation_progress(
    plan_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Track progress of remediation plan"""
    pass
```

**Gap Analysis Logic:**
```python
# utils/gap_analyzer.py
def identify_gaps(framework: str, current_state: dict) -> List[dict]:
    """Identify gaps between framework requirements and current state"""
    # Load framework requirements
    requirements = load_framework_requirements(framework)
    
    gaps = []
    for requirement in requirements:
        if not is_requirement_met(requirement, current_state):
            gap = {
                "requirement_id": requirement["id"],
                "requirement": requirement["description"],
                "severity": calculate_severity(requirement),
                "current_state": get_current_state(requirement),
                "required_state": requirement["required_state"]
            }
            gaps.append(gap)
    
    return gaps
```

---

## Database Schema Additions

### MongoDB Collections to Add:

```python
# Risk Assessment Collection
risk_assessments = {
    "_id": ObjectId,
    "user_id": str,
    "assessment_date": datetime,
    "risk_score": float,
    "risks": {
        "critical": [risk_objects],
        "high": [risk_objects],
        "medium": [risk_objects],
        "low": [risk_objects]
    },
    "recommendations": [str],
    "status": str  # "active", "mitigated", "closed"
}

# Gap Analysis Collection
gap_analyses = {
    "_id": ObjectId,
    "user_id": str,
    "framework": str,
    "analysis_date": datetime,
    "gaps": [gap_objects],
    "remediation_plan_id": str,
    "status": str  # "pending", "in_progress", "completed"
}

# Remediation Plans Collection
remediation_plans = {
    "_id": ObjectId,
    "gap_analysis_id": str,
    "user_id": str,
    "tasks": [task_objects],
    "created_date": datetime,
    "target_completion": datetime,
    "status": str,
    "progress": float  # 0-100
}

# Audit Trail Collection
audit_trails = {
    "_id": ObjectId,
    "user_id": str,
    "action": str,
    "resource_type": str,
    "resource_id": str,
    "timestamp": datetime,
    "details": dict,
    "ip_address": str,
    "user_agent": str
}
```

---

## Integration with Existing Modules

### 1. Connect to Compliance Chat
```python
# Use existing compliance_rag functions
from compliance_rag import process_query_optimized

# In risk assessment
def assess_compliance_risks():
    # Query compliance chat for framework requirements
    query = "What are the critical GDPR requirements?"
    response = process_query_optimized(query)
    # Use response to identify risks
```

### 2. Connect to Azure Checker
```python
# Use existing Azure compliance results
from routes.azure_checker import get_latest_compliance_results

# In gap analysis
def analyze_azure_gaps():
    azure_results = get_latest_compliance_results()
    # Compare against framework requirements
```

### 3. Connect to Document Analysis
```python
# Use existing document analysis
from compliance_rag import analyze_privacy_policy

# In risk assessment
def assess_document_risks():
    doc_analysis = analyze_privacy_policy(document_text, "GDPR")
    # Extract risks from analysis
```

---

## Frontend Integration

### Add to UserDashboard.jsx

```jsx
// Add new tabs/sections
const tabs = [
  { id: 'chat', label: 'Compliance Chat', icon: FaComments },
  { id: 'azure', label: 'Azure Checker', icon: FaCloud },
  { id: 'dashboard', label: 'Dashboard', icon: FaChartLine }, // NEW
  { id: 'risk', label: 'Risk Assessment', icon: FaExclamationTriangle }, // NEW
  { id: 'gaps', label: 'Gap Analysis', icon: FaClipboardList }, // NEW
  // ... existing tabs
];
```

---

## Testing Strategy

### Unit Tests
- Risk calculation logic
- Gap identification algorithms
- Dashboard data aggregation

### Integration Tests
- API endpoint testing
- Database operations
- Module interactions

### E2E Tests
- Complete workflow testing
- User journey testing

---

## Deployment Considerations

1. **Database Migrations**: Create indexes for new collections
2. **API Versioning**: Use `/api/v1/` prefix for new endpoints
3. **Caching**: Implement Redis for dashboard data
4. **Background Jobs**: Use Celery for risk assessment calculations
5. **Monitoring**: Add logging and metrics for new modules

---

## Next Steps

1. Start with Compliance Dashboard (highest visibility)
2. Implement Risk Assessment (immediate value)
3. Add Gap Analysis (actionable insights)
4. Integrate with existing modules
5. Add frontend components
6. Test and deploy incrementally

