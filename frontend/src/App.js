import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const [institutionDetails, setInstitutionDetails] = useState(null);
  const [delayedFundingData, setDelayedFundingData] = useState(null);
  const [delayedFundingDepartments, setDelayedFundingDepartments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [delayedFundingLoading, setDelayedFundingLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showDelayedFundingAnalysis, setShowDelayedFundingAnalysis] = useState(false);
  const [showDepartmentDelayedFunding, setShowDepartmentDelayedFunding] = useState(false);
  
  // PI Details Modal State
  const [selectedPi, setSelectedPi] = useState(null);
  const [piDetails, setPiDetails] = useState(null);
  const [piDetailsLoading, setPiDetailsLoading] = useState(false);
  const [showPiModal, setShowPiModal] = useState(false);

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get('/api/layoff-leaderboard?limit=25');
      setLeaderboardData(response.data);
      setLastUpdated(new Date().toLocaleString());
    } catch (err) {
      setError(`Failed to fetch data: ${err.message}`);
      console.error('Error fetching leaderboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchInstitutionDetails = async (institutionName) => {
    try {
      setDetailsLoading(true);
      setError(null);
      
      // Fetch both university details and delayed funding data
      const [detailsResponse, delayedFundingResponse] = await Promise.all([
        axios.get(`/api/university-details/${encodeURIComponent(institutionName)}`),
        axios.get(`/api/delayed-funding/${encodeURIComponent(institutionName)}`)
      ]);
      
      // Map the delayed funding response to the expected structure
      const delayedFundingData = delayedFundingResponse.data;
      const mappedDelayedFunding = {
        undisbursed_amount: delayedFundingData.disbursement_analysis?.summary?.total_undisbursed || 0,
        disbursement_efficiency: delayedFundingData.disbursement_analysis?.summary?.disbursement_efficiency || 'N/A',
        delayed_awards_count: delayedFundingData.disbursement_analysis?.summary?.awards_with_significant_delays || 0,
        cash_flow_risk: {
          level: delayedFundingData.overall_risk_level || 'UNKNOWN'
        },
        note: delayedFundingData.disbursement_analysis?.summary?.total_undisbursed === 0 ? 
              "No cancelled grants found for this institution, or department information not available." : null,
        // Map cancelled grants data from delayed funding response and fix field mapping
        cancelled_grants_impact: delayedFundingData.cancelled_grants_impact ? {
          ...delayedFundingData.cancelled_grants_impact,
          // Map top_affected_pis to top_pis for frontend compatibility
          top_pis: delayedFundingData.cancelled_grants_impact.top_affected_pis || []
        } : null,
        // Map non-renewal grants data from delayed funding response and fix field mapping
        nonrenewal_grants_impact: delayedFundingData.nonrenewal_grants_impact ? {
          ...delayedFundingData.nonrenewal_grants_impact,
          // Map top_affected_pis to top_pis for frontend compatibility
          top_pis: delayedFundingData.nonrenewal_grants_impact.top_affected_pis || []
        } : null
      };
      
      // Merge the delayed funding data into institution details
      const mergedData = {
        ...detailsResponse.data,
        delayed_funding: mappedDelayedFunding,
        // Add departments from cancelled grants analysis for the departments section
        departments: mappedDelayedFunding.cancelled_grants_impact?.department_losses ? 
          Object.entries(mappedDelayedFunding.cancelled_grants_impact.department_losses).map(([dept, amount]) => ({
            department: dept,
            total_terminated_funding: amount,
            grants_count: 0, // Will be populated if we have more detailed data
            unique_pis: 0    // Will be populated if we have more detailed data
          })) : []
      };
      
      setInstitutionDetails(mergedData);
    } catch (err) {
      setError(`Failed to fetch institution details: ${err.message}`);
      console.error('Error fetching institution details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const fetchDelayedFundingAnalysis = async (institutionName) => {
    try {
      setDelayedFundingLoading(true);
      setError(null);
      
      const response = await axios.get(`/api/enhanced-delayed-funding/${encodeURIComponent(institutionName)}`);
      setDelayedFundingData(response.data);
      setShowDelayedFundingAnalysis(true);
    } catch (err) {
      setError(`Failed to fetch delayed funding analysis: ${err.message}`);
      console.error('Error fetching delayed funding analysis:', err);
    } finally {
      setDelayedFundingLoading(false);
    }
  };

  const fetchDelayedFundingByDepartments = async (institutionName) => {
    try {
      setDelayedFundingLoading(true);
      setError(null);
      
      const response = await axios.get(`/api/delayed-funding-departments/${encodeURIComponent(institutionName)}`);
      setDelayedFundingDepartments(response.data);
      setShowDepartmentDelayedFunding(true);
    } catch (err) {
      setError(`Failed to fetch delayed funding by departments: ${err.message}`);
      console.error('Error fetching delayed funding by departments:', err);
    } finally {
      setDelayedFundingLoading(false);
    }
  };

  const downloadDelayedFundingCSV = async (institutionName) => {
    try {
      // Try to use the CSV endpoint first
      try {
        const response = await axios.get(`/api/enhanced-delayed-funding/${encodeURIComponent(institutionName)}/csv`, {
          responseType: 'blob'
        });
        
        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        
        // Generate filename
        const safeInstitutionName = institutionName.replace(/[^a-zA-Z0-9\s\-_]/g, '').trim();
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        link.setAttribute('download', `enhanced_funding_analysis_${safeInstitutionName}_${timestamp}.csv`);
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        link.remove();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        
      } catch (csvError) {
        // Fallback: generate CSV from analysis data
        console.log('CSV endpoint failed, generating from analysis data:', csvError);
        
        // Get the analysis data
        const response = await axios.get(`/api/enhanced-delayed-funding/${encodeURIComponent(institutionName)}`);
        const analysisData = response.data;
        
        // Generate CSV content manually
        let csvContent = "Enhanced Delayed Funding Analysis Report\n";
        csvContent += `Institution:,${institutionName}\n`;
        csvContent += `Generated:,${new Date().toLocaleString()}\n\n`;
        
        // Summary
        csvContent += "SUMMARY METRICS\n";
        csvContent += "Metric,Value\n";
        
        const summary = analysisData.summary || analysisData.overview || analysisData.financial_overview || {};
        const undisbursed = summary.total_undisbursed || summary.undisbursed_amount || 0;
        const efficiency = summary.disbursement_efficiency || '0.0%';
        
        csvContent += `Total Undisbursed Amount,"$${isNaN(undisbursed) ? 0 : undisbursed.toLocaleString()}"\n`;
        csvContent += `Disbursement Efficiency,${efficiency}\n`;
        
        // Create and download
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        const safeInstitutionName = institutionName.replace(/[^a-zA-Z0-9\s\-_]/g, '').trim();
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        link.setAttribute('download', `enhanced_funding_analysis_${safeInstitutionName}_${timestamp}.csv`);
        
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      }
      
    } catch (err) {
      setError(`Failed to download CSV: ${err.message}`);
      console.error('Error downloading CSV:', err);
    }
  };

  const fetchPiDetails = async (piName, institutionName) => {
    try {
      setPiDetailsLoading(true);
      setError(null);
      
      const response = await axios.get(`/api/pi-grant-details/${encodeURIComponent(institutionName)}/${encodeURIComponent(piName)}`);
      setPiDetails(response.data);
      setSelectedPi(piName);
      setShowPiModal(true);
    } catch (err) {
      setError(`Failed to fetch PI details: ${err.message}`);
      console.error('Error fetching PI details:', err);
    } finally {
      setPiDetailsLoading(false);
    }
  };

  const closePiModal = () => {
    setShowPiModal(false);
    setSelectedPi(null);
    setPiDetails(null);
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const formatCurrency = (amount) => {
    // Handle NaN, null, undefined, and invalid values
    if (amount == null || isNaN(amount) || amount === '' || typeof amount === 'string') {
      return '$0';
    }
    
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const getRiskBadgeClass = (riskLevel) => {
    const level = riskLevel.toLowerCase();
    return `risk-badge risk-${level}`;
  };

  const exportToCSV = () => {
    if (!leaderboardData?.institutions) return;

    const headers = [
      'Institution',
      'Risk Level',
      'Risk Score',
      'At-Risk Positions',
      'Recently Lost Positions',
      'Total Lab Size',
      'Funding Cliff %',
      'Active Funding',
      'Active Grants Count',
      'Terminated Grants Count',
      'Top Departments',
      'NIH Funding',
      'NSF Funding',
      'DoD Funding',
      'DoE Funding',
      'NIH Percentage',
      'NSF Percentage',
      'DoD Percentage',
      'DoE Percentage'
    ];

    const csvData = leaderboardData.institutions.map(institution => [
      institution.institution,
      institution.risk_level,
      institution.risk_score,
      institution.at_risk_positions,
      institution.recently_lost_positions,
      institution.estimated_lab_size,
      institution.funding_cliff_percentage,
      institution.total_active_funding,
      institution.active_grants_count,
      institution.terminated_grants_count,
      institution.top_departments?.map(d => `${d.department} (${d.percentage}%)`).join('; ') || '',
      institution.funding_diversification?.nih_funding || 0,
      institution.funding_diversification?.nsf_funding || 0,
      institution.funding_diversification?.dod_funding || 0,
      institution.funding_diversification?.doe_funding || 0,
      institution.funding_diversification?.nih_percentage || 0,
      institution.funding_diversification?.nsf_percentage || 0,
      institution.funding_diversification?.dod_percentage || 0,
      institution.funding_diversification?.doe_percentage || 0
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => 
        typeof cell === 'string' && cell.includes(',') ? `"${cell}"` : cell
      ).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `layoff-risk-leaderboard-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportAllToCSV = async () => {
    try {
      setLoading(true);
      
      // Fetch all data with a high limit
      const response = await axios.get('/api/layoff-leaderboard?limit=1000');
      const allData = response.data;

      if (!allData?.data) {
        alert('No data available for export');
        return;
      }

      const headers = [
        'Institution',
        'Risk Level',
        'Risk Score',
        'At-Risk Positions',
        'Recently Lost Positions',
        'Total Lab Size',
        'Funding Cliff %',
        'Active Funding',
        'Active Grants Count',
        'Terminated Grants Count',
        'Top Departments',
        'NIH Funding',
        'NSF Funding',
        'DoD Funding',
        'DoE Funding',
        'NIH Percentage',
        'NSF Percentage',
        'DoD Percentage',
        'DoE Percentage'
      ];

      const csvData = allData.institutions.map(institution => [
        institution.institution,
        institution.risk_level,
        institution.risk_score,
        institution.at_risk_positions,
        institution.recently_lost_positions,
        institution.estimated_lab_size,
        institution.funding_cliff_percentage,
        institution.total_active_funding,
        institution.active_grants_count,
        institution.terminated_grants_count,
        institution.top_departments?.map(d => `${d.department} (${d.percentage}%)`).join('; ') || '',
        institution.funding_diversification?.nih_funding || 0,
        institution.funding_diversification?.nsf_funding || 0,
        institution.funding_diversification?.dod_funding || 0,
        institution.funding_diversification?.doe_funding || 0,
        institution.funding_diversification?.nih_percentage || 0,
        institution.funding_diversification?.nsf_percentage || 0,
        institution.funding_diversification?.dod_percentage || 0,
        institution.funding_diversification?.doe_percentage || 0
      ]);

      const csvContent = [
        headers.join(','),
        ...csvData.map(row => row.map(cell => 
          typeof cell === 'string' && cell.includes(',') ? `"${cell}"` : cell
        ).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `complete-layoff-risk-analysis-${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      alert(`Successfully exported ${allData.data.length} institutions to CSV`);

    } catch (err) {
      console.error('Error exporting full data:', err);
      alert(`Export failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const InstitutionCard = ({ institution }) => {
    const nihPercentage = institution.funding_diversification?.nih_percentage || 0;
    const nsfPercentage = institution.funding_diversification?.nsf_percentage || 0;
    const dodPercentage = institution.funding_diversification?.dod_percentage || 0;
    const doePercentage = institution.funding_diversification?.doe_percentage || 0;
    const nasaPercentage = institution.funding_diversification?.nasa_percentage || 0;
    const otherPercentage = institution.funding_diversification?.other_percentage || 0;

    const handleInstitutionClick = () => {
      setSelectedInstitution(institution);
      fetchInstitutionDetails(institution.institution);
    };

    return (
      <div className="institution-card" onClick={handleInstitutionClick} style={{ cursor: 'pointer' }}>
        <div className="institution-header">
          <div className="institution-name">{institution.institution}</div>
          <div className={getRiskBadgeClass(institution.risk_level)}>
            {institution.risk_level}
          </div>
        </div>

        <div className="metrics-grid">
          <div className="metric">
            <div className="metric-label">At-Risk Positions</div>
            <div className="metric-value">{institution.at_risk_positions}</div>
            <div className="metric-sublabel">Based on terminated research grants</div>
          </div>
          <div className="metric">
            <div className="metric-label">Recently Lost Positions</div>
            <div className="metric-value">{institution.recently_lost_positions}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Total Lab Size</div>
            <div className="metric-value">{institution.estimated_lab_size}</div>
            <div className="metric-sublabel">Based on total funding</div>
          </div>
          <div className="metric">
            <div className="metric-label">Risk Score</div>
            <div className="metric-value">{institution.risk_score}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Active Funding</div>
            <div className="metric-value">{formatCurrency(institution.total_active_funding)}</div>
            <div className="metric-sublabel">USASpending.gov total</div>
          </div>
          <div className="metric">
            <div className="metric-label">Research Funding Cliff</div>
            <div className="metric-value">{institution.funding_cliff_percentage}%</div>
            <div className="metric-sublabel">Terminated NIH/NSF vs total</div>
          </div>
        </div>

        {institution.funding_diversification && (
          <div className="funding-breakdown">
            <div className="funding-breakdown-label">Funding Sources (USASpending.gov)</div>
            <div className="funding-bar">
              <div 
                className="funding-nih" 
                style={{ width: `${nihPercentage}%` }}
              ></div>
              <div 
                className="funding-nsf" 
                style={{ width: `${nsfPercentage}%` }}
              ></div>
              <div 
                className="funding-dod" 
                style={{ width: `${dodPercentage}%` }}
              ></div>
              <div 
                className="funding-doe" 
                style={{ width: `${doePercentage}%` }}
              ></div>
              <div 
                className="funding-nasa" 
                style={{ width: `${nasaPercentage}%`, backgroundColor: '#ff6b6b' }}
              ></div>
              <div 
                className="funding-other" 
                style={{ width: `${otherPercentage}%`, backgroundColor: '#95a5a6' }}
              ></div>
            </div>
            <div className="funding-legend">
              <div className="legend-item">
                <div className="legend-color funding-nih"></div>
                <span>NIH: {nihPercentage}% ({formatCurrency(institution.funding_diversification.nih_funding)})</span>
              </div>
              <div className="legend-item">
                <div className="legend-color funding-nsf"></div>
                <span>NSF: {nsfPercentage}% ({formatCurrency(institution.funding_diversification.nsf_funding)})</span>
              </div>
              {dodPercentage > 0 && (
                <div className="legend-item">
                  <div className="legend-color funding-dod"></div>
                  <span>DoD: {dodPercentage}% ({formatCurrency(institution.funding_diversification.dod_funding)})</span>
                </div>
              )}
              {doePercentage > 0 && (
                <div className="legend-item">
                  <div className="legend-color funding-doe"></div>
                  <span>DoE: {doePercentage}% ({formatCurrency(institution.funding_diversification.doe_funding)})</span>
                </div>
              )}
              {nasaPercentage > 0 && (
                <div className="legend-item">
                  <div className="legend-color" style={{ backgroundColor: '#ff6b6b' }}></div>
                  <span>NASA: {nasaPercentage}% ({formatCurrency(institution.funding_diversification.nasa_funding)})</span>
                </div>
              )}
              {otherPercentage > 0 && (
                <div className="legend-item">
                  <div className="legend-color" style={{ backgroundColor: '#95a5a6' }}></div>
                  <span>Other: {otherPercentage}% ({formatCurrency(institution.funding_diversification.other_funding)})</span>
                </div>
              )}
            </div>
            {institution.funding_diversification.terminated_research_funding > 0 && (
              <div className="terminated-funding-info" style={{ marginTop: '10px', padding: '8px', backgroundColor: '#fff3cd', borderRadius: '4px', fontSize: '0.9em' }}>
                <strong>Terminated Research Funding:</strong> {formatCurrency(institution.funding_diversification.terminated_research_funding)} from NIH/NSF grants
              </div>
            )}
          </div>
        )}

        {institution.top_departments && institution.top_departments.length > 0 && (
          <div className="departments">
            <div className="departments-label">Top Departments by Funding</div>
            <div className="department-tags">
              {institution.top_departments.map((dept, index) => (
                <div 
                  key={index} 
                  className={`department-tag ${index === 0 ? 'primary' : ''}`}
                  title={`${dept.grants} grants, ${formatCurrency(dept.funding)} (${dept.percentage}%)`}
                >
                  {dept.department} ({dept.percentage}%)
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const InstitutionDetails = ({ institution, onBack }) => {
    return (
      <div className="institution-details">
        <div className="details-header">
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <button 
              onClick={onBack}
              className="back-button"
              style={{
                padding: '8px 16px',
                border: '1px solid #667eea',
                borderRadius: '5px',
                background: 'white',
                color: '#667eea',
                cursor: 'pointer'
              }}
            >
              ← Back to Leaderboard
            </button>
            <button 
              onClick={() => fetchDelayedFundingAnalysis(institution.institution)}
              disabled={delayedFundingLoading}
              style={{
                padding: '8px 16px',
                border: '1px solid #ff9800',
                borderRadius: '5px',
                background: delayedFundingLoading ? '#f5f5f5' : 'white',
                color: delayedFundingLoading ? '#999' : '#ff9800',
                cursor: delayedFundingLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {delayedFundingLoading ? 'Loading...' : '💰 Cash Flow Analysis'}
            </button>
            <button 
              onClick={() => fetchDelayedFundingByDepartments(institution.institution)}
              disabled={delayedFundingLoading}
              style={{
                padding: '8px 16px',
                border: '1px solid #9c27b0',
                borderRadius: '5px',
                background: delayedFundingLoading ? '#f5f5f5' : 'white',
                color: delayedFundingLoading ? '#999' : '#9c27b0',
                cursor: delayedFundingLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {delayedFundingLoading ? 'Loading...' : '🏢 Delayed Funding by Department'}
            </button>
            <button 
              onClick={() => downloadDelayedFundingCSV(institution.institution)}
              style={{
                padding: '8px 16px',
                border: '1px solid #4caf50',
                borderRadius: '5px',
                background: 'white',
                color: '#4caf50',
                cursor: 'pointer'
              }}
            >
              📊 Download CSV Report
            </button>
          </div>
          <h2 style={{ color: '#333', margin: '0 0 20px 0' }}>
            {institution.institution} - Cancelled Grants by Department
          </h2>
        </div>

        {detailsLoading && (
          <div className="loading">Loading university details...</div>
        )}

        {institutionDetails && institutionDetails.overview && (
          <div className="details-content">
            {/* Overview Section */}
            <div className="overview-section" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
              <h3>University Overview</h3>
              <div className="overview-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                <div className="overview-metric">
                  <div className="metric-label">Active Funding</div>
                  <div className="metric-value">{formatCurrency(institutionDetails.overview?.total_active_funding || 0)}</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-label">Terminated Funding</div>
                  <div className="metric-value">{formatCurrency(institutionDetails.overview?.total_terminated_funding || 0)}</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-label">Funding Cliff</div>
                  <div className="metric-value">{institutionDetails.overview?.funding_cliff_percentage || 0}%</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-label">Departments Affected</div>
                  <div className="metric-value">{institutionDetails.overview?.total_departments_affected || 0}</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-label">PIs Affected</div>
                  <div className="metric-value">{institutionDetails.overview?.total_pis_affected || 0}</div>
                </div>
                <div className="overview-metric">
                  <div className="metric-label">Positions at Risk</div>
                  <div className="metric-value">{Math.round(institutionDetails.overview?.estimated_total_positions_at_risk || 0)}</div>
                </div>
              </div>
            </div>

            {/* Active Funding Breakdown */}
            <div className="funding-breakdown-section" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#e8f5e8', borderRadius: '8px' }}>
              <h3>Active Funding by Agency</h3>
              <div className="funding-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                {institutionDetails.funding_breakdown?.nih_funding > 0 && (
                  <div className="agency-funding">
                    <strong>NIH:</strong> {formatCurrency(institutionDetails.funding_breakdown.nih_funding)}
                  </div>
                )}
                {institutionDetails.funding_breakdown?.nsf_funding > 0 && (
                  <div className="agency-funding">
                    <strong>NSF:</strong> {formatCurrency(institutionDetails.funding_breakdown.nsf_funding)}
                  </div>
                )}
                {institutionDetails.funding_breakdown?.dod_funding > 0 && (
                  <div className="agency-funding">
                    <strong>DoD:</strong> {formatCurrency(institutionDetails.funding_breakdown.dod_funding)}
                  </div>
                )}
                {institutionDetails.funding_breakdown?.doe_funding > 0 && (
                  <div className="agency-funding">
                    <strong>DoE:</strong> {formatCurrency(institutionDetails.funding_breakdown.doe_funding)}
                  </div>
                )}
                {institutionDetails.funding_breakdown?.nasa_funding > 0 && (
                  <div className="agency-funding">
                    <strong>NASA:</strong> {formatCurrency(institutionDetails.funding_breakdown.nasa_funding)}
                  </div>
                )}
                {institutionDetails.funding_breakdown?.other_funding > 0 && (
                  <div className="agency-funding">
                    <strong>Other:</strong> {formatCurrency(institutionDetails.funding_breakdown.other_funding)}
                  </div>
                )}
              </div>
            </div>

            {/* Delayed Funding Analysis */}
            {institutionDetails.delayed_funding && (
              <div className="delayed-funding-section" style={{ 
                marginBottom: '30px', 
                padding: '20px', 
                backgroundColor: institutionDetails.delayed_funding.cash_flow_risk?.level === 'CRITICAL' ? '#ffebee' : 
                                institutionDetails.delayed_funding.cash_flow_risk?.level === 'HIGH' ? '#fff3e0' : '#f3e5f5', 
                borderRadius: '8px',
                border: institutionDetails.delayed_funding.cash_flow_risk?.level === 'CRITICAL' ? '2px solid #f44336' :
                        institutionDetails.delayed_funding.cash_flow_risk?.level === 'HIGH' ? '2px solid #ff9800' : '1px solid #ddd'
              }}>
                <h3 style={{ color: institutionDetails.delayed_funding.cash_flow_risk?.level === 'CRITICAL' ? '#d32f2f' : '#333' }}>
                  Cash Flow & Delayed Funding Analysis
                  {institutionDetails.delayed_funding.cash_flow_risk?.level && institutionDetails.delayed_funding.cash_flow_risk.level !== 'UNKNOWN' && (
                    <span style={{ 
                      marginLeft: '10px', 
                      padding: '4px 8px', 
                      borderRadius: '4px', 
                      fontSize: '12px', 
                      backgroundColor: institutionDetails.delayed_funding.cash_flow_risk.level === 'CRITICAL' ? '#f44336' : 
                                      institutionDetails.delayed_funding.cash_flow_risk.level === 'HIGH' ? '#ff9800' : '#4caf50',
                      color: 'white'
                    }}>
                      {institutionDetails.delayed_funding.cash_flow_risk.level}
                    </span>
                  )}
                </h3>
                {institutionDetails.delayed_funding.note ? (
                  <div style={{ fontStyle: 'italic', color: '#666' }}>
                    {institutionDetails.delayed_funding.note}
                  </div>
                ) : (
                  <div className="delayed-funding-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px' }}>
                    <div className="delayed-funding-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Undisbursed Amount</div>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#d32f2f' }}>
                        {formatCurrency(institutionDetails.delayed_funding.undisbursed_amount)}
                      </div>
                    </div>
                    <div className="delayed-funding-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Disbursement Efficiency</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
                        {institutionDetails.delayed_funding.disbursement_efficiency}
                      </div>
                    </div>
                    <div className="delayed-funding-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Awards with Delays</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
                        {institutionDetails.delayed_funding.delayed_awards_count}
                      </div>
                    </div>
                  </div>
                )}
                {institutionDetails.delayed_funding.cash_flow_risk?.level === 'CRITICAL' && (
                  <div style={{ 
                    marginTop: '15px', 
                    padding: '10px', 
                    backgroundColor: '#ffcdd2', 
                    borderRadius: '4px', 
                    fontSize: '14px',
                    border: '1px solid #f44336'
                  }}>
                    <strong>⚠️ Critical Cash Flow Risk:</strong> This institution has significant delayed funding that may impact research operations. 
                    Immediate attention to disbursement delays is recommended.
                  </div>
                )}
                {institutionDetails.delayed_funding.cash_flow_risk?.level === 'HIGH' && (
                  <div style={{ 
                    marginTop: '15px', 
                    padding: '10px', 
                    backgroundColor: '#ffe0b2', 
                    borderRadius: '4px', 
                    fontSize: '14px',
                    border: '1px solid #ff9800'
                  }}>
                    <strong>⚠️ High Cash Flow Risk:</strong> Monitor disbursement delays closely as they may affect research continuity.
                  </div>
                )}
              </div>
            )}

            {/* Cancelled Grants Impact */}
            {institutionDetails.delayed_funding && institutionDetails.delayed_funding.cancelled_grants_impact && (
              <div className="cancelled-grants-section" style={{ 
                marginBottom: '30px', 
                padding: '20px', 
                backgroundColor: '#ffebee', 
                borderRadius: '8px',
                border: '2px solid #f44336'
              }}>
                <h3 style={{ color: '#d32f2f', display: 'flex', alignItems: 'center' }}>
                  🚫 Cancelled Grants Impact
                  <span style={{ 
                    marginLeft: '10px', 
                    padding: '4px 8px', 
                    borderRadius: '4px', 
                    fontSize: '12px', 
                    backgroundColor: '#f44336',
                    color: 'white'
                  }}>
                    FUNDING LOST
                  </span>
                </h3>
                
                <div className="cancelled-grants-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                  <div className="cancelled-metric">
                    <div style={{ fontSize: '12px', color: '#666' }}>Total Lost Funding</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#d32f2f' }}>
                      {formatCurrency(institutionDetails.delayed_funding.cancelled_grants_impact.total_lost_funding)}
                    </div>
                  </div>
                  <div className="cancelled-metric">
                    <div style={{ fontSize: '12px', color: '#666' }}>PIs Impacted</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#d32f2f' }}>
                      {institutionDetails.delayed_funding.cancelled_grants_impact.total_affected_pis || 0}
                    </div>
                  </div>
                </div>

                {/* Top PIs */}
                {institutionDetails.delayed_funding.cancelled_grants_impact.top_pis && 
                 institutionDetails.delayed_funding.cancelled_grants_impact.top_pis.length > 0 && (
                  <div style={{ marginBottom: '20px' }}>
                    <h4 style={{ color: '#d32f2f', marginBottom: '10px' }}>Most Impacted PIs</h4>
                    <div style={{ display: 'grid', gap: '8px' }}>
                      {institutionDetails.delayed_funding.cancelled_grants_impact.top_pis.slice(0, 5).map((pi, index) => (
                        <div key={index} style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          padding: '8px 12px', 
                          backgroundColor: 'white', 
                          borderRadius: '4px',
                          border: '1px solid #ffcdd2',
                          cursor: 'pointer',
                          transition: 'background-color 0.2s'
                        }}
                        onClick={() => fetchPiDetails(pi.pi_name, selectedInstitution)}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                        >
                          <div>
                            <strong style={{ color: '#1976d2', textDecoration: 'underline' }}>{pi.pi_name}</strong>
                            <div style={{ fontSize: '12px', color: '#666' }}>{pi.department}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                              {formatCurrency(pi.lost_funding)}
                            </div>
                            <div style={{ fontSize: '12px', color: '#666' }}>
                              {pi.grants_count} grants
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Department Losses */}
                {institutionDetails.delayed_funding.cancelled_grants_impact.department_losses && 
                 Object.keys(institutionDetails.delayed_funding.cancelled_grants_impact.department_losses).length > 0 && (
                  <div>
                    <h4 style={{ color: '#d32f2f', marginBottom: '10px' }}>Losses by Department</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
                      {Object.entries(institutionDetails.delayed_funding.cancelled_grants_impact.department_losses)
                        .slice(0, 6).map(([dept, amount]) => (
                        <div key={dept} style={{ 
                          padding: '8px 12px', 
                          backgroundColor: 'white', 
                          borderRadius: '4px',
                          border: '1px solid #ffcdd2',
                          display: 'flex',
                          justifyContent: 'space-between'
                        }}>
                          <span style={{ fontSize: '14px' }}>{dept}</span>
                          <span style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                            {formatCurrency(amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ 
                  marginTop: '15px', 
                  padding: '8px 12px', 
                  backgroundColor: '#ffcdd2', 
                  borderRadius: '4px', 
                  fontSize: '12px',
                  color: '#666',
                  fontStyle: 'italic'
                }}>
                  {institutionDetails.delayed_funding.cancelled_grants_impact.methodology_note}
                </div>
              </div>
            )}

            {/* Non-Renewal Grants Impact */}
            {institutionDetails.delayed_funding && institutionDetails.delayed_funding.nonrenewal_grants_impact && (
              <div className="nonrenewal-grants-section" style={{ 
                marginBottom: '30px', 
                padding: '20px', 
                backgroundColor: '#fff3e0', 
                borderRadius: '8px',
                border: '2px solid #ff9800'
              }}>
                <h3 style={{ color: '#e65100', display: 'flex', alignItems: 'center' }}>
                  📉 Non-Renewal Grants Impact
                  <span style={{ 
                    marginLeft: '10px', 
                    padding: '4px 8px', 
                    borderRadius: '4px', 
                    fontSize: '12px', 
                    backgroundColor: '#ff9800',
                    color: 'white'
                  }}>
                    NOT RENEWED
                  </span>
                </h3>
                
                <div className="nonrenewal-grants-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                  <div className="nonrenewal-metric">
                    <div style={{ fontSize: '12px', color: '#666' }}>Lost from Non-Renewals</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#e65100' }}>
                      {formatCurrency(institutionDetails.delayed_funding.nonrenewal_grants_impact.total_lost_funding)}
                    </div>
                  </div>
                  <div className="nonrenewal-metric">
                    <div style={{ fontSize: '12px', color: '#666' }}>PIs Affected</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#e65100' }}>
                      {institutionDetails.delayed_funding.nonrenewal_grants_impact.pis_impacted}
                    </div>
                  </div>
                </div>

                {/* Show zero state or data */}
                {institutionDetails.delayed_funding.nonrenewal_grants_impact.pis_impacted === 0 ? (
                  <div style={{ 
                    padding: '15px', 
                    backgroundColor: '#e8f5e8', 
                    borderRadius: '4px',
                    border: '1px solid #4caf50',
                    textAlign: 'center'
                  }}>
                    <div style={{ color: '#2e7d32', fontWeight: 'bold' }}>
                      ✅ No Non-Renewal Issues Detected
                    </div>
                    <div style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                      All eligible grants that expired in the analysis period have renewal evidence.
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Top PIs for non-renewals */}
                    {institutionDetails.delayed_funding.nonrenewal_grants_impact.top_pis && 
                     institutionDetails.delayed_funding.nonrenewal_grants_impact.top_pis.length > 0 && (
                      <div style={{ marginBottom: '20px' }}>
                        <h4 style={{ color: '#e65100', marginBottom: '10px' }}>Most Affected PIs</h4>
                        <div style={{ display: 'grid', gap: '8px' }}>
                          {institutionDetails.delayed_funding.nonrenewal_grants_impact.top_pis.slice(0, 5).map((pi, index) => (
                            <div key={index} style={{ 
                              display: 'flex', 
                              justifyContent: 'space-between', 
                              padding: '8px 12px', 
                              backgroundColor: 'white', 
                              borderRadius: '4px',
                              border: '1px solid #ffcc02',
                              cursor: 'pointer',
                              transition: 'background-color 0.2s'
                            }}
                            onClick={() => fetchPiDetails(pi.pi_name, selectedInstitution)}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                            >
                              <div>
                                <strong style={{ color: '#1976d2', textDecoration: 'underline' }}>{pi.pi_name}</strong>
                                <div style={{ fontSize: '12px', color: '#666' }}>{pi.department}</div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{ fontWeight: 'bold', color: '#e65100' }}>
                                  {formatCurrency(pi.lost_funding)}
                                </div>
                                <div style={{ fontSize: '12px', color: '#666' }}>
                                  {pi.grants_count} grants
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Department Losses */}
                    {institutionDetails.delayed_funding.nonrenewal_grants_impact.department_losses && 
                     Object.keys(institutionDetails.delayed_funding.nonrenewal_grants_impact.department_losses).length > 0 && (
                      <div>
                        <h4 style={{ color: '#e65100', marginBottom: '10px' }}>Non-Renewal Losses by Department</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
                          {Object.entries(institutionDetails.delayed_funding.nonrenewal_grants_impact.department_losses)
                            .slice(0, 6).map(([dept, amount]) => (
                            <div key={dept} style={{ 
                              padding: '8px 12px', 
                              backgroundColor: 'white', 
                              borderRadius: '4px',
                              border: '1px solid #ffcc02',
                              display: 'flex',
                              justifyContent: 'space-between'
                            }}>
                              <span style={{ fontSize: '14px' }}>{dept}</span>
                              <span style={{ fontWeight: 'bold', color: '#e65100' }}>
                                {formatCurrency(amount)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                <div style={{ 
                  marginTop: '15px', 
                  padding: '8px 12px', 
                  backgroundColor: '#ffe0b2', 
                  borderRadius: '4px', 
                  fontSize: '12px',
                  color: '#666',
                  fontStyle: 'italic'
                }}>
                  {institutionDetails.delayed_funding.nonrenewal_grants_impact.methodology_note}
                  {institutionDetails.delayed_funding.nonrenewal_grants_impact.analysis_period && (
                    <div style={{ marginTop: '4px' }}>
                      Analysis Period: {institutionDetails.delayed_funding.nonrenewal_grants_impact.analysis_period}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const DelayedFundingAnalysis = ({ data, onBack }) => {
    if (!data) return null;

    return (
      <div className="delayed-funding-analysis">
        <div className="details-header">
          <button 
            onClick={onBack}
            className="back-button"
            style={{
              padding: '8px 16px',
              border: '1px solid #667eea',
              borderRadius: '5px',
              background: 'white',
              color: '#667eea',
              cursor: 'pointer',
              marginBottom: '20px'
            }}
          >
            ← Back to Leaderboard
          </button>
          <h2 style={{ color: '#333', margin: '0 0 20px 0' }}>
            {data.institution} - Delayed Funding Analysis
          </h2>
        </div>

        {/* Risk Overview */}
        <div className="risk-overview" style={{ 
          marginBottom: '30px', 
          padding: '20px', 
          backgroundColor: data.cash_flow_risk.level === 'CRITICAL' ? '#ffebee' : 
                          data.cash_flow_risk.level === 'HIGH' ? '#fff3e0' : '#e8f5e8',
          borderRadius: '8px',
          border: data.cash_flow_risk.level === 'CRITICAL' ? '2px solid #f44336' :
                  data.cash_flow_risk.level === 'HIGH' ? '2px solid #ff9800' : '1px solid #4caf50'
        }}>
          <h3 style={{ 
            color: data.cash_flow_risk.level === 'CRITICAL' ? '#d32f2f' : 
                   data.cash_flow_risk.level === 'HIGH' ? '#f57c00' : '#2e7d32' 
          }}>
            Cash Flow Risk Assessment: {data.cash_flow_risk.level}
            <span style={{ 
              marginLeft: '15px', 
              fontSize: '24px', 
              fontWeight: 'bold' 
            }}>
              Score: {data.cash_flow_risk.score}
            </span>
          </h3>
          <div style={{ fontSize: '16px', marginBottom: '15px' }}>
            <strong>Severity:</strong> {data.cash_flow_risk.severity}
          </div>
          {data.cash_flow_risk.risk_factors.length > 0 && (
            <div>
              <strong>Risk Factors:</strong>
              <ul style={{ marginTop: '8px' }}>
                {data.cash_flow_risk.risk_factors.map((factor, index) => (
                  <li key={index} style={{ marginBottom: '4px' }}>{factor}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Financial Overview */}
        <div className="financial-overview" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
          <h3>Financial Overview</h3>
          <div className="financial-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <div className="financial-metric">
              <div className="metric-label">Total Awarded</div>
              <div className="metric-value">{formatCurrency(data.financial_overview.total_awarded)}</div>
            </div>
            <div className="financial-metric">
              <div className="metric-label">Total Disbursed</div>
              <div className="metric-value">{formatCurrency(data.financial_overview.total_disbursed)}</div>
            </div>
            <div className="financial-metric">
              <div className="metric-label">Undisbursed Amount</div>
              <div className="metric-value" style={{ color: '#d32f2f', fontWeight: 'bold' }}>
                {formatCurrency(data.financial_overview.undisbursed_amount)}
              </div>
            </div>
            <div className="financial-metric">
              <div className="metric-label">Disbursement Efficiency</div>
              <div className="metric-value">{data.financial_overview.disbursement_efficiency}</div>
            </div>
            <div className="financial-metric">
              <div className="metric-label">Undisbursed Percentage</div>
              <div className="metric-value">{data.financial_overview.undisbursed_percentage}</div>
            </div>
          </div>
        </div>

        {/* Delayed Awards Details */}
        <div className="delayed-awards" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#fff3e0', borderRadius: '8px' }}>
          <h3>Delayed Awards Analysis</h3>
          <div className="delayed-awards-summary" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginBottom: '20px' }}>
            <div>
              <strong>Awards with Delays:</strong> {data.delayed_awards.count}
            </div>
            <div>
              <strong>Total Awards:</strong> {data.delayed_awards.total_awards_analyzed}
            </div>
            <div>
              <strong>Delay Frequency:</strong> {data.delayed_awards.delay_frequency}
            </div>
          </div>
          
          {data.delayed_awards.awards_details.length > 0 && (
            <div>
              <h4>Most Delayed Awards:</h4>
              {data.delayed_awards.awards_details.slice(0, 3).map((award, index) => (
                <div key={index} style={{ 
                  padding: '10px', 
                  border: '1px solid #ddd', 
                  borderRadius: '4px', 
                  marginBottom: '10px',
                  backgroundColor: 'white'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div style={{ flex: 1 }}>
                      <div><strong>Award ID:</strong> {award.award_id}</div>
                      <div><strong>Agency:</strong> {award.agency}</div>
                      <div><strong>Description:</strong> {award.description || 'N/A'}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ color: '#d32f2f', fontWeight: 'bold' }}>
                        {formatCurrency(award.undisbursed_amount)} undisbursed
                      </div>
                      <div>Disbursement: {(award.disbursement_rate * 100).toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Implications and Recommendations */}
        <div className="implications" style={{ padding: '20px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
          <h3>Implications & Recommendations</h3>
          <div style={{ marginBottom: '15px' }}>
            <strong>Cash Flow Impact:</strong> {data.implications.estimated_cash_flow_impact}
          </div>
          <div style={{ marginBottom: '15px' }}>
            <strong>Operational Risk:</strong> {data.implications.operational_risk}
          </div>
          {data.implications.recommended_actions.filter(action => action).length > 0 && (
            <div>
              <strong>Recommended Actions:</strong>
              <ul style={{ marginTop: '8px' }}>
                {data.implications.recommended_actions.filter(action => action).map((action, index) => (
                  <li key={index} style={{ marginBottom: '4px' }}>{action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Cancelled Grants Impact */}
        {data.cancelled_grants_impact && (
          <div className="cancelled-grants-section" style={{ 
            marginBottom: '30px', 
            padding: '20px', 
            backgroundColor: '#ffebee', 
            borderRadius: '8px',
            border: '2px solid #f44336'
          }}>
            <h3 style={{ color: '#d32f2f', display: 'flex', alignItems: 'center' }}>
              🚫 Cancelled Grants Impact
              <span style={{ 
                marginLeft: '10px', 
                padding: '4px 8px', 
                borderRadius: '4px', 
                fontSize: '12px', 
                backgroundColor: '#f44336',
                color: 'white'
              }}>
                FUNDING LOST
              </span>
            </h3>
            
            <div className="cancelled-grants-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
              <div className="cancelled-metric">
                <div style={{ fontSize: '12px', color: '#666' }}>Total Lost Funding</div>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#d32f2f' }}>
                  {formatCurrency(data.cancelled_grants_impact.total_lost_funding)}
                </div>
              </div>
              <div className="cancelled-metric">
                <div style={{ fontSize: '12px', color: '#666' }}>PIs Impacted</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#d32f2f' }}>
                  {data.cancelled_grants_impact.total_affected_pis || 0}
                </div>
              </div>
            </div>

            {/* Top PIs */}
            {data.cancelled_grants_impact.top_pis && 
             data.cancelled_grants_impact.top_pis.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: '#d32f2f', marginBottom: '10px' }}>Most Impacted PIs</h4>
                <div style={{ display: 'grid', gap: '8px' }}>
                  {data.cancelled_grants_impact.top_pis.slice(0, 5).map((pi, index) => (
                    <div key={index} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      padding: '8px 12px', 
                      backgroundColor: 'white', 
                      borderRadius: '4px',
                      border: '1px solid #ffcdd2',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s'
                    }}
                    onClick={() => fetchPiDetails(pi.pi_name, selectedInstitution)}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                    >
                      <div>
                        <strong style={{ color: '#1976d2', textDecoration: 'underline' }}>{pi.pi_name}</strong>
                        <div style={{ fontSize: '12px', color: '#666' }}>{pi.department}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                          {formatCurrency(pi.lost_funding)}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {pi.grants_count} grants
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Department Losses */}
            {data.cancelled_grants_impact.department_losses && 
             Object.keys(data.cancelled_grants_impact.department_losses).length > 0 && (
              <div>
                <h4 style={{ color: '#d32f2f', marginBottom: '10px' }}>Losses by Department</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
                  {Object.entries(data.cancelled_grants_impact.department_losses)
                    .slice(0, 6).map(([dept, amount]) => (
                    <div key={dept} style={{ 
                      padding: '8px 12px', 
                      backgroundColor: 'white', 
                      borderRadius: '4px',
                      border: '1px solid #ffcdd2',
                      display: 'flex',
                      justifyContent: 'space-between'
                    }}>
                      <span style={{ fontSize: '14px' }}>{dept}</span>
                      <span style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                        {formatCurrency(amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ 
              marginTop: '15px', 
              padding: '8px 12px', 
              backgroundColor: '#ffcdd2', 
              borderRadius: '4px', 
              fontSize: '12px',
              color: '#666',
              fontStyle: 'italic'
            }}>
              {data.cancelled_grants_impact.methodology_note}
            </div>
          </div>
        )}

        {/* Non-Renewal Grants Impact */}
        {data.nonrenewal_grants_impact && (
          <div className="nonrenewal-grants-section" style={{ 
            marginBottom: '30px', 
            padding: '20px', 
            backgroundColor: '#fff3e0', 
            borderRadius: '8px',
            border: '2px solid #ff9800'
          }}>
            <h3 style={{ color: '#f57c00', display: 'flex', alignItems: 'center' }}>
              ⚠️ Non-Renewal Grants Impact
              <span style={{ 
                marginLeft: '10px', 
                padding: '4px 8px', 
                borderRadius: '4px', 
                fontSize: '12px', 
                backgroundColor: '#ff9800',
                color: 'white'
              }}>
                RENEWAL RISK
              </span>
            </h3>
            
            <div className="nonrenewal-grants-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
              <div className="nonrenewal-metric">
                <div style={{ fontSize: '12px', color: '#666' }}>Total At-Risk Funding</div>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f57c00' }}>
                  {formatCurrency(data.nonrenewal_grants_impact.total_lost_funding)}
                </div>
              </div>
              <div className="nonrenewal-metric">
                <div style={{ fontSize: '12px', color: '#666' }}>PIs At Risk</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f57c00' }}>
                  {data.nonrenewal_grants_impact.pis_impacted}
                </div>
              </div>
            </div>

            {/* Top PIs */}
            {data.nonrenewal_grants_impact.top_pis && 
             data.nonrenewal_grants_impact.top_pis.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: '#f57c00', marginBottom: '10px' }}>Most At-Risk PIs</h4>
                <div style={{ display: 'grid', gap: '8px' }}>
                  {data.nonrenewal_grants_impact.top_pis.slice(0, 5).map((pi, index) => (
                    <div key={index} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      padding: '8px 12px', 
                      backgroundColor: 'white', 
                      borderRadius: '4px',
                      border: '1px solid #ffcc02',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s'
                    }}
                    onClick={() => fetchPiDetails(pi.pi_name, selectedInstitution)}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                    >
                      <div>
                        <strong style={{ color: '#1976d2', textDecoration: 'underline' }}>{pi.pi_name}</strong>
                        <div style={{ fontSize: '12px', color: '#666' }}>{pi.department}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 'bold', color: '#f57c00' }}>
                          {formatCurrency(pi.lost_funding)}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {pi.grants_count} grants
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Department Losses */}
            {data.nonrenewal_grants_impact.department_losses && 
             Object.keys(data.nonrenewal_grants_impact.department_losses).length > 0 && (
              <div>
                <h4 style={{ color: '#f57c00', marginBottom: '10px' }}>At-Risk by Department</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
                  {Object.entries(data.nonrenewal_grants_impact.department_losses)
                    .slice(0, 6).map(([dept, amount]) => (
                    <div key={dept} style={{ 
                      padding: '8px 12px', 
                      backgroundColor: 'white', 
                      borderRadius: '4px',
                      border: '1px solid #ffcc02',
                      display: 'flex',
                      justifyContent: 'space-between'
                    }}>
                      <span style={{ fontSize: '14px' }}>{dept}</span>
                      <span style={{ fontWeight: 'bold', color: '#f57c00' }}>
                        {formatCurrency(amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ 
              marginTop: '15px', 
              padding: '8px 12px', 
              backgroundColor: '#ffcc02', 
              borderRadius: '4px', 
              fontSize: '12px',
              color: '#666',
              fontStyle: 'italic'
            }}>
              {data.nonrenewal_grants_impact.methodology_note}
            </div>
          </div>
        )}

      </div>
    );
  };

  const DepartmentDelayedFundingAnalysis = ({ data, onBack }) => {
    if (!data || data.error) {
      return (
        <div className="delayed-funding-analysis">
          <div className="details-header">
            <button onClick={onBack} style={{ padding: '8px 16px', border: '1px solid #667eea', borderRadius: '5px', background: 'white', color: '#667eea', cursor: 'pointer', marginBottom: '20px' }}>
              ← Back to Leaderboard
            </button>
            <h2>{data?.institution || 'Institution'} - Delayed Funding by Department</h2>
          </div>
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            {data?.error || 'No delayed funding data available by department.'}
            {data?.note && <div style={{ marginTop: '10px', fontSize: '14px' }}>{data.note}</div>}
          </div>
        </div>
      );
    }

    return (
      <div className="delayed-funding-analysis">
        <div className="details-header">
          <button onClick={onBack} style={{ padding: '8px 16px', border: '1px solid #667eea', borderRadius: '5px', background: 'white', color: '#667eea', cursor: 'pointer', marginBottom: '20px' }}>
            ← Back to Leaderboard
          </button>
          <h2 style={{ color: '#333', margin: '0 0 20px 0' }}>
            {data.institution} - Delayed Funding by Department
          </h2>
        </div>

        {/* Overview Section */}
        <div className="overview-section" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
          <h3>Institution Overview</h3>
          <div className="overview-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <div className="overview-metric">
              <div className="metric-label">Total Undisbursed</div>
              <div className="metric-value">{formatCurrency(data.overview.total_undisbursed)}</div>
            </div>
            <div className="overview-metric">
              <div className="metric-label">Cash Flow Risk</div>
              <div className="metric-value" style={{ color: data.overview.cash_flow_risk === 'CRITICAL' ? '#d32f2f' : data.overview.cash_flow_risk === 'HIGH' ? '#f57c00' : '#2e7d32' }}>
                {data.overview.cash_flow_risk}
              </div>
            </div>
            <div className="overview-metric">
              <div className="metric-label">Disbursement Efficiency</div>
              <div className="metric-value">{data.overview.disbursement_efficiency}</div>
            </div>
            <div className="overview-metric">
              <div className="metric-label">Departments Affected</div>
              <div className="metric-value">{data.overview.departments_affected}</div>
            </div>
            <div className="overview-metric">
              <div className="metric-label">High Risk Departments</div>
              <div className="metric-value">{data.overview.high_risk_departments}</div>
            </div>
            <div className="overview-metric">
              <div className="metric-label">Positions Affected</div>
              <div className="metric-value">{data.institutional_impact.total_positions_potentially_affected}</div>
            </div>
          </div>
        </div>

        {/* Risk Summary */}
        <div className="risk-summary" style={{ marginBottom: '30px', padding: '20px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
          <h3>Risk Distribution</h3>
          <div className="risk-distribution" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '10px' }}>
            {Object.entries(data.department_analysis.summary_by_risk).map(([risk, count]) => (
              <div key={risk} style={{ textAlign: 'center', padding: '10px', backgroundColor: 'white', borderRadius: '4px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: risk === 'CRITICAL' ? '#d32f2f' : risk === 'HIGH' ? '#f57c00' : risk === 'MEDIUM' ? '#ff9800' : '#4caf50' }}>
                  {count}
                </div>
                <div style={{ fontSize: '12px', textTransform: 'capitalize' }}>{risk.toLowerCase()}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Departments with Delayed Funding */}
        <div className="departments-section">
          <h3>Departments with Delayed Funding</h3>
          {data.department_analysis.departments && data.department_analysis.departments.length > 0 ? (
            <div className="departments-list">
              {data.department_analysis.departments.map((dept, index) => (
                <div key={index} className="department-card" style={{ 
                  border: '1px solid #ddd', 
                  borderRadius: '8px', 
                  padding: '20px', 
                  marginBottom: '20px',
                  backgroundColor: dept.risk_level === 'CRITICAL' ? '#ffebee' : 
                                  dept.risk_level === 'HIGH' ? '#fff3e0' : '#f9f9f9',
                  borderLeft: `5px solid ${dept.risk_level === 'CRITICAL' ? '#f44336' : dept.risk_level === 'HIGH' ? '#ff9800' : '#4caf50'}`
                }}>
                  <div className="department-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                    <h4 style={{ margin: 0, color: '#333' }}>{dept.department}</h4>
                    <div className="department-summary" style={{ textAlign: 'right' }}>
                      <div style={{ 
                        fontSize: '12px', 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        backgroundColor: dept.risk_level === 'CRITICAL' ? '#f44336' : dept.risk_level === 'HIGH' ? '#ff9800' : '#4caf50',
                        color: 'white',
                        marginBottom: '5px'
                      }}>
                        {dept.risk_level} RISK
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#d32f2f' }}>
                        {formatCurrency(dept.total_undisbursed)}
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {dept.awards_count} awards • {dept.delayed_awards_count} delayed
                      </div>
                    </div>
                  </div>

                  <div className="department-metrics" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '15px' }}>
                    <div className="dept-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Total Awarded</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{formatCurrency(dept.total_awarded)}</div>
                    </div>
                    <div className="dept-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Disbursed</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{formatCurrency(dept.total_disbursed)}</div>
                    </div>
                    <div className="dept-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Efficiency</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{dept.disbursement_efficiency}%</div>
                    </div>
                    <div className="dept-metric">
                      <div style={{ fontSize: '12px', color: '#666' }}>Positions Affected</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{dept.estimated_positions_affected}</div>
                    </div>
                  </div>

                  {/* Most Impacted Awards */}
                  {dept.most_impacted_awards && dept.most_impacted_awards.length > 0 && (
                    <div className="most-impacted-awards">
                      <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '10px' }}>
                        Most Impacted Awards:
                      </div>
                      <div className="awards-list">
                        {dept.most_impacted_awards.slice(0, 2).map((award, awardIndex) => (
                          <div key={awardIndex} className="award-item" style={{ 
                            padding: '10px', 
                            border: '1px solid #e0e0e0', 
                            borderRadius: '4px', 
                            marginBottom: '8px',
                            backgroundColor: 'white'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div style={{ flex: 1, marginRight: '10px' }}>
                                <div style={{ fontWeight: 'bold', fontSize: '13px', marginBottom: '4px' }}>
                                  {award.pi_name} • {award.award_id}
                                </div>
                                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                                  {award.description || 'No description available'}
                                </div>
                                <div style={{ fontSize: '11px', color: '#888' }}>
                                  {award.agency} • {award.start_date} - {award.end_date}
                                </div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                                  {formatCurrency(award.undisbursed_amount)} undisbursed
                                </div>
                                <div style={{ fontSize: '11px', color: '#666' }}>
                                  {(award.disbursement_rate * 100).toFixed(1)}% disbursed
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
              No departments with delayed funding found.
            </div>
          )}
        </div>

        {/* Recommendations */}
        {data.recommendations && (
          <div className="recommendations" style={{ padding: '20px', backgroundColor: '#e8f5e8', borderRadius: '8px' }}>
            <h3>Recommendations</h3>
            {data.recommendations.priority_departments && (
              <div style={{ marginBottom: '15px' }}>
                <strong>Priority Departments:</strong>
                <ul style={{ marginTop: '8px' }}>
                  {data.recommendations.priority_departments.map((rec, index) => (
                    <li key={index} style={{ marginBottom: '4px' }}>
                      <strong>{rec.department}:</strong> {rec.action} ({formatCurrency(rec.undisbursed_amount)} undisbursed)
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data.recommendations.next_steps && (
              <div>
                <strong>Next Steps:</strong>
                <ul style={{ marginTop: '8px' }}>
                  {data.recommendations.next_steps.map((step, index) => (
                    <li key={index} style={{ marginBottom: '4px' }}>{step}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading layoff risk data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">
          <strong>Error:</strong> {error}
          <br />
          <button onClick={fetchLeaderboard} className="refresh-button" style={{ marginTop: '10px' }}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const totalAtRisk = leaderboardData?.institutions?.reduce((sum, inst) => sum + inst.at_risk_positions, 0) || 0;
  const totalRecentlyLost = leaderboardData?.institutions?.reduce((sum, inst) => sum + inst.recently_lost_positions, 0) || 0;
  const totalFunding = leaderboardData?.institutions?.reduce((sum, inst) => sum + inst.total_active_funding, 0) || 0;

  return (
    <div className="container">
      <div className="header">
        <h1>🚨 Academic Layoff Risk Tracker</h1>
        <p>Real-time analysis of federal funding risks across research institutions</p>
      </div>

      {showDepartmentDelayedFunding && delayedFundingDepartments ? (
        <DepartmentDelayedFundingAnalysis 
          data={delayedFundingDepartments} 
          onBack={() => {
            setShowDepartmentDelayedFunding(false);
            setDelayedFundingDepartments(null);
          }} 
        />
      ) : showDelayedFundingAnalysis && delayedFundingData ? (
        <DelayedFundingAnalysis 
          data={delayedFundingData} 
          onBack={() => {
            setShowDelayedFundingAnalysis(false);
            setDelayedFundingData(null);
          }} 
        />
      ) : selectedInstitution ? (
        <InstitutionDetails 
          institution={selectedInstitution} 
          onBack={() => {
            setSelectedInstitution(null);
            setInstitutionDetails(null);
          }} 
        />
      ) : (
        <>
          <div className="stats-bar">
            <div className="stat-item">
              <div className="stat-number">{formatNumber(totalAtRisk)}</div>
              <div className="stat-label">Total At-Risk Positions</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">{formatNumber(totalRecentlyLost)}</div>
              <div className="stat-label">Recently Lost Positions</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">{leaderboardData?.total_institutions || 0}</div>
              <div className="stat-label">Institutions Analyzed</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">{formatCurrency(totalFunding)}</div>
              <div className="stat-label">Total Active Funding</div>
            </div>
          </div>

          <div className="leaderboard-controls" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <button 
              onClick={fetchLeaderboard} 
              className="refresh-button"
              disabled={loading}
            >
              {loading ? 'Refreshing...' : '🔄 Refresh Data'}
            </button>

            <div className="export-controls">
              <button 
                onClick={exportToCSV}
                className="export-button"
                disabled={!leaderboardData?.institutions || loading}
                style={{
                  padding: '10px 20px',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: leaderboardData?.institutions ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                  fontWeight: '500',
                  opacity: leaderboardData?.institutions ? 1 : 0.6,
                  marginRight: '10px'
                }}
              >
                📊 Export Current View
              </button>

              <button 
                onClick={exportAllToCSV}
                className="export-all-button"
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  background: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  opacity: loading ? 0.6 : 1
                }}
              >
                📈 Export All Data
              </button>
            </div>
          </div>

          <div className="leaderboard">
            <div className="leaderboard-header">
              🏆 Institution Risk Leaderboard - Click to View Details
              {lastUpdated && <span style={{ float: 'right', fontSize: '0.9rem', opacity: 0.8 }}>
                Last updated: {lastUpdated}
              </span>}
            </div>
            
            {leaderboardData?.institutions?.map((institution, index) => (
              <InstitutionCard key={index} institution={institution} />
            ))}
          </div>

          <div style={{ marginTop: '30px', padding: '20px', background: 'white', borderRadius: '10px', fontSize: '0.9rem', color: '#666' }}>
            <strong>New Methodology:</strong> Active funding totals from USASpending.gov (most comprehensive federal data). 
            Risk scores calculated from terminated NIH/NSF research grants vs total funding (50%), recent research losses (30%), 
            and agency concentration penalties (20%). Agency diversification bonuses up to 30% for 5+ funding sources. 
            <br/><br/>
            <strong>Data Sources:</strong> USASpending.gov for comprehensive funding totals, NIH RePORTER + NSF Awards for research-specific risk analysis.
          </div>
        </>
      )}
    </div>
  );
}

export default App;
