import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { motion } from 'framer-motion';
import { 
  FaCheckCircle, 
  FaExclamationTriangle, 
  FaTimesCircle,
  FaCloud,
  FaFileAlt,
  FaSpinner,
  FaClock
} from 'react-icons/fa';
import { buildApiUrl } from '@/lib/api';

// Compliance Gauge Component
const ComplianceGauge = ({ score }) => {
  const percentage = Math.min(Math.max(score, 0), 100);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const offset = circumference - (percentage / 100) * circumference;
  
  const getColor = () => {
    if (score >= 80) return '#10b981'; // green
    if (score >= 60) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  return (
    <div className="relative w-32 h-32">
      <svg className="transform -rotate-90 w-32 h-32">
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke="#e5e7eb"
          strokeWidth="8"
          fill="none"
        />
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke={getColor()}
          strokeWidth="8"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold" style={{ color: getColor() }}>
            {score}
          </div>
          <div className="text-xs text-gray-500">/ 100</div>
        </div>
      </div>
    </div>
  );
};

const AzureComplianceLatestResult = () => {
  const { authToken } = useAuth();
  const [latestResult, setLatestResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLatestResult = async () => {
      try {
        setLoading(true);
        const response = await fetch(buildApiUrl('/api/azure-checker/latest-result'), {
          headers: authToken ? {
            'Authorization': `Bearer ${authToken}`
          } : {}
        });

        if (response.ok) {
          const data = await response.json();
          if (data.status === 'success' && data.result) {
            setLatestResult(data.result);
          } else {
            setLatestResult(null); // No results yet
          }
        } else {
          throw new Error('Failed to fetch latest result');
        }
      } catch (err) {
        console.error('Error fetching latest Azure compliance result:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (authToken) {
      fetchLatestResult();
    }
  }, [authToken]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'Compliant':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Partial':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Non-Compliant':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Compliant':
        return <FaCheckCircle className="text-green-600" />;
      case 'Partial':
        return <FaExclamationTriangle className="text-yellow-600" />;
      case 'Non-Compliant':
        return <FaTimesCircle className="text-red-600" />;
      default:
        return <FaCloud />;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 flex items-center justify-center">
        <FaSpinner className="animate-spin text-primary text-2xl" />
        <span className="ml-3 text-gray-600">Loading latest analysis...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-red-600">Error loading latest result: {error}</div>
      </div>
    );
  }

  if (!latestResult) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center gap-3 text-gray-600">
          <FaCloud className="text-2xl" />
          <div>
            <p className="font-semibold">No Azure Compliance Analysis Yet</p>
            <p className="text-sm">Upload a document in Azure Compliance Checker to see results here.</p>
          </div>
        </div>
      </div>
    );
  }

  // Check if this is multi-framework result
  const isMultiFramework = latestResult.frameworks && latestResult.framework_scores;
  const overallScore = latestResult.overall_score || latestResult.score || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-white to-blue-50 rounded-lg shadow-lg p-6 border border-blue-100"
    >
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <FaCloud className="text-3xl text-blue-600" />
          <div>
            <h4 className="font-bold text-gray-900 text-lg">Multi-Framework Compliance Analysis</h4>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
              <FaFileAlt className="text-xs" />
              <span className="truncate max-w-md">{latestResult.document_name}</span>
            </div>
          </div>
        </div>
        <div className={`px-4 py-2 rounded-full border-2 flex items-center gap-2 ${getStatusColor(latestResult.overall_status)} shadow-sm`}>
          {getStatusIcon(latestResult.overall_status)}
          <span className="font-bold text-sm">{latestResult.overall_status}</span>
        </div>
      </div>

      {/* Overall Score Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Overall Score Gauge */}
        <div className="bg-white rounded-xl p-6 shadow-md border border-gray-200">
          <div className="flex flex-col items-center justify-center">
            <ComplianceGauge score={overallScore} />
            <p className="mt-3 text-base font-bold text-gray-800">Overall Compliance Score</p>
            <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
              <FaClock className="text-xs" />
              <span>{formatDate(latestResult.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Framework Scores Grid */}
        {isMultiFramework && latestResult.framework_scores && (
          <div className="bg-white rounded-xl p-6 shadow-md border border-gray-200">
            <h5 className="font-bold text-gray-900 mb-4 text-center">Framework Scores</h5>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(latestResult.framework_scores).map(([framework, score]) => {
                const status = score >= 80 ? 'Compliant' : score >= 60 ? 'Partial' : 'Non-Compliant';
                const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
                const frameworkName = framework === 'gdpr' ? 'GDPR' : 
                                     framework === 'iso27001' ? 'ISO 27001' :
                                     framework === 'iso27017' ? 'ISO 27017' :
                                     framework === 'iso27018' ? 'ISO 27018' :
                                     framework.charAt(0).toUpperCase() + framework.slice(1);
                
                return (
                  <div key={framework} className="bg-gradient-to-br from-gray-50 to-white p-3 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
                    <div className="text-center">
                      <div className="text-xs font-semibold text-gray-600 uppercase mb-2">
                        {frameworkName}
                      </div>
                      <div className="text-3xl font-bold mb-1" style={{ color }}>
                        {score}
                      </div>
                      <div className="text-xs px-2 py-1 rounded-full inline-block" style={{
                        backgroundColor: color + '20',
                        color: color
                      }}>
                        {status}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Legacy single-framework display */}
        {!isMultiFramework && (
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-600">Categories Analyzed</p>
              <p className="text-lg font-semibold text-gray-900">{latestResult.categories_analyzed}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Checks</p>
              <p className="text-lg font-semibold text-gray-900">{latestResult.total_checks}</p>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      {latestResult.summary && (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-gray-700 leading-relaxed">{latestResult.summary}</p>
        </div>
      )}
    </motion.div>
  );
};

export default AzureComplianceLatestResult;

