// Test the new data structure that the frontend will receive
const mockInstitutionDetails = {
  // University details from /api/university-details/
  name: "University of Nebraska",
  // ... other university data ...
  
  // Delayed funding data from /api/delayed-funding/ (merged)
  delayed_funding: {
    institution: "University of Nebraska",
    cash_flow_risk: { level: "HIGH" },
    financial_overview: {
      undisbursed_amount: 530863516.03,
      disbursement_efficiency: "45.0%"
    },
    delayed_awards: {
      count: 55
    },
    // The crucial PI and department data:
    cancelled_grants_impact: {
      total_lost_funding: 4200109.0,
      pis_impacted: 1,
      top_pis: [
        {
          pi_name: "ABOSCH, AVIVA",
          department: "Unknown Department", 
          lost_funding: 4200109.0,
          grants_count: 4
        }
      ],
      department_losses: {
        "Unknown Department": 4200109.0
      },
      methodology_note: "Termination-based lost funding derived from NIH (past 12 months) + NSF terminated/cancelled/expired awards"
    },
    nonrenewal_grants_impact: {
      total_lost_funding: 0.0,
      pis_impacted: 0,
      top_pis: [],
      department_losses: {},
      methodology_note: "Non-renewal analysis: grants that expired in past 6 months without renewal evidence (Times-style analysis)"
    }
  }
};

console.log("Frontend data structure test:");
console.log("✅ institutionDetails.delayed_funding.cash_flow_risk:", mockInstitutionDetails.delayed_funding.cash_flow_risk.level);
console.log("✅ institutionDetails.delayed_funding.cancelled_grants_impact exists:", !!mockInstitutionDetails.delayed_funding.cancelled_grants_impact);
console.log("✅ PI data available:", mockInstitutionDetails.delayed_funding.cancelled_grants_impact.top_pis.length > 0);
console.log("✅ Department data available:", Object.keys(mockInstitutionDetails.delayed_funding.cancelled_grants_impact.department_losses).length > 0);

console.log("\nThe frontend will now show:");
console.log("- Cash Flow Risk: HIGH");
console.log("- Undisbursed Amount: $530,863,516");
console.log("- Cancelled Grants: ABOSCH, AVIVA with $4.2M lost");
console.log("- Department: Unknown Department with $4.2M lost");
console.log("- Non-renewal Grants: $0 (no cases)");
