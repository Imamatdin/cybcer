import ReactMarkdown from 'react-markdown';

const ResultsDashboard = ({ data, onReset }) => {
    const { summary, genome } = data;

    // Calculate Gemini estimate (3s per step is conservative for GPT-4/Gemini visual comparison)
    const stepCount = summary?.steps || 0;
    const metrics = summary || { total_time: 0, steps: 0, speedup: 0 };
    const geminiTime = stepCount * 3.0; // Estimate
    const cerebrasTime = metrics.total_time;

    // Bar widths (normalize to 100%)
    const maxTime = Math.max(geminiTime, cerebrasTime) * 1.1; // 10% buffer
    const cerebrasWidth = Math.max((cerebrasTime / maxTime) * 100, 1);
    const geminiWidth = Math.max((geminiTime / maxTime) * 100, 1);

    return (
        <div className="results-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 style={{ color: 'var(--color-success)' }}>MISSION ACCOMPLISHED</h1>
                <button onClick={onReset}>NEW SIMULATION</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                <div className="panel" style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>TOTAL DURATION</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>{metrics.total_time?.toFixed(2)}s</div>
                </div>
                <div className="panel" style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>ATTACK STEPS</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>{metrics.steps}</div>
                </div>
                <div className="panel" style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>SPEEDUP FACTOR</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--color-info)' }}>{metrics.speedup?.toFixed(1)}x</div>
                </div>
            </div>

            <div className="panel" style={{ marginBottom: '2rem' }}>
                <h3>INFERENCE SPEED COMPARISON</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr 80px', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ fontWeight: 'bold' }}>CEREBRAS</div>
                    <div style={{ background: '#222', height: '24px', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                            width: `${cerebrasWidth}%`,
                            height: '100%',
                            background: 'linear-gradient(90deg, #33ff33, #33ccff)',
                            transition: 'width 1s ease-out'
                        }} />
                    </div>
                    <div style={{ textAlign: 'right' }}>{cerebrasTime?.toFixed(1)}s</div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr 80px', gap: '1rem', alignItems: 'center' }}>
                    <div style={{ fontWeight: 'bold', color: '#888' }}>GEMINI</div>
                    <div style={{ background: '#222', height: '24px', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                            width: `${geminiWidth}%`,
                            height: '100%',
                            background: '#555',
                            transition: 'width 1s ease-out'
                        }} />
                    </div>
                    <div style={{ textAlign: 'right', color: '#888' }}>~{geminiTime?.toFixed(1)}s</div>
                </div>
            </div>

            {genome && (
                <div className="panel genome-panel">
                    <h2 style={{ color: 'var(--color-info)', borderBottom: '1px solid #333', paddingBottom: '0.5rem' }}>
                        SECURITY GENOME ANALYSIS
                    </h2>
                    <div style={{ lineHeight: '1.6', padding: '1rem' }}>
                        <ReactMarkdown>{genome}</ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ResultsDashboard;
