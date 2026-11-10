export default function ReportEditor({ width, height, value, onChange, onClose, onGeneratePdf }) {
  return (
    <div style={{ position: 'relative', width, height }}>
      <div style={{ position: 'absolute', top: 10, left: 10, right: 10, display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: 8, zIndex: 2 }}>
        <div>
          <button className="panel-btn secondary" onClick={() => { navigator.clipboard?.writeText(value).catch(()=>{}); }}>Copy</button>
          <button className="panel-btn secondary" style={{ marginLeft: 8 }} onClick={onClose}>Close</button>
          <button className="panel-btn" style={{ marginLeft: 8 }} onClick={() => onGeneratePdf && onGeneratePdf(value)}>
            Generate PDF
          </button>
        </div>
      </div>
      <textarea
        className="panel-input"
        style={{ position: 'absolute', top: 50, left: 10, right: 10, bottom: 10, width: 'auto', height: 'auto', whiteSpace: 'pre', fontFamily: 'monospace', lineHeight: 1.4 }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
