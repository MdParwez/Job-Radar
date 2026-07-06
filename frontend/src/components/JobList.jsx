import JobCard from "./JobCard.jsx";

export default function JobList({ jobs, loading, searched }) {
  if (loading) {
    return (
      <div className="loading-state">
        <div>Scanning job boards for fresh postings…</div>
        <div className="loading-scan" />
      </div>
    );
  }

  if (!searched) {
    return (
      <div className="empty-state">
        Upload your resume and hit <strong>Find matching jobs</strong> to start scanning.
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="empty-state">
        No fresh postings matched right now — try widening the max age or adding more sources.
      </div>
    );
  }

  return (
    <div className="job-grid">
      {jobs.map((job) => <JobCard job={job} key={job.id} />)}
    </div>
  );
}
