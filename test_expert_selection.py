#!/usr/bin/env python3
"""
Quick test script for expert selection system.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Complytics Backend'))

from compliance_rag import select_relevant_experts, detect_query_type

def test_expert_selection():
    """Test expert selection for various queries."""
    
    test_queries = [
        "PCI DSS for healthcare payment processing",
        "HIPAA compliance for patient data storage", 
        "Azure Active Directory security configuration",
        "GDPR cross-border data transfers",
        "SOX financial reporting requirements",
        "Business continuity planning procedures",
        "FERPA compliance for student records"
    ]
    
    print("Expert Selection Test Results")
    print("=" * 50)
    
    for query in test_queries:
        try:
            experts = select_relevant_experts(query)
            query_type, detected_experts = detect_query_type(query)
            
            print(f"\nQuery: {query}")
            print(f"  Selected Experts: {experts}")
            print(f"  Query Type: {query_type}")
            print(f"  Detected Experts: {detected_experts}")
            
        except Exception as e:
            print(f"\nQuery: {query}")
            print(f"  ERROR: {str(e)}")

if __name__ == "__main__":
    test_expert_selection() 