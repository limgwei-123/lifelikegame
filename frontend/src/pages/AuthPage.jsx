import React, { useState } from "react";
import { Field } from "../components/Field.jsx";

export function AuthPage({ onEnter }) {
  const [mode, setMode] = useState("login");
  const isLogin = mode === "login";

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

        <form className="form-grid">
          <Field label="Email">
            <input autoComplete="email" placeholder="you@example.com" type="email" />
          </Field>
          <Field label="Password">
            <input
              autoComplete={isLogin ? "current-password" : "new-password"}
              placeholder="Enter password"
              type="password"
            />
          </Field>
          <button className="primary-button" onClick={onEnter} type="button">
            {isLogin ? "Login" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}
