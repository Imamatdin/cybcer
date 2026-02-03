import { useState, useEffect, useRef } from 'react';

export const useAttackStream = (targetUrl) => {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('idle'); // idle, attacking, done, error
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const eventSourceRef = useRef(null);

  const startAttack = (urlOverride) => {
    const activeUrl = urlOverride || targetUrl;
    if (!activeUrl) return;

    // Reset state
    setEvents([]);
    setStatus('attacking');
    setError(null);
    setResults(null);

    try {
      // Connect to SSE endpoint
      const url = `http://localhost:8000/attack?target=${encodeURIComponent(activeUrl)}`;
      const evtSource = new EventSource(url);
      eventSourceRef.current = evtSource;

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'done') {
            setStatus('done');
            evtSource.close();
          } else if (data.type === 'summary') {
            setResults(prev => ({ ...prev, summary: data }));
          } else if (data.type === 'genome') {
            setResults(prev => ({ ...prev, genome: data.content }));
          } else {
            // Regular event (think, action, observation, etc.)
            setEvents(prev => [...prev, data]);
          }
        } catch (e) {
          console.error("Failed to parse event", e);
        }
      };

      evtSource.onerror = (err) => {
        console.error("EventSource error", err);
        // Sometimes onerror fires on close, check if we are done
        if (status !== 'done') {
          evtSource.close();
          // Optional: Don't set error if we just finished normally? 
          // For now, let's assume if it errors in 'attacking' state it's real.
          if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
            // Connection closed
          } else {
            setError("Connection lost");
            setStatus('error');
          }
        }
      };

    } catch (e) {
      console.error("Failed to start attack", e);
      setError(e.message);
      setStatus('error');
    }
  };

  const stopAttack = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setStatus('done'); // Or 'aborted'
    }
  };

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    events,
    status,
    error,
    results,
    startAttack,
    stopAttack
  };
};
