import React, { useMemo, useState } from "react";
import { generateAiPlan } from "../api/aiPlannerApi.js";
import { CreateSheet } from "../components/CreateSheet.jsx";
import { Field } from "../components/Field.jsx";
import { PageHeader } from "../components/PageHeader.jsx";
import { formatScheduleLabel } from "../utils/scheduleLabels.js";

export function AiPlannerPage({ onConfirmPlan }) {
  const [prompt, setPrompt] = useState("");
  const [conversationHistory, setConversationHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [readyPlan, setReadyPlan] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const planTaskCount = useMemo(() => readyPlan?.tasks?.length ?? 0, [readyPlan]);

  const submitPrompt = async (event) => {
    event.preventDefault();
    const userPrompt = prompt.trim();
    if (!userPrompt || submitting) return;

    setSubmitting(true);
    setError("");
    setMessages((current) => [...current, { role: "user", content: userPrompt }]);
    setPrompt("");

    try {
      const response = await generateAiPlan({
        user_prompt: userPrompt,
        conversation_history: conversationHistory
      });

      setConversationHistory(response.conversation_history ?? []);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.message,
          questions: response.questions ?? [],
          status: response.status
        }
      ]);

      if (response.status === "plan_ready" && response.plan) {
        setReadyPlan(response.plan);
        setConfirmOpen(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const confirmPlan = async () => {
    if (!readyPlan || saving) return;

    setSaving(true);
    setError("");
    try {
      await onConfirmPlan(readyPlan);
      setConfirmOpen(false);
      setReadyPlan(null);
      setMessages([]);
      setConversationHistory([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow="AI" title="Planner" />

      <section className="ai-planner-layout">
        <div className="panel ai-planner-panel">
          <div className="section-title compact">
            <div>
              <p className="eyebrow">Assistant</p>
              <h3>Plan builder</h3>
            </div>
            {readyPlan ? <span className="pill">Plan ready</span> : null}
          </div>

          {error ? <p className="empty-text">{error}</p> : null}

          <div className="ai-chat-log" aria-live="polite">
            {messages.length === 0 ? (
              <p className="empty-text">Tell the planner your goal, constraints, and weekly availability.</p>
            ) : null}

            {messages.map((message, index) => (
              <article className={`ai-message ${message.role}`} key={`${message.role}-${index}`}>
                <strong>{message.role === "user" ? "You" : "AI Planner"}</strong>
                <p>{message.content}</p>
                {message.status === "plan_ready" ? <span className="pill">Plan ready</span> : null}
                {message.questions?.length ? (
                  <div className="ai-question-list">
                    {message.questions.map((question) => (
                      <span key={question}>{question}</span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <form className="ai-planner-form" onSubmit={submitPrompt}>
            <Field label="Message">
              <textarea
                name="prompt"
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="I want to build a workout routine..."
                rows="4"
                value={prompt}
              />
            </Field>
            <button className="primary-button" disabled={submitting} type="submit">
              {submitting ? "Planning..." : "Send"}
            </button>
          </form>
        </div>
      </section>

      <CreateSheet
        eyebrow="AI Planner"
        title="Confirm plan"
        open={confirmOpen}
        onClose={() => {
          if (!saving) setConfirmOpen(false);
        }}
      >
        <div className="plan-preview">
          <div className="plain-card">
            <p className="eyebrow">Plan ready</p>
            <h4>{readyPlan?.goal_title}</h4>
            <p>{planTaskCount} tasks will be created from this plan.</p>
          </div>

          <div className="task-list">
            {readyPlan?.tasks?.map((task, index) => (
              <article className="task-card" key={`${task.title}-${index}`}>
                <div className="task-main">
                  <div className="check-dot" aria-hidden="true" />
                  <div>
                    <div className="task-title-row">
                      <h4>{task.title}</h4>
                      <span className="pill muted">
                        {formatScheduleLabel(task.schedule_type, task.schedule_value_json)}
                      </span>
                    </div>
                    <p>{task.description}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <div className="confirm-actions">
            <button className="secondary-button" disabled={saving} onClick={() => setConfirmOpen(false)} type="button">
              Cancel
            </button>
            <button className="primary-button" disabled={saving} onClick={confirmPlan} type="button">
              {saving ? "Saving..." : "Confirm"}
            </button>
          </div>
        </div>
      </CreateSheet>
    </>
  );
}
