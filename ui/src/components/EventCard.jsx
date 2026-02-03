import { useMemo } from 'react';

const EventCard = ({ event }) => {
    const { type, content, tool, params, time, message } = event;

    const style = useMemo(() => {
        switch (type) {
            case 'think':
                return { borderColor: 'var(--color-info)', icon: '🧠', title: 'REASONING' };
            case 'action':
                return { borderColor: 'var(--color-warning)', icon: '⚡', title: 'ACTION' };
            case 'observation':
                if (content?.toLowerCase().includes('success') || content?.toLowerCase().includes('found')) {
                    return { borderColor: 'var(--color-success)', icon: '✅', title: 'OBSERVATION' };
                }
                return { borderColor: 'var(--text-dim)', icon: '👁️', title: 'OBSERVATION' };
            case 'success':
                return { borderColor: 'var(--color-success)', icon: '🏆', title: 'SUCCESS' };
            case 'warning':
                return { borderColor: 'var(--color-warning)', icon: '⚠️', title: 'WARNING' };
            case 'error':
                return { borderColor: 'var(--color-danger)', icon: '❌', title: 'ERROR' };
            default:
                return { borderColor: 'var(--text-dim)', icon: '📝', title: 'LOG' };
        }
    }, [type, content]);

    return (
        <div className="event-card panel" style={{
            borderLeft: `4px solid ${style.borderColor}`,
            padding: '1rem',
            marginBottom: '1rem',
            animation: 'fadeIn 0.3s ease-out'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <div style={{ color: style.borderColor, fontWeight: 'bold' }}>
                    {style.icon} {style.title}
                </div>
                {time && <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{time?.toFixed(3)}s</div>}
            </div>

            <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace' }}>
                {type === 'action' ? (
                    <div>
                        <span style={{ color: 'var(--color-warning)' }}>{tool}</span>
                        <span style={{ color: 'var(--text-dim)' }}>(</span>
                        {Object.entries(params || {}).map(([k, v], i) => (
                            <span key={k}>
                                {i > 0 && ', '}
                                <span style={{ color: '#aaa' }}>{k}=</span>
                                <span style={{ color: '#fff' }}>"{String(v).substring(0, 50)}{String(v).length > 50 ? '...' : ''}"</span>
                            </span>
                        ))}
                        <span style={{ color: 'var(--text-dim)' }}>)</span>
                    </div>
                ) : (type === 'success' || type === 'warning' || type === 'error') ? (
                    message || content
                ) : (
                    content
                )}
            </div>
        </div>
    );
};

export default EventCard;
