#!/usr/bin/env python3
"""
HHS Terminated Grants Parser
Fetches and parses the official HHS terminated grants PDF data

Based on TAGGS system: https://taggs.hhs.gov/Content/Data/HHS_Grants_Terminated.pdf
"""

import httpx
import asyncio
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any
import re
import io
import PyPDF2
import camelot
import tabula

class HHSTerminatedGrantsParser:
    """
    Parser for official HHS terminated grants data from TAGGS system
    """
    
    def __init__(self):
        self.pdf_url = "https://taggs.hhs.gov/Content/Data/HHS_Grants_Terminated.pdf"
        self.cache_file = "hhs_terminated_grants_cache.json"
        
    async def fetch_terminated_grants_pdf(self) -> bytes:
        """
        Fetch the official HHS terminated grants PDF
        """
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                print(f"🔍 Fetching HHS terminated grants PDF from: {self.pdf_url}")
                response = await client.get(self.pdf_url)
                response.raise_for_status()
                
                if response.headers.get('content-type', '').startswith('application/pdf'):
                    print(f"✅ Successfully fetched PDF ({len(response.content)} bytes)")
                    return response.content
                else:
                    print(f"⚠️ Unexpected content type: {response.headers.get('content-type')}")
                    return response.content
                    
        except httpx.RequestError as e:
            print(f"❌ Network error fetching PDF: {e}")
            raise
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error fetching PDF: {e.response.status_code}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error fetching PDF: {e}")
            raise
    
    def parse_pdf_with_tabula(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Parse PDF using tabula-py (requires Java)
        """
        try:
            print("🔍 Attempting to parse PDF with tabula...")
            
            # Save PDF content to temporary file
            with open("/tmp/hhs_terminated.pdf", "wb") as f:
                f.write(pdf_content)
            
            # Read tables from PDF
            tables = tabula.read_pdf("/tmp/hhs_terminated.pdf", pages='all', multiple_tables=True)
            
            terminated_grants = []
            
            for i, df in enumerate(tables):
                print(f"📊 Table {i+1}: {df.shape[0]} rows, {df.shape[1]} columns")
                print(f"Columns: {list(df.columns)}")
                
                # Convert DataFrame to grant records
                for _, row in df.iterrows():
                    grant_record = self._extract_grant_from_row(row, table_index=i)
                    if grant_record:
                        terminated_grants.append(grant_record)
            
            print(f"✅ Extracted {len(terminated_grants)} terminated grants from PDF")
            return terminated_grants
            
        except Exception as e:
            print(f"❌ Error parsing PDF with tabula: {e}")
            return []
    
    def parse_pdf_with_camelot(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Parse PDF using camelot (alternative parser)
        """
        try:
            print("🔍 Attempting to parse PDF with camelot...")
            
            # Save PDF content to temporary file
            with open("/tmp/hhs_terminated.pdf", "wb") as f:
                f.write(pdf_content)
            
            # Read tables from PDF
            tables = camelot.read_pdf("/tmp/hhs_terminated.pdf", pages='all')
            
            terminated_grants = []
            
            for i, table in enumerate(tables):
                df = table.df
                print(f"📊 Table {i+1}: {df.shape[0]} rows, {df.shape[1]} columns")
                print(f"Accuracy: {table.accuracy:.2f}%")
                
                # Convert DataFrame to grant records
                for _, row in df.iterrows():
                    grant_record = self._extract_grant_from_row(row, table_index=i)
                    if grant_record:
                        terminated_grants.append(grant_record)
            
            print(f"✅ Extracted {len(terminated_grants)} terminated grants from PDF")
            return terminated_grants
            
        except Exception as e:
            print(f"❌ Error parsing PDF with camelot: {e}")
            return []
    
    def parse_pdf_with_pypdf2(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Fallback: Parse PDF text using PyPDF2
        """
        try:
            print("🔍 Attempting to parse PDF with PyPDF2 (text extraction)...")
            
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            full_text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                full_text += page.extract_text() + "\n"
            
            print(f"📄 Extracted {len(full_text)} characters of text")
            
            # Parse text for grant information
            terminated_grants = self._parse_text_for_grants(full_text)
            
            print(f"✅ Extracted {len(terminated_grants)} terminated grants from text")
            return terminated_grants
            
        except Exception as e:
            print(f"❌ Error parsing PDF with PyPDF2: {e}")
            return []
    
    def _extract_grant_from_row(self, row, table_index: int = 0) -> Dict[str, Any]:
        """
        Extract grant information from a table row
        """
        try:
            # Common column patterns to look for
            grant_record = {
                'source': 'HHS_TAGGS_Terminated',
                'table_index': table_index,
                'raw_data': dict(row),
                'termination_reason': 'Official HHS Terminated Grants List'
            }
            
            # Try to identify common columns
            row_dict = dict(row)
            columns = [str(col).lower() for col in row_dict.keys()]
            
            # Look for grant number/ID
            for col, value in row_dict.items():
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['grant', 'award', 'number', 'id']):
                    grant_record['project_num'] = str(value).strip()
                elif any(keyword in col_lower for keyword in ['recipient', 'grantee', 'organization']):
                    grant_record['organization'] = {'org_name': str(value).strip()}
                elif any(keyword in col_lower for keyword in ['pi', 'investigator', 'contact']):
                    grant_record['contact_pi_name'] = str(value).strip()
                elif any(keyword in col_lower for keyword in ['amount', 'funding', 'dollar']):
                    try:
                        # Extract numeric value
                        amount_str = str(value).replace('$', '').replace(',', '').strip()
                        grant_record['award_amount'] = float(amount_str)
                    except:
                        pass
                elif any(keyword in col_lower for keyword in ['title', 'project', 'description']):
                    grant_record['project_title'] = str(value).strip()
                elif any(keyword in col_lower for keyword in ['date', 'terminated', 'ended']):
                    grant_record['termination_date'] = str(value).strip()
            
            # Only return if we have at least a grant number or organization
            if grant_record.get('project_num') or grant_record.get('organization'):
                return grant_record
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting grant from row: {e}")
            return None
    
    def _parse_text_for_grants(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse raw text for grant information using regex patterns
        """
        terminated_grants = []
        
        try:
            # Split text into lines
            lines = text.split('\n')
            
            # Look for grant number patterns (common HHS formats)
            grant_patterns = [
                r'[1-9][A-Z]\d{2}[A-Z]{2}\d{6}-\d{2}[A-Z]?\d?',  # NIH format
                r'[A-Z]{2,3}-\d{4,6}',  # CDC/HRSA format
                r'\d{4}-\d{4,6}',  # General HHS format
            ]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for grant numbers
                for pattern in grant_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        grant_record = {
                            'source': 'HHS_TAGGS_Terminated',
                            'project_num': match,
                            'raw_text_line': line,
                            'termination_reason': 'Official HHS Terminated Grants List'
                        }
                        
                        # Try to extract additional info from the same line
                        if '$' in line:
                            amount_match = re.search(r'\$[\d,]+', line)
                            if amount_match:
                                try:
                                    amount_str = amount_match.group().replace('$', '').replace(',', '')
                                    grant_record['award_amount'] = float(amount_str)
                                except:
                                    pass
                        
                        terminated_grants.append(grant_record)
            
            return terminated_grants
            
        except Exception as e:
            print(f"❌ Error parsing text for grants: {e}")
            return []
    
    async def get_terminated_grants(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get terminated grants data, using cache if available and recent
        """
        # Check cache first
        if use_cache:
            try:
                with open(self.cache_file, 'r') as f:
                    cached_data = json.load(f)
                    cache_date = datetime.fromisoformat(cached_data['cached_at'])
                    
                    # Use cache if less than 24 hours old
                    if (datetime.now() - cache_date).total_seconds() < 86400:
                        print(f"✅ Using cached HHS terminated grants data ({len(cached_data['grants'])} grants)")
                        return cached_data['grants']
            except:
                pass
        
        # Fetch fresh data
        try:
            pdf_content = await self.fetch_terminated_grants_pdf()
            
            # Try multiple parsing methods
            terminated_grants = []
            
            # Method 1: tabula (best for tables)
            try:
                terminated_grants = self.parse_pdf_with_tabula(pdf_content)
                if terminated_grants:
                    print(f"✅ Successfully parsed {len(terminated_grants)} grants with tabula")
                else:
                    raise Exception("No grants found with tabula")
            except Exception as e:
                print(f"⚠️ Tabula parsing failed: {e}")
                
                # Method 2: camelot (alternative table parser)
                try:
                    terminated_grants = self.parse_pdf_with_camelot(pdf_content)
                    if terminated_grants:
                        print(f"✅ Successfully parsed {len(terminated_grants)} grants with camelot")
                    else:
                        raise Exception("No grants found with camelot")
                except Exception as e:
                    print(f"⚠️ Camelot parsing failed: {e}")
                    
                    # Method 3: PyPDF2 text extraction (fallback)
                    terminated_grants = self.parse_pdf_with_pypdf2(pdf_content)
                    if terminated_grants:
                        print(f"✅ Successfully parsed {len(terminated_grants)} grants with PyPDF2")
            
            # Cache the results
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'grants': terminated_grants,
                'source_url': self.pdf_url
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"💾 Cached {len(terminated_grants)} terminated grants")
            return terminated_grants
            
        except Exception as e:
            print(f"❌ Error fetching terminated grants: {e}")
            # Return empty list if all methods fail
            return []
    
    def filter_terminated_grants_by_institution(self, terminated_grants: List[Dict[str, Any]], institution_name: str) -> List[Dict[str, Any]]:
        """
        Filter terminated grants by institution
        """
        filtered_grants = []
        institution_upper = institution_name.upper()
        institution_keywords = institution_upper.split()
        
        for grant in terminated_grants:
            # Check organization name
            org_name = ""
            if isinstance(grant.get('organization'), dict):
                org_name = grant['organization'].get('org_name', '').upper()
            elif grant.get('organization'):
                org_name = str(grant['organization']).upper()
            
            # Check raw text for institution mentions
            raw_text = grant.get('raw_text_line', '').upper()
            
            # Institution matching
            is_match = False
            
            # Exact match
            if institution_upper in org_name or institution_upper in raw_text:
                is_match = True
            # Keyword matching (require at least 2 significant keywords)
            elif len(institution_keywords) >= 2:
                common_words = {'THE', 'OF', 'AT', 'AND', 'FOR', 'UNIVERSITY', 'COLLEGE'}
                significant_keywords = [k for k in institution_keywords if k not in common_words and len(k) > 3]
                
                if len(significant_keywords) >= 2:
                    matches = sum(1 for keyword in significant_keywords if keyword in org_name or keyword in raw_text)
                    if matches >= 2:
                        is_match = True
            
            if is_match:
                filtered_grants.append(grant)
        
        print(f"🎯 Found {len(filtered_grants)} terminated grants for {institution_name}")
        return filtered_grants

async def test_hhs_parser():
    """
    Test the HHS terminated grants parser
    """
    parser = HHSTerminatedGrantsParser()
    
    print("=== Testing HHS Terminated Grants Parser ===\n")
    
    # Test fetching terminated grants
    terminated_grants = await parser.get_terminated_grants(use_cache=False)
    
    if terminated_grants:
        print(f"✅ Successfully fetched {len(terminated_grants)} terminated grants")
        
        # Show sample data
        print("\n📊 Sample terminated grants:")
        for i, grant in enumerate(terminated_grants[:3]):
            print(f"  {i+1}. Grant: {grant.get('project_num', 'Unknown')}")
            print(f"     Org: {grant.get('organization', {}).get('org_name', 'Unknown')}")
            print(f"     Amount: ${grant.get('award_amount', 0):,.0f}")
            print(f"     Source: {grant.get('source', 'Unknown')}")
            print()
        
        # Test filtering by institution
        uchicago_grants = parser.filter_terminated_grants_by_institution(
            terminated_grants, 
            "University of Chicago"
        )
        
        if uchicago_grants:
            print(f"🎯 Found {len(uchicago_grants)} terminated grants for University of Chicago:")
            for grant in uchicago_grants[:5]:
                print(f"  • {grant.get('project_num', 'Unknown')}: ${grant.get('award_amount', 0):,.0f}")
        else:
            print("⚠️ No terminated grants found for University of Chicago")
    
    else:
        print("❌ No terminated grants data found")

if __name__ == "__main__":
    asyncio.run(test_hhs_parser())
