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
        },
        {
            "query": "What is Azure Active Directory?",
            "expected_experts": ["security"],
            "description": "Azure/identity management query"
        }
    ]
    
    print("Testing Enhanced Expert Selection")
    print("=" * 50)
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        try:
            selected_experts = select_relevant_experts(test_case["query"])
            
            # Check if at least one expected expert is selected
            has_expected = any(expert in selected_experts for expert in test_case["expected_experts"])
            
            status = "PASS" if has_expected else "FAIL"
            print(f"Test {i}: {status}")
            print(f"  Query: {test_case['query']}")
            print(f"  Expected: {test_case['expected_experts']}")
            print(f"  Selected: {selected_experts}")
            print(f"  Description: {test_case['description']}")
            print()
            
            if has_expected:
                success_count += 1
                
        except Exception as e:
            print(f"Test {i}: ERROR - {str(e)}")
            print(f"  Query: {test_case['query']}")
            print()
    
    success_rate = (success_count / len(test_cases)) * 100
    print(f"Expert Selection Results: {success_count}/{len(test_cases)} tests passed ({success_rate:.1f}%)")
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
    
    print("Testing Expert Coverage")
    print("=" * 50)
    
    covered_experts = set()
    for expert_type, query in expert_test_queries.items():
        try:
            selected_experts = select_relevant_experts(query)
            if expert_type in selected_experts:
                covered_experts.add(expert_type)
                print(f"PASS {expert_type}: Selected correctly")
            else:
                print(f"FAIL {expert_type}: Not selected (got: {selected_experts})")
        except Exception as e:
            print(f"ERROR {expert_type}: {str(e)}")
    
    coverage_rate = (len(covered_experts) / len(expert_test_queries)) * 100
    print(f"\nExpert Coverage: {len(covered_experts)}/{len(expert_test_queries)} experts can be selected ({coverage_rate:.1f}%)")
    return coverage_rate > 80  # Expect at least 80% coverage

def test_compliance_classification():
    """Test the intelligent compliance classification system."""
    from compliance_rag import is_compliance_related
    
    test_cases = [
        # Should be classified as compliance-related
        {"query": "What is Azure Active Directory?", "expected": True, "description": "Identity management question"},
        {"query": "GDPR requirements for data processing", "expected": True, "description": "Privacy regulation"},
        {"query": "How to implement ISO 27001 controls", "expected": True, "description": "Security framework"},
        {"query": "PCI DSS compliance checklist", "expected": True, "description": "Payment security"},
        {"query": "Business continuity planning", "expected": True, "description": "Operational compliance"},
        
        # Should NOT be classified as compliance-related
        {"query": "What's the weather today?", "expected": False, "description": "Weather question"},
        {"query": "How to cook pasta?", "expected": False, "description": "Cooking question"},
        {"query": "Latest movie recommendations", "expected": False, "description": "Entertainment question"},
        {"query": "Football scores", "expected": False, "description": "Sports question"},
        {"query": "Personal health advice", "expected": False, "description": "Medical advice"},
    ]
    
    print("Testing Compliance Classification")
    print("=" * 50)
    
    correct_count = 0
    for i, test_case in enumerate(test_cases, 1):
        try:
            is_compliance, reason = is_compliance_related(test_case["query"])
            is_correct = is_compliance == test_case["expected"]
            
            status = "PASS" if is_correct else "FAIL"
            print(f"Test {i}: {status}")
            print(f"  Query: {test_case['query']}")
            print(f"  Expected: {test_case['expected']}")
            print(f"  Classified: {is_compliance}")
            print(f"  Reason: {reason}")
            print(f"  Description: {test_case['description']}")
            print()
            
            if is_correct:
                correct_count += 1
                
        except Exception as e:
            print(f"Test {i}: ERROR - {str(e)}")
            print(f"  Query: {test_case['query']}")
            print()
    
    accuracy = (correct_count / len(test_cases)) * 100
    print(f"Classification Accuracy: {correct_count}/{len(test_cases)} tests correct ({accuracy:.1f}%)")
    return accuracy > 80  # Expect at least 80% accuracy

def main():
    """Run all tests for the enhanced mixture of experts system."""
    print("Enhanced Mixture of Experts Test Suite")
    print("=" * 60)
    print()
    
    # Test expert selection
    print("1. Testing Expert Selection Logic...")
    selection_test_passed = test_expert_selection()
    print()
    
    # Test expert coverage
    print("2. Testing Expert Coverage...")
    coverage_test_passed = test_expert_coverage()
    print()
    
    # Test compliance classification
    print("3. Testing Compliance Classification...")
    classification_test_passed = test_compliance_classification()
    print()
    
    # Overall results
    all_passed = selection_test_passed and coverage_test_passed and classification_test_passed
    if all_passed:
        print("SUCCESS: All tests passed! Enhanced mixture of experts system is working correctly.")
        return True
    else:
        print("WARNING: Some tests failed. Review the system logic.")
        if not selection_test_passed:
            print("  - Expert selection needs improvement")
        if not coverage_test_passed:
            print("  - Expert coverage needs improvement")
        if not classification_test_passed:
            print("  - Compliance classification needs improvement")
        return False

if __name__ == "__main__":
    main() 