# Funding Data Architecture Update

## Summary
Successfully implemented funding data separation in `layoff_estimator.py` to optimize data quality for different use cases.

## New Architecture

### 1. Institution Analysis (`fetch_institution_grants`)
- **Sources**: NIH Reporter API + NSF Awards API (direct)
- **Use Case**: Detailed institution analysis, PI information, project details
- **Data Quality**: High-quality data with PI names, project titles, detailed metadata
- **Agencies**: NIH and NSF only
- **Benefits**: Rich metadata, reliable PI information, detailed project descriptions

### 2. Total Funding Calculations (`fetch_total_funding_grants`)
- **Sources**: USASpending.gov API
- **Use Case**: Funding resources, leaderboards, total active funding amounts
- **Data Quality**: Most accurate funding totals across all federal agencies
- **Agencies**: All federal agencies (NIH, NSF, DOD, DOE, NASA, USDA, EPA, etc.)
- **Benefits**: Comprehensive coverage, accurate funding amounts, official federal data

## Key Functions Updated

### New Functions
1. `fetch_institution_grants()` - NIH + NSF for detailed analysis
2. `fetch_total_funding_grants()` - USASpending.gov for comprehensive funding
3. `get_institution_total_funding()` - Summary funding data by agency

### Updated Functions
1. `estimate_institution_impact()` - Now uses both data sources appropriately
2. `analyze_pi_lab_impact()` - Uses institution grants for detailed PI analysis

### Legacy Function
- `fetch_combined_grants()` - Marked as deprecated, users should use specific functions

## File Updates

### Core Files
- **layoff_estimator.py**: New architecture implemented
- **main.py**: Updated to use appropriate functions
- **enhanced_main.py**: Updated endpoints and caching

### Test Results
- ✅ Institution analysis: 654 NIH grants with detailed metadata
- ✅ Total funding: $3.3B comprehensive funding from USASpending.gov
- ✅ Data separation working correctly
- ✅ Both APIs functioning independently

## Usage Guidelines

### For Institution/PI Analysis
```python
# Use this for detailed analysis with PI names and project info
grants = await fetch_institution_grants(organization="University of Chicago")
```

### For Funding Totals/Leaderboards
```python
# Use this for accurate funding amounts across all agencies
funding_data = await get_institution_total_funding("University of Chicago")
```

### For Full Analysis
```python
# This automatically uses both sources appropriately
analysis = await estimate_institution_impact("University of Chicago")
```

## Benefits of This Architecture

1. **Data Quality**: Each use case gets the best available data source
2. **Performance**: Focused queries reduce API overhead
3. **Accuracy**: Funding totals use the most comprehensive federal database
4. **Detail**: Institution analysis uses high-quality direct APIs
5. **Flexibility**: Easy to adjust sources per use case without affecting others

## Migration Notes

- Existing code using `fetch_combined_grants()` should migrate to specific functions
- Frontend funding displays will now use USASpending.gov data for accuracy
- Institution analysis pages will use NIH/NSF APIs for detailed information
- No breaking changes - legacy function still available but deprecated
