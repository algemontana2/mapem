// frontend/src/features/upload/pages/UploadPage.jsx
import React, { useState, useContext, useRef } from "react";
import { UploadStatusContext } from "@shared/context/UploadStatusContext";
import { uploadTree } from "@lib/api/api";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [response, setResponse] = useState(null);
  const fileInputRef = useRef(null);

  const { setStatus, setVisible } = useContext(UploadStatusContext);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.name.endsWith(".ged")) {
      setFile(selectedFile);
      setUploadStatus("");
    } else {
      setFile(null);
      setUploadStatus("❌ Please select a `.ged` file.");
    }
  };

  const handleUpload = async () => {
    if (!file || !file.name.endsWith(".ged")) {
      setUploadStatus("❌ Please select a `.ged` file first.");
      return;
    }

    setUploadStatus("⏳ Uploading...");
    setVisible(true);
    setStatus("📤 Uploading GEDCOM file...");

    try {
      const data = await uploadTree(file);

      setStatus("🧬 Parsing & saving tree...");
      await new Promise((r) => setTimeout(r, 1000));

      setStatus("🌍 Geocoding locations...");
      await new Promise((r) => setTimeout(r, 1000));

      setStatus("✅ Upload complete!");
      setTimeout(() => setVisible(false), 1500);

      setResponse(data);
      setUploadStatus("✅ Upload successful!");
    } catch (err) {
      setStatus("❌ Upload failed.");
      setTimeout(() => setVisible(false), 1500);

      let trace = "";
      try {
        const parsed = JSON.parse(err.request?.responseText);
        trace = parsed?.trace || "";
        if (import.meta.env.DEV) console.log("🧠 Backend Trace:\n", trace);
      } catch (parseErr) {
        console.warn("⚠️ Could not parse backend trace:", parseErr);
      }

      setUploadStatus(`❌ Upload failed: ${err.message}`);
      console.error("❌ Upload error:", err);
    }
  };

  return (
    <main className="flex flex-col items-center justify-start px-6 pt-16 pb-24 text-text max-w-3xl mx-auto">
      <h2 className="text-3xl md:text-4xl font-display font-semibold text-text mb-4 text-center">
        Upload GEDCOM File
      </h2>

      <p className="text-dim text-sm mb-8 text-center">
        Select a `.ged` file to start mapping your family’s journey.
      </p>

      <div className="w-full bg-surface rounded-xl border border-border p-6 shadow-md">
        <div className="flex flex-col items-center gap-4 w-full">
          <button
            onClick={() => fileInputRef.current.click()}
            className="w-full max-w-xs px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-semibold tracking-wide transition-all backdrop-blur border border-white/20 shadow-md"
          >
            {file ? `📄 ${file.name}` : "📂 Choose .ged File"}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".ged"
            onChange={handleFileChange}
            className="hidden"
          />

          <button
            onClick={handleUpload}
            className="w-full max-w-xs px-4 py-2 rounded-lg bg-yellow-400 hover:bg-yellow-300 text-black text-sm font-bold tracking-wide transition-all shadow-md"
          >
            Upload
          </button>
        </div>

        {uploadStatus && (
          <div
            className={`mt-6 text-sm px-4 py-3 rounded-md flex items-center gap-2
              ${
                uploadStatus.startsWith("✅")
                  ? "bg-green-800 text-green-200"
                  : uploadStatus.startsWith("❌")
                  ? "bg-red-800 text-red-300"
                  : "bg-zinc-800 text-white"
              }`}
          >
            {uploadStatus}
          </div>
        )}

        {response && (
          <div className="mt-6 text-sm bg-zinc-900 rounded-lg p-4 border border-zinc-700 overflow-x-auto">
            <h3 className="font-bold mb-2 text-accent">Response:</h3>
            <pre className="text-xs text-green-400">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </main>
  );
}
