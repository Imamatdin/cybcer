import { useState, useRef, useEffect } from 'react';

export const useSOCStream = () => {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('idle'); // idle, running, done, error
  const [results, setResults] = useState(null);
  const pollRef = useRef(null);

  const fetchState = async () => {
    try {
      const res = await fetch('http://localhost:5173/api/state');
      if (!res.ok) throw new Error('Fetch failed');
      const data = await res.json();
      // Update status and results
      setStatus(data.status || 'idle');
      setResults(prev => ({ ...prev, ...data }));
      // Keep recent events always populated
      if (data.red && Array.isArray(data.red.recent_events)) {
        setEvents(data.red.recent_events);
      }
    } catch (e) {
      console.error('Failed to fetch /api/state', e);
      setStatus('error');
    }
  };

  const startSOC = async (botsPath = 'cybcer-soc/data/bots') => {
    // clear previous
    setEvents([]);
    setResults(null);
    setStatus('running');

    try {
      await fetch('http://localhost:5173/api/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bots_path: botsPath }) });
    } catch (e) {
      console.error('Failed to POST /api/start', e);
    }

    // start polling
    if (pollRef.current) clearInterval(pollRef.current);
    await fetchState();
    pollRef.current = setInterval(fetchState, 750);
  };

  const resetSOC = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setEvents([]);
    setStatus('idle');
    setResults(null);
  };

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return {
    events,
    status,
    results,
    startSOC,
    resetSOC
  };
};