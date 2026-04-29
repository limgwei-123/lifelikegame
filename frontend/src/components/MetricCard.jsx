import React from "react";

export function MetricCard({ label, value, detail }) {
  return (
    <section className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </section>
  );
}
