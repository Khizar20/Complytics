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
import { buildApiUrl } from '@/lib/api';

const AzureComplianceChecker = () => {
  const { authToken } = useAuth();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [checkerStatus, setCheckerStatus] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [generatingChecklist, setGeneratingChecklist] = useState(false);
  const [selectedFramework, setSelectedFramework] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState(null);
  const [analyzingSnapshot, setAnalyzingSnapshot] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [generationProgress, setGenerationProgress] = useState(0);

  // Check if Azure Checker is ready
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(buildApiUrl('/api/azure-checker/status'), {
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

  useEffect(() => {
    const fetchSnapshot = async () => {
      setSnapshotLoading(true);
      setSnapshotError(null);
      try {
        const response = await fetch(buildApiUrl('/api/azure/config/snapshot/latest'), {
          headers: authToken ? {
            'Authorization': `Bearer ${authToken}`
          } : {}
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || errorData.message || 'Failed to load Azure snapshot');
        }

        const data = await response.json();
        if (data.exists) {
          setSnapshot(data.snapshot);
        } else {
          setSnapshot(null);
        }
      } catch (err) {
        console.error('Error fetching Azure snapshot:', err);
        setSnapshot(null);
        setSnapshotError(err.message || 'Unable to load Azure snapshot');
      } finally {
        setSnapshotLoading(false);
      }
    };

    if (authToken) {
      fetchSnapshot();
    } else {
      setSnapshot(null);
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
    setAnalysisProgress(0);

    // Simulate progress steps
    const progressSteps = [
      { step: 1, message: 'Uploading document...', progress: 10 },
      { step: 2, message: 'Extracting text...', progress: 25 },
      { step: 3, message: 'Processing content...', progress: 40 },
      { step: 4, message: 'Analyzing compliance...', progress: 60 },
      { step: 5, message: 'Checking frameworks...', progress: 80 },
      { step: 6, message: 'Generating report...', progress: 95 }
    ];

    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 95) return prev;
        const currentStep = progressSteps.find(s => s.progress > prev) || progressSteps[progressSteps.length - 1];
        return Math.min(prev + 5, currentStep.progress);
      });
    }, 500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(buildApiUrl('/api/azure-checker/analyze'), {
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

      setAnalysisProgress(100);
      const data = await response.json();
      setAnalysis(data);
      setError(null);
    } catch (error) {
      console.error('Error analyzing document:', error);
      setError(error.message || 'Failed to analyze document');
    } finally {
      clearInterval(progressInterval);
      setUploading(false);
      setAnalyzing(false);
      setTimeout(() => setAnalysisProgress(0), 1000);
    }
  };

  const handleAnalyzeSnapshot = async () => {
    if (!snapshot) {
      setError('No fetched Azure settings snapshot is available. Please fetch settings from Azure first.');
      return;
    }

    setAnalyzingSnapshot(true);
    setAnalyzing(true);
    setError(null);
    setChecklist(null);
    setSelectedFramework(null);
    setAnalysis(null);
    setAnalysisProgress(0);

    // Simulate progress for snapshot analysis
    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 95) return prev;
        return prev + 5;
      });
    }, 500);

    try {
      const response = await fetch(buildApiUrl('/api/azure-checker/analyze-snapshot'), {
        method: 'POST',
        headers: authToken ? {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        } : {}
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to analyze fetched settings');
      }

      setAnalysisProgress(100);
      const data = await response.json();
      setAnalysis(data);
      setError(null);
    } catch (err) {
      console.error('Error analyzing fetched settings:', err);
      setError(err.message || 'Failed to analyze fetched settings');
    } finally {
      clearInterval(progressInterval);
      setAnalyzingSnapshot(false);
      setAnalyzing(false);
      setTimeout(() => setAnalysisProgress(0), 1000);
    }
  };

  const handleGenerateReport = async () => {
    if (!analysis) return;

    setGeneratingReport(true);

    try {
      const response = await fetch(buildApiUrl('/api/azure-checker/generate-report'), {
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

  const handleGenerateChecklist = async (framework = null) => {
    if (!analysis || !analysis.result_id) {
      setError('Please analyze a document first');
      return;
    }

    setGeneratingChecklist(true);
    setError(null);
    setGenerationProgress(0);

    // Simulate progress steps
    const progressInterval = setInterval(() => {
      setGenerationProgress(prev => {
        if (prev >= 95) return prev;
        return prev + 3;
      });
    }, 300);

    try {
      const url = framework 
        ? buildApiUrl(`/api/azure-checker/generate-checklist/${analysis.result_id}?framework=${framework}`)
        : buildApiUrl(`/api/azure-checker/generate-checklist/${analysis.result_id}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate checklist');
      }

      setGenerationProgress(100);
      const data = await response.json();
      setChecklist(data);
      setSelectedFramework(framework);
      setError(null);
    } catch (error) {
      console.error('Error generating checklist:', error);
      setError(error.message || 'Failed to generate compliance checklist');
    } finally {
      clearInterval(progressInterval);
      setGeneratingChecklist(false);
      setTimeout(() => setGenerationProgress(0), 1000);
    }
  };

  const exportChecklistToCSV = () => {
    if (!checklist) return;

    const headers = ['ID', 'Title', 'Priority', 'Effort', 'Gap Addressed', 'Azure Portal Path', 'Azure Services', 'Framework Reference'];
    const rows = checklist.checklist_items.map(item => [
      item.id,
      `"${item.title}"`,
      item.priority,
      item.effort,
      `"${item.gap_addressed}"`,
      `"${item.azure_portal_path || 'N/A'}"`,
      `"${item.azure_services?.join(', ') || 'N/A'}"`,
      `"${item.framework_reference || 'N/A'}"`
    ]);

    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `compliance_checklist_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportChecklistToPDF = async () => {
    if (!analysis || !analysis.result_id || !checklist) {
      setError('Please generate a checklist first');
      return;
    }

    try {
      const url = selectedFramework
        ? buildApiUrl(`/api/azure-checker/export-checklist-pdf/${analysis.result_id}?framework=${selectedFramework}`)
        : buildApiUrl(`/api/azure-checker/export-checklist-pdf/${analysis.result_id}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to export PDF');
      }

      // Download the PDF
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `compliance_checklist_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting checklist PDF:', error);
      setError(error.message || 'Failed to export PDF checklist');
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

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 bg-white rounded-2xl shadow-lg p-6 border border-blue-100"
        >
          <div className="flex items-center gap-3 mb-3">
            <FaCloud className="text-2xl text-indigo-600" />
            <h2 className="text-2xl font-bold text-gray-900">Fetched Azure Settings Snapshot</h2>
          </div>

          {snapshotLoading ? (
            <div className="flex items-center gap-2 text-gray-600">
              <FaSpinner className="animate-spin" />
              Loading snapshot...
            </div>
          ) : snapshot ? (
            <div>
              <p className="text-gray-700">
                <strong>Last fetched:</strong>{' '}
                {snapshot.timestamp ? new Date(snapshot.timestamp).toLocaleString() : 'Unknown'}
              </p>
              <p className="text-sm text-gray-600 mt-3 leading-relaxed">
                We captured these Azure settings automatically via Microsoft Graph. Due to API and licensing limitations
                this snapshot may not include every Azure control. You can analyze this partial snapshot for quick insights,
                or upload a full Azure configuration document for a comprehensive review.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleAnalyzeSnapshot}
                  disabled={analyzingSnapshot || checkerStatus?.status !== 'ready'}
                  className="flex items-center gap-2 bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors relative overflow-hidden"
                >
                  {analyzingSnapshot ? (
                    <>
                      <div className="absolute inset-0 bg-indigo-700" style={{ width: `${analysisProgress}%`, transition: 'width 0.3s ease' }}></div>
                      <div className="relative z-10 flex items-center gap-3">
                        <FaSpinner className="animate-spin" />
                        <span>Analyzing Snapshot... {analysisProgress}%</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <FaShieldAlt />
                      Analyze Fetched Settings
                    </>
                  )}
                </button>
                <span className="text-xs text-gray-500 italic">
                  Tip: Upload a detailed configuration file for deeper analysis.
                </span>
              </div>
              {analyzingSnapshot && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-sm text-gray-600">
                    <span>Progress</span>
                    <span className="font-semibold">{analysisProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <motion.div
                      className="bg-indigo-600 h-2.5 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${analysisProgress}%` }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    {analysisProgress < 25 && <span>📤 Processing snapshot data...</span>}
                    {analysisProgress >= 25 && analysisProgress < 50 && <span>📄 Extracting configuration...</span>}
                    {analysisProgress >= 50 && analysisProgress < 75 && <span>🔍 Analyzing compliance...</span>}
                    {analysisProgress >= 75 && analysisProgress < 95 && <span>📊 Checking frameworks...</span>}
                    {analysisProgress >= 95 && <span>✅ Finalizing analysis...</span>}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              <p className="text-gray-700">
                No Azure settings snapshot is stored yet. Run the Azure configuration fetch to capture the latest
                tenant settings, or upload a configuration document below for analysis.
              </p>
            </div>
          )}

          {snapshotError && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{snapshotError}</p>
            </div>
          )}
        </motion.div>

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
              className="mt-6 w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 relative overflow-hidden"
            >
              {analyzing ? (
                <>
                  <div className="absolute inset-0 bg-blue-700" style={{ width: `${analysisProgress}%`, transition: 'width 0.3s ease' }}></div>
                  <div className="relative z-10 flex items-center gap-3">
                    <FaSpinner className="animate-spin" />
                    <span>Analyzing Document... {analysisProgress}%</span>
                  </div>
                </>
              ) : (
                <>
                  <FaShieldAlt />
                  Analyze Document
                </>
              )}
            </button>
            
            {analyzing && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>Progress</span>
                  <span className="font-semibold">{analysisProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                  <motion.div
                    className="bg-blue-600 h-2.5 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${analysisProgress}%` }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  />
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  {analysisProgress < 25 && <span>📤 Uploading document...</span>}
                  {analysisProgress >= 25 && analysisProgress < 40 && <span>📄 Extracting text...</span>}
                  {analysisProgress >= 40 && analysisProgress < 60 && <span>⚙️ Processing content...</span>}
                  {analysisProgress >= 60 && analysisProgress < 80 && <span>🔍 Analyzing compliance...</span>}
                  {analysisProgress >= 80 && analysisProgress < 95 && <span>📊 Checking frameworks...</span>}
                  {analysisProgress >= 95 && <span>✅ Finalizing report...</span>}
                </div>
              </div>
            )}

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
                  {analysis.source_type && (
                    <div className="text-gray-700">
                      <strong>Source:</strong>{' '}
                      {analysis.source_type === 'snapshot' ? 'Fetched Azure settings snapshot' : 'Uploaded document'}
                    </div>
                  )}
                  {analysis.source_metadata?.snapshot_timestamp && (
                    <div className="text-gray-700">
                      <strong>Snapshot Captured:</strong>{' '}
                      {new Date(analysis.source_metadata.snapshot_timestamp).toLocaleString()}
                    </div>
                  )}
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

        {/* Compliance Checklist Section */}
        <AnimatePresence>
          {analysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-6 bg-white rounded-2xl shadow-lg p-6"
            >
              <div className="mb-6 space-y-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <FaListAlt className="text-blue-600" />
                    Compliance Checklist
                  </h2>
                  <p className="text-gray-600 mt-1">
                    Generate an actionable checklist to achieve full compliance based on identified gaps
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <span className="text-sm font-medium text-gray-700">Generate Checklist:</span>
                  {Object.keys(analysis.frameworks || {}).map((fw) => (
                    <button
                      key={fw}
                      onClick={() => handleGenerateChecklist(fw)}
                      disabled={generatingChecklist}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium shadow-sm hover:shadow-md"
                    >
                      {fw === 'gdpr' ? 'GDPR' : fw === 'iso27001' ? 'ISO 27001' : fw === 'iso27017' ? 'ISO 27017' : fw === 'iso27018' ? 'ISO 27018' : fw.toUpperCase()}
                    </button>
                  ))}
                  <button
                    onClick={() => handleGenerateChecklist()}
                    disabled={generatingChecklist}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium shadow-sm hover:shadow-md"
                  >
                    {generatingChecklist ? (
                      <>
                        <FaSpinner className="animate-spin inline mr-2" />
                        Generating...
                      </>
                    ) : (
                      'All Frameworks'
                    )}
                  </button>
                </div>
              </div>

              {checklist && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-6"
                >
                  <div className="space-y-4 mb-6 pb-4 border-b border-gray-200">
                    <div>
                      <p className="text-lg font-semibold text-gray-900">
                        {checklist.total_items} Actionable Items
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        Frameworks: {checklist.frameworks.map(fw => 
                          fw === 'gdpr' ? 'GDPR' : fw === 'iso27001' ? 'ISO 27001' : fw === 'iso27017' ? 'ISO 27017' : fw === 'iso27018' ? 'ISO 27018' : fw.toUpperCase()
                        ).join(', ')}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-sm font-medium text-gray-700">Export Options:</span>
                      <button
                        onClick={exportChecklistToCSV}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-sm hover:shadow-md font-medium"
                      >
                        <FaDownload />
                        Export CSV
                      </button>
                      <button
                        onClick={exportChecklistToPDF}
                        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-sm hover:shadow-md font-medium"
                      >
                        <FaFilePdf />
                        Export PDF
                      </button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {checklist.checklist_items.map((item, index) => {
                      const priorityColors = {
                        'CRITICAL': 'bg-red-100 border-red-300 text-red-800',
                        'HIGH': 'bg-orange-100 border-orange-300 text-orange-800',
                        'MEDIUM': 'bg-yellow-100 border-yellow-300 text-yellow-800',
                        'LOW': 'bg-blue-100 border-blue-300 text-blue-800'
                      };
                      const effortColors = {
                        'Quick': 'bg-green-100 text-green-800',
                        'Moderate': 'bg-yellow-100 text-yellow-800',
                        'Complex': 'bg-red-100 text-red-800'
                      };

                      return (
                        <motion.div
                          key={item.id || index}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.05 }}
                          className="border rounded-lg p-5 hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <span className="text-lg font-bold text-gray-700">#{item.id}</span>
                                <h3 className="text-lg font-semibold text-gray-900">{item.title}</h3>
                              </div>
                              <p className="text-gray-700 mb-3">{item.description}</p>
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-sm font-medium text-gray-600">Gap Addressed:</span>
                                <span className="text-sm text-gray-800">{item.gap_addressed}</span>
                              </div>
                              {item.azure_portal_path && (
                                <div className="mb-2 p-2 bg-blue-50 rounded border border-blue-200">
                                  <span className="text-sm font-semibold text-blue-900">📍 Azure Portal Path:</span>
                                  <p className="text-sm text-blue-800 mt-1">{item.azure_portal_path}</p>
                                </div>
                              )}
                              {item.settings_to_configure && typeof item.settings_to_configure === 'object' && (
                                <div className="mb-2 p-3 bg-gray-50 rounded border border-gray-200">
                                  <p className="text-sm font-semibold text-gray-900 mb-2">⚙️ Settings to Configure:</p>
                                  <div className="space-y-1 text-sm">
                                    <div><span className="font-medium">Setting:</span> {item.settings_to_configure.setting_name || 'N/A'}</div>
                                    <div><span className="font-medium">Current Value:</span> {item.settings_to_configure.current_value || 'N/A'}</div>
                                    <div><span className="font-medium">Required Value:</span> {item.settings_to_configure.required_value || 'N/A'}</div>
                                    <div><span className="font-medium">Location:</span> {item.settings_to_configure.location || 'N/A'}</div>
                                  </div>
                                </div>
                              )}
                            </div>
                            <div className="flex flex-col gap-2 ml-4">
                              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${priorityColors[item.priority] || priorityColors.MEDIUM}`}>
                                {item.priority}
                              </span>
                              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${effortColors[item.effort] || effortColors.Moderate}`}>
                                {item.effort}
                              </span>
                            </div>
                          </div>

                          {item.azure_services && item.azure_services.length > 0 && (
                            <div className="mb-3">
                              <span className="text-sm font-medium text-gray-600">Azure Services: </span>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {item.azure_services.map((service, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                                    {service}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {item.implementation_steps && item.implementation_steps.length > 0 && (
                            <div className="mb-3">
                              <p className="text-sm font-semibold text-gray-700 mb-2">📋 Step-by-Step Implementation Guide:</p>
                              <div className="space-y-3">
                                {item.implementation_steps.map((step, idx) => {
                                  if (typeof step === 'object' && step.step_number) {
                                    return (
                                      <div key={idx} className="pl-4 border-l-2 border-blue-300">
                                        <div className="font-semibold text-sm text-gray-900">
                                          Step {step.step_number}: {step.action}
                                        </div>
                                        {step.details && (
                                          <div className="text-sm text-gray-700 mt-1">{step.details}</div>
                                        )}
                                        {step.what_to_look_for && (
                                          <div className="text-xs text-gray-500 italic mt-1">
                                            👁️ What to look for: {step.what_to_look_for}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  } else {
                                    return (
                                      <div key={idx} className="text-sm text-gray-700">
                                        • {typeof step === 'string' ? step : JSON.stringify(step)}
                                      </div>
                                    );
                                  }
                                })}
                              </div>
                            </div>
                          )}
                          {item.verification_steps && item.verification_steps.length > 0 && (
                            <div className="mb-3 p-3 bg-green-50 rounded border border-green-200">
                              <p className="text-sm font-semibold text-green-900 mb-2">✅ Verification Steps:</p>
                              <ul className="list-disc list-inside space-y-1 text-sm text-green-800">
                                {item.verification_steps.map((vStep, idx) => (
                                  <li key={idx}>{vStep}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {item.additional_notes && (
                            <div className="mb-3 p-2 bg-yellow-50 rounded border border-yellow-200">
                              <p className="text-xs font-semibold text-yellow-900 mb-1">⚠️ Additional Notes:</p>
                              <p className="text-xs text-yellow-800">{item.additional_notes}</p>
                            </div>
                          )}

                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="flex items-center justify-between text-sm">
                              <div>
                                <span className="text-gray-600">Expected Outcome: </span>
                                <span className="text-gray-800">{item.expected_outcome}</span>
                              </div>
                              {item.framework_reference && (
                                <span className="text-gray-500 italic">
                                  {item.framework_reference}
                                </span>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {generatingChecklist && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-12 space-y-6"
                >
                  <div className="relative inline-block">
                    <FaListAlt className="text-6xl mx-auto mb-4 text-blue-600 opacity-20" />
                    <FaSpinner className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-4xl text-blue-600 animate-spin" />
                  </div>
                  <div className="space-y-4">
                    <div className="flex items-center justify-center gap-3">
                      <span className="text-2xl font-bold text-blue-600">{generationProgress}%</span>
                      <span className="text-gray-600">Generating Checklist...</span>
                    </div>
                    <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-3 overflow-hidden">
                      <motion.div
                        className="bg-gradient-to-r from-blue-600 to-indigo-600 h-3 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${generationProgress}%` }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                      />
                    </div>
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                      {generationProgress < 30 && <span>📋 Preparing checklist structure...</span>}
                      {generationProgress >= 30 && generationProgress < 60 && <span>🔍 Analyzing compliance gaps...</span>}
                      {generationProgress >= 60 && generationProgress < 90 && <span>✍️ Generating actionable items...</span>}
                      {generationProgress >= 90 && <span>✅ Finalizing checklist...</span>}
                    </div>
                  </div>
                </motion.div>
              )}
              
              {!checklist && !generatingChecklist && (
                <div className="text-center py-8 text-gray-500">
                  <FaListAlt className="text-4xl mx-auto mb-3 opacity-30" />
                  <p>Click a framework button above to generate a compliance checklist</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AzureComplianceChecker;

