import { useState } from "react";
import ResumeUpload from "./components/ResumeUpload.jsx";
import ProfileSummary from "./components/ProfileSummary.jsx";
import FilterPanel from "./components/FilterPanel.jsx";
import JobList from "./components/JobList.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [sources, setSources] = useState(["remoteok", "weworkremotely", "linkedin", "indeed", "wellfound", "arbeitnow"]);
  const [maxAge, setMaxAge] = useState(24);
  const [minMatchScore, setMinMatchScore] = useState(70);
  const [minExperience, setMinExperience] = useState(2);
  const [maxExperience, setMaxExperience] = useState(6);
  const [requireVerifiedFreshness, setRequireVerifiedFreshness] = useState(true);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [searched, setSearched] = useState(false);
  const [meta, setMeta] = useState(null);

  const runSearch = async () => {
    if (!profile) return;
    setLoading(true);
    setSearched(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile,
          sources,
          max_age_hours: maxAge,
          min_match_score: minMatchScore,
          min_experience_years: minExperience,
          max_experience_years: maxExperience,
          require_verified_freshness: requireVerifiedFreshness,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Job search failed.");
      }
      const data = await res.json();
      setJobs(data.jobs);
      setMeta({ found: data.total_found, filtered: data.total_after_filter });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadExcel = async () => {
    if (jobs.length === 0) return;
    setExporting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobs }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Export failed.");
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : "job-radar-matches.xlsx";

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="brand">
            <span className="brand-mark" />
            Job Radar
          </div>
          <div className="header-sub">Fresh remote roles, matched to your resume, in one scan.</div>
        </div>
      </header>

      <section className="hero">
        <div>
          <h1>Every remote board.<br /><span className="accent">One 24-hour sweep.</span></h1>
          <p>
            Upload your resume once. Job Radar reads your experience with an LLM, then scans
            RemoteOK, WeWorkRemotely, LinkedIn, Indeed, Wellfound, Naukri, and Arbeitnow — plus
            opt-in country-scoped discovery for Germany, Ireland, UK, Poland, Sweden, Denmark,
            Brazil, Chile, the Philippines, Malaysia, Indonesia, Japan, Australia, the UAE
            (Dubai, Abu Dhabi), Qatar, Saudi Arabia, Bahrain, Kuwait, and Oman — for roles
            posted in the last 24 hours, ranked by fit, one click from apply.
          </p>
          <div className="pill-row">
            <span className="pill">groq · llama-3.3-70b</span>
            <span className="pill">langgraph agent</span>
            <span className="pill">7 global sources</span>
            <span className="pill">19 country-scoped</span>
            <span className="pill">&lt; 24h freshness</span>
          </div>
        </div>
        <div className="radar-dial" aria-hidden="true">
          <span className="radar-blip" style={{ top: "30%", left: "60%" }} />
          <span className="radar-blip" style={{ top: "62%", left: "38%" }} />
          <span className="radar-blip" style={{ top: "48%", left: "75%" }} />
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <div className="main-grid">
        <aside>
          <ResumeUpload apiBase={API_BASE} onParsed={setProfile} onError={setError} />
          <ProfileSummary profile={profile} />
          <FilterPanel
            sources={sources}
            setSources={setSources}
            maxAge={maxAge}
            setMaxAge={setMaxAge}
            minMatchScore={minMatchScore}
            setMinMatchScore={setMinMatchScore}
            minExperience={minExperience}
            setMinExperience={setMinExperience}
            maxExperience={maxExperience}
            setMaxExperience={setMaxExperience}
            requireVerifiedFreshness={requireVerifiedFreshness}
            setRequireVerifiedFreshness={setRequireVerifiedFreshness}
            onSearch={runSearch}
            loading={loading}
            disabled={!profile}
          />
        </aside>

        <main>
          <div className="results-header">
            <span className="results-title">Matched jobs</span>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              {meta && (
                <span className="results-count">
                  {meta.filtered} fresh / {meta.found} scanned
                </span>
              )}
              {jobs.length > 0 && (
                <button className="btn btn-ghost" onClick={downloadExcel} disabled={exporting} style={{ padding: "8px 14px", fontSize: 13 }}>
                  {exporting ? "Preparing…" : "⇩ Export to Excel"}
                </button>
              )}
            </div>
          </div>
          <JobList jobs={jobs} loading={loading} searched={searched} />
        </main>
      </div>
    </div>
  );
}
