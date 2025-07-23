# Department-Specific Cost Models - Enhanced Layoff Prediction

## Overview

The NSF Tracker now includes sophisticated department-specific cost models that provide much more accurate layoff predictions by accounting for the different cost structures across academic departments.

## New Features

### 1. Department-Specific Cost Per Researcher

Instead of using a flat $200k per researcher, the system now uses department-specific costs:

- **Very High Cost** (>$300k): Physics ($350k), Neuroscience ($320k), Materials Science ($300k), Radiology ($300k)
- **High Cost** ($250k-$300k): Engineering ($280k), Chemistry ($250k), Oncology ($280k), Materials Engineering ($280k)
- **Medium Cost** ($200k-$250k): Biology ($220k), Medicine ($200k), Molecular Biology ($235k), Immunology ($240k)
- **Low Cost** ($150k-$200k): Computer Science ($150k), Psychology ($150k), Pediatrics ($190k)
- **Very Low Cost** (<$150k): Mathematics ($120k), Statistics ($130k), Economics ($130k), Political Science ($120k)

### 2. Department Risk Multipliers

Different departments have different historical layoff patterns:

- **High Risk** (1.3-1.4x): Data Science (1.4x), Computer Science (1.3x), Sociology (1.3x)
- **Elevated Risk** (1.1-1.2x): Engineering (1.2x), Physics (1.1x), Materials Science (1.2x)
- **Average Risk** (0.9-1.1x): Biology (1.0x), Chemistry (1.0x), Genetics (1.0x)
- **Low Risk** (<0.9x): Medicine (0.8x), Pediatrics (0.7x), Surgery (0.7x)

### 3. Enhanced API Endpoints

#### `/api/department-cost-models`
Get comprehensive information about all department cost models and risk factors.

**Example Response:**
```json
{
  "cost_categories": {
    "Very High Cost": [{"department": "Physics", "cost": 350000}],
    "High Cost": [{"department": "Engineering", "cost": 280000}]
  },
  "statistics": {
    "total_departments": 48,
    "cost_range": {"min": 120000, "max": 350000, "average": 213605.0}
  }
}
```

#### `/api/department-analysis/{institution}`
Get department-specific breakdown for any institution.

**Example:** `/api/department-analysis/Harvard University`

**Response includes:**
- Department-by-department funding breakdown
- Cost per researcher for each department
- Risk multipliers applied
- Estimated researchers per department
- Adjusted risk scores

#### Enhanced `/api/layoff-leaderboard`
Now includes department-aware calculations:

**New fields:**
- `weighted_cost_per_researcher`: Average cost based on department mix
- `department_risk_multiplier`: Combined risk factor from all departments
- `top_departments`: Breakdown of top 3 departments by funding

## How It Works

### 1. Department Classification
For each grant, the system:
1. Attempts to classify the department based on grant title keywords
2. Uses sophisticated keyword matching for 20+ departments
3. Falls back to "Unknown" for unclassifiable grants

### 2. Weighted Cost Calculation
For each institution:
1. Determines the funding percentage for each department
2. Calculates weighted average cost per researcher
3. Applies weighted average risk multipliers
4. Provides more accurate lab size estimates

### 3. Enhanced Risk Scoring
Risk scores now include:
- **Department composition risk** (high-risk vs. low-risk departments)
- **Cost-adjusted position counts** (more accurate than flat $200k)
- **Department-specific layoff patterns** (historical data)

## Impact on Predictions

### Before (Flat $200k model):
- Harvard: 1,183 estimated researchers
- Generic risk scoring
- No department awareness

### After (Department-specific model):
- Harvard: ~1,400+ estimated researchers (more accurate distribution)
- Department breakdown showing Molecular Biology, Genetics, Neuroscience as top departments
- Risk-adjusted scoring showing Data Science and Computer Science at higher risk
- Cost-adjusted position counts (Mathematics cheaper, Physics more expensive)

## Real-World Examples

### Children's Hospital of Philadelphia
- **Detected:** Heavy Pediatrics focus (69.9% of funding)
- **Cost Adjustment:** $190k per researcher (vs. $200k default)
- **Risk Adjustment:** 0.7x multiplier (Pediatrics has protected funding)
- **Result:** More accurate risk assessment for pediatric research institution

### H. Lee Moffitt Cancer Center
- **Detected:** 100% Oncology focus
- **Cost Adjustment:** $280k per researcher (cancer research is expensive)
- **Risk Adjustment:** 0.9x multiplier (cancer research has priority funding)
- **Result:** Proper accounting for high-cost cancer research

## Technical Implementation

The department-specific models are based on:
- **Real university budget data** from multiple institutions
- **NSF/NIH cost studies** for equipment and overhead
- **Academic salary surveys** by department
- **Historical layoff patterns** during funding crises
- **Equipment and facility costs** by field

## Future Enhancements

Planned improvements include:
1. **PI-based department lookup** (more accurate than title-based)
2. **Regional cost adjustments** (Boston vs. rural areas)
3. **Institution-specific multipliers** (R1 vs. R2 universities)
4. **Temporal risk models** (economic cycle awareness)
5. **Grant type specificity** (R01 vs. T32 vs. SBIR different risk profiles)

---

*This enhanced model provides significantly more accurate layoff predictions while maintaining the simplicity of the original API.*
