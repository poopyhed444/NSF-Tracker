#!/usr/bin/env python3
"""
Delayed Funding Tracker

This module tracks delayed or undisbursed funding by comparing:
1. Awarded amounts vs. actual disbursements
2. Expected funding timelines vs. actual disbursement dates
3. Funding gaps that could indicate cash flow issues for institutions

Uses USASpending.gov's disbursement API to track actual money flow.
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
                            "end_date": "2025-12-31"
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
    
    def analyze_funding_delays_by_department(self, disbursement_data: List[Dict[str, Any]], pi_cache: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
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
            
            # Try to extract PI name from award description or use recipient contact info
            pi_name = self._extract_pi_from_award(award)
            
            # Match PI to department
            department = match_pi_to_department(pi_name, institution_name, pi_cache) if pi_name else "Unknown Department"
            
            # Calculate disbursement metrics for this award
            disbursement_rate = outlayed / awarded if awarded > 0 else 0
            is_delayed = disbursement_rate < 0.5 and awarded > 10000  # Consider significant awards
            
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
    
    def _extract_pi_from_award(self, award: Dict[str, Any]) -> str:
        """Extract PI name from award data"""
        # USASpending.gov doesn't typically include PI names in the main award data
        # For now, we'll return None and rely on the department matching logic
        # to handle "Unknown Department" cases
        
        # Could potentially be enhanced by cross-referencing with NIH/NSF grant databases
        # that do contain PI information
        return None
    
    def analyze_funding_delays(self, disbursement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding delays and disbursement gaps"""
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
            'delayed_awards_count': 0
        }
        
        if not disbursement_data:
            return analysis
        
        for award in disbursement_data:
            awarded = float(award.get('Award Amount', 0) or 0)
            obligated = float(award.get('Obligated Amount', 0) or 0)
            outlayed = float(award.get('Outlayed Amount', 0) or 0)
            
            analysis['total_awarded_amount'] += awarded
            analysis['total_obligated_amount'] += obligated
            analysis['total_outlayed_amount'] += outlayed
            
            # Calculate disbursement delay
            if awarded > 0:
                disbursement_rate = outlayed / awarded
                obligation_rate = obligated / awarded
                
                # Flag awards with significant delays (less than 50% disbursed after obligation)
                if obligation_rate > 0.1 and disbursement_rate < 0.5:
                    delay_severity = 1 - disbursement_rate
                    analysis['awards_with_delays'].append({
                        'award_id': award.get('Award ID'),
                        'award_amount': awarded,
                        'obligated_amount': obligated,
                        'outlayed_amount': outlayed,
                        'disbursement_rate': disbursement_rate,
                        'delay_severity': delay_severity,
                        'description': award.get('Award Description', ''),
                        'agency': award.get('Awarding Agency', ''),
                        'start_date': award.get('Start Date', ''),
                        'undisbursed_amount': awarded - outlayed
                    })
                    analysis['delayed_awards_count'] += 1
        
        # Calculate overall metrics
        if analysis['total_awarded_amount'] > 0:
            analysis['disbursement_efficiency'] = analysis['total_outlayed_amount'] / analysis['total_awarded_amount']
            analysis['undisbursed_amount'] = analysis['total_awarded_amount'] - analysis['total_outlayed_amount']
            
            # Calculate delayed funding risk score (0-100)
            undisbursed_rate = analysis['undisbursed_amount'] / analysis['total_awarded_amount']
            delay_frequency = analysis['delayed_awards_count'] / analysis['total_awards']
            
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
        
        # Sort delayed awards by severity
        analysis['awards_with_delays'].sort(key=lambda x: x['delay_severity'], reverse=True)
        
        return analysis
    
    async def get_institution_funding_delays(self, institution_name: str) -> Dict[str, Any]:
        """Get complete funding delay analysis for an institution"""
        disbursement_data = await self.get_institution_disbursements(institution_name)
        analysis = self.analyze_funding_delays(disbursement_data)
        
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
                'awards_with_significant_delays': analysis['delayed_awards_count']
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
        
        # Get department-level analysis
        dept_analysis = tracker.analyze_funding_delays_by_department(
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
                'high_risk_departments': len(dept_analysis['highest_risk_departments'])
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
