const GLOBAL_SOURCES = [
  { key: "remoteok", label: "RemoteOK" },
  { key: "weworkremotely", label: "WeWorkRemotely" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "indeed", label: "Indeed" },
  { key: "wellfound", label: "Wellfound" },
  { key: "naukri", label: "Naukri (India)" },
  { key: "arbeitnow", label: "Arbeitnow (Germany/EU)" },
];

// Country-scoped discovery. Some are backed by the official Adzuna API
// (marked below), the rest by broader search-based discovery.
const REGIONAL_SOURCES = [
  { key: "germany", label: "Germany", adzuna: true },
  { key: "uk", label: "United Kingdom", adzuna: true },
  { key: "poland", label: "Poland", adzuna: true },
  { key: "australia", label: "Australia", adzuna: true },
  { key: "brazil", label: "Brazil", adzuna: true },
  { key: "ireland", label: "Ireland" },
  { key: "sweden", label: "Sweden" },
  { key: "denmark", label: "Denmark" },
  { key: "chile", label: "Chile" },
  { key: "philippines", label: "Philippines" },
  { key: "malaysia", label: "Malaysia" },
  { key: "indonesia", label: "Indonesia" },
  { key: "japan", label: "Japan" },
  { key: "uae", label: "UAE (Dubai, Abu Dhabi)" },
  { key: "qatar", label: "Qatar" },
  { key: "saudi_arabia", label: "Saudi Arabia" },
  { key: "bahrain", label: "Bahrain" },
  { key: "kuwait", label: "Kuwait" },
  { key: "oman", label: "Oman" },
];

const ALL_GLOBAL_KEYS = GLOBAL_SOURCES.map((s) => s.key);
const ALL_REGIONAL_KEYS = REGIONAL_SOURCES.map((s) => s.key);

export default function FilterPanel({
  sources, setSources,
  maxAge, setMaxAge,
  minMatchScore, setMinMatchScore,
  minExperience, setMinExperience,
  maxExperience, setMaxExperience,
  requireVerifiedFreshness, setRequireVerifiedFreshness,
  onSearch, loading, disabled,
}) {
  const toggle = (key) => {
    setSources((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    );
  };

  const allGlobalSelected = ALL_GLOBAL_KEYS.every((k) => sources.includes(k));
  const allRegionalSelected = ALL_REGIONAL_KEYS.every((k) => sources.includes(k));

  const toggleAll = (allKeys, allSelected) => {
    setSources((prev) => {
      if (allSelected) {
        // deselect just this group's keys, keep everything else untouched
        return prev.filter((s) => !allKeys.includes(s));
      }
      const withoutGroup = prev.filter((s) => !allKeys.includes(s));
      return [...withoutGroup, ...allKeys];
    });
  };

  return (
    <div className="panel">
      <h3>Sources</h3>
      <p className="panel-sub">Pick which boards to scan.</p>

      <label className="checkbox-row" style={{ fontWeight: 600 }}>
        <input
          type="checkbox"
          checked={allGlobalSelected}
          onChange={() => toggleAll(ALL_GLOBAL_KEYS, allGlobalSelected)}
        />
        Select all
      </label>
      {GLOBAL_SOURCES.map((s) => (
        <label className="checkbox-row" key={s.key}>
          <input
            type="checkbox"
            checked={sources.includes(s.key)}
            onChange={() => toggle(s.key)}
          />
          {s.label}
        </label>
      ))}

      <div className="panel-sub" style={{ marginTop: 14, marginBottom: 2 }}>
        Regional (country-scoped discovery)
      </div>
      <label className="checkbox-row" style={{ fontWeight: 600 }}>
        <input
          type="checkbox"
          checked={allRegionalSelected}
          onChange={() => toggleAll(ALL_REGIONAL_KEYS, allRegionalSelected)}
        />
        Select all
      </label>
      {REGIONAL_SOURCES.map((s) => (
        <label className="checkbox-row" key={s.key}>
          <input
            type="checkbox"
            checked={sources.includes(s.key)}
            onChange={() => toggle(s.key)}
          />
          {s.label}
          {s.adzuna && <span className="tag" style={{ marginLeft: 6 }}>Adzuna</span>}
        </label>
      ))}

      <div style={{ marginTop: 16 }}>
        <div className="slider-label">
          <span>Max age</span>
          <span>{maxAge}h</span>
        </div>
        <input
          type="range"
          min="1"
          max="72"
          value={maxAge}
          onChange={(e) => setMaxAge(Number(e.target.value))}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <div className="slider-label">
          <span>Minimum match</span>
          <span>{minMatchScore}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={minMatchScore}
          onChange={(e) => setMinMatchScore(Number(e.target.value))}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <div className="slider-label">
          <span>Experience range</span>
          <span>{minExperience}–{maxExperience} yrs</span>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            type="number"
            min="0"
            max="40"
            value={minExperience}
            onChange={(e) => setMinExperience(Number(e.target.value))}
            style={{
              width: "100%", background: "var(--bg-panel-raised)", border: "1px solid var(--border)",
              borderRadius: 8, color: "var(--text)", padding: "8px 10px", fontFamily: "var(--font-mono)", fontSize: 13,
            }}
          />
          <input
            type="number"
            min="0"
            max="40"
            value={maxExperience}
            onChange={(e) => setMaxExperience(Number(e.target.value))}
            style={{
              width: "100%", background: "var(--bg-panel-raised)", border: "1px solid var(--border)",
              borderRadius: 8, color: "var(--text)", padding: "8px 10px", fontFamily: "var(--font-mono)", fontSize: 13,
            }}
          />
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={requireVerifiedFreshness}
            onChange={(e) => setRequireVerifiedFreshness(e.target.checked)}
          />
          Only show verified-fresh dates
        </label>
        <div className="panel-sub" style={{ marginTop: 2 }}>
          Search-discovered sources (LinkedIn, Indeed, Naukri, Wellfound,
          country boards) don't always expose a real post date. On by default
          so "last 24h" actually means last 24h — turn off to see more
          results with unconfirmed timing.
        </div>
      </div>

      <button className="btn btn-primary" onClick={onSearch} disabled={disabled || loading}>
        {loading ? "Scanning boards…" : "Find matching jobs"}
      </button>
    </div>
  );
}
