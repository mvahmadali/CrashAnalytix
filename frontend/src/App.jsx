import { useState } from "react";
import * as React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";
import "./App.css";
import Header from "./components/Header";
import VideoPreview from "./components/VideoPreview";
import FileUpload from "./components/FileUpload";
import ResultDisplay from "./components/ResultDisplay";
import LoadingOverlay from "./components/LoadingOverlay";
import AccidentDetailsPage from "./pages/AccidentDetailsPage";
import LoadingAnimation from "./components/LoadingAnimation";
import useVideoUpload from "./hooks/useVideoUpload";
import AccidentHistory from "./pages/AccidentHistory";
import AccidentDetailsView from "./pages/AccidentDetailsView";

// Main App with Router
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainApp />} />
        <Route path="/detect" element={<DetectPage />} />
        <Route path="/accident-history" element={<AccidentHistory />} />
        <Route path="/accident-details/:id" element={<AccidentDetailsView />} />
      </Routes>
    </Router>
  );
}

// Your existing app functionality (Home page)
function MainApp() {
  const navigate = useNavigate();

  const handleViewHistory = () => {
    navigate("/accident-history");
  };

  const handleUploadFootage = () => {
    navigate("/detect");
  };

  // Show main app (Home page)
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-cover bg-center overflow-hidden">
      {/* <div className="absolute inset-0 bg-cover bg-center z-0" style={{ backgroundImage: "url('./assets/bg.jpg')" }} /> */}

      <div className="relative z-10 flex flex-col items-center text-center px-4">
        <Header />
        
        <button
          onClick={handleUploadFootage}
          className="mb-4 px-6 py-3 bg-gradient-to-r from-[#ff7e5f] to-[#feb47b] text-white font-semibold rounded-lg 
           hover:from-[#ff6a6a] hover:to-[#ff7e5f] transition-all duration-300
           shadow-lg hover:shadow-xl hover:shadow-orange-500/30
           transform hover:scale-105 active:scale-95"
        >
          Upload footage for analysis
        </button>
        
        <button
          onClick={handleViewHistory}
          className="mb-4 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold rounded-lg 
           hover:from-cyan-700 hover:to-blue-700 transition-all duration-300
           shadow-lg hover:shadow-xl hover:shadow-cyan-500/30
           transform hover:scale-105 active:scale-95"
        >
          View Accident History
        </button>
      </div>
    </div>
  );
}

// New Detect Page component
function DetectPage() {
  const navigate = useNavigate();
  const {
    video,
    preview,
    result,
    loading,
    videoRef,
    handleFileChange,
    handleUpload,
    getProcessedAccidentData,
  } = useVideoUpload();

  const [showDetailsPage, setShowDetailsPage] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);

  // Add detect-page class to body when component mounts
  React.useEffect(() => {
    document.body.classList.add('detect-page');
    return () => {
      document.body.classList.remove('detect-page');
    };
  }, []);

  const handleViewDetails = () => {
    setShowAnimation(true);

    // After 5 seconds, show the details page
    setTimeout(() => {
      setShowAnimation(false);
      setShowDetailsPage(true);
    }, 4000);
  };

  const handleBackToHome = () => {
    setShowDetailsPage(false);
  };

  // Show loading animation
  if (showAnimation) {
    return <LoadingAnimation />;
  }

  // Show accident details page
  if (showDetailsPage) {
    const processedAccidentData = getProcessedAccidentData();
    return (
      <AccidentDetailsPage
        onBack={handleBackToHome}
        accidentData={processedAccidentData}
      />
    );
  }

  // Show detect page with upload functionality
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-cover bg-center overflow-hidden">
      {/* <div className="absolute inset-0 bg-cover bg-center z-0" style={{ backgroundImage: "url('./assets/bg.jpg')" }} /> */}

      <div className="relative z-10 flex flex-col items-center text-center px-4">
        <Header />
        
        {/* Back to Home button */}
        <button
          onClick={() => navigate("/")}
          className="mb-4 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white font-medium rounded-lg 
           transition-all duration-300 shadow-md hover:shadow-lg
           transform hover:scale-105 active:scale-95"
        >
          ← Back to Home
        </button>

        {/* Upload box - always visible on this page */}
        <div className="glass-container-static bg-cyan-900/20 backdrop-blur-xl rounded-2xl p-8 shadow-2xl w-full max-w-md relative">
          {loading && <LoadingOverlay />}

          <VideoPreview preview={preview} videoRef={videoRef} />
          <FileUpload handleFileChange={handleFileChange} preview={preview} />

          <button
            onClick={handleUpload}
            disabled={loading}
            className="w-full mt-6 bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold py-3 px-6 rounded-xl transition-all 
                      transform hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed
                      shadow-lg hover:shadow-cyan-500/40 relative z-10"
          >
            {loading ? "Analyzing..." : "Detect Collision"}
          </button>

          <ResultDisplay
            result={result}
            loading={loading}
            onViewDetails={handleViewDetails}
          />
        </div>
      </div>
    </div>
  );
}

export default App;