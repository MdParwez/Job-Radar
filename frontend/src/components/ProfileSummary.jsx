export default function ProfileSummary({ profile }) {
  if (!profile) return null;
  return (
    <div className="panel">
      <h3>{profile.name || "Your profile"}</h3>
      <p className="panel-sub">{profile.summary || "Parsed from your resume."}</p>

      <div className="stat-row">
        <div className="stat">
          <span className="stat-value">{profile.total_experience_years ?? "—"}</span>
          <span className="stat-label">Years exp.</span>
        </div>
        <div className="stat">
          <span className="stat-value">{profile.skills?.length ?? 0}</span>
          <span className="stat-label">Skills found</span>
        </div>
      </div>

      {profile.preferred_roles?.length > 0 && (
        <>
          <div className="panel-sub" style={{ marginBottom: 4 }}>Search roles</div>
          <div className="tag-list">
            {profile.preferred_roles.map((r) => <span className="tag" key={r}>{r}</span>)}
          </div>
        </>
      )}

      {profile.skills?.length > 0 && (
        <>
          <div className="panel-sub" style={{ marginTop: 14, marginBottom: 4 }}>Top skills</div>
          <div className="tag-list">
            {profile.skills.slice(0, 14).map((s) => <span className="tag" key={s}>{s}</span>)}
          </div>
        </>
      )}
    </div>
  );
}
