function freshnessClass(hoursAgo, dateVerified) {
  if (hoursAgo == null || dateVerified === false) return "unverified";
  if (hoursAgo <= 6) return "fresh";
  if (hoursAgo <= 24) return "recent";
  return "older";
}

function freshnessLabel(hoursAgo, dateVerified) {
  if (hoursAgo == null || dateVerified === false) return "date unverified";
  if (hoursAgo < 1) return "< 1h ago";
  return `${Math.round(hoursAgo)}h ago`;
}

export default function JobCard({ job }) {
  const unverified = job.hours_ago == null || job.date_verified === false;

  return (
    <div className="job-card">
      <div>
        <h4 className="job-card-title">{job.title}</h4>
        <p className="job-card-company">{job.company} · {job.location}</p>

        <div className="job-meta">
          <span className="freshness" title={unverified ? "This source doesn't expose a reliable post date — treat the timing as approximate." : ""}>
            <span className={`freshness-dot ${freshnessClass(job.hours_ago, job.date_verified)}`} />
            {freshnessLabel(job.hours_ago, job.date_verified)}
          </span>
          <span className="source-badge">{job.source}</span>
          {job.salary && <span className="source-badge">{job.salary}</span>}
          {(job.required_experience_min != null || job.required_experience_max != null) && (
            <span className="source-badge">
              {job.required_experience_min ?? "0"}–{job.required_experience_max ?? "?"} yrs
            </span>
          )}
        </div>

        <p className="job-desc">{job.description}</p>
      </div>

      <div className="job-actions">
        {job.match_score != null && (
          <div className="match-score" title={job.match_reason || ""}>
            <span className="num">{Math.round(job.match_score)}</span>% match
          </div>
        )}
        <a className="btn btn-apply" href={job.url} target="_blank" rel="noopener noreferrer">
          Apply →
        </a>
      </div>
    </div>
  );
}
