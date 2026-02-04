import { useState } from 'react';
import AttackLaunch from './components/AttackLaunch';
import AttackProgress from './components/AttackProgress';
import ResultsDashboard from './components/ResultsDashboard';
import SOCDashboard from './components/SOCDashboard';
import { useAttackStream } from './hooks/useAttackStream';
import { useSOCStream } from './hooks/useSOCStream';
import './App.css';
import './soc-styles.css';  // Add after App.css import

function App() {
  const [mode, setMode] = useState('soc'); // 'red' or 'soc'
  const [targetUrl, setTargetUrl] = useState('');
  
  // Red team hook
  const { events: redEvents, status: redStatus, results: redResults, startAttack, stopAttack } = useAttackStream(targetUrl);
  
  // SOC hook
  const { events: socEvents, status: socStatus, results: socResults, startSOC, resetSOC } = useSOCStream();

  const handleStartRed = (url) => {
    setTargetUrl(url);
    startAttack(url);
  };

  const handleReset = () => {
    setTargetUrl('');
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
          {(redStatus === 'attacking' || redStatus === 'error' || (redStatus === 'done' && !redResults)) && (
            <AttackProgress events={redEvents} onStop={stopAttack} />
          )}
          {redStatus === 'done' && redResults && (
            <ResultsDashboard data={redResults} onReset={handleReset} />
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