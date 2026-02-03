import { useEffect, useRef } from 'react';
import EventCard from './EventCard';

const AttackProgress = ({ events, onStop }) => {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [events]);

    return (
        <div className="progress-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h2>LIVE ATTACK FEED <span className="blink">_</span></h2>
                <button onClick={onStop} style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)' }}>
                    ABORT SEQUENCE
                </button>
            </div>

            <div className="feed" style={{
                height: '70vh',
                overflowY: 'auto',
                paddingRight: '1rem',
                border: '1px solid #333',
                background: '#000',
                padding: '1rem'
            }}>
                {events.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
                        Initializing connection to Cerebras API...
                    </div>
                )}

                {events.map((event, index) => (
                    <EventCard key={index} event={event} />
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};

export default AttackProgress;
