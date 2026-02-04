import { useState } from 'react';
import AttackLaunch from './components/AttackLaunch';
import AttackProgress from './components/AttackProgress';
import ResultsDashboard from './components/ResultsDashboard';
import SOCDashboard from './components/SOCDashboard';
import { useAttackStream } from './hooks/useAttackStream';
import { useSOCStream } from './hooks/useSOCStream';
import './App.css';
import './soc-styles.css';

function App() {
  const [mode, setMode] = useState('red');
  const [targetUrl, setTargetUrl] = useState('');
  // SOC hook
  const { events: socEvents, status: socStatus, results: socResults, startSOC, resetSOC } = useSOCStream();

  // Callback when red team fails/aborts - switch to SOC
  const handleFallbackToSOC = () => {
    console.log('Red team failed/aborted, switching to SOC mode...');
    setMode('soc');
    // Auto-start SOC analysis
    startSOC({ scenario: 'success' });
  };

  // Red team hook with fallback
  const { 
    events: redEvents, 
    status: redStatus, 
    results: redResults, 
    startAttack, 
    stopAttack 
  } = useAttackStream(targetUrl, handleFallbackToSOC);

  const handleStartRed = (url) => {
    setTargetUrl(url);
    startAttack(url);
    // SOC starts immediately — steps 1-4 are local, step 5 (LLM) will back off
    // and retry if rate-limited by the concurrent attack.
    startSOC({ scenario: 'success' });
  };

  const handleReset = () => {
    window.location.reload();
  };

  return (
    <div className="app-container">
      <div className="scan-line"></div>
      
      {/* Mode Toggle */}
      <div className="mode-toggle">
        <button 
          className={`mode-btn ${mode === 'red' ? 'active' : ''}`}
          onClick={() => setMode('red')}
        >
          🔴 Red Team
        </button>
        <button 
          className={`mode-btn ${mode === 'soc' ? 'active' : ''}`}
          onClick={() => setMode('soc')}
        >
          🔵 SOC Autopilot
        </button>
      </div>

      {/* Red Team Mode */}
      {mode === 'red' && (
        <>
          {redStatus === 'idle' && (
            <AttackLaunch onStart={handleStartRed} />
          )}
          {(redStatus === 'attacking' || redStatus === 'error') && (
            <AttackProgress events={redEvents} onStop={stopAttack} />
          )}
          {redStatus === 'done' && redResults && (
            <ResultsDashboard data={redResults} events={redEvents} onReset={handleReset} />
          )}
        </>
      )}

      {/* SOC Autopilot Mode */}
      {mode === 'soc' && (
        <SOCDashboard 
          events={socEvents}
          status={socStatus}
          results={socResults}
          onStart={startSOC}
          onReset={resetSOC}
        />
      )}
    </div>
  );
}

export default App;