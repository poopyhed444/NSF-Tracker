import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const [institutionDetails, setInstitutionDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

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
      
      const response = await axios.get(`/api/institution-details?institution=${encodeURIComponent(institutionName)}`);
      setInstitutionDetails(response.data);
    } catch (err) {
      setError(`Failed to fetch institution details: ${err.message}`);
      console.error('Error fetching institution details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const formatCurrency = (amount) => {
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
            {institution.institution} - Detailed Analysis
          </h2>
        </div>

        {detailsLoading && (
          <div className="loading">Loading detailed institution data...</div>
        )}

        {institutionDetails && (
          <div className="details-content">
            <div className="details-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '30px' }}>
              <div className="detail-card">
                <h3>Risk Assessment</h3>
                <div className="metric">
                  <div className="metric-label">Risk Level</div>
                  <div className={`metric-value ${institution.risk_level.toLowerCase()}`}>
                    {institution.risk_level}
                  </div>
                </div>
                <div className="metric">
                  <div className="metric-label">Risk Score</div>
                  <div className="metric-value">{institution.risk_score}</div>
                </div>
              </div>

              <div className="detail-card">
                <h3>Lab Size & Impact</h3>
                <div className="metric">
                  <div className="metric-label">Estimated Lab Size</div>
                  <div className="metric-value">{institution.estimated_lab_size} researchers</div>
                </div>
                <div className="metric">
                  <div className="metric-label">At-Risk Positions</div>
                  <div className="metric-value">{institution.at_risk_positions}</div>
                </div>
              </div>

              <div className="detail-card">
                <h3>Funding Status</h3>
                <div className="metric">
                  <div className="metric-label">Total Active Funding</div>
                  <div className="metric-value">{formatCurrency(institution.total_active_funding)}</div>
                </div>
                <div className="metric">
                  <div className="metric-label">Funding Cliff</div>
                  <div className="metric-value">{institution.funding_cliff_percentage}%</div>
                </div>
              </div>
            </div>

            {institutionDetails.pi_details && (
              <div className="pi-section">
                <h3>Principal Investigators</h3>
                <div className="pi-grid">
                  {institutionDetails.pi_details.slice(0, 10).map((pi, index) => (
                    <div key={index} className="pi-card">
                      <div className="pi-name">{pi.name}</div>
                      <div className="pi-department">{pi.department}</div>
                      <div className="pi-grants">{pi.grant_count} grants • {formatCurrency(pi.total_funding)}</div>
                      {pi.recent_grants && (
                        <div className="recent-grants">
                          {pi.recent_grants.slice(0, 2).map((grant, idx) => (
                            <div key={idx} className="grant-item">
                              {grant.title.substring(0, 60)}...
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
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

      {selectedInstitution ? (
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
