import { useState, useEffect, useRef } from 'react';

export const useAttackStream = (targetUrl, onFallbackToSOC) => {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const eventSourceRef = useRef(null);
  const statusRef = useRef('idle');
  const eventsRef = useRef([]);

  const startAttack = (urlOverride) => {
    const activeUrl = urlOverride || targetUrl;
    if (!activeUrl) return;

    setEvents([]);
    eventsRef.current = [];
    setStatus('attacking');
    statusRef.current = 'attacking';
    setError(null);
    setResults(null);

    try {
      const url = `/attack?target=${encodeURIComponent(activeUrl)}`;
      const evtSource = new EventSource(url);
      eventSourceRef.current = evtSource;

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'done') {
            setStatus('done');
            statusRef.current = 'done';
            evtSource.close();
          } else if (data.type === 'summary') {
            setResults(prev => ({ ...prev, summary: data }));
          } else if (data.type === 'genome') {
            setResults(prev => ({ ...prev, genome: data.content }));
          } else if (data.type === 'error') {
            // Attack failed - trigger SOC fallback
            const updated = [...eventsRef.current, data];
            eventsRef.current = updated;
            setEvents(updated);
            evtSource.close();
            if (onFallbackToSOC) {
              onFallbackToSOC(updated);
            }
          } else {
            const updated = [...eventsRef.current, data];
            eventsRef.current = updated;
            setEvents(updated);
          }
        } catch (e) {
          console.error("Failed to parse event", e);
        }
      };

      evtSource.onerror = (err) => {
        // onerror fires on normal close too — ignore if already done
        if (statusRef.current === 'done') return;
        console.error("EventSource error", err);
        evtSource.close();
        setStatus('error');
        statusRef.current = 'error';
        if (onFallbackToSOC) {
          onFallbackToSOC(eventsRef.current);
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
      statusRef.current = 'done';
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      if (onFallbackToSOC) {
        onFallbackToSOC(eventsRef.current);
      }
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