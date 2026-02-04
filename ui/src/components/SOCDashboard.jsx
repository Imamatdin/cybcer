import { useState } from 'react';

function SOCDashboard({ events, status, results, onStart, onReset }) {
  const [botsPath, setBotsPath] = useState('cybcer-soc/data/bots');

  const handleStart = (e) => {
    e.preventDefault();
    onStart(botsPath);
  };

  // IDLE STATE - Launch Screen
  if (status === 'idle') {
    return (
      <div className="soc-container">
        <div className="soc-launch">
          <div className="soc-header">
            <h1>🔵 SOC AUTOPILOT</h1>
            <p className="soc-subtitle">Cerebras-Powered Incident Response</p>
          </div>
          
          <div className="soc-stats-preview">
            <div className="stat-box">
              <span className="stat-value">924</span>
              <span className="stat-label">Events/Batch</span>
            </div>
            <div className="stat-box highlight">
              <span className="stat-value">&lt;10s</span>
              <span className="stat-label">Time to Brief</span>
            </div>
            <div className="stat-box">
              <span className="stat-value">443</span>
              <span className="stat-label">Tokens/sec</span>
            </div>
            <div className="stat-box">
              <span className="stat-value">2.1x</span>
              <span className="stat-label">vs Gemini</span>
            </div>
          </div>

          <form onSubmit={handleStart} className="soc-form">
            <div className="input-row">
              <input
                type="text"
                value={botsPath}
                onChange={(e) => setBotsPath(e.target.value)}
                placeholder="cybcer-soc/data/bots"
              />
              <button type="submit" className="start-btn">
                ▶ ANALYZE
              </button>
            </div>
          </form>

          <div className="soc-pipeline">
            <h3>Pipeline</h3>
            <div className="pipeline-steps">
              <div className="pipeline-step">📥 Ingest Events</div>
              <div className="pipeline-arrow">→</div>
              <div className="pipeline-step">🔍 Build Case</div>
              <div className="pipeline-arrow">→</div>
              <div className="pipeline-step">🛡️ CVE Intel</div>
              <div className="pipeline-arrow">→</div>
              <div className="pipeline-step">📋 Patch Plan</div>
              <div className="pipeline-arrow">→</div>
              <div className="pipeline-step">⚡ Cerebras Brief</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // RUNNING STATE - Progress View
  if (status === 'running') {
    const currentStep = events.filter(e => e.type === 'status').pop()?.step || 1;
    const progressData = events.filter(e => e.type === 'progress').reduce((acc, e) => ({ ...acc, ...e }), {});

    return (
      <div className="soc-container">
        <div className="soc-progress">
          <div className="soc-header">
            <h1>🔵 ANALYZING...</h1>
          </div>

          <div className="progress-steps">
            {[
              { id: 1, name: 'Ingest', icon: '📥' },
              { id: 2, name: 'Case', icon: '🔍' },
              { id: 3, name: 'CVEs', icon: '🛡️' },
              { id: 4, name: 'Patch', icon: '📋' },
              { id: 5, name: 'Brief', icon: '⚡' },
            ].map(step => (
              <div key={step.id} className={`progress-step ${step.id < currentStep ? 'done' : ''} ${step.id === currentStep ? 'active' : ''}`}>
                <div className="step-icon">{step.icon}</div>
                <div className="step-name">{step.name}</div>
                {step.id === currentStep && <div className="step-spinner"></div>}
                {step.id < currentStep && <div className="step-check">✓</div>}
              </div>
            ))}
          </div>

          <div className="live-metrics">
            {progressData.events_count && (
              <div className="metric">
                <span className="metric-value">{progressData.events_count}</span>
                <span className="metric-label">Events</span>
              </div>
            )}
            {progressData.hosts && (
              <div className="metric">
                <span className="metric-value">{progressData.hosts}</span>
                <span className="metric-label">Hosts</span>
              </div>
            )}
            {progressData.ips && (
              <div className="metric">
                <span className="metric-value">{progressData.ips}</span>
                <span className="metric-label">IPs</span>
              </div>
            )}
            {progressData.evidence && (
              <div className="metric">
                <span className="metric-value">{progressData.evidence}</span>
                <span className="metric-label">Evidence</span>
              </div>
            )}
          </div>

          <div className="event-log">
            {events.slice(-10).map((e, i) => (
              <div key={i} className={`log-entry ${e.type}`}>
                {e.type === 'status' && `🔄 ${e.message}`}
                {e.type === 'progress' && e.events_count && `📊 Loaded ${e.events_count} events`}
                {e.type === 'progress' && e.hosts && `🖥️ ${e.hosts} hosts, ${e.ips} IPs, ${e.evidence} evidence`}
                {e.type === 'progress' && e.cves && `🛡️ Enriched ${e.cves.length} CVEs`}
                {e.type === 'progress' && e.patch_plan && `📋 Patch plan ready`}
                {e.type === 'error' && `❌ ${e.message}`}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // DONE STATE - Results Dashboard
  if (status === 'done' && results) {
    const { summary, brief, cerebras_time, tokens_per_sec, patch_plan } = results;

    return (
      <div className="soc-container">
        <div className="soc-results">
          {/* Speed Banner */}
          <div className="speed-banner">
            <div className="speed-stat main">
              <span className="speed-value">{cerebras_time || summary?.cerebras_time || '?'}s</span>
              <span className="speed-label">CEREBRAS TIME</span>
            </div>
            <div className="speed-stat">
              <span className="speed-value">{Math.round(tokens_per_sec || summary?.tokens_per_sec || 0)}</span>
              <span className="speed-label">TOKENS/SEC</span>
            </div>
            <div className="speed-stat">
              <span className="speed-value">{summary?.events_count || results?.events_count || '924'}</span>
              <span className="speed-label">EVENTS</span>
            </div>
            <div className="speed-stat">
              <span className="speed-value">{summary?.total_time || '?'}s</span>
              <span className="speed-label">TOTAL</span>
            </div>
          </div>

          <div className="results-grid">
            {/* Incident Summary */}
            <div className="result-card summary-card">
              <h2>📋 Incident Summary</h2>
              <div className="case-id">{brief?.case_id || 'CASE-001'}</div>
              <p className="summary-text">{brief?.summary || 'Analysis complete.'}</p>
              {brief?.confidence && (
                <div className="confidence">
                  <span>Confidence: {Math.round(brief.confidence * 100)}%</span>
                  <div className="confidence-bar">
                    <div className="confidence-fill" style={{ width: `${brief.confidence * 100}%` }}></div>
                  </div>
                </div>
              )}
            </div>

            {/* Key Entities */}
            <div className="result-card entities-card">
              <h2>🎯 Key Entities</h2>
              <div className="entities-grid">
                <div className="entity-col">
                  <h4>Hosts</h4>
                  {(brief?.key_entities?.hosts || []).slice(0, 5).map((h, i) => (
                    <div key={i} className="entity-item">{h}</div>
                  ))}
                </div>
                <div className="entity-col">
                  <h4>IPs</h4>
                  {(brief?.key_entities?.ips || []).slice(0, 5).map((ip, i) => (
                    <div key={i} className="entity-item">{ip}</div>
                  ))}
                </div>
                <div className="entity-col">
                  <h4>Users</h4>
                  {(brief?.key_entities?.users || []).slice(0, 5).map((u, i) => (
                    <div key={i} className="entity-item">{u}</div>
                  ))}
                </div>
              </div>
            </div>

            {/* MITRE ATT&CK */}
            <div className="result-card attack-card">
              <h2>⚔️ MITRE ATT&CK</h2>
              {(brief?.attack_mapping || []).map((atk, i) => (
                <div key={i} className="attack-item">
                  <span className="technique">{atk.technique}</span>
                  <span className="rationale">{atk.rationale}</span>
                </div>
              ))}
            </div>

            {/* Containment */}
            <div className="result-card containment-card">
              <h2>🛑 Containment</h2>
              {(brief?.containment_steps || []).map((step, i) => (
                <div key={i} className="containment-item">
                  <span className="action">{i + 1}. {step.action}</span>
                  <span className="why">{step.why}</span>
                </div>
              ))}
            </div>

            {/* Patch Plan */}
            <div className="result-card patch-card">
              <h2>🔧 Patch Priority</h2>
              <table className="patch-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Service</th>
                    <th>Urgency</th>
                  </tr>
                </thead>
                <tbody>
                  {(patch_plan || results?.patch_plan || []).slice(0, 5).map((p, i) => (
                    <tr key={i}>
                      <td>{p.priority || i + 1}</td>
                      <td>{p.service}</td>
                      <td><span className={`urgency ${p.urgency}`}>{p.urgency}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Timeline */}
            <div className="result-card timeline-card">
              <h2>📅 Timeline</h2>
              <div className="timeline-list">
                {(brief?.timeline || []).slice(0, 6).map((t, i) => (
                  <div key={i} className="timeline-item">
                    <span className="ts">{t.ts?.split('T')[1]?.substring(0, 8) || t.ts}</span>
                    <span className="event">{t.event}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="results-footer">
            <button onClick={onReset} className="reset-btn">🔄 New Analysis</button>
          </div>
        </div>
      </div>
    );
  }

  // ERROR STATE
  return (
    <div className="soc-container">
      <div className="soc-error">
        <h1>❌ Error</h1>
        <p>Something went wrong. Check console for details.</p>
        <button onClick={onReset} className="reset-btn">🔄 Try Again</button>
      </div>
    </div>
  );
}

export default SOCDashboard;