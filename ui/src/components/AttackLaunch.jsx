import { useState } from 'react';

const AttackLaunch = ({ onStart }) => {
    const [url, setUrl] = useState('http://localhost:5000');
    const [loading, setLoading] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (url) {
            setLoading(true);
            onStart(url);
        }
    };

    return (
        <div className="launch-container" style={{ textAlign: 'center', marginTop: '10vh' }}>
            <h1>Cerebras Red Team Simulator</h1>
            <p style={{ color: 'var(--text-dim)', marginBottom: '3rem' }}>
                Autonomous Penetration Testing Agent
            </p>

            <div className="panel" style={{ maxWidth: '600px', margin: '0 auto' }}>
                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-dim)' }}>
                            TARGET URL
                        </label>
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="http://target.com"
                        />
                    </div>

                    <button type="submit" disabled={loading} style={{ width: '100%', fontSize: '1.2rem' }}>
                        {loading ? 'Initializing...' : 'INITIALIZE ATTACK SEQUENCE'}
                    </button>
                </form>
            </div>

            <div style={{ marginTop: '2rem', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                POWERED BY CEREBRAS INFERENCE
            </div>
        </div>
    );
};

export default AttackLaunch;
