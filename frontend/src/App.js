import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [loading, setLoading] = useState(true);
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
    </div>
  );
}

export default App;
