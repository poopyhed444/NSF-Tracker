#!/usr/bin/env python3
"""
Enhanced Delayed Funding Tracker - Times Methodology Implementation

This module implements a methodology similar to The New York Times analysis of 
delayed NIH funding, adapted for multi-agency federal research grants.

Key Features:
1. Renewal Timeline Analysis - Identifies grants that should have renewed but didn't
2. Historical Pattern Matching - Uses grant renewal patterns to detect delays
3. Multi-Agency Coverage - NIH, NSF, DoD, DoE, NASA, etc.
4. Automated Classification - Uses AI classification for research areas
5. Comprehensive Risk Assessment - Combines disbursement and renewal delays

Based on Times methodology:
- Focus on continuation/noncompeting renewals
- Account for reporting lags
- Use historical renewal timing patterns
- Manual verification capabilities
"""

import json
import asyncio
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import re

def normalize_department_name(dept_name, grant_context=None):
    """
    Enhanced department name normalization with NLP analysis.
    
    Args:
        dept_name: Original department name from grant data
        grant_context: Dict with grant information for NLP analysis (optional)
                      Should include: project_title, project_abstract, etc.
    """
    if not dept_name or dept_name is None:
        dept_name = "Other"
    
    dept_str = str(dept_name).strip()
    
    # Handle various representations of null/none/empty/other
    if dept_str.lower() in ['null', 'none', '', 'unknown department', 'unknown', 'n/a', 'na', 'other']:
        # Try to use BERT classification if grant context is available
        if grant_context:
            try:
                from bert_classifier import predict_from_research_context
                
                # Extract text for classification
                title = grant_context.get('project_title', '')
                abstract = grant_context.get('abstract', grant_context.get('project_abstract', ''))
                org_name = ''
                
                # Extract organization name from grant data
                org_info = grant_context.get('organization', {})
                if isinstance(org_info, dict):
                    org_name = org_info.get('org_name', '')
                elif isinstance(org_info, list) and org_info:
                    org_name = org_info[0].get('org_name', '') if isinstance(org_info[0], dict) else ''
                
                # Use Enhanced BERT to classify based on project content
                nlp_result = predict_from_research_context(
                    title=title,
                    abstract=abstract,
                    affiliation=org_name,
                    keywords=[]
                )
                
                classified_dept = nlp_result.get('department', 'Other')
                confidence = nlp_result.get('confidence', 0)
                
                print(f"� Enhanced BERT analysis: '{title[:50]}...' -> {classified_dept} (confidence: {confidence:.2f})")
                
                # Use BERT result if it's not "Unknown" and has reasonable confidence
                if classified_dept and classified_dept != 'Unknown' and confidence > 0.05:  # Lower threshold for BERT
                    print(f"� ✅ Using Enhanced BERT result: {classified_dept} (confidence: {confidence:.2f})")
                    return classified_dept
                else:
                    print(f"⚠️ Enhanced BERT confidence too low ({confidence:.2f}) or returned Unknown, using 'Other'")
                        
            except Exception as e:
                print(f"⚠️ Enhanced BERT classification failed: {e}")
        
        return "Other"
    
    return dept_str

# Import existing functionality
from delayed_funding_tracker import DelayedFundingTracker
from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants
from grant_cache import get_combined_cache, save_combined_cache, clear_cache
try:
    from bert_classifier import get_bert_classifier
    BertClassifier = get_bert_classifier
except ImportError:
    BertClassifier = None


class EnhancedDelayedFundingTracker:
    """
    Enhanced delayed funding tracker implementing Times-style methodology
    """
    
    def __init__(self):
        self.base_url = "https://api.reporter.nih.gov/v2"
        self.nsf_url = "https://www.research.gov/research-portal/api/v1"
        self.usaspending_url = "https://api.usaspending.gov/api/v2"
        self.session = None
        
        # Times methodology parameters
        self.reporting_lag_days = 120  # 4 months like Times analysis
        self.renewal_window_days = 365  # Look for renewals within 1 year
        self.minimum_award_threshold = 50000  # Focus on significant awards
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def _is_renewal_eligible_grant(self, grant: Dict[str, Any]) -> bool:
        """
        Determine if a grant is eligible for renewal based on Times criteria
        """
        # Check if it's a research grant type that typically renews
        grant_type = grant.get('activity_code', '').upper()
        renewable_types = [
            'R01', 'R21', 'R03', 'R15', 'R16', 'R25',  # NIH Research grants
            'T32', 'T34', 'F31',  # Training grants
            'P01', 'P30', 'P50',  # Program grants
            'U01', 'U19', 'U54'   # Cooperative agreements
        ]
        
        # Check if grant duration suggests multi-year funding
        try:
            start_date = datetime.strptime(grant.get('project_start_date', '')[:10], '%Y-%m-%d')
            end_date = datetime.strptime(grant.get('project_end_date', '')[:10], '%Y-%m-%d')
            duration_years = (end_date - start_date).days / 365.25
            
            # Multi-year grants are typically renewable
            if duration_years >= 2:
                return True
        except:
            pass
        
        # Check if it's explicitly marked as renewable or continuing
        project_title = grant.get('project_title', '').lower()
        if any(term in project_title for term in ['year 2', 'year 3', 'continuation', 'renewal']):
            return True
            
        return grant_type in renewable_types
    
    def _calculate_expected_renewal_date(self, grant: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate when a grant should have been renewed based on historical patterns
        """
        try:
            start_date = datetime.strptime(grant.get('project_start_date', '')[:10], '%Y-%m-%d')
            end_date = datetime.strptime(grant.get('project_end_date', '')[:10], '%Y-%m-%d')
            
            # For multi-year grants, renewal typically happens annually
            # Calculate the anniversary date
            current_year = datetime.now().year
            
            # If grant started in previous years, renewal should be on anniversary
            if start_date.year < current_year:
                expected_renewal = start_date.replace(year=current_year)
                
                # If that date has passed and we're still within the grant period
                if expected_renewal < datetime.now() and datetime.now() < end_date:
                    return expected_renewal
                    
            return None
        except:
            return None
    
    async def analyze_renewal_delays(self, 
                                   institution_name: str,
                                   start_date: str = None, 
                                   end_date: str = None,
                                   grants_data: list = None) -> Dict[str, Any]:
        """
        Analyze delayed renewals using Times methodology
        """
        if not start_date:
            # Default to Times-style analysis period (last 4 months)
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=self.reporting_lag_days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # Get current active grants for institution (use provided data or fetch)
        if grants_data is not None:
            grants = grants_data
            print(f"📊 Using provided grants data: {len(grants)} grants")
        else:
            try:
                grants = await fetch_institution_grants(
                    organization=institution_name,
                    active_only=True,
                    max_records_per_source=5000
                )
            except Exception as e:
                print(f"Error fetching grants for {institution_name}: {e}")
                return {"error": str(e)}
        
        # Analyze for renewal delays
        expected_renewals = []
        missing_renewals = []
        total_at_risk_amount = 0
        
        for grant in grants:
            if not self._is_renewal_eligible_grant(grant):
                continue
                
            expected_renewal_date = self._calculate_expected_renewal_date(grant)
            if not expected_renewal_date:
                continue
                
            # Check if renewal period has passed
            if expected_renewal_date < datetime.now() - timedelta(days=30):  # 30-day grace period
                award_amount = float(grant.get('award_amount', 0) or 0)
                
                # Look for evidence of renewal (similar grant from same PI recently)
                renewal_found = await self._check_for_renewal_evidence(grant, grants)
                
                expected_renewals.append({
                    'grant': grant,
                    'expected_renewal_date': expected_renewal_date.isoformat(),
                    'award_amount': award_amount,
                    'days_overdue': (datetime.now() - expected_renewal_date).days,
                    'renewal_found': renewal_found
                })
                
                if not renewal_found:
                    missing_renewals.append(expected_renewals[-1])
                    total_at_risk_amount += award_amount
        
        # Calculate metrics
        renewal_rate = 0
        if expected_renewals:
            renewed_count = len([r for r in expected_renewals if r['renewal_found']])
            renewal_rate = (renewed_count / len(expected_renewals)) * 100
        
        risk_level = "LOW"
        if len(missing_renewals) > 5 or total_at_risk_amount > 10000000:
            risk_level = "HIGH"
        elif len(missing_renewals) > 2 or total_at_risk_amount > 5000000:
            risk_level = "MEDIUM"
        
        return {
            'institution': institution_name,
            'analysis_period': f"{start_date} to {end_date}",
            'expected_renewals': len(expected_renewals),
            'missing_renewals': len(missing_renewals),
            'renewal_rate': renewal_rate,
            'at_risk_amount': total_at_risk_amount,
            'risk_level': risk_level,
            'detailed_missing_renewals': missing_renewals[:10],  # Top 10 for review
            'methodology': 'Times-style renewal analysis',
            'analysis_date': datetime.now().isoformat()
        }
    
    async def _check_for_renewal_evidence(self, 
                                        original_grant: Dict[str, Any], 
                                        all_grants: List[Dict[str, Any]]) -> bool:
        """
        Check if there's evidence of renewal for a grant
        """
        pi_name = original_grant.get('contact_pi_name', '') or ''
        project_title = original_grant.get('project_title', '') or ''
        
        if not pi_name:
            return False
        
        # Look for grants from same PI with similar title or continuation keywords
        for grant in all_grants:
            if grant == original_grant:
                continue
                
            grant_pi = grant.get('contact_pi_name', '') or ''
            grant_title = grant.get('project_title', '') or ''
            
            # Same PI check - ensure both are strings
            if grant_pi and pi_name and (pi_name.lower() in grant_pi.lower() or grant_pi.lower() in pi_name.lower()):
                # Check for continuation indicators
                if grant_title and any(term in grant_title.lower() for term in [
                    'year 2', 'year 3', 'year 4', 'continuation', 'renewal',
                    'phase ii', 'phase 2', 'continued', 'supplement'
                ]):
                    return True
                    
                # Similar title check (basic keyword overlap)
                if project_title and grant_title:
                    original_words = set(project_title.lower().split())
                    grant_words = set(grant_title.lower().split())
                    
                    # Remove common words
                    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from'}
                    original_words -= common_words
                    grant_words -= common_words
                    
                    if len(original_words) > 0:
                        overlap = len(original_words & grant_words) / len(original_words)
                        if overlap > 0.4:  # 40% keyword overlap
                            return True
        
        return False
    
    async def analyze_comprehensive_delays(self, 
                                         institution_name: str,
                                         pi_cache: Dict[str, Any] = None,
                                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Comprehensive delay analysis combining Times methodology with disbursement tracking
        """
        # Check cache first (skip if force_refresh)
        cache_key = f"enhanced_comprehensive_delays_{institution_name}"
        if not force_refresh:
            try:
                cached_data = get_combined_cache() or []
                for item in cached_data:
                    if item.get('cache_key') == cache_key:
                        # Check if cache is still valid (2 hours for enhanced analysis)
                        cache_time = datetime.fromisoformat(item.get('cached_at', '2000-01-01'))
                        if (datetime.now() - cache_time).total_seconds() < 7200:  # 2 hours cache
                            print(f"Using cached enhanced analysis for {institution_name}")
                            return item.get('data')
            except Exception as e:
                print(f"Enhanced cache check error: {e}")
        else:
            print(f"🔄 Force refresh enabled - bypassing cache for {institution_name}")
        
        # Fetch grants data once for both analyses
        print("🔍 Fetching grants data for comprehensive analysis...")
        try:
            fresh_grants = await fetch_institution_grants(
                organization=institution_name,
                active_only=True,
                max_records_per_source=5000
            )
            print(f"📊 Fetched {len(fresh_grants)} grants for comprehensive analysis")
        except Exception as e:
            print(f"Error fetching grants for {institution_name}: {e}")
            fresh_grants = []
        
        # 1. Renewal delay analysis (Times method) - pass grants to avoid refetching
        renewal_analysis = await self.analyze_renewal_delays(institution_name, grants_data=fresh_grants)
        
        # 2. Disbursement delay analysis (existing method)
        disbursement_tracker = DelayedFundingTracker()
        async with disbursement_tracker:
            disbursement_analysis = await disbursement_tracker.get_institution_funding_delays(institution_name)
        
        # 3. Combined risk assessment
        renewal_risk = 0
        if renewal_analysis.get('risk_level') == 'HIGH':
            renewal_risk = 75
        elif renewal_analysis.get('risk_level') == 'MEDIUM':
            renewal_risk = 50
        elif renewal_analysis.get('risk_level') == 'LOW':
            renewal_risk = 25
        
        disbursement_risk = disbursement_analysis.get('disbursement_analysis', {}).get('delayed_funding_risk', 0)
        
        # Combined risk score (weighted average)
        combined_risk = (renewal_risk * 0.6) + (disbursement_risk * 0.4)
        
        # Overall risk level
        if combined_risk >= 70:
            overall_risk = "CRITICAL"
        elif combined_risk >= 50:
            overall_risk = "HIGH"
        elif combined_risk >= 30:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"
        
        # Identify most impacted areas
        agencies_with_delays = []
        most_impacted_department = "Analysis needed"
        
        # Calculate total at-risk funding
        renewal_at_risk = renewal_analysis.get('at_risk_amount', 0)
        disbursement_at_risk = disbursement_analysis.get('summary', {}).get('total_undisbursed', 0)
        total_at_risk = renewal_at_risk + disbursement_at_risk
        
        # 4. Cancelled grants analysis (fetch terminated grants)
        print("🔍 Analyzing cancelled grants impact...")
        try:
            cancelled_grants_impact = await self._analyze_cancelled_grants(institution_name, pi_cache)
            print(f"✅ Cancelled grants analysis completed: {cancelled_grants_impact.get('total_affected_pis', 0)} PIs affected")
        except Exception as e:
            print(f"❌ Error in cancelled grants analysis: {e}")
            cancelled_grants_impact = {
                'total_lost_funding': 0,
                'grants_cancelled': 0,
                'departments_affected': 0,
                'total_affected_pis': 0,
                'risk_level': 'UNKNOWN',
                'top_affected_pis': [],
                'department_losses': {},
                'error': f'Cancelled grants analysis failed: {str(e)}'
            }
        
        # 5. Non-renewal grants analysis (use fresh grant data)
        print("🔍 Analyzing non-renewal grants impact...")
        try:
            print(f"📊 Using {len(fresh_grants)} fresh grants for non-renewal analysis")
            
            if not fresh_grants:
                print("No fresh grants available for non-renewal analysis, creating stub result")
                nonrenewal_grants_impact = {
                    'total_lost_funding': 0,
                    'grants_eligible_for_renewal': 0,
                    'missing_renewals_count': 0,
                    'renewal_rate': 100,  # Assume good if we can't analyze
                    'risk_level': 'LOW',
                    'departments_affected': 0,
                    'pis_impacted': 0,
                    'top_affected_pis': [],
                    'department_losses': {},
                    'methodology_note': 'Non-renewal analysis skipped - no fresh grants available'
                }
            else:
                nonrenewal_grants_impact = await self._analyze_nonrenewal_grants(institution_name, fresh_grants, pi_cache)
                print(f"✅ Non-renewal analysis completed: {nonrenewal_grants_impact.get('missing_renewals_count', 0)} missing renewals found")
                
        except Exception as e:
            print(f"Error in non-renewal analysis: {e}")
            nonrenewal_grants_impact = {
                'total_lost_funding': 0,
                'grants_eligible_for_renewal': 0,
                'missing_renewals_count': 0,
                'renewal_rate': 0,
                'risk_level': 'UNKNOWN',
                'departments_affected': 0,
                'pis_impacted': 0,
                'top_affected_pis': [],
                'department_losses': {},
                'error': str(e)
            }
        
        result = {
            'institution': institution_name,
            'analysis_date': datetime.now().isoformat(),
            'methodology': 'Combined Times-style renewal analysis + disbursement tracking',
            
            # Overall assessment
            'overall_risk_level': overall_risk,
            'combined_risk_score': round(combined_risk, 1),
            'total_at_risk': total_at_risk,
            
            # Detailed breakdowns
            'renewal_analysis': renewal_analysis,
            'disbursement_analysis': disbursement_analysis,
            'cancelled_grants_impact': cancelled_grants_impact,
            'nonrenewal_grants_impact': nonrenewal_grants_impact,
            
            # Key insights
            'agencies_with_delays': agencies_with_delays,
            'most_impacted_department': most_impacted_department,
            
            # Action items (Times-style insights)
            'immediate_concerns': self._generate_immediate_concerns(renewal_analysis, disbursement_analysis),
            'recommended_actions': self._generate_action_recommendations(combined_risk, renewal_analysis, disbursement_analysis)
        }
        
        # Cache the result using proper analysis cache (not grants cache!)
        try:
            # Don't pollute the grants cache with analysis results!
            # The combined_grants.json should only contain raw grant data from APIs
            # Analysis results should go in a separate cache system
            print(f"✅ Enhanced comprehensive analysis complete for {institution_name} (not cached to avoid grants cache pollution)")
        except Exception as e:
            print(f"Enhanced caching error: {e}")
        
        return result
    
    def _generate_immediate_concerns(self, 
                                   renewal_analysis: Dict[str, Any], 
                                   disbursement_analysis: Dict[str, Any]) -> List[str]:
        """Generate immediate concerns based on analysis"""
        concerns = []
        
        missing_renewals = renewal_analysis.get('missing_renewals', 0)
        if missing_renewals > 3:
            concerns.append(f"{missing_renewals} grants overdue for renewal")
        
        disbursement_risk = disbursement_analysis.get('summary', {}).get('cash_flow_risk', 'LOW')
        if disbursement_risk in ['HIGH', 'CRITICAL']:
            concerns.append("Significant disbursement delays affecting cash flow")
        
        at_risk_amount = renewal_analysis.get('at_risk_amount', 0)
        if at_risk_amount > 5000000:
            concerns.append(f"${at_risk_amount:,.0f} in funding at risk from delayed renewals")
        
        return concerns if concerns else ["No immediate concerns identified"]
    
    def _generate_action_recommendations(self, 
                                       combined_risk: float,
                                       renewal_analysis: Dict[str, Any], 
                                       disbursement_analysis: Dict[str, Any]) -> List[str]:
        """Generate action recommendations based on risk level"""
        actions = []
        
        if combined_risk >= 70:
            actions.extend([
                "Immediate intervention required - contact agency program officers",
                "Review grant compliance and reporting requirements",
                "Consider emergency bridge funding for critical research",
                "Implement weekly monitoring of grant status"
            ])
        elif combined_risk >= 50:
            actions.extend([
                "Proactive outreach to program officers recommended",
                "Review and expedite any pending grant reports",
                "Monitor renewal deadlines closely",
                "Prepare contingency funding plans"
            ])
        else:
            actions.extend([
                "Continue routine monitoring of grant renewals",
                "Maintain good compliance practices",
                "Monitor for changes in renewal patterns"
            ])
        
        return actions
    
    async def _analyze_nonrenewal_grants(self, institution_name: str, active_grants: list, pi_cache: Dict[str, Any] = None) -> dict:
        """
        Analyze non-renewal grants using Times-style methodology.
        Identifies grants that should have been renewed but show no evidence of renewal.
        """
        try:
            print(f"🔍 Analyzing non-renewal grants for {institution_name}")
            print(f"🚨 DEBUG: Method started successfully, active_grants type: {type(active_grants)}, length: {len(active_grants)}")
            
            from datetime import datetime, timedelta
            print(f"🚨 DEBUG: Imported datetime successfully")
            
            # Analysis period: last 24 months for renewal eligibility
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)  # Extended to 2 years
            print(f"🚨 DEBUG: Date calculations completed")
            
            print(f"📊 Non-renewal analysis period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"📋 Total active grants to analyze: {len(active_grants)}")
            
            # Find grants eligible for renewal that haven't been renewed
            renewal_eligible_grants = []
            missing_renewals = []
            nonrenewal_dept_losses = {}
            nonrenewal_grants_by_pi = {}
            
            print(f"🔄 Starting loop through {len(active_grants)} grants...")
            
            for i, grant in enumerate(active_grants):
                if i % 100 == 0:
                    print(f"🔄 Processing grant {i}/{len(active_grants)}")
                
                # Check if grant is eligible for renewal
                if self._is_renewal_eligible_grant(grant):
                    print(f"🎯 Grant {i} is renewal eligible")
                    expected_renewal_date = self._calculate_expected_renewal_date(grant)
                    
                    if expected_renewal_date and expected_renewal_date < datetime.now() - timedelta(days=90):  # 90-day grace period
                        pi_name = (grant.get('contact_pi_name') or grant.get('pi_name') or '').strip()
                        amount = float(grant.get('award_amount', 0) or 0)
                        
                        print(f"✅ Found eligible grant from {pi_name}, amount: ${amount:,.0f}")
                        
                        # Check for renewal evidence (simplified without async issues)
                        renewal_found = self._check_for_renewal_evidence_sync(grant, active_grants)
                        
                        renewal_info = {
                            'grant': grant,
                            'pi_name': pi_name,
                            'expected_renewal_date': expected_renewal_date.isoformat(),
                            'award_amount': amount,
                            'days_overdue': (datetime.now() - expected_renewal_date).days,
                            'renewal_found': renewal_found,
                            'project_title': grant.get('project_title', ''),
                            'project_num': grant.get('project_num') or grant.get('award_id'),
                            'funding_agency': grant.get('funding_agency', 'Unknown')
                        }
                        
                        renewal_eligible_grants.append(renewal_info)
                        
                        if not renewal_found:
                            print(f"⚠️ No renewal found for {pi_name}")
                            missing_renewals.append(renewal_info)
                            
                            # Department-level tracking (simplified without async lookup)
                            dept = 'Other'
                            try:
                                org_info = grant.get('organization', {})
                                if isinstance(org_info, dict):
                                    dept = org_info.get('dept_type', 'Other')
                                elif isinstance(org_info, list) and org_info:
                                    dept = org_info[0].get('dept_type', 'Other')
                            except:
                                pass
                            
                            # Normalize department name with NLP analysis if needed
                            dept = normalize_department_name(dept, grant)
                            
                            nonrenewal_dept_losses[dept] = nonrenewal_dept_losses.get(dept, 0) + amount
                            
                            # PI-level tracking
                            if pi_name not in nonrenewal_grants_by_pi:
                                nonrenewal_grants_by_pi[pi_name] = {
                                    'pi_name': pi_name,
                                    'department': dept,
                                    'lost_funding': 0,
                                    'grants': []
                                }
                            
                            nonrenewal_grants_by_pi[pi_name]['lost_funding'] += amount
                            nonrenewal_grants_by_pi[pi_name]['grants'].append({
                                'award_id': grant.get('project_num') or grant.get('award_id'),
                                'project_title': grant.get('project_title', ''),
                                'amount': amount,
                                'expected_renewal': expected_renewal_date.isoformat(),
                                'days_overdue': (datetime.now() - expected_renewal_date).days,
                                'funding_agency': grant.get('funding_agency', 'Unknown')
                            })
            
            # Calculate metrics
            print(f"📈 Calculating metrics for {len(missing_renewals)} missing renewals out of {len(renewal_eligible_grants)} eligible grants...")
            
            total_at_risk_funding = sum(r['award_amount'] for r in missing_renewals)
            renewal_rate = 0
            if renewal_eligible_grants:
                renewed_count = len([r for r in renewal_eligible_grants if r['renewal_found']])
                renewal_rate = (renewed_count / len(renewal_eligible_grants)) * 100
            
            top_affected_pis = sorted(nonrenewal_grants_by_pi.values(), key=lambda x: x['lost_funding'], reverse=True)[:10]
            
            risk_level = "LOW"
            if len(missing_renewals) > 5 or total_at_risk_funding > 10000000:
                risk_level = "HIGH"
            elif len(missing_renewals) > 2 or total_at_risk_funding > 5000000:
                risk_level = "MEDIUM"
            
            print(f"✅ Non-renewal analysis complete for {institution_name}: {len(missing_renewals)} missing renewals, ${total_at_risk_funding:,.0f} at risk, {renewal_rate:.1f}% renewal rate, {risk_level} risk")
            
            return {
                'total_lost_funding': total_at_risk_funding,
                'grants_eligible_for_renewal': len(renewal_eligible_grants),
                'missing_renewals_count': len(missing_renewals),
                'renewal_rate': renewal_rate,
                'risk_level': risk_level,
                'departments_affected': len(nonrenewal_dept_losses),
                'pis_impacted': len(nonrenewal_grants_by_pi),
                'top_affected_pis': [
                    {
                        'pi_name': pi['pi_name'],
                        'department': pi['department'],
                        'lost_funding': pi['lost_funding'],
                        'grants_count': len(pi['grants'])
                    } for pi in top_affected_pis
                ],
                'department_losses': dict(sorted(nonrenewal_dept_losses.items(), key=lambda x: x[1], reverse=True)),
                'detailed_missing_renewals': missing_renewals[:10],  # Top 10 for review
                'analysis_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'methodology_note': 'Times-style non-renewal analysis: identifies grants eligible for renewal that show no evidence of renewal within expected timeframes'
            }
            
        except Exception as e:
            print(f"❌ Error in non-renewal analysis: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_lost_funding': 0,
                'grants_eligible_for_renewal': 0,
                'missing_renewals_count': 0,
                'renewal_rate': 0,
                'risk_level': 'UNKNOWN',
                'departments_affected': 0,
                'pis_impacted': 0,
                'top_affected_pis': [],
                'department_losses': {},
                'detailed_missing_renewals': [],
                'analysis_period': '',
                'methodology_note': 'Non-renewal analysis failed',
                'error': str(e)
            }

    def _check_for_renewal_evidence_sync(self, original_grant: Dict[str, Any], all_grants: List[Dict[str, Any]]) -> bool:
        """
        Synchronous version of renewal evidence check to avoid async issues
        """
        pi_name = original_grant.get('contact_pi_name', '') or ''
        project_title = original_grant.get('project_title', '') or ''
        
        if not pi_name:
            return False
        
        # Look for grants from same PI with similar title or continuation keywords
        for grant in all_grants:
            if grant == original_grant:
                continue
                
            grant_pi = grant.get('contact_pi_name', '') or ''
            grant_title = grant.get('project_title', '') or ''
            
            # Same PI check - ensure both are strings
            if grant_pi and pi_name and (pi_name.lower() in grant_pi.lower() or grant_pi.lower() in pi_name.lower()):
                # Check for continuation indicators
                if grant_title and any(term in grant_title.lower() for term in [
                    'year 2', 'year 3', 'year 4', 'continuation', 'renewal',
                    'phase ii', 'phase 2', 'continued', 'supplement'
                ]):
                    return True
                    
                # Similar title check (basic keyword overlap)
                if project_title and grant_title:
                    original_words = set(project_title.lower().split())
                    grant_words = set(grant_title.lower().split())
                    
                    # Remove common words
                    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from'}
                    original_words -= common_words
                    grant_words -= common_words
                    
                    if len(original_words) > 0:
                        overlap = len(original_words & grant_words) / len(original_words)
                        if overlap > 0.4:  # 40% keyword overlap
                            return True
        
        return False

    async def _analyze_cancelled_grants(self, institution_name: str, pi_cache: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze cancelled/terminated grants impact"""
        try:
            # Import helper function
            from pi_department_lookup import get_department_string
            from datetime import datetime, timedelta
            
            # Fetch terminated grants from NIH using end date criteria (like the old implementation)
            terminated_grants = []
            
            # Use httpx instead of aiohttp (like the working implementation)
            import httpx
            
            # Fetch terminated grants from multiple agencies
            
            # 1. NIH terminated grants search using project end date  
            print("🔍 Fetching terminated NIH grants...")
            nih_url = "https://api.reporter.nih.gov/v2/projects/search"
            
            # Use end date criteria instead of award status
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # Last year
            
            payload = {
                "criteria": {
                    "project_end_date": {
                        "from_date": start_date.strftime("%Y-%m-%d"),
                        "to_date": end_date.strftime("%Y-%m-%d")
                    }
                },
                "include_fields": [
                    "ProjectNum", "Organization", "ContactPiName", "AwardAmount", 
                    "ProjectStartDate", "ProjectEndDate", "ProjectTitle", "FiscalYear"
                ],
                "offset": 0,
                "limit": 500  # NIH API max limit
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(nih_url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    nih_terminated = data.get("results", [])
                    # Add agency identifier
                    for grant in nih_terminated:
                        grant['funding_agency'] = 'NIH'
                    terminated_grants.extend(nih_terminated)
                    print(f"Fetched {len(nih_terminated)} recently ended grants from NIH")
            except httpx.RequestError as e:
                print(f"Error fetching NIH terminated grants (request): {e}")
            except httpx.HTTPStatusError as e:
                print(f"Error fetching NIH terminated grants (HTTP): {e}")
            except Exception as e:
                print(f"Error fetching NIH terminated grants (general): {e}")
            
            # 2. NSF terminated grants search - identify grants that ended unusually early
            print("🔍 Fetching potentially terminated NSF grants...")
            nsf_url = "https://www.research.gov/awardapi-service/v1/awards.json"
            
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    # Search for NSF grants that ended in the last year
                    nsf_params = {
                        'printFields': 'id,title,startDate,expDate,awardeeName,fundsObligatedAmt,pdPIName,agency',
                        'rpp': '500',
                        'offset': '1'
                    }
                    
                    # Add institution filter if specific enough
                    if len(institution_name.split()) >= 2:
                        # Use the main institution name for NSF search
                        main_institution = institution_name.split()[0] + " " + institution_name.split()[1]
                        nsf_params['awardeeName'] = main_institution
                    
                    response = await client.get(nsf_url, params=nsf_params)
                    response.raise_for_status()
                    data = response.json()
                    
                    nsf_awards = data.get('response', {}).get('award', [])
                    nsf_terminated = []
                    
                    # Filter for grants that ended in the last year and may be terminated
                    for award in nsf_awards:
                        exp_date_str = award.get('expDate', '')
                        start_date_str = award.get('startDate', '')
                        
                        if exp_date_str and start_date_str:
                            try:
                                exp_date_obj = datetime.strptime(exp_date_str[:10], '%Y-%m-%d')
                                start_date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                                
                                # Check if grant ended in the last year
                                if start_date <= exp_date_obj <= end_date:
                                    # Calculate grant duration in months
                                    duration_months = (exp_date_obj - start_date_obj).days / 30.44
                                    
                                    # Flag as potentially terminated if duration < 18 months (typical NSF grants are 2-3+ years)
                                    if duration_months < 18:
                                        # Convert to format similar to NIH data
                                        nsf_grant = {
                                            'project_num': award.get('id'),
                                            'organization': {'org_name': award.get('awardeeName', '')},
                                            'contact_pi_name': award.get('pdPIName', ''),
                                            'award_amount': award.get('fundsObligatedAmt', 0),
                                            'project_start_date': start_date_str,
                                            'project_end_date': exp_date_str,
                                            'project_title': award.get('title', ''),
                                            'funding_agency': 'NSF'
                                        }
                                        nsf_terminated.append(nsf_grant)
                            except ValueError:
                                continue  # Skip grants with invalid dates
                    
                    terminated_grants.extend(nsf_terminated)
                    print(f"Fetched {len(nsf_terminated)} potentially terminated NSF grants (duration < 18 months)")
                    
            except httpx.RequestError as e:
                print(f"Error fetching NSF terminated grants (request): {e}")
            except httpx.HTTPStatusError as e:
                print(f"Error fetching NSF terminated grants (HTTP): {e}")
            except Exception as e:
                print(f"Error fetching NSF terminated grants (general): {e}")
            
            # Process terminated grants by department
            cancelled_dept_losses = {}
            cancelled_grants_by_pi = {}
            total_cancelled_funding = 0
            
            # Institution matching keywords
            institution_upper = institution_name.upper()
            institution_keywords = institution_upper.split()
            
            for grant in terminated_grants:
                # Check if grant belongs to target institution
                grant_org = grant.get('organization', {})
                if isinstance(grant_org, dict):
                    org_name = grant_org.get('org_name', '').upper()
                else:
                    org_name = ''
                
                # Improved institution matching - require more specific matches
                is_institution_match = False
                
                # For exact match or very close match
                if institution_upper in org_name or org_name in institution_upper:
                    is_institution_match = True
                # For partial match, require multiple significant keywords
                elif len(institution_keywords) >= 2:
                    # Count how many significant keywords match (exclude common words)
                    common_words = {'THE', 'OF', 'AT', 'AND', 'FOR'}
                    significant_keywords = [k for k in institution_keywords if k not in common_words and len(k) > 3]
                    
                    if len(significant_keywords) >= 2:
                        matches = sum(1 for keyword in significant_keywords if keyword in org_name)
                        # Require at least 2 significant keyword matches
                        is_institution_match = matches >= 2
                
                if is_institution_match:
                    pi_name = (grant.get('contact_pi_name') or grant.get('pi_name') or '').strip()
                    if pi_name:
                        # Use department lookup function if available, with NLP fallback
                        if pi_cache:
                            from pi_department_lookup import get_department_string
                            dept = get_department_string(pi_name, institution_name)
                        else:
                            dept = "Other"
                        
                        # Normalize department name with NLP analysis if needed
                        dept = normalize_department_name(dept, grant)
                        
                        amount = float(grant.get('award_amount', 0) or 0)
                        total_cancelled_funding += amount
                        
                        # Track department losses
                        cancelled_dept_losses[dept] = cancelled_dept_losses.get(dept, 0) + amount
                        
                        # Track PI-level losses
                        if pi_name not in cancelled_grants_by_pi:
                            cancelled_grants_by_pi[pi_name] = {
                                'pi_name': pi_name,
                                'department': dept,
                                'lost_funding': 0,
                                'grants': []
                            }
                        
                        cancelled_grants_by_pi[pi_name]['lost_funding'] += amount
                        cancelled_grants_by_pi[pi_name]['grants'].append({
                            'award_id': grant.get('project_num') or grant.get('award_id'),
                            'project_title': grant.get('project_title', ''),
                            'amount': amount,
                            'status': 'Recently Ended',
                            'end_date': grant.get('project_end_date'),
                            'funding_agency': grant.get('funding_agency', 'NIH')
                        })
            
            # Get top affected PIs
            top_cancelled_pis = sorted(
                cancelled_grants_by_pi.values(), 
                key=lambda x: x['lost_funding'], 
                reverse=True
            )[:10]
            
            # Calculate risk level based on funding lost and number of grants
            risk_level = "LOW"
            grants_cancelled = len(cancelled_grants_by_pi)
            if grants_cancelled > 5 or total_cancelled_funding > 10000000:
                risk_level = "HIGH"
            elif grants_cancelled > 2 or total_cancelled_funding > 5000000:
                risk_level = "MEDIUM"
            
            return {
                'total_lost_funding': total_cancelled_funding,
                'grants_cancelled': grants_cancelled,
                'departments_affected': len(cancelled_dept_losses),
                'total_affected_pis': len(cancelled_grants_by_pi),
                'risk_level': risk_level,
                'top_affected_pis': [
                    {
                        'pi_name': pi['pi_name'],
                        'department': pi['department'],
                        'lost_funding': pi['lost_funding'],
                        'grants_count': len(pi['grants'])
                    } for pi in top_cancelled_pis
                ],
                'department_losses': dict(sorted(cancelled_dept_losses.items(), key=lambda x: x[1], reverse=True)),
                'methodology_note': 'Analysis based on NIH grants that ended in the last 12 months'
            }
            
        except Exception as e:
            print(f"Error in cancelled grants analysis: {e}")
            return {
                'total_lost_funding': 0,
                'grants_cancelled': 0,
                'departments_affected': 0,
                'total_affected_pis': 0,
                'risk_level': 'UNKNOWN',
                'top_affected_pis': [],
                'department_losses': {},
                'error': str(e)
            }
    
    async def analyze_delays_by_department(self, 
                                         institution_name: str,
                                         pi_cache: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Department-level delay analysis using Times methodology
        """
        # Get comprehensive analysis
        comprehensive = await self.analyze_comprehensive_delays(institution_name, pi_cache)
        
        # Extract department-specific insights from renewal analysis
        renewal_data = comprehensive['renewal_analysis']
        missing_renewals = renewal_data.get('detailed_missing_renewals', [])
        
        # Group by department (simplified - would need PI-department matching)
        departments = []
        dept_totals = defaultdict(lambda: {
            'undisbursed': 0,
            'delayed_renewals': 0,
            'total_grants': 0,
            'at_risk_amount': 0
        })
        
        # Process missing renewals by department
        for renewal in missing_renewals:
            grant = renewal['grant']
            pi_name = grant.get('contact_pi_name', 'Unknown PI')
            
            # Simple department assignment (would use PI cache in real implementation)
            department = self._assign_department_from_grant(grant, pi_cache or {})
            
            dept_totals[department]['delayed_renewals'] += 1
            dept_totals[department]['at_risk_amount'] += renewal['award_amount']
            dept_totals[department]['total_grants'] += 1
        
        # Convert to department list
        for dept_name, totals in dept_totals.items():
            risk_level = "LOW"
            if totals['delayed_renewals'] > 2 or totals['at_risk_amount'] > 2000000:
                risk_level = "HIGH"
            elif totals['delayed_renewals'] > 1 or totals['at_risk_amount'] > 500000:
                risk_level = "MEDIUM"
            
            departments.append({
                'name': dept_name,
                'delayed_renewals': totals['delayed_renewals'],
                'at_risk_amount': totals['at_risk_amount'],
                'undisbursed': totals['undisbursed'],  # Would add disbursement data
                'risk_level': risk_level,
                'total_grants_analyzed': totals['total_grants']
            })
        
        # Sort by risk
        departments.sort(key=lambda x: x['at_risk_amount'], reverse=True)
        
        return {
            'institution': institution_name,
            'analysis_date': datetime.now().isoformat(),
            'methodology': 'Times-style department-level renewal analysis',
            'departments': departments,
            'summary': {
                'total_departments_with_delays': len(departments),
                'total_delayed_renewals': sum(d['delayed_renewals'] for d in departments),
                'total_at_risk_funding': sum(d['at_risk_amount'] for d in departments)
            }
        }
    
    def _assign_department_from_grant(self, grant: Dict[str, Any], pi_cache: Dict[str, Any]) -> str:
        """
        Assign department based on grant information and PI cache
        """
        pi_name = grant.get('contact_pi_name', '')
        
        # Check PI cache first
        if pi_name in pi_cache:
            return pi_cache[pi_name].get('department', 'Unknown Department')
        
        # Fallback to grant title keywords
        title = grant.get('project_title', '').lower()
        
        # Simple keyword-based department assignment
        dept_keywords = {
            'Biology': ['biology', 'biological', 'molecular', 'genetics', 'genomics'],
            'Medicine': ['medical', 'clinical', 'patient', 'disease', 'therapeutic'],
            'Chemistry': ['chemistry', 'chemical', 'synthesis', 'catalysis'],
            'Physics': ['physics', 'quantum', 'particle', 'materials'],
            'Engineering': ['engineering', 'technology', 'development', 'design'],
            'Computer Science': ['computer', 'computational', 'algorithm', 'software'],
            'Neuroscience': ['neuroscience', 'brain', 'neural', 'cognitive'],
            'Psychology': ['psychology', 'behavioral', 'mental health']
        }
        
        for dept, keywords in dept_keywords.items():
            if any(keyword in title for keyword in keywords):
                return dept
        
        return 'Unknown Department'


# Standalone functions for API integration
async def analyze_delayed_funding_enhanced(institution_name: str, 
                                         method: str = "comprehensive") -> Dict[str, Any]:
    """
    Enhanced delayed funding analysis using Times methodology
    
    Args:
        institution_name: Name of institution to analyze
        method: "renewal", "disbursement", or "comprehensive"
    """
    async with EnhancedDelayedFundingTracker() as tracker:
        if method == "renewal":
            return await tracker.analyze_renewal_delays(institution_name)
        elif method == "disbursement":
            standard_tracker = DelayedFundingTracker()
            async with standard_tracker:
                return await standard_tracker.get_institution_funding_delays(institution_name)
        else:  # comprehensive
            return await tracker.analyze_comprehensive_delays(institution_name)


async def analyze_institutional_renewal_patterns(institutions: List[str]) -> Dict[str, Any]:
    """
    Analyze renewal patterns across multiple institutions (Times-style analysis)
    """
    results = {}
    overall_stats = {
        'total_institutions': len(institutions),
        'institutions_with_delays': 0,
        'total_missing_renewals': 0,
        'total_at_risk_funding': 0
    }
    
    async with EnhancedDelayedFundingTracker() as tracker:
        for institution in institutions:
            try:
                analysis = await tracker.analyze_renewal_delays(institution)
                results[institution] = analysis
                
                if analysis.get('missing_renewals', 0) > 0:
                    overall_stats['institutions_with_delays'] += 1
                
                overall_stats['total_missing_renewals'] += analysis.get('missing_renewals', 0)
                overall_stats['total_at_risk_funding'] += analysis.get('at_risk_amount', 0)
                
            except Exception as e:
                results[institution] = {"error": str(e)}
    
    return {
        'analysis_date': datetime.now().isoformat(),
        'methodology': 'Times-style multi-institutional renewal analysis',
        'overall_statistics': overall_stats,
        'institutional_results': results,
        'summary': {
            'percentage_with_delays': (overall_stats['institutions_with_delays'] / len(institutions)) * 100,
            'average_missing_renewals': overall_stats['total_missing_renewals'] / len(institutions),
            'total_funding_at_risk': overall_stats['total_at_risk_funding']
        }
    }


# Test function
async def test_enhanced_methodology():
    """Test the enhanced Times-style methodology"""
    print("=== Testing Enhanced Delayed Funding Analysis (Times Methodology) ===")
    
    test_institutions = [
        "Stanford University",
        "Harvard University", 
        "Massachusetts Institute of Technology"
    ]
    
    async with EnhancedDelayedFundingTracker() as tracker:
        for institution in test_institutions:
            print(f"\n--- Testing: {institution} ---")
            
            # Test renewal analysis
            renewal_results = await tracker.analyze_renewal_delays(institution)
            print(f"Renewal Analysis:")
            print(f"  Expected renewals: {renewal_results.get('expected_renewals', 0)}")
            print(f"  Missing renewals: {renewal_results.get('missing_renewals', 0)}")
            print(f"  At-risk funding: ${renewal_results.get('at_risk_amount', 0):,.0f}")
            print(f"  Risk level: {renewal_results.get('risk_level', 'Unknown')}")
            
            # Test comprehensive analysis
            comprehensive_results = await tracker.analyze_comprehensive_delays(institution)
            print(f"\nComprehensive Analysis:")
            print(f"  Overall risk: {comprehensive_results.get('overall_risk_level', 'Unknown')}")
            print(f"  Combined score: {comprehensive_results.get('combined_risk_score', 0):.1f}/100")
            print(f"  Total at-risk: ${comprehensive_results.get('total_at_risk', 0):,.0f}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_methodology())
