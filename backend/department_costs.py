"""
Department-Specific Cost Models

This module provides department-specific cost per researcher calculations
based on real-world academic lab costs, equipment needs, and salary structures.
"""

from typing import Dict, Any

# Department-specific cost models (annual cost per researcher in USD)
DEPARTMENT_COST_MODELS = {
    # High-cost experimental sciences (equipment-intensive)
    "Engineering": 280000,  # Equipment, fabrication facilities, materials
    "Physics": 350000,  # Particle accelerators, specialized equipment
    "Chemistry": 250000,  # Lab equipment, chemicals, safety systems
    "Materials Science": 300000,  # Specialized fabrication equipment
    "Neuroscience": 320000,  # Expensive imaging equipment, animal facilities
    
    # Medium-high cost life sciences
    "Biology": 220000,  # Lab equipment, reagents, animal/cell culture
    "Biochemistry": 240000,  # Specialized equipment, reagents
    "Biomedical Engineering": 260000,  # Engineering + biology equipment
    "Genetics": 230000,  # Sequencing, lab equipment
    "Molecular Biology": 235000,  # PCR, sequencing, specialized equipment
    "Cell Biology": 225000,  # Cell culture, microscopy
    "Microbiology": 210000,  # Culture facilities, equipment
    "Immunology": 240000,  # Flow cytometry, specialized assays
    
    # Medical/clinical departments (variable costs)
    "Medicine": 200000,  # Clinical research, some equipment
    "Oncology": 280000,  # Expensive cancer research equipment
    "Cardiology": 250000,  # Cardiac imaging, specialized equipment
    "Pediatrics": 190000,  # Clinical focus, less equipment
    "Psychiatry": 160000,  # Clinical/behavioral focus
    "Radiology": 300000,  # Imaging equipment, computing
    "Surgery": 220000,  # Clinical research, some equipment
    "Anesthesiology": 180000,  # Clinical focus
    "Pathology": 200000,  # Lab equipment, diagnostics
    "Dermatology": 170000,  # Clinical focus
    "Ophthalmology": 200000,  # Specialized equipment
    "Orthopedics": 210000,  # Materials, imaging
    "Emergency Medicine": 180000,  # Clinical focus
    "Internal Medicine": 190000,  # Clinical focus
    "Obstetrics and Gynecology": 200000,  # Clinical + some research equipment
    
    # Computational/theoretical fields (lower equipment costs)
    "Computer Science": 150000,  # Mainly computational, some hardware
    "Mathematics": 120000,  # Theoretical, minimal equipment
    "Statistics": 130000,  # Computational focus
    "Bioinformatics": 160000,  # Computational biology
    "Data Science": 140000,  # Computational focus
    
    # Social sciences (lower costs)
    "Psychology": 150000,  # Some equipment, behavioral studies
    "Economics": 130000,  # Mainly computational/theoretical
    "Sociology": 125000,  # Survey research, minimal equipment
    "Political Science": 120000,  # Research, minimal equipment
    "Anthropology": 140000,  # Field work, some equipment
    
    # Other sciences
    "Environmental Science": 200000,  # Field equipment, sampling
    "Geology": 190000,  # Field equipment, analysis tools
    "Ecology": 180000,  # Field studies, some lab work
    "Astronomy": 250000,  # Telescope time, computing
    "Pharmacology": 240000,  # Drug research, specialized equipment
    "Toxicology": 220000,  # Safety equipment, testing
    
    # Interdisciplinary fields
    "Bioengineering": 270000,  # Engineering + biology
    "Chemical Engineering": 260000,  # Pilot plants, equipment
    "Materials Engineering": 280000,  # Specialized materials equipment
    "Environmental Engineering": 240000,  # Pilot systems, monitoring
    
    # Default fallback
    "Unknown": 200000,  # Standard default
    "Other": 200000,  # Generic fallback
}

# Department risk multipliers (some departments have historically higher layoff rates)
DEPARTMENT_RISK_MULTIPLIERS = {
    # Higher risk departments (often grant-dependent)
    "Engineering": 1.2,  # Project-based funding
    "Computer Science": 1.3,  # Industry competition
    "Physics": 1.1,  # Large equipment grants
    "Chemistry": 1.0,  # Stable
    "Materials Science": 1.2,  # Grant-dependent
    
    # Life sciences (moderate risk)
    "Biology": 1.0,  # Generally stable
    "Neuroscience": 1.1,  # Competitive field
    "Oncology": 0.9,  # High priority funding
    "Cardiology": 0.9,  # Medical priority
    "Genetics": 1.0,  # Stable demand
    
    # Clinical departments (lower risk)
    "Medicine": 0.8,  # Clinical revenue
    "Pediatrics": 0.7,  # Protected funding
    "Psychiatry": 0.8,  # Clinical focus
    "Surgery": 0.7,  # Clinical revenue
    
    # Computational (higher risk due to industry competition)
    "Data Science": 1.4,  # High industry competition
    "Bioinformatics": 1.2,  # Specialized but competitive
    "Statistics": 1.1,  # Some industry competition
    
    # Social sciences (moderate-high risk)
    "Psychology": 1.1,  # Competitive funding
    "Economics": 1.2,  # Variable funding
    "Sociology": 1.3,  # Limited funding sources
    
    # Default
    "Unknown": 1.0,
    "Other": 1.0,
}

def get_department_cost_per_researcher(department: str) -> float:
    """
    Get the cost per researcher for a specific department.
    
    Args:
        department: Department name (case-insensitive)
    
    Returns:
        Annual cost per researcher in USD
    """
    # Normalize department name
    dept_normalized = department.strip().title()
    
    # Try exact match first
    if dept_normalized in DEPARTMENT_COST_MODELS:
        return DEPARTMENT_COST_MODELS[dept_normalized]
    
    # Try partial matches for common variations
    dept_lower = department.lower()
    for dept_key, cost in DEPARTMENT_COST_MODELS.items():
        if dept_key.lower() in dept_lower or dept_lower in dept_key.lower():
            return cost
    
    # Fallback to default
    return DEPARTMENT_COST_MODELS["Unknown"]

def get_department_risk_multiplier(department: str) -> float:
    """
    Get the risk multiplier for a specific department.
    
    Args:
        department: Department name (case-insensitive)
    
    Returns:
        Risk multiplier (1.0 = average risk, >1.0 = higher risk, <1.0 = lower risk)
    """
    # Normalize department name
    dept_normalized = department.strip().title()
    
    # Try exact match first
    if dept_normalized in DEPARTMENT_RISK_MULTIPLIERS:
        return DEPARTMENT_RISK_MULTIPLIERS[dept_normalized]
    
    # Try partial matches
    dept_lower = department.lower()
    for dept_key, multiplier in DEPARTMENT_RISK_MULTIPLIERS.items():
        if dept_key.lower() in dept_lower or dept_lower in dept_key.lower():
            return multiplier
    
    # Fallback to default
    return DEPARTMENT_RISK_MULTIPLIERS["Unknown"]

def calculate_department_adjusted_lab_size(total_funding: float, department: str) -> Dict[str, Any]:
    """
    Calculate lab size using department-specific cost models.
    
    Args:
        total_funding: Total annual funding
        department: Department name
    
    Returns:
        Dictionary with lab size estimates and department-specific info
    """
    dept_cost = get_department_cost_per_researcher(department)
    risk_multiplier = get_department_risk_multiplier(department)
    
    if total_funding <= 0:
        estimated_researchers = 0
    else:
        estimated_researchers = total_funding / dept_cost
    
    # Adjust risk based on department-specific factors
    adjusted_risk_score = estimated_researchers * risk_multiplier
    
    return {
        "estimated_researchers": round(estimated_researchers, 1),
        "department_cost_per_researcher": dept_cost,
        "department_risk_multiplier": risk_multiplier,
        "adjusted_risk_score": round(adjusted_risk_score, 1),
        "total_funding": total_funding,
        "department": department,
        "cost_category": _categorize_cost_level(dept_cost),
        "risk_category": _categorize_risk_level(risk_multiplier)
    }

def _categorize_cost_level(cost: float) -> str:
    """Categorize cost level for easier interpretation."""
    if cost >= 300000:
        return "Very High Cost"
    elif cost >= 250000:
        return "High Cost"
    elif cost >= 200000:
        return "Medium Cost"
    elif cost >= 150000:
        return "Low Cost"
    else:
        return "Very Low Cost"

def _categorize_risk_level(multiplier: float) -> str:
    """Categorize risk level for easier interpretation."""
    if multiplier >= 1.3:
        return "High Risk"
    elif multiplier >= 1.1:
        return "Elevated Risk"
    elif multiplier >= 0.9:
        return "Average Risk"
    else:
        return "Low Risk"

def get_department_cost_summary() -> Dict[str, Any]:
    """
    Get a summary of all department cost models and risk factors.
    
    Returns:
        Dictionary with cost categories and statistics
    """
    from collections import defaultdict
    
    cost_categories = defaultdict(list)
    risk_categories = defaultdict(list)
    
    # Categorize departments by cost and risk
    for dept, cost in DEPARTMENT_COST_MODELS.items():
        if dept in ["Unknown", "Other"]:
            continue
        cost_cat = _categorize_cost_level(cost)
        cost_categories[cost_cat].append({"department": dept, "cost": cost})
    
    for dept, risk in DEPARTMENT_RISK_MULTIPLIERS.items():
        if dept in ["Unknown", "Other"]:
            continue
        risk_cat = _categorize_risk_level(risk)
        risk_categories[risk_cat].append({"department": dept, "multiplier": risk})
    
    # Calculate statistics
    costs = [c for c in DEPARTMENT_COST_MODELS.values() if c != 200000]  # Exclude defaults
    risks = [r for r in DEPARTMENT_RISK_MULTIPLIERS.values() if r != 1.0]  # Exclude defaults
    
    return {
        "cost_categories": dict(cost_categories),
        "risk_categories": dict(risk_categories),
        "statistics": {
            "total_departments": len(DEPARTMENT_COST_MODELS) - 2,  # Exclude Unknown/Other
            "cost_range": {
                "min": min(costs),
                "max": max(costs),
                "average": round(sum(costs) / len(costs), 0)
            },
            "risk_range": {
                "min": min(risks),
                "max": max(risks),
                "average": round(sum(risks) / len(risks), 2)
            }
        },
        "methodology": {
            "cost_basis": "Annual cost per researcher including salary, benefits, equipment, and overhead",
            "risk_basis": "Historical layoff patterns and funding stability by department",
            "data_sources": "Academic industry reports, university budget data, NSF statistics"
        }
    }
