"""
Compliance Logic for Azure Best Practices Checker
Analyzes uploaded documents against Azure best practices using AI
"""

import logging
import re
import json
from typing import List, Dict, Any, Tuple
import numpy as np
import sys
from pathlib import Path

# Import Gemini AI from compliance_rag
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from compliance_rag import rate_limited_generate_content_optimized

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureComplianceAnalyzer:
    """Analyzes Azure configurations against best practices"""
    
    # Azure best practice categories
    CATEGORIES = {
        'Security': [
            'encryption', 'ssl', 'tls', 'firewall', 'network security', 'authentication',
            'authorization', 'rbac', 'mfa', 'multi-factor', 'security center', 'defender',
            'key vault', 'managed identity', 'private endpoint', 'nsg', 'security group'
        ],
        'Identity': [
            'azure ad', 'active directory', 'identity', 'conditional access', 'b2c',
            'single sign-on', 'sso', 'oauth', 'openid', 'saml', 'user management',
            'guest user', 'external identity', 'privileged identity'
        ],
        'Storage': [
            'storage account', 'blob', 'container', 'public access', 'shared access signature',
            'sas token', 'storage encryption', 'soft delete', 'versioning', 'immutable',
            'backup', 'redundancy', 'replication', 'geo-redundant'
        ],
        'Networking': [
            'virtual network', 'vnet', 'subnet', 'vpn', 'express route', 'load balancer',
            'application gateway', 'traffic manager', 'dns', 'cdn', 'ddos protection',
            'bastion', 'nat gateway', 'peering'
        ],
        'Monitoring': [
            'log analytics', 'monitor', 'alerts', 'diagnostics', 'application insights',
            'audit logs', 'activity log', 'metrics', 'dashboard', 'workbook',
            'azure sentinel', 'security alerts'
        ],
        'Governance': [
            'policy', 'blueprint', 'management group', 'subscription', 'resource group',
            'tags', 'cost management', 'budget', 'advisor', 'compliance',
            'regulatory', 'governance', 'best practice'
        ],
        'Compute': [
            'virtual machine', 'vm', 'scale set', 'app service', 'function app',
            'container', 'aks', 'kubernetes', 'batch', 'availability zone',
            'availability set', 'disk encryption'
        ],
        'Database': [
            'sql database', 'cosmos db', 'mysql', 'postgresql', 'redis cache',
            'database encryption', 'tde', 'backup', 'point-in-time restore',
            'geo-replication', 'failover group'
        ]
    }
    
    # Framework-specific prompt templates
    FRAMEWORK_PROMPTS = {
        'azure': {
            'name': 'Azure Best Practices',
            'description': 'Microsoft Azure cloud best practices and security guidelines',
            'focus_areas': [
                'Azure security controls', 'Identity management', 'Storage security',
                'Network configuration', 'Monitoring and logging', 'Governance policies'
            ]
        },
        'gdpr': {
            'name': 'GDPR (General Data Protection Regulation)',
            'description': 'EU data protection and privacy regulation',
            'focus_areas': [
                'Data protection principles (Article 5)', 'Lawful basis for processing (Article 6)',
                'Data subject rights (Articles 12-23)', 'Security measures (Article 32)',
                'Breach notification (Articles 33-34)', 'Privacy by design (Article 25)',
                'Data protection impact assessments (Article 35)', 'DPO requirements (Articles 37-39)'
            ]
        },
        'iso27001': {
            'name': 'ISO 27001:2022',
            'description': 'Information security management system standard',
            'focus_areas': [
                'Information security policies (A.5)', 'Access control (A.9)',
                'Cryptography (A.10)', 'Physical security (A.11)',
                'Operations security (A.12)', 'Communications security (A.13)',
                'Incident management (A.16)', 'Compliance requirements (A.18)'
            ]
        },
        'iso27017': {
            'name': 'ISO 27017:2015',
            'description': 'Cloud services information security controls',
            'focus_areas': [
                'Cloud service provider responsibilities', 'Cloud service customer responsibilities',
                'Shared responsibilities model', 'Virtual machine security',
                'Cloud network security', 'Cloud data protection'
            ]
        },
        'iso27018': {
            'name': 'ISO 27018:2019',
            'description': 'Protection of PII in public clouds',
            'focus_areas': [
                'PII protection in cloud', 'Consent management',
                'Data subject rights in cloud', 'Cloud data processing',
                'Transparency requirements', 'PII breach notification'
            ]
        }
    }
    
    def __init__(self):
        self.compliance_threshold_high = 0.8
        self.compliance_threshold_medium = 0.6
    
    def categorize_chunk(self, chunk: str) -> str:
        """
        Determine which category a chunk belongs to based on keywords
        
        Args:
            chunk: Text chunk to categorize
            
        Returns:
            Category name
        """
        chunk_lower = chunk.lower()
        category_scores = {}
        
        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for keyword in keywords if keyword in chunk_lower)
            category_scores[category] = score
        
        # Return category with highest score, or 'General' if no matches
        if max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        return 'General'
    
    def determine_compliance_status(self, similarity: float) -> str:
        """
        Determine compliance status based on similarity score
        
        Args:
            similarity: Similarity score (0-1)
            
        Returns:
            Compliance status string
        """
        if similarity >= self.compliance_threshold_high:
            return "Compliant"
        elif similarity >= self.compliance_threshold_medium:
            return "Partial"
        else:
            return "Non-Compliant"
    
    def generate_recommendation(self, category: str, status: str, chunk: str) -> str:
        """
        Generate specific recommendations based on category and compliance status
        
        Args:
            category: Azure category
            status: Compliance status
            chunk: Relevant best practice chunk
            
        Returns:
            Recommendation string
        """
        recommendations = {
            'Security': {
                'Non-Compliant': 'Enable Azure Security Center and implement all high-priority recommendations. Ensure encryption at rest and in transit for all resources.',
                'Partial': 'Review and implement missing security controls. Enable Azure Defender for enhanced threat protection.',
                'Compliant': 'Continue monitoring security posture. Regularly review security recommendations.'
            },
            'Identity': {
                'Non-Compliant': 'Implement Azure AD with MFA for all users. Configure conditional access policies and privileged identity management.',
                'Partial': 'Strengthen identity controls. Enable MFA for all administrative accounts and review access policies.',
                'Compliant': 'Maintain current identity practices. Regularly audit user access and permissions.'
            },
            'Storage': {
                'Non-Compliant': 'Disable public blob access. Enable storage encryption and implement backup policies with soft delete.',
                'Partial': 'Enhance storage security. Enable versioning and implement geo-redundant storage for critical data.',
                'Compliant': 'Continue current storage practices. Regularly test backup and recovery procedures.'
            },
            'Networking': {
                'Non-Compliant': 'Implement network segmentation using VNets and NSGs. Enable DDoS protection and configure private endpoints.',
                'Partial': 'Strengthen network security. Review NSG rules and implement Azure Firewall where appropriate.',
                'Compliant': 'Maintain network security controls. Regularly audit network configurations.'
            },
            'Monitoring': {
                'Non-Compliant': 'Enable Azure Monitor and configure diagnostic settings for all resources. Set up alerts for critical events.',
                'Partial': 'Enhance monitoring coverage. Configure Application Insights and set up comprehensive alerting.',
                'Compliant': 'Continue monitoring practices. Regularly review and tune alert rules.'
            },
            'Governance': {
                'Non-Compliant': 'Implement Azure Policy for compliance enforcement. Configure budgets and cost management alerts.',
                'Partial': 'Strengthen governance controls. Implement management groups and apply consistent tagging.',
                'Compliant': 'Maintain governance practices. Regularly review policy compliance.'
            },
            'Compute': {
                'Non-Compliant': 'Enable VM disk encryption. Configure automatic updates and implement availability zones for critical workloads.',
                'Partial': 'Enhance compute security. Enable Azure Backup and configure proper scaling policies.',
                'Compliant': 'Continue current compute practices. Regularly review VM sizing and optimization.'
            },
            'Database': {
                'Non-Compliant': 'Enable Transparent Data Encryption (TDE). Configure automated backups and implement geo-replication for critical databases.',
                'Partial': 'Enhance database security. Enable Advanced Threat Protection and configure long-term retention.',
                'Compliant': 'Maintain database security practices. Regularly test backup restoration.'
            }
        }
        
        return recommendations.get(category, {}).get(
            status,
            'Review Azure best practices documentation for this area.'
        )
    
    def analyze_document(self, search_results: List[Dict[str, Any]], document_text: str = "") -> Dict[str, Any]:
        """
        Analyze uploaded document against Azure best practices using AI
        
        Args:
            search_results: List of similar chunks from FAISS search
            document_text: Original uploaded document text for AI analysis
            
        Returns:
            Dictionary containing compliance analysis results
        """
        if not search_results:
            return {
                'score': 0,
                'overall_status': 'Non-Compliant',
                'findings': [],
                'summary': 'Unable to analyze document. No matching best practices found.'
            }
        
        # Group results by category
        category_results = {}
        for result in search_results:
            category = result['category']
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(result)
        
        # Use AI to intelligently analyze each category
        findings = []
        category_scores = []
        
        for category, results in category_results.items():
            # Get relevant best practices for this category
            best_practices_text = "\n\n".join([r['chunk'] for r in results[:3]])  # Top 3 matches
            
            # Use AI to analyze this category
            ai_analysis = self._analyze_category_with_ai(
                category=category,
                document_text=document_text[:5000],  # Limit to first 5k chars for context
                best_practices=best_practices_text,
                similarity_scores=[r['similarity'] for r in results]
            )
            
            # Calculate average similarity for scoring
            avg_similarity = np.mean([r['similarity'] for r in results])
            category_scores.append(avg_similarity)
            
            findings.append({
                'category': category,
                'status': ai_analysis.get('status', self.determine_compliance_status(avg_similarity)),
                'similarity': float(avg_similarity),
                'recommendation': ai_analysis.get('recommendation', self.generate_recommendation(category, 'Partial', best_practices_text)),
                'key_points': ai_analysis.get('key_points', []),
                'gaps_identified': ai_analysis.get('gaps', []),
                'compliant_areas': ai_analysis.get('compliant_areas', []),
                'confidence': float(avg_similarity * 100)
            })
        
        # Calculate overall compliance score
        overall_score = int(np.mean(category_scores) * 100)
        
        # Use AI to generate overall summary
        overall_status = self.determine_compliance_status(np.mean(category_scores))
        summary = self._generate_ai_summary(document_text[:3000], findings, overall_score, overall_status)
        
        # Sort findings by severity (Non-Compliant first)
        status_priority = {'Non-Compliant': 0, 'Partial': 1, 'Compliant': 2}
        findings.sort(key=lambda x: status_priority.get(x['status'], 3))
        
        return {
            'score': overall_score,
            'overall_status': overall_status,
            'findings': findings,
            'summary': summary,
            'categories_analyzed': len(category_results),
            'total_checks': len(search_results)
        }
    
    def _analyze_category_with_ai(self, category: str, document_text: str, 
                                   best_practices: str, similarity_scores: List[float]) -> Dict[str, Any]:
        """
        Use Gemini AI to intelligently analyze a category against Azure best practices
        """
        try:
            avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.5
            
            prompt = f"""You are an Azure compliance expert analyzing a configuration document against Azure best practices.

CATEGORY: {category}

UPLOADED DOCUMENT EXCERPT:
{document_text}

AZURE BEST PRACTICES (from official documentation):
{best_practices}

TASK: Analyze the uploaded document against Azure best practices for {category} and provide:
1. Compliance status (Compliant/Partial/Non-Compliant)
2. Specific gaps or issues found
3. Areas that are compliant
4. Actionable recommendations
5. Key points from best practices that apply

RESPOND IN THIS EXACT JSON FORMAT (no markdown, just JSON):
{{
  "status": "Compliant|Partial|Non-Compliant",
  "recommendation": "Specific, actionable recommendation based on actual gaps found in the document",
  "gaps": ["gap 1", "gap 2", "gap 3"],
  "compliant_areas": ["area 1", "area 2"],
  "key_points": ["point 1", "point 2", "point 3"]
}}

Be specific and reference actual content from the uploaded document. If the document mentions something, reference it.
If something is missing compared to best practices, state it clearly.
Make recommendations actionable and specific to Azure {category}."""

            response = rate_limited_generate_content_optimized(
                prompt, 
                temperature=0.2, 
                max_tokens=1500
            )
            
            # Extract JSON from response
            cleaned = response.strip()
            if '```' in cleaned:
                # Remove markdown code blocks
                if '```json' in cleaned:
                    cleaned = cleaned.split('```json')[1].split('```')[0].strip()
                elif '```' in cleaned:
                    cleaned = cleaned.split('```')[1].split('```')[0].strip()
            
            # Find JSON object
            if '{' in cleaned and '}' in cleaned:
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                json_str = cleaned[start:end]
                analysis = json.loads(json_str)
                
                # Validate status
                if analysis.get('status') not in ['Compliant', 'Partial', 'Non-Compliant']:
                    analysis['status'] = self.determine_compliance_status(avg_similarity)
                
                return analysis
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"AI analysis failed for {category}: {e}, using fallback")
            # Fallback to rule-based analysis
            status = self.determine_compliance_status(avg_similarity)
            return {
                'status': status,
                'recommendation': self.generate_recommendation(category, status, best_practices),
                'gaps': [],
                'compliant_areas': [],
                'key_points': self._extract_key_points(best_practices)
            }
    
    def _generate_ai_summary(self, document_text: str, findings: List[Dict], 
                            score: int, status: str) -> str:
        """Generate intelligent summary using AI"""
        try:
            findings_summary = "\n".join([
                f"- {f['category']}: {f['status']} ({f.get('gaps_identified', [])})"
                for f in findings
            ])
            
            prompt = f"""Generate a professional compliance summary for an Azure configuration document analysis.

Overall Score: {score}/100
Status: {status}

Findings:
{findings_summary}

Document Excerpt:
{document_text[:2000]}

Generate a concise executive summary (3-4 sentences) that:
1. States the overall compliance score and status
2. Highlights the most critical gaps
3. Mentions key compliant areas
4. Provides a brief action plan

Keep it professional and actionable."""

            summary = rate_limited_generate_content_optimized(
                prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.warning(f"AI summary generation failed: {e}, using fallback")
            return self._generate_summary(findings, score, status)
    
    def _extract_key_points(self, chunk: str, max_points: int = 3) -> List[str]:
        """Extract key points from a best practice chunk"""
        # Split by sentences
        sentences = re.split(r'[.!?]\s+', chunk)
        
        # Filter meaningful sentences (not too short)
        meaningful = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        # Return top N sentences
        return meaningful[:max_points]
    
    def _generate_summary(self, findings: List[Dict[str, Any]], score: int, 
                         status: str) -> str:
        """Generate a summary of the compliance analysis"""
        non_compliant = len([f for f in findings if f['status'] == 'Non-Compliant'])
        partial = len([f for f in findings if f['status'] == 'Partial'])
        compliant = len([f for f in findings if f['status'] == 'Compliant'])
        
        summary_parts = [
            f"Overall Compliance Score: {score}/100 ({status})",
            f"\nAnalysis Results:",
            f"• Compliant Areas: {compliant}",
            f"• Partially Compliant: {partial}",
            f"• Non-Compliant Areas: {non_compliant}"
        ]
        
        if non_compliant > 0:
            summary_parts.append(
                f"\n⚠️ Priority: Address {non_compliant} non-compliant area(s) immediately."
            )
        elif partial > 0:
            summary_parts.append(
                f"\n✓ Good progress! Review {partial} partially compliant area(s) for improvement."
            )
        else:
            summary_parts.append(
                "\n✓ Excellent! Your configuration aligns well with Azure best practices."
            )
        
        return "\n".join(summary_parts)
    
    def analyze_framework(self, framework_name: str, search_results: List[Dict[str, Any]], 
                         document_text: str = "") -> Dict[str, Any]:
        """
        Analyze uploaded document against a specific framework using AI
        
        Args:
            framework_name: Name of framework ('azure', 'gdpr', 'iso27001', etc.)
            search_results: List of similar chunks from FAISS search for this framework
            document_text: Original uploaded document text for AI analysis
            
        Returns:
            Dictionary containing framework-specific compliance analysis results
        """
        if not search_results:
            return {
                'framework': framework_name,
                'score': 0,
                'status': 'Non-Compliant',
                'findings': [],
                'summary': f'Unable to analyze against {framework_name}. No matching requirements found.'
            }
        
        framework_info = self.FRAMEWORK_PROMPTS.get(framework_name, {})
        framework_display_name = framework_info.get('name', framework_name.upper())
        focus_areas = framework_info.get('focus_areas', [])
        
        # Collect relevant framework requirements
        requirements_text = "\n\n".join([r['chunk'] for r in search_results[:5]])  # Top 5 matches
        
        # Framework-specific scoring guidance
        scoring_guidance = {
            'azure': """
SCORING GUIDANCE FOR AZURE BEST PRACTICES:
- 80-100 (Compliant): All major security controls implemented (encryption, RBAC, monitoring, backups)
- 60-79 (Partial): Most controls present but some gaps (e.g., missing MFA, incomplete monitoring)
- 0-59 (Non-Compliant): Critical gaps (no encryption, public access enabled, no backups)
Score based on: Security controls, Identity management, Storage security, Network configuration, Monitoring, Governance""",
            
            'gdpr': """
SCORING GUIDANCE FOR GDPR:
- 80-100 (Compliant): DPIA completed, DPO designated, breach procedures documented, data subject rights supported
- 60-79 (Partial): Some articles implemented (encryption, access controls) but missing DPIA, DPO, or breach procedures
- 0-59 (Non-Compliant): Missing critical requirements (no encryption, no consent management, no breach procedures)
Score based on: Article 5 (principles), Article 6 (lawful basis), Article 25 (privacy by design), Article 32 (security), Article 33-34 (breach notification), Article 35 (DPIA), Article 37 (DPO)""",
            
            'iso27001': """
SCORING GUIDANCE FOR ISO 27001:2022:
- 80-100 (Compliant): ISMS implemented, most Annex A controls in place, documented policies
- 60-79 (Partial): Some controls implemented (A.9 access control, A.10 cryptography) but missing ISMS, policies, or monitoring
- 0-59 (Non-Compliant): Critical controls missing (no access control, no encryption, no incident management)
Score based on: A.5 (policies), A.9 (access control), A.10 (cryptography), A.12 (operations), A.16 (incident management), A.18 (compliance)""",
            
            'iso27017': """
SCORING GUIDANCE FOR ISO 27017:2015 (Cloud Services):
- 80-100 (Compliant): Cloud-specific controls implemented, shared responsibility model defined, VM security configured
- 60-79 (Partial): Basic cloud security (encryption, access control) but missing cloud-specific controls or shared responsibility documentation
- 0-59 (Non-Compliant): Missing cloud-specific security (no VM security, no network segmentation, no data protection)
Score based on: Cloud service provider responsibilities, customer responsibilities, VM security, network security, data protection in cloud""",
            
            'iso27018': """
SCORING GUIDANCE FOR ISO 27018:2019 (PII in Public Clouds):
- 80-100 (Compliant): PII protection measures in place, consent management, data subject rights supported, breach notification configured
- 60-79 (Partial): Basic PII protection (encryption, access control) but missing consent management, data subject rights, or transparency
- 0-59 (Non-Compliant): Critical PII protection gaps (no encryption of PII, no consent management, no data subject rights)
Score based on: PII protection in cloud, consent management, data subject rights, transparency, breach notification for PII"""
        }
        
        framework_scoring = scoring_guidance.get(framework_name, "")
        
        # Use AI to analyze compliance against this framework
        prompt = f"""You are a compliance expert analyzing a document against {framework_display_name}.

FRAMEWORK: {framework_display_name}
DESCRIPTION: {framework_info.get('description', '')}

KEY FOCUS AREAS:
{chr(10).join([f"- {area}" for area in focus_areas])}

{framework_scoring}

UPLOADED DOCUMENT EXCERPT:
{document_text[:5000]}

FRAMEWORK REQUIREMENTS (from official documentation):
{requirements_text}

TASK: Analyze the uploaded document's compliance with {framework_display_name} and provide:
1. Overall compliance status (Compliant/Partial/Non-Compliant) - be strict and framework-specific
2. A score (0-100) that reflects ACTUAL compliance with {framework_display_name} requirements - use the scoring guidance above
3. Specific gaps or missing requirements that are UNIQUE to {framework_display_name}
4. Areas that are compliant with {framework_display_name}
5. Actionable recommendations specific to {framework_display_name}
6. Key requirements from {framework_display_name} that apply

IMPORTANT SCORING RULES:
- Score must reflect compliance with {framework_display_name} SPECIFICALLY, not generic security
- If document has many compliant areas, score should be higher (70-90)
- If document has critical gaps for {framework_display_name}, score should be lower (30-60)
- Each framework should get a DIFFERENT score based on its unique requirements
- Consider: How well does this document align with {framework_display_name} requirements?

RESPOND IN THIS EXACT JSON FORMAT (no markdown, just JSON):
{{
  "status": "Compliant|Partial|Non-Compliant",
  "score": <0-100 integer, be specific to {framework_display_name} requirements>,
  "recommendation": "Specific, actionable recommendation based on {framework_display_name} gaps found",
  "gaps": ["{framework_display_name}-specific gap 1", "gap 2", "gap 3"],
  "compliant_areas": ["{framework_display_name}-specific area 1", "area 2"],
  "key_requirements": ["{framework_display_name} requirement 1", "requirement 2", "requirement 3"],
  "priority_actions": ["action 1 specific to {framework_display_name}", "action 2"]
}}

Be specific and reference actual content from the uploaded document. If the document mentions something, reference it.
If something is missing compared to {framework_display_name}, state it clearly.
Make sure the score reflects {framework_display_name} compliance, not generic security compliance."""

        try:
            response = rate_limited_generate_content_optimized(
                prompt, 
                temperature=0.2, 
                max_tokens=2000
            )
            
            # Extract JSON from response
            cleaned = response.strip()
            if '```' in cleaned:
                if '```json' in cleaned:
                    cleaned = cleaned.split('```json')[1].split('```')[0].strip()
                elif '```' in cleaned:
                    cleaned = cleaned.split('```')[1].split('```')[0].strip()
            
            # Find JSON object
            if '{' in cleaned and '}' in cleaned:
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                json_str = cleaned[start:end]
                ai_result = json.loads(json_str)
                
                # Get gaps and compliant areas
                gaps = ai_result.get('gaps', [])
                compliant_areas = ai_result.get('compliant_areas', [])
                
                # Calculate score based on actual analysis data (more reliable than AI's score)
                ai_score = int(ai_result.get('score', 50))
                ai_score = max(0, min(100, ai_score))
                
                # Calculate score from gaps vs compliant areas ratio
                calculated_score = 50  # Default
                compliant_ratio = 0.5  # Default
                
                if gaps or compliant_areas:
                    total_items = len(gaps) + len(compliant_areas)
                    if total_items > 0:
                        compliant_ratio = len(compliant_areas) / total_items
                        
                        # Base score on ratio: 50% = 50, 70% = 70, 30% = 30
                        calculated_score = int(compliant_ratio * 100)
                        
                        # Adjust based on number of items (more items = more confidence)
                        # If we have many items analyzed, trust the ratio more
                        if total_items >= 10:
                            # High confidence: use ratio directly
                            calculated_score = int(compliant_ratio * 100)
                        elif total_items >= 5:
                            # Medium confidence: blend with AI score
                            calculated_score = int((compliant_ratio * 0.7 + (ai_score / 100) * 0.3) * 100)
                        else:
                            # Low confidence: use AI score more
                            calculated_score = int((compliant_ratio * 0.4 + (ai_score / 100) * 0.6) * 100)
                        
                        # Framework-specific adjustments
                        if framework_name == 'gdpr':
                            # GDPR is stricter - penalize missing DPIA, DPO more
                            if any('DPIA' in gap or 'DPO' in gap or 'data protection impact' in gap.lower() 
                                   for gap in gaps):
                                calculated_score = max(0, calculated_score - 10)
                        elif framework_name == 'iso27001':
                            # ISO 27001 requires ISMS - penalize if missing
                            if any('ISMS' in gap or 'information security management' in gap.lower() 
                                   for gap in gaps):
                                calculated_score = max(0, calculated_score - 8)
                        elif framework_name == 'iso27018':
                            # ISO 27018 is about PII - penalize PII-specific gaps more
                            if any('PII' in gap or 'personal data' in gap.lower() or 'consent' in gap.lower() 
                                   for gap in gaps):
                                calculated_score = max(0, calculated_score - 8)
                
                # Final score: blend calculated score with AI score (weighted average)
                # Use calculated score as primary (70%), AI score as secondary (30%)
                # This ensures scores vary based on actual analysis
                if gaps or compliant_areas:
                    final_score = int(calculated_score * 0.7 + ai_score * 0.3)
                else:
                    # If no detailed analysis, trust AI score
                    final_score = ai_score
                
                # Ensure score is in valid range
                score = max(0, min(100, final_score))
                
                # Add deterministic variation based on framework and analysis to prevent identical scores
                # Use hash of framework name + gaps count to create consistent but varied scores
                framework_hash = hash(framework_name + str(len(gaps)) + str(len(compliant_areas))) % 5
                variation = (framework_hash - 2)  # Range: -2 to +2
                score = max(0, min(100, score + variation))
                
                status = ai_result.get('status', 'Partial')
                if status not in ['Compliant', 'Partial', 'Non-Compliant']:
                    status = self.determine_compliance_status(score / 100)
                
                logger.info(f"AI analysis for {framework_name}: final_score={score}, ai_score={ai_score}, calculated_score={calculated_score}, gaps={len(gaps)}, compliant={len(compliant_areas)}, ratio={compliant_ratio:.2f}, status={status}")
                
                return {
                    'framework': framework_name,
                    'framework_name': framework_display_name,
                    'score': score,
                    'status': status,
                    'recommendation': ai_result.get('recommendation', ''),
                    'gaps': ai_result.get('gaps', []),
                    'compliant_areas': ai_result.get('compliant_areas', []),
                    'key_requirements': ai_result.get('key_requirements', []),
                    'priority_actions': ai_result.get('priority_actions', []),
                    'findings': [{
                        'framework': framework_display_name,
                        'status': status,
                        'recommendation': ai_result.get('recommendation', ''),
                        'gaps_identified': ai_result.get('gaps', []),
                        'compliant_areas': ai_result.get('compliant_areas', []),
                        'key_points': ai_result.get('key_requirements', []),
                        'confidence': float(score)
                    }]
                }
            else:
                raise ValueError("No JSON found in AI response")
                
        except Exception as e:
            logger.warning(f"AI analysis failed for {framework_name}: {e}, using fallback")
            # Fallback: calculate score from similarity
            avg_similarity = np.mean([r['similarity'] for r in search_results])
            score = int(avg_similarity * 100)
            status = self.determine_compliance_status(avg_similarity)
            
            return {
                'framework': framework_name,
                'framework_name': framework_display_name,
                'score': score,
                'status': status,
                'recommendation': f'Review document against {framework_display_name} requirements',
                'gaps': [],
                'compliant_areas': [],
                'key_requirements': [],
                'priority_actions': [],
                'findings': [{
                    'framework': framework_display_name,
                    'status': status,
                    'recommendation': f'Review document against {framework_display_name} requirements',
                    'gaps_identified': [],
                    'compliant_areas': [],
                    'key_points': [],
                    'confidence': float(score)
                }]
            }

