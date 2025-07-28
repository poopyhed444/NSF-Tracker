import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [federalData, setFederalData] = useState(null);
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [loading, setLoading] = useState(true);
  const [federalLoading, setFederalLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedAgencies, setSelectedAgencies] = useState(['NSF', 'NIH', 'DOD', 'DOE', 'NASA']);

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

  const fetchFederalData = async () => {
    try {
      setFederalLoading(true);
      setError(null);
      
      const agencyParam = selectedAgencies.join(',');
      const response = await axios.get(`/api/federal-agencies/data?agencies=${agencyParam}&include_awards=true&include_opportunities=false&limit=500`);
      setFederalData(response.data);
    } catch (err) {
      setError(`Failed to fetch federal data: ${err.message}`);
      console.error('Error fetching federal data:', err);
    } finally {
      setFederalLoading(false);
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
    if (!leaderboardData?.data) return;

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
      'NIH Percentage',
      'NSF Percentage'
    ];

    const csvData = leaderboardData.data.map(institution => [
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
      institution.funding_diversification?.nih_percentage || 0,
      institution.funding_diversification?.nsf_percentage || 0
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
        'NIH Percentage',
        'NSF Percentage'
      ];

      const csvData = allData.data.map(institution => [
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
        institution.funding_diversification?.nih_percentage || 0,
        institution.funding_diversification?.nsf_percentage || 0
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

    return (
      <div className="institution-card">
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
          </div>
          <div className="metric">
            <div className="metric-label">Recently Lost Positions</div>
            <div className="metric-value">{institution.recently_lost_positions}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Total Lab Size</div>
            <div className="metric-value">{institution.estimated_lab_size}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Risk Score</div>
            <div className="metric-value">{institution.risk_score}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Active Funding</div>
            <div className="metric-value">{formatCurrency(institution.total_active_funding)}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Funding Cliff</div>
            <div className="metric-value">{institution.funding_cliff_percentage}%</div>
          </div>
        </div>

        {institution.funding_diversification && (
          <div className="funding-breakdown">
            <div className="funding-breakdown-label">Funding Sources</div>
            <div className="funding-bar">
              <div 
                className="funding-nih" 
                style={{ width: `${nihPercentage}%` }}
              ></div>
              <div 
                className="funding-nsf" 
                style={{ width: `${nsfPercentage}%` }}
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
            </div>
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

  const FederalAgencyExplorer = () => {
    const exportFederalToCSV = () => {
      if (!federalData?.data?.labs) return;

      const headers = [
        'Institution Name',
        'Total Funding', 
        'Total Awards',
        'Average Award Amount',
        'PI Count Estimate',
        'Funding Trend',
        'Top Agencies',
        'Research Areas'
      ];

      const csvData = federalData.data.labs.map(lab => [
        lab.institution_name || '',
        lab.total_funding || 0,
        lab.total_awards || 0,
        lab.avg_award_amount || 0,
        lab.pi_count || 0,
        lab.funding_trend || '',
        Object.keys(lab.agency_breakdown || {}).join('; '),
        (lab.top_research_areas || []).join('; ')
      ]);

      const csvContent = [headers, ...csvData]
        .map(row => row.map(cell => `"${String(cell || '').replace(/"/g, '""')}"`).join(','))
        .join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `federal-labs-${selectedAgencies.join('-')}-${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      alert(`Successfully exported ${federalData.data.labs.length} lab funding summaries to CSV`);
    };

    const handleAgencyToggle = (agency) => {
      setSelectedAgencies(prev => 
        prev.includes(agency) 
          ? prev.filter(a => a !== agency)
          : [...prev, agency]
      );
    };

    return (
      <div>
        {/* Agency Selection */}
        <div className="leaderboard-controls" style={{ marginBottom: '20px' }}>
          <div>
            <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Select Agencies:</h3>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {['NSF', 'NIH', 'DOD', 'DOE', 'NASA'].map(agency => (
                <button
                  key={agency}
                  onClick={() => handleAgencyToggle(agency)}
                  style={{
                    padding: '8px 16px',
                    border: '2px solid #667eea',
                    borderRadius: '20px',
                    background: selectedAgencies.includes(agency) ? '#667eea' : 'white',
                    color: selectedAgencies.includes(agency) ? 'white' : '#667eea',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: '500',
                    transition: 'all 0.3s ease'
                  }}
                >
                  {agency}
                </button>
              ))}
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
            <button 
              onClick={fetchFederalData} 
              className="refresh-button"
              disabled={federalLoading || selectedAgencies.length === 0}
            >
              {federalLoading ? 'Loading...' : '🔄 Fetch Lab Data'}
            </button>
            
            {federalData?.data?.labs && (
              <button 
                onClick={exportFederalToCSV}
                className="export-button"
                disabled={federalLoading}
              >
                📊 Export Labs CSV
              </button>
            )}
          </div>
        </div>

        {/* Federal Data Display */}
        {federalLoading && (
          <div className="loading">Loading federal agency lab data...</div>
        )}

        {federalData?.data && (
          <div className="leaderboard">
            <div className="leaderboard-header">
              🏛️ Federal Research Labs Funding Summary
              <div style={{ float: 'right', fontSize: '0.9rem', opacity: 0.8 }}>
                {federalData.data.summary?.total_labs || 0} labs • ${(federalData.data.summary?.total_funding || 0).toLocaleString()} total
              </div>
            </div>
            
            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', padding: '20px' }}>
              <div className="metric" style={{ textAlign: 'center' }}>
                <div className="metric-label">Total Labs</div>
                <div className="metric-value">{formatNumber(federalData.data.summary?.total_labs || 0)}</div>
              </div>
              <div className="metric" style={{ textAlign: 'center' }}>
                <div className="metric-label">Total Funding</div>
                <div className="metric-value">{formatCurrency(federalData.data.summary?.total_funding || 0)}</div>
              </div>
              <div className="metric" style={{ textAlign: 'center' }}>
                <div className="metric-label">Total Awards</div>
                <div className="metric-value">{formatNumber(federalData.data.summary?.total_awards || 0)}</div>
              </div>
              <div className="metric" style={{ textAlign: 'center' }}>
                <div className="metric-label">Agencies Queried</div>
                <div className="metric-value">{(federalData.data.summary?.agencies_queried || []).join(', ')}</div>
              </div>
            </div>

            {/* Top Labs by Funding */}
            <div style={{ padding: '0 20px 20px' }}>
              <h3 style={{ color: '#333', marginBottom: '15px' }}>Research Labs by Federal Funding</h3>
              {(federalData.data.labs || []).map((lab, index) => (
                <div key={index} className="institution-card" style={{ marginBottom: '15px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div className="institution-name" style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                        {lab.institution_name}
                      </div>
                      
                      {/* Funding Breakdown */}
                      <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '8px' }}>
                        <strong>Agency Breakdown:</strong>
                        {Object.entries(lab.agency_breakdown || {}).map(([agency, data]) => (
                          <span key={agency} style={{ marginRight: '15px' }}>
                            {agency}: {formatCurrency(data.funding)} ({data.awards} awards)
                          </span>
                        ))}
                      </div>
                      
                      {/* Recent Awards */}
                      {lab.recent_awards && lab.recent_awards.length > 0 && (
                        <div style={{ color: '#666', fontSize: '0.85rem', marginTop: '5px' }}>
                          <strong>Recent Awards:</strong> {lab.recent_awards.slice(0, 2).map(award => 
                            `${award.agency} - ${formatCurrency(award.amount)}`
                          ).join(' • ')}
                        </div>
                      )}
                      
                      {/* Research Areas */}
                      {lab.top_research_areas && lab.top_research_areas.length > 0 && (
                        <div style={{ color: '#666', fontSize: '0.85rem', marginTop: '3px' }}>
                          <strong>Research Areas:</strong> {lab.top_research_areas.join(', ')}
                        </div>
                      )}
                    </div>
                    
                    <div style={{ textAlign: 'right', marginLeft: '20px' }}>
                      <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#667eea' }}>
                        {formatCurrency(lab.total_funding || 0)}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        {lab.total_awards || 0} awards • ~{lab.pi_count || 0} PIs
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#666' }}>
                        Avg: {formatCurrency(lab.avg_award_amount || 0)}
                      </div>
                      <div style={{ 
                        fontSize: '0.8rem', 
                        color: lab.funding_trend === 'increasing' ? '#28a745' : 
                               lab.funding_trend === 'decreasing' ? '#dc3545' : '#6c757d',
                        fontWeight: '500'
                      }}>
                        📈 {lab.funding_trend || 'stable'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const TabNavigation = () => (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      marginBottom: '30px',
      borderBottom: '2px solid #eee'
    }}>
      <button
        onClick={() => setActiveTab('leaderboard')}
        style={{
          padding: '15px 30px',
          border: 'none',
          background: activeTab === 'leaderboard' ? '#667eea' : 'transparent',
          color: activeTab === 'leaderboard' ? 'white' : '#667eea',
          fontSize: '16px',
          fontWeight: '600',
          cursor: 'pointer',
          borderRadius: '8px 8px 0 0',
          transition: 'all 0.3s ease'
        }}
      >
        🚨 Risk Leaderboard
      </button>
      <button
        onClick={() => setActiveTab('federal')}
        style={{
          padding: '15px 30px',
          border: 'none',
          background: activeTab === 'federal' ? '#667eea' : 'transparent',
          color: activeTab === 'federal' ? 'white' : '#667eea',
          fontSize: '16px',
          fontWeight: '600',
          cursor: 'pointer',
          borderRadius: '8px 8px 0 0',
          marginLeft: '5px',
          transition: 'all 0.3s ease'
        }}
      >
        🏛️ Federal Agencies
      </button>
    </div>
  );

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

  const totalAtRisk = leaderboardData?.data?.reduce((sum, inst) => sum + inst.at_risk_positions, 0) || 0;
  const totalRecentlyLost = leaderboardData?.data?.reduce((sum, inst) => sum + inst.recently_lost_positions, 0) || 0;
  const totalFunding = leaderboardData?.data?.reduce((sum, inst) => sum + inst.total_active_funding, 0) || 0;

  return (
    <div className="container">
      <div className="header">
        <h1>🚨 Academic Layoff Risk Tracker</h1>
        <p>Real-time analysis of NIH & NSF funding risks across research institutions</p>
      </div>

      <TabNavigation />

      {activeTab === 'leaderboard' ? (
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
                disabled={!leaderboardData?.data || loading}
                style={{
                  padding: '10px 20px',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: leaderboardData?.data ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                  fontWeight: '500',
                  opacity: leaderboardData?.data ? 1 : 0.6,
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
              🏆 Institution Risk Leaderboard
              {lastUpdated && <span style={{ float: 'right', fontSize: '0.9rem', opacity: 0.8 }}>
                Last updated: {lastUpdated}
              </span>}
            </div>
            
            {leaderboardData?.data?.map((institution, index) => (
              <InstitutionCard key={index} institution={institution} />
            ))}
          </div>

          <div style={{ marginTop: '30px', padding: '20px', background: 'white', borderRadius: '10px', fontSize: '0.9rem', color: '#666' }}>
            <strong>Methodology:</strong> Risk scores combine funding cliff analysis (40%), recent funding loss (30%), lab size impact (20%), 
            and grant concentration penalties (10%). Department-specific cost models and agency diversification bonuses are applied. 
            Data sources: NIH RePORTER and NSF Award Search APIs.
          </div>
        </>
      ) : (
        <FederalAgencyExplorer />
      )}
    </div>
  );
}

export default App;
