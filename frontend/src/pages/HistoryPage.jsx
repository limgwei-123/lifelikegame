import React from "react";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

export function HistoryPage({ ledgers }) {
  return (
    <>
      <PageHeader eyebrow="History" title="Point ledger" />
      <section className="content-grid">
        <div className="panel">
          <div className="section-title compact">
            <h3>Manual Ledger Entry</h3>
          </div>
          <form className="form-grid">
            <Field label="Delta">
              <input placeholder="10" type="number" />
            </Field>
            <Field label="Entry type">
              <select defaultValue="earn">
                <option value="earn">Earn</option>
                <option value="spend">Spend</option>
              </select>
            </Field>
            <Field label="Source type">
              <select defaultValue="manual">
                <option value="checkin">Checkin</option>
                <option value="redemption">Redemption</option>
                <option value="manual">Manual</option>
              </select>
            </Field>
            <Field label="Source id">
              <input placeholder="Optional" type="number" />
            </Field>
            <Field label="Description">
              <textarea rows="4" placeholder="Why points changed" />
            </Field>
            <button className="primary-button" type="button">Add preview</button>
          </form>
        </div>
        <div className="panel wide">
          <div className="section-title compact">
            <h3>Ledger records</h3>
          </div>
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
