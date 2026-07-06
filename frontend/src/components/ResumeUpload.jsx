import { useState, useRef } from "react";

export default function ResumeUpload({ onParsed, onError, apiBase }) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  const pickFile = (f) => {
    if (!f) return;
    const ok = /\.(pdf|docx|txt)$/i.test(f.name);
    if (!ok) {
      onError("Please upload a PDF, DOCX, or TXT file.");
      return;
    }
    setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    onError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${apiBase}/api/resume/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to parse resume.");
      }
      const profile = await res.json();
      onParsed(profile);
    } catch (e) {
      onError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h3>Upload resume</h3>
      <p className="panel-sub">We'll pull your skills, experience & titles automatically.</p>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="dropzone-icon">📄</div>
        <div className="dropzone-title">Drop your resume here</div>
        <div className="dropzone-hint">or click to browse — PDF, DOCX, TXT</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
      </div>

      {file && (
        <div className="file-chip">
          <span>{file.name}</span>
          <button onClick={() => setFile(null)}>remove</button>
        </div>
      )}

      <button className="btn btn-primary" onClick={handleSubmit} disabled={!file || loading}>
        {loading ? "Reading resume…" : "Extract profile"}
      </button>
    </div>
  );
}
