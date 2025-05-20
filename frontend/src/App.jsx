"use client"
import { useState } from "react"
import "./App.css"
import Header from "./components/Header"
import VideoPreview from "./components/VideoPreview"
import FileUpload from "./components/FileUpload"
import ResultDisplay from "./components/ResultDisplay"
import LoadingOverlay from "./components/LoadingOverlay"
import AccidentDetailsPage from "./pages/AccidentDetailsPage"
import LoadingAnimation from "./components/LoadingAnimation"
import useVideoUpload from "./hooks/useVideoUpload"

function App() {
  const { video, preview, result, loading, videoRef, handleFileChange, handleUpload } = useVideoUpload()
  const [showDetailsPage, setShowDetailsPage] = useState(false)
  const [showAnimation, setShowAnimation] = useState(false)

  const handleViewDetails = () => {
    setShowAnimation(true)

    // After 5 seconds, show the details page
    setTimeout(() => {
      setShowAnimation(false)
      setShowDetailsPage(true)
    }, 4000)
  }

  const handleBackToHome = () => {
    setShowDetailsPage(false)
  }

  // Show loading animation
  if (showAnimation) {
    return <LoadingAnimation />
  }

  // Show accident details page
  if (showDetailsPage) {
    return <AccidentDetailsPage onBack={handleBackToHome} />
  }

  // Show main app
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-cover bg-center overflow-hidden">
      {/* <div className="absolute inset-0 bg-cover bg-center z-0" style={{ backgroundImage: "url('./assets/bg.jpg')" }} /> */}

      <div className="relative z-10 flex flex-col items-center text-center px-4">
        <Header />

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

          <ResultDisplay result={result} loading={loading} onViewDetails={handleViewDetails} />
        </div>
      </div>
    </div>
  )
}

export default App
