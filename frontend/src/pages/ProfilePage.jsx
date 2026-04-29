import React, { useState } from "react";
import { Field } from "../components/Field.jsx";
import { MetricCard } from "../components/MetricCard.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

export function ProfilePage({ profile, ledgers, balance }) {
  const [screen, setScreen] = useState("home");

  if (screen === "edit") {
    return (
      <>
        <PageHeader eyebrow="Account" title="Edit Profile">
          <button className="secondary-button" onClick={() => setScreen("home")} type="button">
            Back
          </button>
        </PageHeader>
        <section className="phone-profile">
          <div className="panel">
            <form className="form-grid">
              <Field label="Display name">
                <input defaultValue={profile.display_name} />
              </Field>
              <Field label="Email">
                <input defaultValue={profile.email} type="email" />
              </Field>
              <Field label="Timezone">
                <select defaultValue={profile.timezone}>
                  <option value="Asia/Kuala_Lumpur">Asia/Kuala_Lumpur</option>
                  <option value="Asia/Singapore">Asia/Singapore</option>
                  <option value="UTC">UTC</option>
                </select>
              </Field>
              <button className="primary-button" type="button">Save preview</button>
            </form>
          </div>
        </section>
      </>
    );
  }

  if (screen === "ledger") {
    return (
      <>
        <PageHeader eyebrow="Account" title="Point Ledger">
          <button className="secondary-button" onClick={() => setScreen("home")} type="button">
            Back
          </button>
        </PageHeader>
        <section className="phone-profile">
          <div className="panel">
            <div className="ledger-list">
              {ledgers.map((item) => (
                <article className="ledger-row" key={item.id}>
                  <div>
                    <strong>{item.description}</strong>
                    <span>{item.event_at} · {item.source_type}</span>
                  </div>
                  <b className={item.delta > 0 ? "positive" : "negative"}>
                    {item.delta > 0 ? "+" : ""}{item.delta}
                  </b>
                </article>
              ))}
            </div>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageHeader eyebrow="Account" title="Profile" />

      <section className="metrics-grid">
        <MetricCard label="Point balance" value={`${balance} pts`} detail="Current usable balance" />
        <MetricCard label="Email" value={profile.email} detail="Login account" />
        <MetricCard label="Timezone" value={profile.timezone} detail="Used for daily task timing" />
      </section>

      <section className="phone-profile">
        <div className="panel phone-profile-card">
          <p className="profile-email">{profile.email}</p>
          <div className="phone-profile-actions">
            <button className="profile-menu-button" onClick={() => setScreen("edit")} type="button">
              <span>Edit profile</span>
              <b>›</b>
            </button>
            <button className="profile-menu-button" onClick={() => setScreen("ledger")} type="button">
              <span>Point ledger</span>
              <b>›</b>
            </button>
          </div>
        </div>
        <button className="logout-bottom-button" type="button">Logout</button>
      </section>
    </>
  );
}
