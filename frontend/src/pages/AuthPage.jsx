import React, { useState } from "react";
import { Field } from "../components/Field.jsx";

export function AuthPage({ onSubmit }) {
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const isLogin = mode === "login";

  const submitAuth = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await onSubmit({ mode, email: data.email, password: data.password });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark">LG</div>
          <div>
            <p className="eyebrow">Life OS</p>
            <h1>lifelikegame</h1>
          </div>
        </div>

        <div className="auth-heading">
          <h2>{isLogin ? "Login" : "Create account"}</h2>
          <p>{isLogin ? "Continue managing your life game." : "Start tracking goals, tasks, and points."}</p>
        </div>

        <div className="auth-toggle" role="tablist" aria-label="Auth mode">
          <button
            className={isLogin ? "segment active" : "segment"}
            onClick={() => setMode("login")}
            type="button"
          >
            Login
          </button>
          <button
            className={!isLogin ? "segment active" : "segment"}
            onClick={() => setMode("signup")}
            type="button"
          >
            Signup
          </button>
        </div>

        <form className="form-grid" onSubmit={submitAuth}>
          <Field label="Email">
            <input autoComplete="email" name="email" placeholder="you@example.com" required type="email" />
          </Field>
          <Field label="Password">
            <input
              autoComplete={isLogin ? "current-password" : "new-password"}
              name="password"
              placeholder="Enter password"
              required
              type="password"
            />
          </Field>
          {error ? <p className="empty-text">{error}</p> : null}
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? "Working..." : isLogin ? "Login" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}
