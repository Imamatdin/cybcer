import { useState } from 'react';
import AttackLaunch from './components/AttackLaunch';
import AttackProgress from './components/AttackProgress';
import ResultsDashboard from './components/ResultsDashboard';
import { useAttackStream } from './hooks/useAttackStream';
import './App.css';

function App() {
  const [targetUrl, setTargetUrl] = useState('');
  // Use custom hook
  const { events, status, results, startAttack, stopAttack } = useAttackStream(targetUrl);

  const handleStart = (url) => {
    setTargetUrl(url);
    startAttack(url);
  };

  const handleReset = () => {
    setTargetUrl('');
    // Can just reload or reset state. For simplicity, reload to clear hook state fully if needed,
    // but better to just reset url.
    window.location.reload();
  };

  return (
    <div className="app-container">
      <div className="scan-line"></div>

      {status === 'idle' && (
        <AttackLaunch onStart={handleStart} />
      )}

      {(status === 'attacking' || status === 'error' || (status === 'done' && !results)) && (
        <AttackProgress events={events} onStop={stopAttack} />
      )}

      {status === 'done' && results && (
        <ResultsDashboard data={results} onReset={handleReset} />
      )}
    </div>
  );
}

export default App;
