import bgimage from "../assets/bg2.jpg";
import { useState } from "react";
import jsPDF from "jspdf";
import accidentImage from "../assets/dummy.png"; // Changed this to match your import in AccidentDetailsPage

function AccidentDetailsPage({ onBack, accidentData }) {
  // If no accidentData is provided, use default dummy data
  const [accidentDetails, setAccidentDetails] = useState(
    accidentData || {
      severity: "moderate",
      vehicles: {
        count: 2,
        types: ["Sedan", "SUV"],
      },
      pedestrians: 1,
      licensePlate: "ABC-1234",
      visibleLicensePlates: ["ABC-1234"],
      timestamp: new Date().toLocaleString(),
      accidentType: "Vehicle collision",
      classification: "Accident",
    }
  );

  // PDF generation state
  const [isGenerating, setIsGenerating] = useState(false);

  // Get severity color based on accident severity
  const getSeverityColor = (severity) => {
    switch(severity.toLowerCase()) {
      case "minor":
        return "green";
      case "moderate":
        return "yellow";
      case "severe":
        return "red";
      default:
        return "yellow"; // Default to moderate/yellow
    }
  };

  // Generate PDF functionality from Report.jsx
  const generatePDF = () => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 20;
    let y = 15;

    // ===== HEADER =====
    doc.setTextColor(0, 51, 102); // Darker blue for better contrast
    doc.setFontSize(20);
    doc.setFont("helvetica", "bold");
    doc.text("CrashAnalytix Accident Report", pageWidth / 2, y, {
      align: "center",
    });
    y += 12;

    doc.setDrawColor(180, 180, 180); // Slightly darker divider
    doc.line(margin, y, pageWidth - margin, y);
    y += 8;

    // ===== REPORT SUMMARY =====
    const summaryBoxHeight = 22;
    doc.setDrawColor(210); // Slightly darker border
    doc.setFillColor(245, 245, 245); // Slightly darker background
    doc.roundedRect(
      margin,
      y,
      pageWidth - 2 * margin,
      summaryBoxHeight,
      4,
      4,
      "FD"
    );

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 51, 102); // Matching header color
    doc.text("REPORT SUMMARY", margin + 5, y + 7);

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(70, 70, 70); // Darker gray for better readability
    doc.text("Timestamp: " + accidentDetails.timestamp, margin + 5, y + 13);

    y += summaryBoxHeight + 8;

    // ===== SEVERITY ASSESSMENT =====
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 51, 102); // Matching header color
    doc.text("SEVERITY ASSESSMENT", margin, y);
    y += 8;

    // Set color based on severity
    const severityColors = {
      minor: [0, 153, 51], // Green
      moderate: [255, 153, 0], // Orange
      severe: [204, 0, 0], // Red
    };

    // Get color based on severity (default to moderate if not found)
    const textColor =
      severityColors[accidentDetails.severity.toLowerCase()] || severityColors.moderate;

    // Display severity text instead of number
    doc.setFontSize(28);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(...textColor);

    // Capitalize first letter of severity
    const displaySeverity =
      accidentDetails.severity.charAt(0).toUpperCase() +
      accidentDetails.severity.slice(1);

    doc.text(displaySeverity, pageWidth / 2, y, { align: "center" });
    y += 12;

    const riskBarWidth = pageWidth - 2 * margin;
    const riskBarHeight = 8;

    // Enhanced gradient colors
    doc.setFillColor(0, 153, 51); // Darker green (minor)
    doc.rect(margin, y, riskBarWidth * 0.3, riskBarHeight, "F");
    doc.setFillColor(255, 204, 0); // Brighter yellow (moderate)
    doc.rect(
      margin + riskBarWidth * 0.3,
      y,
      riskBarWidth * 0.3,
      riskBarHeight,
      "F"
    );
    doc.setFillColor(204, 0, 0); // Darker red (severe)
    doc.rect(
      margin + riskBarWidth * 0.6,
      y,
      riskBarWidth * 0.4,
      riskBarHeight,
      "F"
    );

    // Position marker based on severity - FIXED POSITIONING
    let markerPosition;
    switch (accidentDetails.severity.toLowerCase()) {
      case "minor":
        markerPosition = 0.15; // Left position (green zone)
        break;
      case "moderate":
        markerPosition = 0.45; // Middle position (yellow zone)
        break;
      case "severe":
        markerPosition = 0.8; // Right position (red zone)
        break;
      default:
        markerPosition = 0.45; // Default to middle if unknown
    }

    doc.setFillColor(51, 51, 51); // Darker marker
    doc.rect(
      margin + riskBarWidth * markerPosition - 1,
      y - 2,
      2,
      riskBarHeight + 4,
      "F"
    );

    y += riskBarHeight + 5;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(70, 70, 70);
    doc.text("Low Risk", margin, y);
    doc.text("High Risk", pageWidth - margin - 25, y, { align: "right" });
    y += 10;

    doc.setDrawColor(180, 180, 180);
    doc.line(margin, y, pageWidth - margin, y);
    y += 8;

    // ===== INCIDENT DETAILS BOX =====
    const tableBoxHeight = 45;
    doc.setDrawColor(210);
    doc.setFillColor(245, 245, 245);
    doc.roundedRect(
      margin,
      y,
      pageWidth - 2 * margin,
      tableBoxHeight,
      4,
      4,
      "FD"
    );

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 51, 102);
    doc.text("INCIDENT DETAILS", margin + 5, y + 7);

    y += 10;

    // Table header with subtle background
    doc.setFillColor(235, 235, 235);
    doc.rect(margin, y, pageWidth - 2 * margin, 10, "F");
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 51, 102);
    doc.text("Category", margin + 5, y + 7);
    doc.text("Details", margin + 70, y + 7);
    y += 8;

    // Table rows with alternating subtle shading
    const licensePlates =
      accidentDetails.visibleLicensePlates &&
      accidentDetails.visibleLicensePlates.length > 0
        ? accidentDetails.visibleLicensePlates.join(", ")
        : accidentDetails.licensePlate;

    const incidentDetails = [
      {
        label: "Entities Involved",
        value: `${accidentDetails.vehicles.count} Vehicles, ${accidentDetails.pedestrians} Pedestrian`,
      },
      { label: "Accident Type", value: accidentDetails.accidentType },
      { label: "License Plates", value: licensePlates },
    ];

    incidentDetails.forEach((item, index) => {
      if (index % 2 === 0) {
        doc.setFillColor(250, 250, 250);
        doc.rect(margin, y, pageWidth - 2 * margin, 10, "F");
      }

      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      doc.setTextColor(...(index === 2 ? [204, 0, 0] : [70, 70, 70])); // Corrected
      doc.text(item.label, margin + 5, y + 7);
      doc.setTextColor(...(index === 2 ? [204, 0, 0] : [40, 40, 40])); // Corrected
      doc.text(item.value, margin + 70, y + 7);
      y += 8;
    });

    y += 10;

    // ===== ACCIDENT IMAGE =====
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 51, 102);
    doc.text("ACCIDENT SNAPSHOT", margin, y);
    y += 15;

    const imgWidth = (pageWidth - 2 * margin) * 0.8;
    const imgHeight = (imgWidth * 9) / 16;
    const imgX = (pageWidth - imgWidth) / 2;

    // Enhanced image border
    const boxPadding = 4;
    doc.setDrawColor(180, 180, 180);
    doc.setLineWidth(0.8); // Slightly thicker border
    doc.rect(
      imgX - boxPadding,
      y - boxPadding,
      imgWidth + 2 * boxPadding,
      imgHeight + 2 * boxPadding
    );

    doc.addImage(accidentImage, "JPG", imgX, y, imgWidth, imgHeight);
    y += imgHeight + boxPadding * 2 + 5;

    // ===== FOOTER =====
    doc.setDrawColor(180, 180, 180);
    doc.setLineWidth(0.5);
    doc.line(20, y, 190, y);

    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text("Generated by | CrashAnalytiX", 105, y + 10, {
      align: "center",
    });

    return doc;
  };

  const handleDownload = () => {
    setIsGenerating(true);
    setTimeout(() => {
      try {
        const doc = generatePDF();
        doc.save(`crashanalytix_report_${new Date().getTime()}.pdf`);
      } catch (error) {
        console.error("PDF generation error:", error);
      } finally {
        setIsGenerating(false);
      }
    }, 300);
  };

  // Determine if there are multiple license plates to display
  const renderLicensePlates = () => {
    if (
      accidentDetails.visibleLicensePlates &&
      accidentDetails.visibleLicensePlates.length > 0
    ) {
      return accidentDetails.visibleLicensePlates.map((plate, index) => (
        <div
          key={index}
          className="border-4 border-blue-800 bg-white px-6 py-3 rounded"
        >
          <span className="text-2xl font-bold tracking-wider text-blue-900">
            {plate}
          </span>
        </div>
      ));
    } else {
      return (
        <div className="border-4 border-blue-800 bg-white px-6 py-3 rounded">
          <span className="text-2xl font-bold tracking-wider text-blue-900">
            License number not visible
          </span>
        </div>
      );
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col bg-cover bg-center"
      style={{ backgroundImage: "url('./assets/bg4.jpg')" }}
    >
      {/* Header */}
      <header className="bg-gradient-to-r from-red-900/80 to-red-700/80 p-4 shadow-lg">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-3xl font-bold text-white">
            Post Analysis Details
          </h1>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-all"
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto p-6 flex-grow">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left column */}
          <div className="space-y-6">
            <div className="bg-white/90 rounded-xl shadow-lg p-6">
              {/* Classification Output */}
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Classification Output
              </h2>
              <div className="flex justify-center">
                <div className="bg-red-50 p-4 rounded-lg text-center w-60">
                  <h3 className="font-bold text-red-800 mb-2">Result</h3>
                  <div className="text-xl font-bold text-red-600">
                    {accidentDetails.classification}
                  </div>
                </div>
              </div>
            </div>

            {/* Involved Entities */}
            <div className="bg-white/90 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Involved Entities
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-bold text-blue-800 mb-2">Vehicles</h3>
                  <p className="text-gray-700">
                    Count: {accidentDetails.vehicles.count}
                  </p>
                  <p className="text-gray-700">
                    Types: {accidentDetails.vehicles.types.join(", ")}
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h3 className="font-bold text-purple-800 mb-2">
                    Pedestrians
                  </h3>
                  <p className="text-gray-700">
                    Count: {accidentDetails.pedestrians}
                  </p>
                  <p className="text-gray-700">
                    Status:{" "}
                    {accidentDetails.pedestrians > 0
                      ? "Minor injuries"
                      : "None involved"}
                  </p>
                </div>
              </div>
            </div>

            {/* License Plate */}
            <div className="bg-white/90 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                License Plate Recognition
              </h2>
              <div className="flex items-center justify-center bg-gray-100 p-4 rounded-lg">
                <div className="flex justify-evenly w-full max-w-4xl">
                  {renderLicensePlates()}
                </div>
              </div>
              <p className="mt-4 text-gray-600 text-center">
                License plate extracted using OCR technology from the accident
                footage.
              </p>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Severity Score - IMPROVED VERSION */}
            <div className="bg-white/90 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Severity Score
              </h2>

              {/* Labels above scale */}
              <div className="flex justify-between text-sm font-semibold mb-1 px-1">
                <span className="text-green-600">Minor</span>
                <span className="text-yellow-600">Moderate</span>
                <span className="text-red-600">Severe</span>
              </div>

              {/* Severity Bar - with gradient background */}
              <div className="h-3 rounded-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 relative">
                {/* Severity marker (circle indicator) - positioned based on severity */}
                <div 
                  className={`absolute top-1/2 transform -translate-y-1/2 h-5 w-5 rounded-full border-2 border-white shadow-md ${
                    accidentDetails.severity.toLowerCase() === "minor"
                      ? "bg-green-600 left-[16%]"
                      : accidentDetails.severity.toLowerCase() === "moderate"
                      ? "bg-yellow-600 left-[50%]"
                      : "bg-red-600 left-[84%]"
                  }`}
                ></div>
              </div>

              <p className="text-gray-600 mt-3">
                This accident has been classified as{" "}
                <span
                  className={`font-bold ${
                    accidentDetails.severity.toLowerCase() === "minor"
                      ? "text-green-600"
                      : accidentDetails.severity.toLowerCase() === "moderate"
                      ? "text-yellow-600"
                      : "text-red-600"
                  }`}
                >
                  {accidentDetails.severity}
                </span>{" "}
                based on impact analysis.
              </p>
            </div>

            {/* Accident Snapshot */}
            <div className="bg-white/90 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Accident Snapshot
              </h2>
              <div className="bg-gray-200 rounded-lg overflow-hidden">
                <div className="relative">
                  <img
                    src={bgimage}
                    alt="Accident Snapshot"
                    className="w-full h-64 object-cover"
                  />
                  {/* Bounding boxes */}
                </div>
                <p className="p-3 text-sm text-gray-600">
                  Frame captured at the moment of impact with object detection
                  highlighting.
                </p>
              </div>
            </div>
            {/* Download Report Button */}

            <div className="bg-white/90 rounded-xl shadow-lg p-6 flex flex-col items-center justify-center">
              <button
                onClick={handleDownload}
                disabled={isGenerating}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-800 text-white font-bold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 flex items-center gap-2"
              >
                {isGenerating ? (
                  <span className="flex items-center gap-2">
                    <svg
                      className="animate-spin h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    GENERATING REPORT
                  </span>
                ) : (
                  <>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    DOWNLOAD CONCISE REPORT
                  </>
                )}
              </button>
              <p className="mt-3 text-gray-600 text-sm text-center">
                Generate a professional PDF report with all incident details
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800/80 text-white p-4 text-center">
        <p>© 2025 Accident Detection System | All Rights Reserved</p>
      </footer>
    </div>
  );
}

export default AccidentDetailsPage;