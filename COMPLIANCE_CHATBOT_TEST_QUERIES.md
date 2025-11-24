# Compliance Chatbot Test Queries

This document contains comprehensive test queries for the compliance chatbot, organized by category.

## 1. Basic Compliance Framework Questions

### ISO 27001
- "What are the ISO 27001 access control requirements?"
- "Explain control A.9 and what organizations need to implement for user access management."
- "What is ISO 27001 Control A.12.3.1 about?"
- "Tell me about ISO 27001 encryption requirements."
- "What does ISO 27001 say about incident management?"
- "Explain ISO 27001 Control A.8.2.3 for data encryption."
- "What are the requirements for ISO 27001 Control A.18.1.3?"

### GDPR
- "What are the GDPR data subject rights?"
- "Explain Article 17 GDPR - Right to Erasure."
- "What does GDPR Article 32 require for data security?"
- "Tell me about GDPR Article 6 - Lawful basis for processing."
- "What is GDPR Article 15 about?"
- "Explain GDPR Article 5(1)(a) - Lawful, fair, and transparent processing."
- "What are the requirements for GDPR Article 7 - Conditions for consent?"

### SOC 2
- "What are the SOC 2 Trust Services Criteria?"
- "Explain SOC 2 CC6.1 control requirements."
- "What does SOC 2 require for access controls?"
- "Tell me about SOC 2 monitoring requirements."

### HIPAA
- "What are HIPAA security rule requirements?"
- "Explain HIPAA administrative safeguards."
- "What does HIPAA require for encryption?"

### PCI DSS
- "What are PCI DSS requirements for cardholder data?"
- "Explain PCI DSS Requirement 3.4 for data encryption."
- "What does PCI DSS require for network security?"

---

## 2. Scenario-Based Questions (Compliance Officer Perspective)

### Scenario 1: New Organization Setup
- "I'm setting up a new SaaS company that handles customer data. What compliance frameworks should I implement first, and what are the key requirements for AWS cloud infrastructure?"
- "We're a healthcare startup processing patient data. What compliance requirements do we need to meet, and how should we implement them in Azure?"

### Scenario 2: Access Control Implementation
- "Our organization needs to implement user access management for ISO 27001. We're using AWS IAM. What specific controls do we need to implement and how?"
- "We have 500 employees and need to implement role-based access control for GDPR compliance. What are the requirements and best practices?"

### Scenario 3: Data Processing & Privacy
- "We collect customer email addresses and purchase history. What GDPR requirements apply, and how should we handle data subject access requests?"
- "Our application processes payment card data. What PCI DSS controls do we need to implement, and how do they map to ISO 27001?"

### Scenario 4: Incident Response
- "We had a data breach affecting 10,000 users. What are our GDPR notification requirements and timeline?"
- "What incident response procedures are required by ISO 27001 Control A.16.1.1?"

### Scenario 5: Third-Party Risk
- "We're using a third-party cloud provider (AWS) for storing customer data. What compliance requirements apply to vendor management?"
- "Our organization outsources customer support. What GDPR requirements do we need to ensure in our vendor contracts?"

---

## 3. Follow-Up Questions (Context Retention Testing)

### Test Sequence 1: ISO 27001 Access Control
1. "What are the ISO 27001 access control requirements?"
2. "What about user access provisioning? What controls apply?"
3. "How do I implement this in AWS?"
4. "What about access reviews? How often should they be done?"

### Test Sequence 2: GDPR Data Processing
1. "What GDPR requirements apply to processing customer email addresses?"
2. "What if the customer wants to delete their data?"
3. "How long can we keep the data?"
4. "What about data we've shared with third parties?"

### Test Sequence 3: Multi-Framework
1. "What encryption requirements does ISO 27001 have?"
2. "How does this compare to GDPR Article 32?"
3. "What about PCI DSS encryption requirements?"
4. "Can you create a unified encryption policy that satisfies all three?"

### Test Sequence 4: Implementation Guidance
1. "What are the key ISO 27001 controls for cloud security?"
2. "How do I implement these in Azure?"
3. "What specific Azure services should I use?"
4. "What about monitoring and logging?"

---

## 4. Technical Implementation Questions

### AWS-Specific
- "How do I implement ISO 27001 Control A.9.2.1 (User access management) using AWS IAM?"
- "What AWS services help meet GDPR Article 32 encryption requirements?"
- "How do I use AWS KMS to satisfy PCI DSS Requirement 3.4?"
- "What AWS CloudTrail configurations are needed for SOC 2 CC7.2?"

### Azure-Specific
- "How do I implement ISO 27001 access controls in Azure AD?"
- "What Azure services help with GDPR data subject rights?"
- "How do I configure Azure Key Vault for compliance?"

### GCP-Specific
- "How do I implement ISO 27001 controls in Google Cloud Platform?"
- "What GCP services help with GDPR compliance?"

### Multi-Cloud
- "We use both AWS and Azure. How do we maintain consistent compliance across both platforms?"

---

## 5. Control Mapping & Cross-Reference Questions

- "Map ISO 27001 Control A.8.2.3 to GDPR Article 32."
- "How do SOC 2 CC6.1 and ISO 27001 A.9.2.1 relate?"
- "What PCI DSS requirements overlap with ISO 27001 encryption controls?"
- "Create a control mapping table showing ISO 27001, GDPR, and SOC 2 requirements for access control."

---

## 6. Edge Cases & Stress Tests

### Empty/Minimal Queries
- ""
- "?"
- "help"
- "compliance"
- "what"

### Very Long Queries
- "I need to understand all the requirements for implementing a comprehensive information security management system that complies with ISO 27001, GDPR, SOC 2 Type II, PCI DSS Level 1, and HIPAA for a healthcare SaaS platform that processes payment card data, stores patient health information, and operates across multiple cloud providers including AWS, Azure, and GCP, with offices in the EU, US, and Asia, serving customers globally, and we need to understand access controls, encryption requirements, incident response procedures, vendor management, data retention policies, audit logging, monitoring, and all the technical implementation details for each framework and how they map to each other and what the common requirements are and what's unique to each framework and how to implement them in our specific cloud infrastructure setup."

### Ambiguous Queries
- "What about that thing?"
- "Tell me more."
- "How do I do it?"
- "What's required?"

### Typos & Misspellings
- "What are the ISO 2701 access control requirments?"
- "Explain GDPR Artical 17."
- "What does SOC2 require?"
- "Tell me about HIPPA requirements."

### Mixed Languages (if applicable)
- "¿Qué son los requisitos de GDPR?" (Spanish)
- "Was sind die ISO 27001 Anforderungen?" (German)

### Non-Compliance Questions
- "What's the weather today?"
- "How do I cook pasta?"
- "Tell me a joke."
- "What is artificial intelligence?"

### Questions About Non-Existent Controls
- "What is ISO 27001 Control A.99.9.9?"
- "Explain GDPR Article 999."
- "What does SOC 2 CC99.99 require?"

### Questions with Conflicting Information
- "ISO 27001 says encryption is optional, but GDPR requires it. Which is correct?"

### Questions About Future/Outdated Standards
- "What are the requirements for ISO 27001:2025?"
- "Tell me about GDPR 2.0."

---

## 7. Evidence & Citation Testing

### Questions That Should Cite Documents
- "What does the ISO 27001 standard say about access control?"
- "Quote the exact GDPR Article 17 text."
- "What is the exact wording of ISO 27001 Control A.9.2.1?"

### Questions That Should Use LLM Knowledge
- "What are best practices for implementing ISO 27001 in a startup?"
- "How do I prepare for an ISO 27001 audit?"
- "What are common mistakes organizations make with GDPR compliance?"

### Hybrid Questions (Some in docs, some not)
- "What are the ISO 27001 access control requirements, and how do I implement them in AWS?" (requirements in docs, AWS implementation not)

---

## 8. Multi-Framework Comparison Questions

- "Compare ISO 27001 and SOC 2 access control requirements."
- "What are the differences between GDPR and CCPA data subject rights?"
- "How do ISO 27001, NIST, and SOC 2 compare for cloud security?"
- "What compliance frameworks are most relevant for a fintech company?"

---

## 9. Industry-Specific Questions

### Healthcare
- "What compliance requirements apply to a telemedicine platform?"
- "How do HIPAA and GDPR requirements differ for healthcare data?"

### Financial Services
- "What compliance frameworks are required for a fintech startup?"
- "How do PCI DSS and ISO 27001 work together for payment processing?"

### E-commerce
- "What compliance requirements apply to an e-commerce platform processing payments?"
- "How do GDPR and PCI DSS requirements overlap for online stores?"

---

## 10. Process & Procedure Questions

- "What is the process for conducting an ISO 27001 risk assessment?"
- "How do I create a GDPR data processing impact assessment?"
- "What are the steps for responding to a GDPR data subject access request?"
- "How do I conduct an access review for ISO 27001 compliance?"

---

## 11. Compliance Program Questions

- "How do I build a compliance program from scratch?"
- "What's the order of implementing compliance frameworks?"
- "How long does it take to achieve ISO 27001 certification?"
- "What resources do I need for GDPR compliance?"

---

## 12. Testing Context Retention

### Conversation Flow Test
1. "I'm a compliance officer at a healthcare startup."
2. "We process patient data and payment information."
3. "What compliance frameworks apply?"
4. "Focus on the encryption requirements."
5. "How do I implement this in AWS?"
6. "What about access controls?"
7. "Map these to ISO 27001 controls."

### Memory Test
1. "My organization uses AWS and has 200 employees."
2. "We process customer data including emails and purchase history."
3. "What compliance requirements apply?"
4. [Wait 5 minutes or ask unrelated question]
5. "Going back to my organization, what about data retention?"

---

## 13. Table Generation Testing

- "Create a table mapping ISO 27001 controls to AWS services."
- "Show me a table of GDPR articles and their requirements."
- "Generate a compliance control mapping table for ISO 27001, GDPR, and SOC 2."

---

## 14. Error Handling & Recovery

### Test Rate Limiting
- Send 50 rapid queries in succession
- Test if fallback keys are used correctly

### Test Empty Responses
- "What is ISO 27001 Control A.9.2.1?" (if not in docs, should still answer)

### Test Partial Information
- "What are the ISO 27001 requirements?" (very broad, should provide comprehensive answer)

---

## 15. Special Characters & Formatting

- "What is ISO 27001 Control A.9.2.1?"
- "Explain GDPR Article 17 (Right to Erasure)."
- "What does SOC 2 CC6.1 require?"
- "Tell me about ISO/IEC 27001:2022."

---

## Testing Checklist

When testing, verify:
- [ ] Evidence from documents is highlighted in green
- [ ] Control IDs and article numbers are highlighted in green
- [ ] Tables are rendered as proper HTML tables (not markdown)
- [ ] Follow-up questions maintain context
- [ ] LLM knowledge supplements document information
- [ ] Answers are complete and not truncated
- [ ] Rate limiting triggers fallback to next API key
- [ ] Edge cases are handled gracefully
- [ ] Multi-framework questions are answered comprehensively
- [ ] Technical implementation questions provide actionable guidance
- [ ] Scenario-based questions are answered contextually

---

## Recommended Test Sequence

1. **Basic Functionality**: Start with simple ISO 27001 and GDPR questions
2. **Evidence Citation**: Test that document evidence is highlighted
3. **Context Retention**: Use follow-up question sequences
4. **Scenario Testing**: Test real-world compliance officer scenarios
5. **Edge Cases**: Test empty queries, typos, non-compliance questions
6. **Multi-Framework**: Test cross-framework mapping and comparison
7. **Technical Implementation**: Test AWS/Azure/GCP-specific questions
8. **Stress Testing**: Test rate limits and error recovery
9. **Table Generation**: Verify HTML table rendering
10. **End-to-End**: Complete conversation flows with multiple topics

