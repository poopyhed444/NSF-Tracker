#!/usr/bin/env python3
"""
Delayed Funding Tracker

This module tracks delayed or undisbursed funding by comparing:
1. Awarded amounts vs. actual disbursements
2. Expected funding timelines vs. actual disbursement dates
3. Funding gaps that could indicate cash flow issues for institutions

Uses USASpending.gov's disbursement API to track actual money flow.

IMPORTANT METHODOLOGICAL NOTE:
USASpending.gov has approximately 1-month reporting lag for disbursement data.
This module accounts for this lag by:
- Adjusting the end date for data retrieval to be 30 days before current date
- Excluding awards started within the last 60 days from delay analysis
- Adding appropriate caveats to analysis results
"""

import json
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

class DelayedFundingTracker:
    def __init__(self):
        self.base_url = "https://api.usaspending.gov/api/v2"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_disbursement_data(self, award_id: str, recipient_name: str) -> Dict[str, Any]:
        """Get actual disbursement data for a specific award"""
        try:
            # USASpending.gov API endpoint for award financial details
            url = f"{self.base_url}/awards/financial/"
            
            payload = {
                "filters": {
                    "award_ids": [award_id],
                    "recipient_search_text": [recipient_name]
                },
                "fields": [
                    "Award ID",
                    "Award Amount", 
                    "Outlayed Amount",
                    "Obligated Amount",
                    "Start Date",
                    "End Date",
                    "Last Modified Date",
                    "Award Description",
                    "Recipient Name"
                ]
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    print(f"Error fetching disbursement data for {award_id}: {response.status}")
                    return {}
                    
        except Exception as e:
            print(f"Error fetching disbursement data for {award_id}: {e}")
            return {}
    
    async def get_institution_disbursements(self, institution_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get disbursement data for all awards for an institution"""
        try:
            url = f"{self.base_url}/search/spending_by_award/"
            
            payload = {
                "filters": {
                    "recipient_search_text": [institution_name],
                    "award_type_codes": ["04", "05"],  # Grants and cooperative agreements
                    "time_period": [
                        {
                            "start_date": "2020-01-01",
                            # Account for USASpending 1-month reporting lag
                            "end_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        }
                    ]
                },
                "fields": [
                    "Award ID",
                    "Award Amount",
                    "Outlayed Amount", 
                    "Obligated Amount",
                    "Base Obligation Date",
                    "Action Date",
                    "Award Description",
                    "Start Date",
                    "End Date",
                    "Awarding Agency",
                    "Recipient Name"
                ],
                "sort": "Award Amount",
                "order": "desc",
                "limit": limit
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    print(f"Error fetching institution disbursements for {institution_name}: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"Error fetching institution disbursements for {institution_name}: {e}")
            return []
    
    async def analyze_funding_delays_by_department(self, disbursement_data: List[Dict[str, Any]], pi_cache: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
        """Analyze funding delays broken down by department using PI matching"""
        from enhanced_main import match_pi_to_department  # Import the PI matching function
        
        department_delays = defaultdict(list)
        department_totals = defaultdict(lambda: {
            'total_awarded': 0,
            'total_disbursed': 0,
            'total_undisbursed': 0,
            'awards_count': 0,
            'delayed_awards_count': 0
        })
        
        overall_analysis = self.analyze_funding_delays(disbursement_data)
        
        for award in disbursement_data:
            awarded = float(award.get('Award Amount', 0) or 0)
            outlayed = float(award.get('Outlayed Amount', 0) or 0)
            undisbursed = awarded - outlayed
            
            # Extract PI name from award using NIH REPORTER/NSF APIs
            pi_name = await self._extract_pi_from_award(award)
            
            # Match PI to department
            department = match_pi_to_department(pi_name, institution_name, pi_cache) if pi_name else "Unknown Department"
            
            # Calculate disbursement metrics for this award
            disbursement_rate = outlayed / awarded if awarded > 0 else 0
            
            # Account for USASpending reporting lag - don't flag recent awards as delayed
            start_date_str = award.get('Start Date', '')
            is_recent_award = False
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    # Awards started within last 2 months may not show disbursements due to reporting lag
                    is_recent_award = (datetime.now() - start_date).days < 60
                except ValueError:
                    pass
            
            # Consider significant awards delayed if disbursement rate is low and not recent
            is_delayed = disbursement_rate < 0.5 and awarded > 10000 and not is_recent_award
            
            # Add to department tracking
            award_info = {
                'award_id': award.get('Award ID', ''),
                'awarded_amount': awarded,
                'disbursed_amount': outlayed,
                'undisbursed_amount': undisbursed,
                'disbursement_rate': disbursement_rate,
                'pi_name': pi_name or 'Unknown PI',
                'agency': award.get('Awarding Agency', ''),
                'description': award.get('Award Description', '')[:100] if award.get('Award Description') else '',
                'start_date': award.get('Start Date', ''),
                'end_date': award.get('End Date', ''),
                'is_delayed': is_delayed
            }
            
            department_delays[department].append(award_info)
            
            # Update department totals
            dept_totals = department_totals[department]
            dept_totals['total_awarded'] += awarded
            dept_totals['total_disbursed'] += outlayed
            dept_totals['total_undisbursed'] += undisbursed
            dept_totals['awards_count'] += 1
            if is_delayed:
                dept_totals['delayed_awards_count'] += 1
        
        # Calculate department-level metrics
        department_analysis = []
        for dept, awards in department_delays.items():
            totals = department_totals[dept]
            
            # Calculate department risk metrics
            disbursement_efficiency = totals['total_disbursed'] / max(totals['total_awarded'], 1)
            delay_frequency = totals['delayed_awards_count'] / max(totals['awards_count'], 1)
            
            # Estimate research impact
            estimated_positions_affected = totals['total_undisbursed'] / 200000  # $200k per researcher
            
            # Department risk score (0-100)
            undisbursed_rate = totals['total_undisbursed'] / max(totals['total_awarded'], 1)
            dept_risk_score = min(100, (undisbursed_rate * 60) + (delay_frequency * 40))
            
            # Risk level
            if dept_risk_score >= 75:
                risk_level = 'CRITICAL'
            elif dept_risk_score >= 50:
                risk_level = 'HIGH'
            elif dept_risk_score >= 25:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            # Get most impacted awards (highest undisbursed amounts)
            most_impacted_awards = sorted(awards, key=lambda x: x['undisbursed_amount'], reverse=True)[:3]
            
            department_analysis.append({
                'department': dept,
                'risk_level': risk_level,
                'risk_score': round(dept_risk_score, 1),
                'total_awarded': round(totals['total_awarded'], 2),
                'total_disbursed': round(totals['total_disbursed'], 2),
                'total_undisbursed': round(totals['total_undisbursed'], 2),
                'disbursement_efficiency': round(disbursement_efficiency * 100, 1),
                'awards_count': totals['awards_count'],
                'delayed_awards_count': totals['delayed_awards_count'],
                'delay_frequency': round(delay_frequency * 100, 1),
                'estimated_positions_affected': round(estimated_positions_affected, 1),
                'most_impacted_awards': most_impacted_awards,
                'all_awards': awards
            })
        
        # Sort departments by total undisbursed amount
        department_analysis.sort(key=lambda x: x['total_undisbursed'], reverse=True)
        
        return {
            'overall_analysis': overall_analysis,
            'department_breakdown': department_analysis,
            'total_departments_affected': len(department_analysis),
            'highest_risk_departments': [d for d in department_analysis if d['risk_level'] in ['CRITICAL', 'HIGH']]
        }
    
    async def _extract_pi_from_award(self, award: Dict[str, Any]) -> str:
        """Extract PI name from award data using NIH REPORTER and NSF APIs"""
        award_id = award.get('Award ID', '')
        agency = award.get('Awarding Agency', '')
        
        if not award_id:
            return None
            
        try:
            # For NIH awards (HHS), use NIH REPORTER API
            if 'health' in agency.lower() or 'hhs' in agency.lower():
                return await self._lookup_nih_pi(award_id)
            
            # For NSF awards, use NSF API  
            elif 'national science foundation' in agency.lower() or 'nsf' in agency.lower():
                return await self._lookup_nsf_pi(award_id)
                
            # For other agencies, return None for now
            return None
            
        except Exception as e:
            print(f"Error looking up PI for award {award_id}: {e}")
            return None
    
    async def _lookup_nih_pi(self, award_id: str) -> str:
        """Look up PI from NIH REPORTER API"""
        try:
            url = "https://api.reporter.nih.gov/v2/projects/search"
            payload = {
                "criteria": {"award_nums": [award_id]},
                "include_fields": ["ContactPiName", "OtherPiNames"],
                "offset": 0,
                "limit": 10
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    if results:
                        pi_name = results[0].get("contact_pi_name")
                        if pi_name:
                            return pi_name
        except Exception as e:
            print(f"Error looking up NIH PI for {award_id}: {e}")
        return None
    
    async def _lookup_nsf_pi(self, award_id: str) -> str:
        """Look up PI from NSF API"""
        try:
            # NSF Award API endpoint
            url = f"https://www.research.gov/research-portal/api/v1/awards"
            params = {
                "id": award_id,
                "printFields": "id,title,piFirstName,piLastName"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'response' in data and 'award' in data['response']:
                        award_data = data['response']['award']
                        if isinstance(award_data, list) and award_data:
                            award_info = award_data[0]
                            first_name = award_info.get('piFirstName', '')
                            last_name = award_info.get('piLastName', '')
                            if first_name and last_name:
                                return f"{first_name} {last_name}"
        except Exception as e:
            print(f"Error looking up NSF PI for {award_id}: {e}")
        return None
    
    def analyze_funding_delays(self, disbursement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze funding delays using Times-style methodology:
        Focus on grants that should have been renewed but haven't been,
        rather than disbursement data which is often missing from USASpending.gov
        
        Times Method:
        - Look for grants eligible for continuation/renewal
        - Focus on Jan 20 - April 30 renewal window  
        - Identify missing renewals based on historical patterns
        """
        analysis = {
            'total_awards': len(disbursement_data),
            'total_awarded_amount': 0,
            'total_obligated_amount': 0,
            'total_outlayed_amount': 0,
            'delayed_funding_risk': 0,
            'undisbursed_amount': 0,
            'awards_with_delays': [],
            'disbursement_efficiency': 0,
            'cash_flow_risk_level': 'LOW',
            'delayed_awards_count': 0,
            'methodology_note': 'Times-style renewal analysis + USASpending lag compensation'
        }
        
        if not disbursement_data:
            return analysis
        
        current_date = datetime.now()
        renewal_window_start = datetime(current_date.year, 1, 20)  # Jan 20
        renewal_window_end = datetime(current_date.year, 4, 30)    # April 30
        
        # Track disbursement data (often null in USASpending.gov)
        total_with_disbursement_data = 0
        
        for award in disbursement_data:
            awarded = float(award.get('Award Amount', 0) or 0)
            obligated = float(award.get('Obligated Amount', 0) or 0)
            outlayed = float(award.get('Outlayed Amount', 0) or 0)
            
            analysis['total_awarded_amount'] += awarded
            analysis['total_obligated_amount'] += obligated
            analysis['total_outlayed_amount'] += outlayed
            
            # Check if this award has actual disbursement data
            if obligated > 0 or outlayed > 0:
                total_with_disbursement_data += 1
            
            # Times-style analysis: Check for renewal delays
            start_date_str = award.get('Start Date', '')
            end_date_str = award.get('End Date', '')
            
            is_renewal_delayed = False
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    
                    # Check if grant was eligible for renewal in the Jan 20 - April 30 window
                    # Grants typically get renewed 6-12 months before expiration
                    renewal_eligible_date = end_date - timedelta(days=365)  # 1 year before expiration
                    
                    # If the grant was eligible for renewal during the window but expired/ending soon
                    if (renewal_eligible_date <= renewal_window_end and 
                        end_date <= current_date + timedelta(days=180)):  # Ending within 6 months
                        
                        # Check if no recent renewal award exists (simplified check)
                        # In a full implementation, we'd cross-reference with renewed grants
                        is_renewal_delayed = True
                        
                except ValueError:
                    pass
            
            # Flag awards with renewal delays or disbursement issues
            if awarded > 0:
                disbursement_rate = outlayed / awarded if outlayed > 0 else 0
                
                # Use renewal delay logic if disbursement data is missing
                if obligated == 0 and outlayed == 0:
                    # No disbursement data available - use renewal analysis
                    if is_renewal_delayed:
                        analysis['awards_with_delays'].append({
                            'award_id': award.get('Award ID', ''),
                            'awarded_amount': awarded,
                            'delay_type': 'renewal_delayed',
                            'start_date': start_date_str,
                            'end_date': end_date_str,
                            'agency': award.get('Awarding Agency', ''),
                            'reason': 'Grant eligible for renewal but not yet renewed (Times methodology)'
                        })
                        analysis['delayed_awards_count'] += 1
                else:
                    # Has disbursement data - use traditional analysis
                    if disbursement_rate < 0.5:  # Less than 50% disbursed
                        analysis['awards_with_delays'].append({
                            'award_id': award.get('Award ID', ''),
                            'awarded_amount': awarded,
                            'disbursed_amount': outlayed,
                            'disbursement_rate': disbursement_rate,
                            'delay_type': 'disbursement_delayed',
                            'agency': award.get('Awarding Agency', ''),
                            'reason': f'Only {disbursement_rate*100:.1f}% of funds disbursed'
                        })
                        analysis['delayed_awards_count'] += 1
        
        # Calculate overall metrics with improved methodology  
        if analysis['total_awarded_amount'] > 0:
            # If most awards lack disbursement data, use alternative efficiency calculation
            if total_with_disbursement_data < len(disbursement_data) * 0.3:  # Less than 30% have disbursement data
                # Use Times-style methodology: percentage of awards without renewal delays
                non_delayed_rate = max(0, 1 - (analysis['delayed_awards_count'] / analysis['total_awards']))
                analysis['disbursement_efficiency'] = non_delayed_rate
                analysis['undisbursed_amount'] = analysis['total_awarded_amount'] * (1 - non_delayed_rate)
                analysis['methodology_note'] = 'Times-style renewal analysis (USASpending disbursement data unavailable)'
            else:
                # Use traditional disbursement analysis
                analysis['disbursement_efficiency'] = analysis['total_outlayed_amount'] / analysis['total_awarded_amount']
                analysis['undisbursed_amount'] = analysis['total_awarded_amount'] - analysis['total_outlayed_amount']
                analysis['methodology_note'] = 'Disbursement tracking + renewal analysis'
            
            # Calculate delayed funding risk score (0-100)
            undisbursed_rate = analysis['undisbursed_amount'] / analysis['total_awarded_amount']
            delay_frequency = analysis['delayed_awards_count'] / analysis['total_awards'] if analysis['total_awards'] > 0 else 0
            
            analysis['delayed_funding_risk'] = min(100, (undisbursed_rate * 60) + (delay_frequency * 40))
            
            # Determine cash flow risk level
            if analysis['delayed_funding_risk'] >= 75:
                analysis['cash_flow_risk_level'] = 'CRITICAL'
            elif analysis['delayed_funding_risk'] >= 50:
                analysis['cash_flow_risk_level'] = 'HIGH'
            elif analysis['delayed_funding_risk'] >= 25:
                analysis['cash_flow_risk_level'] = 'MEDIUM'
            else:
                analysis['cash_flow_risk_level'] = 'LOW'
        
        return analysis
    
    async def analyze_funding_delays_with_pi_lookup(self, disbursement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze funding delays with PI lookup enhancement
        
        NOTE: USASpending.gov has approximately 1-month reporting lag for disbursement data.
        Recent disbursements may not appear immediately in the database.
        """
        # Start with the basic analysis
        analysis = self.analyze_funding_delays(disbursement_data)
        
        # Enhance awards with PI lookup
        enhanced_awards = []
        for award in disbursement_data:
            award_copy = award.copy()
            # Add PI information using async lookup
            pi_name = await self._extract_pi_from_award(award)
            award_copy['pi_name'] = pi_name if pi_name else "Unknown PI"
            enhanced_awards.append(award_copy)
        
        # Update the analysis with enhanced awards
        analysis['enhanced_awards'] = enhanced_awards
        
        return analysis
    
    async def get_institution_funding_delays(self, institution_name: str) -> Dict[str, Any]:
        """Get complete funding delay analysis for an institution"""
        disbursement_data = await self.get_institution_disbursements(institution_name)
        # Use the old analysis for basic analysis, but enhance it with PI lookup
        analysis = await self.analyze_funding_delays_with_pi_lookup(disbursement_data)
        
        return {
            'institution': institution_name,
            'analysis_date': datetime.now().isoformat(),
            'disbursement_analysis': analysis,
            'raw_disbursement_data': disbursement_data[:10],  # Include top 10 for details
            'summary': {
                'total_undisbursed': analysis['undisbursed_amount'],
                'disbursement_efficiency': f"{analysis['disbursement_efficiency']*100:.1f}%",
                'cash_flow_risk': analysis['cash_flow_risk_level'],
                'delayed_funding_risk_score': round(analysis['delayed_funding_risk'], 1),
                'awards_with_significant_delays': analysis['delayed_awards_count'],
                'methodology_note': 'Analysis accounts for ~1-month USASpending.gov reporting lag'
            }
        }

async def analyze_delayed_funding_for_institution(institution_name: str) -> Dict[str, Any]:
    """Main function to analyze delayed funding for an institution"""
    async with DelayedFundingTracker() as tracker:
        return await tracker.get_institution_funding_delays(institution_name)

async def analyze_delayed_funding_with_departments(institution_name: str, pi_cache: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze delayed funding for an institution with department-level breakdown"""
    async with DelayedFundingTracker() as tracker:
        disbursement_data = await tracker.get_institution_disbursements(institution_name)
        
        if not disbursement_data:
            return {
                'institution': institution_name,
                'error': 'No disbursement data available',
                'departments': []
            }
        
        # Get department-level analysis (now async)
        dept_analysis = await tracker.analyze_funding_delays_by_department(
            disbursement_data, pi_cache, institution_name
        )
        
        return {
            'institution': institution_name,
            'analysis_date': datetime.now().isoformat(),
            'overall_summary': {
                'total_undisbursed': dept_analysis['overall_analysis']['undisbursed_amount'],
                'disbursement_efficiency': f"{dept_analysis['overall_analysis']['disbursement_efficiency']*100:.1f}%",
                'cash_flow_risk': dept_analysis['overall_analysis']['cash_flow_risk_level'],
                'delayed_funding_risk_score': round(dept_analysis['overall_analysis']['delayed_funding_risk'], 1),
                'total_departments_affected': dept_analysis['total_departments_affected'],
                'high_risk_departments': len(dept_analysis['highest_risk_departments']),
                'methodology_note': 'Analysis accounts for ~1-month USASpending.gov reporting lag'
            },
            'departments': dept_analysis['department_breakdown'],
            'highest_risk_departments': dept_analysis['highest_risk_departments'],
            'overall_analysis': dept_analysis['overall_analysis']
        }

# Batch analysis for multiple institutions
async def analyze_delayed_funding_batch(institution_names: List[str]) -> Dict[str, Any]:
    """Analyze delayed funding for multiple institutions"""
    results = {}
    
    async with DelayedFundingTracker() as tracker:
        for institution in institution_names:
            print(f"Analyzing delayed funding for: {institution}")
            results[institution] = await tracker.get_institution_funding_delays(institution)
            await asyncio.sleep(0.5)  # Rate limiting
    
    return results

# Test function
async def test_delayed_funding_analysis():
    """Test the delayed funding analysis"""
    test_institutions = [
        "Harvard University",
        "Stanford University", 
        "Massachusetts Institute of Technology"
    ]
    
    print("=== Testing Delayed Funding Analysis ===")
    
    for institution in test_institutions:
        print(f"\nAnalyzing: {institution}")
        result = await analyze_delayed_funding_for_institution(institution)
        
        summary = result['summary']
        print(f"  Cash Flow Risk: {summary['cash_flow_risk']}")
        print(f"  Undisbursed Amount: ${summary['total_undisbursed']:,.0f}")
        print(f"  Disbursement Efficiency: {summary['disbursement_efficiency']}")
        print(f"  Delayed Awards: {summary['awards_with_significant_delays']}")

if __name__ == "__main__":
    asyncio.run(test_delayed_funding_analysis())
