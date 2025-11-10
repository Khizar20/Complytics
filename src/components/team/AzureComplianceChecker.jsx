import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FaCloudUploadAlt, 
  FaCheckCircle, 
  FaExclamationTriangle, 
  FaTimesCircle,
  FaFilePdf,
  FaFileWord,
  FaFileAlt,
  FaFileCode,
  FaDownload,
  FaSpinner,
  FaInfoCircle,
  FaShieldAlt,
  FaChartPie,
  FaListAlt,
  FaCloud,
  FaServer
} from 'react-icons/fa';

const AzureComplianceChecker = () => {
  const { authToken } = useAuth();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [checkerStatus, setCheckerStatus] = useState(null);

  // Check if Azure Checker is ready
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/azure-checker/status', {
          headers: authToken ? {
            'Authorization': `Bearer ${authToken}`
          } : {}
        });
        const data = await response.json();
        setCheckerStatus(data);
      } catch (error) {
        console.error('Error checking Azure Checker status:', error);
      }
    };
    if (authToken) {
      checkStatus();
    }
  }, [authToken]);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain',
        'application/json'
      ];
      
      if (!allowedTypes.includes(selectedFile.type)) {
        setError('Unsupported file type. Please upload PDF, DOCX, TXT, or JSON files.');
        return;
      }

      setFile(selectedFile);
      setError(null);
      setAnalysis(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setAnalyzing(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/azure-checker/analyze', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json();
      setAnalysis(data);
      setError(null);
    } catch (error) {
      console.error('Error analyzing document:', error);
      setError(error.message || 'Failed to analyze document');
    } finally {
      setUploading(false);
      setAnalyzing(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!analysis) return;

    setGeneratingReport(true);

    try {
      const response = await fetch('http://localhost:8000/api/azure-checker/generate-report', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(analysis)
      });

      if (!response.ok) {
        throw new Error('Failed to generate report');
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `azure_compliance_report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (error) {
      console.error('Error generating report:', error);
      setError('Failed to generate PDF report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Compliant':
        return <FaCheckCircle className="text-green-500 text-xl" />;
      case 'Partial':
        return <FaExclamationTriangle className="text-yellow-500 text-xl" />;
      case 'Non-Compliant':
        return <FaTimesCircle className="text-red-500 text-xl" />;
      default:
        return <FaInfoCircle className="text-gray-500 text-xl" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Compliant':
        return 'text-green-600 bg-green-50';
      case 'Partial':
        return 'text-yellow-600 bg-yellow-50';
      case 'Non-Compliant':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getFileIcon = () => {
    if (!file) return <FaFileAlt className="text-5xl text-gray-400" />;
    
    const ext = file.name.split('.').pop().toLowerCase();
    switch (ext) {
      case 'pdf':
        return <FaFilePdf className="text-5xl text-red-500" />;
      case 'docx':
      case 'doc':
        return <FaFileWord className="text-5xl text-blue-500" />;
      case 'json':
        return <FaFileCode className="text-5xl text-green-500" />;
      default:
        return <FaFileAlt className="text-5xl text-gray-500" />;
    }
  };

  const ComplianceGauge = ({ score }) => {
    const circumference = 2 * Math.PI * 45;
    const strokeDashoffset = circumference - (score / 100) * circumference;
    
    let color = '#ef4444'; // red
    if (score >= 80) color = '#22c55e'; // green
    else if (score >= 60) color = '#eab308'; // yellow

    return (
      <div className="relative w-32 h-32">
        <svg className="w-32 h-32 transform -rotate-90">
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke="#e5e7eb"
            strokeWidth="10"
            fill="none"
          />
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke={color}
            strokeWidth="10"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold" style={{ color }}>{score}</span>
          <span className="text-xs text-gray-500">/ 100</span>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <FaCloud className="text-4xl text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-900">Azure Compliance Checker</h1>
          </div>
          <p className="text-gray-600 text-lg">
            Analyze your Azure configurations and policies against best practices and compliance frameworks
          </p>
        </div>

        {/* Status Banner */}
        {checkerStatus && checkerStatus.status !== 'ready' && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center gap-2">
              <FaExclamationTriangle className="text-yellow-600" />
              <p className="text-yellow-800">
                {checkerStatus.message}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl shadow-lg p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <FaCloudUploadAlt className="text-2xl text-blue-600" />
              <h2 className="text-2xl font-bold text-gray-900">Upload Document</h2>
            </div>

            {/* File Upload Area */}
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-blue-500 transition-colors cursor-pointer"
              onClick={() => document.getElementById('fileInput').click()}
            >
              {getFileIcon()}
              <p className="mt-4 text-gray-700 font-medium">
                {file ? file.name : 'Click to upload or drag and drop'}
              </p>
              <p className="mt-2 text-sm text-gray-500">
                PDF, DOCX, TXT, or JSON (Max 10MB)
              </p>
              <input
                id="fileInput"
                type="file"
                accept=".pdf,.docx,.doc,.txt,.json"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            {/* File Info */}
            {file && (
              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-gray-700">
                  <strong>File:</strong> {file.name}
                </p>
                <p className="text-sm text-gray-700">
                  <strong>Size:</strong> {(file.size / 1024).toFixed(2)} KB
                </p>
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={handleAnalyze}
              disabled={!file || analyzing || checkerStatus?.status !== 'ready'}
              className="mt-6 w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {analyzing ? (
                <>
                  <FaSpinner className="animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <FaShieldAlt />
                  Analyze Document
                </>
              )}
            </button>

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}
          </motion.div>

          {/* Info Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl shadow-lg p-6 text-white"
          >
            <h2 className="text-2xl font-bold mb-4">What We Check</h2>
            <div className="space-y-3">
              {[
                { icon: FaShieldAlt, text: 'Security Controls & Encryption' },
                { icon: FaCheckCircle, text: 'Identity & Access Management' },
                { icon: FaChartPie, text: 'Storage & Data Protection' },
                { icon: FaListAlt, text: 'Networking & Connectivity' },
                { icon: FaInfoCircle, text: 'Monitoring & Governance' },
                { icon: FaServer, text: 'Compute & Database Best Practices' }
              ].map((item, index) => (
                <div key={index} className="flex items-center gap-3">
                  <item.icon className="text-xl" />
                  <span>{item.text}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 p-4 bg-white/10 rounded-lg">
              <p className="text-sm">
                <strong>Supported Files:</strong> Azure configuration files, policy documents, 
                security guidelines, and architectural documentation.
              </p>
            </div>
          </motion.div>
        </div>

        {/* Analysis Results */}
        <AnimatePresence>
          {analysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-6 bg-white rounded-2xl shadow-lg p-6"
            >
              {/* Results Header */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Analysis Results</h2>
                <button
                  onClick={handleGenerateReport}
                  disabled={generatingReport}
                  className="flex items-center gap-2 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-300"
                >
                  {generatingReport ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FaDownload />
                      Export PDF Report
                    </>
                  )}
                </button>
              </div>

              {/* Overall Score Section */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="col-span-1 flex justify-center items-center">
                  <ComplianceGauge score={analysis.overall_score || analysis.score || 0} />
                </div>
                <div className="col-span-2 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-600">Overall Status:</span>
                    <span className={`px-3 py-1 rounded-full font-semibold ${getStatusColor(analysis.overall_status)}`}>
                      {analysis.overall_status}
                    </span>
                  </div>
                  <div className="text-gray-700">
                    <strong>Document:</strong> {analysis.document_name}
                  </div>
                  <div className="text-gray-700">
                    <strong>Frameworks Analyzed:</strong> {analysis.frameworks_analyzed || 1}
                  </div>
                </div>
              </div>

              {/* Framework Scores Grid */}
              {analysis.framework_scores && (
                <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
                  <h3 className="font-bold text-gray-900 mb-4 text-lg flex items-center gap-2">
                    <FaChartPie className="text-blue-600" />
                    Framework Compliance Scores
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {Object.entries(analysis.framework_scores).map(([framework, score]) => {
                      const status = score >= 80 ? 'Compliant' : score >= 60 ? 'Partial' : 'Non-Compliant';
                      return (
                        <div key={framework} className="bg-white p-4 rounded-lg shadow-sm">
                          <div className="text-center">
                            <div className="text-sm font-semibold text-gray-600 uppercase mb-2">
                              {framework === 'gdpr' ? 'GDPR' : 
                               framework === 'iso27001' ? 'ISO 27001' :
                               framework === 'iso27017' ? 'ISO 27017' :
                               framework === 'iso27018' ? 'ISO 27018' :
                               framework.charAt(0).toUpperCase() + framework.slice(1)}
                            </div>
                            <div className="text-3xl font-bold mb-1" style={{ 
                              color: score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : '#ef4444' 
                            }}>
                              {score}
                            </div>
                            <div className={`text-xs px-2 py-1 rounded-full font-semibold inline-block ${getStatusColor(status)}`}>
                              {status}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Summary */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-bold text-gray-900 mb-2">Summary</h3>
                <p className="text-gray-700 whitespace-pre-line">{analysis.summary}</p>
              </div>

              {/* Framework-Specific Findings */}
              <div>
                <h3 className="font-bold text-gray-900 mb-4 text-xl">Detailed Findings by Framework</h3>
                
                {analysis.frameworks ? (
                  /* Multi-framework results */
                  <div className="space-y-6">
                    {Object.entries(analysis.frameworks).map(([frameworkName, frameworkData], fIndex) => (
                      <div key={frameworkName} className="border-2 border-gray-200 rounded-xl p-5 bg-white">
                        <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                          <h4 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            <FaShieldAlt className="text-blue-600" />
                            {frameworkName === 'gdpr' ? 'GDPR' : 
                             frameworkName === 'iso27001' ? 'ISO 27001' :
                             frameworkName === 'iso27017' ? 'ISO 27017' :
                             frameworkName === 'iso27018' ? 'ISO 27018' :
                             frameworkData.framework_name || frameworkName.toUpperCase()}
                          </h4>
                          <div className="flex items-center gap-3">
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(frameworkData.status)}`}>
                              {frameworkData.status}
                            </span>
                            <span className="text-2xl font-bold" style={{
                              color: frameworkData.score >= 80 ? '#22c55e' : frameworkData.score >= 60 ? '#eab308' : '#ef4444'
                            }}>
                              {frameworkData.score}/100
                            </span>
                          </div>
                        </div>

                        {/* Framework Recommendation */}
                        {frameworkData.recommendation && (
                          <div className="mb-3 p-3 bg-blue-50 rounded-lg">
                            <strong className="text-blue-900">Recommendation:</strong>
                            <p className="text-blue-800 text-sm mt-1">{frameworkData.recommendation}</p>
                          </div>
                        )}

                        {/* Gaps */}
                        {frameworkData.gaps && frameworkData.gaps.length > 0 && (
                          <div className="mb-3 p-3 bg-red-50 rounded-lg border border-red-200">
                            <strong className="text-red-900 flex items-center gap-2">
                              <FaExclamationTriangle className="text-red-600" />
                              Gaps Identified:
                            </strong>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                              {frameworkData.gaps.map((gap, idx) => (
                                <li key={idx} className="text-red-800 text-sm">{gap}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Compliant Areas */}
                        {frameworkData.compliant_areas && frameworkData.compliant_areas.length > 0 && (
                          <div className="mb-3 p-3 bg-green-50 rounded-lg border border-green-200">
                            <strong className="text-green-900 flex items-center gap-2">
                              <FaCheckCircle className="text-green-600" />
                              Compliant Areas:
                            </strong>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                              {frameworkData.compliant_areas.map((area, idx) => (
                                <li key={idx} className="text-green-800 text-sm">{area}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Key Requirements */}
                        {frameworkData.key_requirements && frameworkData.key_requirements.length > 0 && (
                          <div className="p-3 bg-gray-50 rounded-lg">
                            <strong className="text-gray-900">Key Requirements:</strong>
                            <ul className="list-disc list-inside mt-1 space-y-1">
                              {frameworkData.key_requirements.map((req, idx) => (
                                <li key={idx} className="text-gray-600 text-sm">{req}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Priority Actions */}
                        {frameworkData.priority_actions && frameworkData.priority_actions.length > 0 && (
                          <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                            <strong className="text-yellow-900">Priority Actions:</strong>
                            <ul className="list-decimal list-inside mt-1 space-y-1">
                              {frameworkData.priority_actions.map((action, idx) => (
                                <li key={idx} className="text-yellow-800 text-sm">{action}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : analysis.findings && analysis.findings.length > 0 ? (
                  /* Legacy single-framework results */
                  <div className="space-y-4">
                    {analysis.findings.map((finding, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            {getStatusIcon(finding.status)}
                            <h4 className="font-bold text-gray-900">{finding.category || finding.framework}</h4>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(finding.status)}`}>
                              {finding.status}
                            </span>
                            <span className="text-sm text-gray-600">
                              Confidence: {finding.confidence.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        <p className="text-gray-700 mb-2">
                          <strong>Recommendation:</strong> {finding.recommendation}
                        </p>
                        
                        {finding.gaps_identified && finding.gaps_identified.length > 0 && (
                          <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200">
                            <strong className="text-red-900 flex items-center gap-2">
                              <FaExclamationTriangle className="text-red-600" />
                              Gaps Identified:
                            </strong>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                              {finding.gaps_identified.map((gap, idx) => (
                                <li key={idx} className="text-red-800 text-sm">{gap}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        
                        {finding.compliant_areas && finding.compliant_areas.length > 0 && (
                          <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200">
                            <strong className="text-green-900 flex items-center gap-2">
                              <FaCheckCircle className="text-green-600" />
                              Compliant Areas:
                            </strong>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                              {finding.compliant_areas.map((area, idx) => (
                                <li key={idx} className="text-green-800 text-sm">{area}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        
                        {finding.key_points && finding.key_points.length > 0 && (
                          <div className="mt-3">
                            <strong className="text-gray-900">Key Best Practices:</strong>
                            <ul className="list-disc list-inside mt-1 space-y-1">
                              {finding.key_points.map((point, idx) => (
                                <li key={idx} className="text-gray-600 text-sm">{point}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No detailed findings available.</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AzureComplianceChecker;

