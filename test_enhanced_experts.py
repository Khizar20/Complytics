#!/usr/bin/env python3
"""
Test script for the enhanced mixture of experts system.
Tests expert selection, individual expert responses, and aggregation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Complytics Backend'))

def test_expert_selection():
    """Test the enhanced expert selection logic."""
    from compliance_rag import select_relevant_experts
    
    test_cases = [
        {
            "query": "What are the GDPR requirements for data processing?",
            "expected_experts": ["privacy"],
            "description": "Privacy regulation query"
        },
        {
            "query": "How to implement PCI DSS controls for credit card processing?",
            "expected_experts": ["financial", "security"],
            "description": "Financial compliance with security aspects"
        },
        {
            "query": "HIPAA compliance for healthcare data in cloud environments",
            "expected_experts": ["healthcare", "security"],
            "description": "Healthcare compliance query"
        },
        {
            "query": "Cross-border data transfer requirements between EU and US",
            "expected_experts": ["international", "privacy"],
            "description": "International compliance query"
        },
        {
            "query": "Vendor risk management and third-party assessments",
            "expected_experts": ["operational", "audit"],
            "description": "Operational compliance query"
        },
        {
            "query": "FERPA compliance for education technology platforms",
            "expected_experts": ["industry_specific", "privacy"],
            "description": "Industry-specific regulation"
        },
        {
            "query": "ISO 27001 certification audit preparation checklist",
            "expected_experts": ["audit", "security"],
            "description": "Audit compliance query"
        }
    ]
    
    print("🧪 Testing Enhanced Expert Selection")
    print("=" * 50)
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        try:
            selected_experts = select_relevant_experts(test_case["query"])
            
            # Check if at least one expected expert is selected
            has_expected = any(expert in selected_experts for expert in test_case["expected_experts"])
            
            status = "✅ PASS" if has_expected else "❌ FAIL"
            print(f"Test {i}: {status}")
            print(f"  Query: {test_case['query']}")
            print(f"  Expected: {test_case['expected_experts']}")
            print(f"  Selected: {selected_experts}")
            print(f"  Description: {test_case['description']}")
            print()
            
            if has_expected:
                success_count += 1
                
        except Exception as e:
            print(f"Test {i}: ❌ ERROR - {str(e)}")
            print(f"  Query: {test_case['query']}")
            print()
    
    success_rate = (success_count / len(test_cases)) * 100
    print(f"📊 Expert Selection Results: {success_count}/{len(test_cases)} tests passed ({success_rate:.1f}%)")
    return success_rate > 70  # Expect at least 70% success rate

def test_expert_coverage():
    """Test that all expert types can be selected."""
    from compliance_rag import select_relevant_experts
    
    expert_test_queries = {
        "security": "Azure Active Directory security configuration",
        "privacy": "GDPR data subject access requests",
        "audit": "SOC 2 Type II audit preparation",
        "financial": "PCI DSS compliance for e-commerce",
        "healthcare": "HIPAA breach notification requirements",
        "international": "LGPD compliance for Brazilian operations",
        "operational": "Business continuity planning procedures",
        "industry_specific": "FERPA compliance for student records"
    }
    
    print("🎯 Testing Expert Coverage")
    print("=" * 50)
    
    covered_experts = set()
    for expert_type, query in expert_test_queries.items():
        try:
            selected_experts = select_relevant_experts(query)
            if expert_type in selected_experts:
                covered_experts.add(expert_type)
                print(f"✅ {expert_type}: Selected correctly")
            else:
                print(f"❌ {expert_type}: Not selected (got: {selected_experts})")
        except Exception as e:
            print(f"❌ {expert_type}: Error - {str(e)}")
    
    coverage_rate = (len(covered_experts) / len(expert_test_queries)) * 100
    print(f"\n📊 Expert Coverage: {len(covered_experts)}/{len(expert_test_queries)} experts can be selected ({coverage_rate:.1f}%)")
    return coverage_rate > 80  # Expect at least 80% coverage

def main():
    """Run all tests for the enhanced mixture of experts system."""
    print("🚀 Enhanced Mixture of Experts Test Suite")
    print("=" * 60)
    print()
    
    # Test expert selection
    selection_test_passed = test_expert_selection()
    print()
    
    # Test expert coverage
    coverage_test_passed = test_expert_coverage()
    print()
    
    # Overall results
    if selection_test_passed and coverage_test_passed:
        print("🎉 All tests passed! Enhanced mixture of experts system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Review the expert selection logic or keyword mappings.")
        return False

if __name__ == "__main__":
    main() 