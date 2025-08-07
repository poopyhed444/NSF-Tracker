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
import aiohttp
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import re

# Import existing functionality
from delayed_funding_tracker import DelayedFundingTracker
from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants
from grant_cache import get_combined_cache, save_combined_cache, clear_cache
try:
    from scibert_classifier import ScibertClassifier
except ImportError:
    ScibertClassifier = None


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
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
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
                                   end_date: str = None) -> Dict[str, Any]:
        """
        Analyze delayed renewals using Times methodology
        """
        if not start_date:
            # Default to Times-style analysis period (last 4 months)
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=self.reporting_lag_days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # Get current active grants for institution
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
        pi_name = original_grant.get('contact_pi_name', '')
        project_title = original_grant.get('project_title', '')
        
        if not pi_name:
            return False
        
        # Look for grants from same PI with similar title or continuation keywords
        for grant in all_grants:
            if grant == original_grant:
                continue
                
            grant_pi = grant.get('contact_pi_name', '')
            grant_title = grant.get('project_title', '')
            
            # Same PI check
            if pi_name.lower() in grant_pi.lower() or grant_pi.lower() in pi_name.lower():
                # Check for continuation indicators
                if any(term in grant_title.lower() for term in [
                    'year 2', 'year 3', 'year 4', 'continuation', 'renewal',
                    'phase ii', 'phase 2', 'continued', 'supplement'
                ]):
                    return True
                    
                # Similar title check (basic keyword overlap)
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
                                         pi_cache: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive delay analysis combining Times methodology with disbursement tracking
        """
        # Check cache first
        cache_key = f"enhanced_comprehensive_delays_{institution_name}"
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
        
        # 1. Renewal delay analysis (Times method)
        renewal_analysis = await self.analyze_renewal_delays(institution_name)
        
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
            
            # Key insights
            'agencies_with_delays': agencies_with_delays,
            'most_impacted_department': most_impacted_department,
            
            # Action items (Times-style insights)
            'immediate_concerns': self._generate_immediate_concerns(renewal_analysis, disbursement_analysis),
            'recommended_actions': self._generate_action_recommendations(combined_risk, renewal_analysis, disbursement_analysis)
        }
        
        # Cache the result
        try:
            cached_data = get_combined_cache() or []
            cached_data.append({
                'cache_key': cache_key,
                'cached_at': datetime.now().isoformat(),
                'data': result
            })
            save_combined_cache(cached_data)
            print(f"Cached enhanced comprehensive analysis for {institution_name}")
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
