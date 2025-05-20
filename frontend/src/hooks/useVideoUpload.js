"use client";

import { useState, useRef } from "react";
import axios from "axios";

function useVideoUpload() {
  const [video, setVideo] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const videoRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setVideo(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleUpload = async () => {
    if (!video) return alert("Please select a video first");

    setLoading(true);
    setResult("");

    const formData = new FormData();
    formData.append("file", video);

    const startTime = performance.now();

    try {
      const response = await axios.post(
        "http://127.0.0.1:5000/predict",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      const endTime = performance.now();
      const timeTaken = (endTime - startTime).toFixed(2);
      console.log(`⏱️ Prediction Time: ${timeTaken} ms`);

      setLoading(false);
      setResult(response.data.result);
    } catch (error) {
      console.error("❌ Error uploading video:", error);
      setLoading(false);
      setResult("Error processing video");
    }
  };

  return {
    video,
    preview,
    result,
    loading,
    videoRef,
    handleFileChange,
    handleUpload,
  };
}

export default useVideoUpload;

// {
//   "result": "Accident Detected",
//   "severity": "High",
//   "entities": [
//     {
//       "type": "car",
//      "license_plate": "undefined",
//     },
//     {
//    "type": "bus",
//      "license_plate": "undefined",
//     },
//     {
//       "type": "pedestrian",
//   ]
// }


// , i am also uploading that file as well, the data that we will expect now 