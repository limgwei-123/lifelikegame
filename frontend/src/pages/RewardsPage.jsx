import React, { useState } from "react";
import { CardMenu } from "../components/CardMenu.jsx";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { MetricCard } from "../components/MetricCard.jsx";
import { PageHeader } from "../components/PageHeader.jsx";

export function RewardsPage({ rewards, balance, onDelete, onRedeem, onSave }) {
  const [activeStatus, setActiveStatus] = useState("available");
  const [isCreating, setIsCreating] = useState(false);
  const [editingReward, setEditingReward] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const availableRewards = rewards.filter((reward) => reward.status !== "redeemed");
  const redeemedRewards = rewards.filter((reward) => reward.status === "redeemed");
  const visibleRewards = activeStatus === "available" ? availableRewards : redeemedRewards;

  const openCreate = () => {
    setEditingReward(null);
    setError("");
    setIsCreating(true);
  };

  const openEdit = (reward) => {
    setEditingReward(reward);
    setError("");
    setIsCreating(true);
  };

  const saveReward = async (event) => {
    event.preventDefault();
    if (saving) return;

    const data = Object.fromEntries(new FormData(event.currentTarget));
    const nextReward = {
      title: data.title,
      description: data.description,
      cost_points: Number(data.cost_points) || 0
    };
    setSaving(true);
    setError("");
    try {
      await onSave(editingReward, nextReward);
      setIsCreating(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const renderRewards = (items, emptyText) => (
    <div className="reward-grid">
      {items.length === 0 ? <p className="empty-text">{emptyText}</p> : null}
      {items.map((reward) => (
        <article className="reward-card editable-card" key={reward.id} onClick={() => openEdit(reward)}>
          <div>
            <div className="card-title-bar">
              <h4>{reward.title}</h4>
              <CardMenu label="Reward actions" onDelete={() => onDelete(reward.id)} />
            </div>
            <p>{reward.description}</p>
          </div>
          <div className="reward-footer">
            <strong>{reward.cost_points} pts</strong>
            {reward.status === "available" ? (
              <button
                className="secondary-button"
                onClick={(event) => {
                  event.stopPropagation();
                  onRedeem(reward.id);
                }}
                type="button"
              >
                Redeem
              </button>
            ) : (
              <span className="status-label">Redeemed</span>
            )}
          </div>
        </article>
      ))}
    </div>
  );

  return (
    <>
      <PageHeader eyebrow="Rewards" title="">
        <button className="fab-button" onClick={openCreate} type="button" aria-label="Create reward">
          +
        </button>
      </PageHeader>
      <section className="metrics-grid">
        <MetricCard label="Available balance" value={`${balance} pts`} detail="Current point ledger balance" />
        <MetricCard label="Rewards" value={rewards.length} detail="Items that can be redeemed" />
      </section>
      <section className="single-panel-layout">
        <div className="panel">
          <div className="section-title compact">
            <h3>Reward list</h3>
          </div>
          <div className="reward-segmented" role="tablist" aria-label="Reward status">
            <button
              className={activeStatus === "available" ? "segment active" : "segment"}
              onClick={() => setActiveStatus("available")}
              type="button"
            >
              <span>Available</span>
              <b>{availableRewards.length}</b>
            </button>
            <button
              className={activeStatus === "redeemed" ? "segment active" : "segment"}
              onClick={() => setActiveStatus("redeemed")}
              type="button"
            >
              <span>Redeemed</span>
              <b>{redeemedRewards.length}</b>
            </button>
          </div>
          {renderRewards(
            visibleRewards,
            activeStatus === "available" ? "No available rewards yet." : "No redeemed rewards yet."
          )}
        </div>
      </section>

      <CreateSheet
        eyebrow="Rewards"
        title={editingReward ? "Edit Reward" : "Create Reward"}
        open={isCreating}
        onClose={() => setIsCreating(false)}
      >
        <form className="form-grid" onSubmit={saveReward}>
          {error ? <p className="empty-text">{error}</p> : null}
          <Field label="Title">
            <input defaultValue={editingReward?.title ?? ""} name="title" placeholder="Hotpot dinner" />
          </Field>
          <Field label="Description">
            <textarea defaultValue={editingReward?.description ?? ""} name="description" rows="4" placeholder="Reward detail" />
          </Field>
          <Field label="Cost points">
            <input defaultValue={editingReward?.cost_points ?? ""} min="0" name="cost_points" placeholder="35" type="number" />
          </Field>
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? "Saving..." : "Save"}
          </button>
        </form>
      </CreateSheet>
    </>
  );
}
