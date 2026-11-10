export default function TopBar({ onLogout }) {
  return (
    <div className="top-right-actions">
      <button className="btn-ghost" onClick={onLogout}>Logout</button>
    </div>
  );
}
