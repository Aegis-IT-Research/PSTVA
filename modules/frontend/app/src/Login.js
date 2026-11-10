import React, { useState } from "react";
import { setToken, clearToken } from "./auth";
import "./Login.css";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/back/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (res.ok && data && data.token) {
        setToken(data.token);
        onLogin && onLogin(data.token);
      } else {
        clearToken();
        setError(data?.error || "Invalid credentials");
      }
    } catch (err) {
      clearToken();
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <form onSubmit={submit} className="login-card">
        <h3 className="login-title">Welcome back</h3>

        {error ? <div className="login-error">{error}</div> : null}

        <div className="login-field">
          <label className="login-label">Username</label>
          <input
            className="login-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            autoFocus
          />
        </div>

        <div className="login-field password-row">
          <label className="login-label">Password</label>
          <input
            className="login-input"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <button
            type="button"
            className="toggle-visibility"
            onClick={() => setShowPassword((s) => !s)}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? "🙈" : "👁️"}
          </button>
        </div>

        <button disabled={loading} type="submit" className="login-btn">
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <div className="login-hint">Default: default / default</div>
      </form>
    </div>
  );
}
