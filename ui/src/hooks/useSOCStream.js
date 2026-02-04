import { useState, useRef, useEffect } from 'react';

export const useSOCStream = () => {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('idle'); // idle, running, done, error
  const [results, setResults] = useState(null);
  const pollRef = useRef(null);

  const fetchState = async () => {
    try {
      const res = await fetch('/api/state');
      if (!res.ok) throw new Error('Fetch failed');
      const data = await res.json();
      // Update status and results
      const newStatus = data.status || 'idle';
      setStatus(newStatus);
      setResults(prev => ({ ...prev, ...data }));
      // Keep recent events always populated
      if (data.red && Array.isArray(data.red.recent_events)) {
        setEvents(data.red.recent_events);
      }
      // Stop polling when done or error
      if (newStatus === 'done' || newStatus === 'error') {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch (e) {
      console.error('Failed to fetch /api/state', e);
      setStatus('error');
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
  };

  const startSOC = async ({ botsPath = null, scenario = 'success', eventsPath = null } = {}) => {
    // clear previous
    setEvents([]);
    setResults(null);
    setStatus('running');

    try {
      const body = {};
      if (eventsPath) body.events_path = eventsPath;
      else if (botsPath) body.bots_path = botsPath;
      else body.scenario = scenario;

      await fetch('/api/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
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