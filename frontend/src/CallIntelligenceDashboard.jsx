import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence, useAnimation, useMotionValue, useSpring } from "framer-motion";

// ─── DESIGN TOKENS ───────────────────────────────────────────────────────────
const C = {
  bg: "#080812",
  surface: "rgba(255,255,255,0.03)",
  surfaceHover: "rgba(255,255,255,0.06)",
  border: "rgba(255,255,255,0.08)",
  borderGlow: "rgba(99,102,241,0.5)",
  primary: "#6366f1",
  primaryGlow: "rgba(99,102,241,0.3)",
  cyan: "#22d3ee",
  cyanGlow: "rgba(34,211,238,0.3)",
  pink: "#f472b6",
  pinkGlow: "rgba(244,114,182,0.3)",
  green: "#4ade80",
  red: "#f87171",
  amber: "#fbbf24",
  text: "#f1f5f9",
  textMuted: "#64748b",
  textDim: "#334155",
};

// ─── MOCK DATA ────────────────────────────────────────────────────────────────
const TRANSCRIPT_LINES = [
  { speaker: "Agent", text: "Thank you for calling Apex Financial Services. My name is Sarah, how can I assist you today?" },
  { speaker: "Customer", text: "Hi Sarah, I'm calling about a payment that was rejected on my account. I'm quite frustrated about this." },
  { speaker: "Agent", text: "I completely understand your frustration, and I sincerely apologize for the inconvenience. Could you please verify your account number so I can pull up your details?" },
  { speaker: "Customer", text: "Sure, it's 4892-7731-0045. I've been a customer for over five years and this has never happened before." },
  { speaker: "Agent", text: "Thank you for verifying. I can see your account clearly now. It appears the payment was declined due to a temporary security flag that was triggered by an unusual transaction pattern." },
  { speaker: "Customer", text: "That's strange. I was just traveling last week. Could that be the reason?" },
  { speaker: "Agent", text: "Absolutely, that's very likely the cause. Our fraud detection system flagged the out-of-state transactions as potentially suspicious. I'll escalate this to our resolution team right away." },
  { speaker: "Customer", text: "Okay, that makes sense. How long will this take to resolve?" },
  { speaker: "Agent", text: "Typically within 24 to 48 hours. You'll receive an SMS and email confirmation once it's cleared. Is there anything else I can help you with today?" },
  { speaker: "Customer", text: "No, that covers it. Thank you for explaining everything so clearly." },
  { speaker: "Agent", text: "My pleasure! Thank you for your patience and for being such a valued customer. Have a wonderful day!" },
];

const KEYWORDS = [
  { word: "payment", weight: 9, color: C.primary },
  { word: "rejected", weight: 7, color: C.red },
  { word: "security", weight: 8, color: C.cyan },
  { word: "account", weight: 10, color: C.primary },
  { word: "fraud", weight: 6, color: C.amber },
  { word: "transaction", weight: 7, color: C.cyan },
  { word: "resolved", weight: 8, color: C.green },
  { word: "frustrated", weight: 5, color: C.pink },
  { word: "verified", weight: 6, color: C.green },
  { word: "escalate", weight: 5, color: C.amber },
  { word: "traveling", weight: 4, color: C.textMuted },
  { word: "confirmation", weight: 5, color: C.green },
  { word: "customer", weight: 9, color: C.primary },
  { word: "apologize", weight: 6, color: C.pink },
];

const SOP_STEPS = [
  { label: "Greeting", passed: true, detail: "Agent identified company & name" },
  { label: "Customer ID", passed: true, detail: "Account number verified" },
  { label: "Problem Capture", passed: true, detail: "Issue documented correctly" },
  { label: "Empathy Statement", passed: true, detail: "Apology provided" },
  { label: "Resolution Offered", passed: true, detail: "Escalation initiated" },
  { label: "Upsell Attempt", passed: false, detail: "No product mention" },
  { label: "Closing Script", passed: true, detail: "Professional farewell" },
];

const STAGES = [
  { id: "upload", label: "Uploading Audio", icon: "⬆", duration: 1800 },
  { id: "decode", label: "Decoding Waveform", icon: "〰", duration: 1400 },
  { id: "transcribe", label: "Transcribing Speech", icon: "✍", duration: 3200 },
  { id: "analyze", label: "Running NLP Analysis", icon: "🧠", duration: 2000 },
  { id: "generate", label: "Generating Insights", icon: "✦", duration: 1200 },
];

const LANGUAGES = ["English (US)", "Spanish", "French", "Arabic", "Hindi", "Portuguese", "German", "Mandarin"];

// ─── UTILITIES ────────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ─── SUBCOMPONENTS ────────────────────────────────────────────────────────────

function GlowOrb({ x, y, color, size = 400, opacity = 0.12 }) {
  return (
    <div
      style={{
        position: "absolute", left: x, top: y,
        width: size, height: size,
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        opacity, borderRadius: "50%", filter: "blur(40px)",
        pointerEvents: "none", transform: "translate(-50%,-50%)",
      }}
    />
  );
}

function NoiseBg() {
  return (
    <svg style={{ position: "fixed", inset: 0, width: "100%", height: "100%", opacity: 0.025, pointerEvents: "none", zIndex: 0 }}>
      <filter id="noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#noise)" />
    </svg>
  );
}

function GridBg() {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
      backgroundImage: `linear-gradient(rgba(99,102,241,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.04) 1px, transparent 1px)`,
      backgroundSize: "60px 60px",
    }} />
  );
}

function Badge({ children, color = C.primary }) {
  return (
    <span style={{
      background: `${color}22`, border: `1px solid ${color}44`,
      color, borderRadius: 6, padding: "2px 10px", fontSize: 11,
      fontFamily: "monospace", letterSpacing: 1,
    }}>{children}</span>
  );
}

function GlassCard({ children, style = {}, hover = true, glow = false, onClick }) {
  const [hovered, setHovered] = useState(false);
  return (
    <motion.div
      onClick={onClick}
      onHoverStart={() => setHovered(true)}
      onHoverEnd={() => setHovered(false)}
      animate={{ boxShadow: glow || hovered ? `0 0 40px ${C.primaryGlow}, 0 8px 32px rgba(0,0,0,0.4)` : "0 4px 24px rgba(0,0,0,0.3)" }}
      style={{
        background: hovered && hover ? C.surfaceHover : C.surface,
        border: `1px solid ${hovered && hover ? "rgba(99,102,241,0.25)" : C.border}`,
        borderRadius: 16, backdropFilter: "blur(20px)",
        transition: "background 0.2s, border 0.2s",
        ...style,
      }}
    >{children}</motion.div>
  );
}

// ─── WAVEFORM ANIMATION ───────────────────────────────────────────────────────
function Waveform({ active = false, color = C.primary, bars = 40, height = 48 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 3, height }}>
      {Array.from({ length: bars }).map((_, i) => (
        <motion.div
          key={i}
          animate={active ? {
            scaleY: [0.15, Math.random() * 0.8 + 0.2, 0.15],
            opacity: [0.4, 1, 0.4],
          } : { scaleY: 0.1, opacity: 0.2 }}
          transition={{ duration: 0.6 + Math.random() * 0.8, repeat: Infinity, delay: i * 0.04, ease: "easeInOut" }}
          style={{
            width: 3, height: "100%", background: color,
            borderRadius: 2, originY: 0.5,
            boxShadow: active ? `0 0 6px ${color}` : "none",
          }}
        />
      ))}
    </div>
  );
}

// ─── CIRCULAR PROGRESS ───────────────────────────────────────────────────────
function CircularProgress({ value, size = 120, label, sublabel, color = C.primary }) {
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * (1 - value / 100);
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`${color}22`} strokeWidth={8} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={8} strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: dash }}
          transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
          filter={`drop-shadow(0 0 8px ${color})`}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <motion.span
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 22, fontWeight: 800, color: C.text, fontFamily: "'Syne', sans-serif" }}
        >{value}%</motion.span>
        {label && <span style={{ fontSize: 9, color: C.textMuted, letterSpacing: 1, textTransform: "uppercase", marginTop: 2 }}>{label}</span>}
      </div>
    </div>
  );
}

// ─── UPLOAD ZONE ──────────────────────────────────────────────────────────────
function UploadZone({ onFileSelect, file, language, setLanguage }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFileSelect(f);
  }, [onFileSelect]);

  return (
    <motion.div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      animate={{
        scale: dragging ? 1.02 : 1,
        boxShadow: dragging
          ? `0 0 80px ${C.primaryGlow}, 0 0 160px ${C.primaryGlow}, inset 0 0 40px rgba(99,102,241,0.1)`
          : `0 0 0px transparent`,
      }}
      style={{
        border: `2px dashed ${dragging ? C.primary : C.border}`,
        borderRadius: 20, padding: "48px 32px", textAlign: "center",
        cursor: "pointer", position: "relative", overflow: "hidden",
        background: dragging ? "rgba(99,102,241,0.06)" : C.surface,
        transition: "background 0.3s, border-color 0.3s",
      }}
      onClick={() => !file && inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept="audio/*" style={{ display: "none" }} onChange={(e) => onFileSelect(e.target.files[0])} />

      {/* Corner accents */}
      {["top-left", "top-right", "bottom-left", "bottom-right"].map((pos) => (
        <div key={pos} style={{
          position: "absolute",
          ...(pos.includes("top") ? { top: 12 } : { bottom: 12 }),
          ...(pos.includes("left") ? { left: 12 } : { right: 12 }),
          width: 20, height: 20,
          borderTop: pos.includes("top") ? `2px solid ${C.primary}` : "none",
          borderBottom: pos.includes("bottom") ? `2px solid ${C.primary}` : "none",
          borderLeft: pos.includes("left") ? `2px solid ${C.primary}` : "none",
          borderRight: pos.includes("right") ? `2px solid ${C.primary}` : "none",
          opacity: dragging ? 1 : 0.4, transition: "opacity 0.3s",
        }} />
      ))}

      <AnimatePresence mode="wait">
        {!file ? (
          <motion.div key="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
              style={{ fontSize: 48, marginBottom: 16 }}
            >🎙</motion.div>
            <div style={{ fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 8, fontFamily: "'Syne', sans-serif" }}>
              {dragging ? "Release to analyze" : "Drop your call recording"}
            </div>
            <div style={{ color: C.textMuted, fontSize: 13 }}>MP3, WAV, M4A, OGG • Max 500MB</div>
            <div style={{ marginTop: 16 }}>
              <span style={{
                background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
                color: "#fff", borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 600,
              }}>Browse Files</span>
            </div>
          </motion.div>
        ) : (
          <motion.div key="file" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
            <div style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 36 }}>🎵</span>
            </div>
            <div style={{ color: C.text, fontWeight: 700, fontSize: 15, marginBottom: 4 }}>{file.name}</div>
            <div style={{ color: C.textMuted, fontSize: 12, marginBottom: 16 }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </div>
            <Waveform active color={C.cyan} bars={50} />
            <div style={{ marginTop: 12 }}>
              <button
                onClick={(e) => { e.stopPropagation(); onFileSelect(null); }}
                style={{ background: "none", border: `1px solid ${C.border}`, color: C.textMuted, borderRadius: 8, padding: "4px 14px", fontSize: 12, cursor: "pointer" }}
              >Remove</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── PROCESSING TIMELINE ──────────────────────────────────────────────────────
function ProcessingTimeline({ currentStage, stageProgress }) {
  return (
    <div style={{ padding: "24px 0" }}>
      {STAGES.map((stage, i) => {
        const done = i < currentStage;
        const active = i === currentStage;
        const pending = i > currentStage;
        return (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}
          >
            {/* Icon */}
            <motion.div
              animate={{
                background: done
                  ? `linear-gradient(135deg, ${C.green}, #16a34a)`
                  : active
                    ? `linear-gradient(135deg, ${C.primary}, ${C.cyan})`
                    : C.surface,
                boxShadow: active ? `0 0 20px ${C.primaryGlow}` : "none",
              }}
              style={{
                width: 44, height: 44, borderRadius: 12,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, flexShrink: 0,
                border: `1px solid ${done ? C.green + "44" : active ? C.primary + "44" : C.border}`,
              }}
            >
              {done ? (
                <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }}>✓</motion.span>
              ) : (
                <motion.span animate={active ? { opacity: [1, 0.5, 1] } : {}} transition={{ duration: 1, repeat: Infinity }}>
                  {stage.icon}
                </motion.span>
              )}
            </motion.div>

            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{
                  fontWeight: 600, fontSize: 14,
                  color: done ? C.green : active ? C.text : C.textMuted,
                  fontFamily: "'Syne', sans-serif",
                }}>{stage.label}</span>
                {active && <span style={{ color: C.cyan, fontSize: 12, fontFamily: "monospace" }}>{Math.round(stageProgress)}%</span>}
                {done && <span style={{ color: C.green, fontSize: 12 }}>Complete</span>}
              </div>

              <div style={{ height: 4, background: C.surface, borderRadius: 4, overflow: "hidden" }}>
                <motion.div
                  animate={{
                    width: done ? "100%" : active ? `${stageProgress}%` : "0%",
                    background: done
                      ? `linear-gradient(90deg, ${C.green}, #16a34a)`
                      : `linear-gradient(90deg, ${C.primary}, ${C.cyan})`,
                  }}
                  transition={{ duration: 0.3 }}
                  style={{ height: "100%", borderRadius: 4, boxShadow: active ? `0 0 8px ${C.cyan}` : "none" }}
                />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ─── LIVE TRANSCRIPT ──────────────────────────────────────────────────────────
function LiveTranscript({ lines, active }) {
  const bottomRef = useRef();
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [lines]);

  return (
    <div style={{ height: 280, overflowY: "auto", padding: "12px 0" }}>
      {lines.map((line, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "flex-start" }}
        >
          <div style={{
            flexShrink: 0, width: 28, height: 28, borderRadius: 8,
            background: line.speaker === "Agent"
              ? `linear-gradient(135deg, ${C.primary}, ${C.cyan})`
              : `linear-gradient(135deg, ${C.pink}, ${C.amber})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 800, color: "#fff", fontFamily: "'Syne', sans-serif",
          }}>{line.speaker[0]}</div>
          <div>
            <div style={{ fontSize: 10, color: C.textMuted, marginBottom: 3, letterSpacing: 1, textTransform: "uppercase" }}>
              {line.speaker}
            </div>
            <div style={{ color: C.text, fontSize: 13, lineHeight: 1.6 }}>
              {line.text}
              {i === lines.length - 1 && active && (
                <motion.span
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity }}
                  style={{ display: "inline-block", width: 8, height: 14, background: C.cyan, borderRadius: 2, marginLeft: 4, verticalAlign: "middle" }}
                />
              )}
            </div>
          </div>
        </motion.div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

// ─── SOP VISUALIZER ───────────────────────────────────────────────────────────
function SOPVisualizer() {
  const passed = SOP_STEPS.filter((s) => s.passed).length;
  const score = Math.round((passed / SOP_STEPS.length) * 100);

  return (
    <GlassCard style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>SOP Compliance</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: C.text, fontFamily: "'Syne', sans-serif" }}>Protocol Validation</div>
        </div>
        <CircularProgress value={score} size={100} label="Score" color={score >= 80 ? C.green : C.amber} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {SOP_STEPS.map((step, i) => (
          <motion.div
            key={step.label}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + i * 0.08, duration: 0.4 }}
            style={{
              display: "flex", alignItems: "center", gap: 12, padding: "10px 14px",
              borderRadius: 10, background: step.passed ? `${C.green}0a` : `${C.red}0a`,
              border: `1px solid ${step.passed ? C.green + "22" : C.red + "22"}`,
            }}
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", delay: 0.2 + i * 0.08 }}
              style={{
                width: 22, height: 22, borderRadius: 6,
                background: step.passed ? `${C.green}22` : `${C.red}22`,
                border: `1px solid ${step.passed ? C.green : C.red}44`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, color: step.passed ? C.green : C.red,
              }}
            >{step.passed ? "✓" : "✕"}</motion.div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.text }}>{step.label}</div>
              <div style={{ fontSize: 11, color: C.textMuted }}>{step.detail}</div>
            </div>
            <Badge color={step.passed ? C.green : C.red}>{step.passed ? "PASS" : "FAIL"}</Badge>
          </motion.div>
        ))}
      </div>
    </GlassCard>
  );
}

// ─── ANALYTICS CARDS ──────────────────────────────────────────────────────────
function AnalyticsCards() {
  const cards = [
    {
      icon: "💳", label: "Payment Method", value: "Credit Card", sub: "Visa ending 0045",
      gradient: `linear-gradient(135deg, ${C.primary}22, ${C.cyan}11)`,
      border: `${C.primary}33`, glow: C.primaryGlow,
    },
    {
      icon: "⚡", label: "Rejection Reason", value: "Fraud Flag", sub: "Travel-triggered security",
      gradient: `linear-gradient(135deg, ${C.red}22, ${C.amber}11)`,
      border: `${C.red}33`, glow: "rgba(248,113,113,0.2)",
    },
    {
      icon: "😊", label: "Customer Sentiment", value: "Positive", sub: "Resolved by end of call",
      gradient: `linear-gradient(135deg, ${C.green}22, ${C.cyan}11)`,
      border: `${C.green}33`, glow: "rgba(74,222,128,0.2)",
    },
    {
      icon: "⏱", label: "Call Duration", value: "4m 22s", sub: "Within SLA target",
      gradient: `linear-gradient(135deg, ${C.cyan}22, ${C.primary}11)`,
      border: `${C.cyan}33`, glow: C.cyanGlow,
    },
    {
      icon: "🎯", label: "Resolution Rate", value: "100%", sub: "First call resolution",
      gradient: `linear-gradient(135deg, ${C.green}22, ${C.primary}11)`,
      border: `${C.green}33`, glow: "rgba(74,222,128,0.2)",
    },
    {
      icon: "📊", label: "Talk Ratio", value: "42 / 58", sub: "Agent / Customer",
      gradient: `linear-gradient(135deg, ${C.pink}22, ${C.primary}11)`,
      border: `${C.pink}33`, glow: C.pinkGlow,
    },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + i * 0.08 }}
          whileHover={{ scale: 1.03, boxShadow: `0 0 30px ${card.glow}` }}
          style={{
            background: card.gradient,
            border: `1px solid ${card.border}`,
            borderRadius: 14, padding: "18px 16px",
            cursor: "pointer", transition: "box-shadow 0.2s",
          }}
        >
          <div style={{ fontSize: 24, marginBottom: 10 }}>{card.icon}</div>
          <div style={{ fontSize: 10, color: C.textMuted, letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 4 }}>{card.label}</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: C.text, fontFamily: "'Syne', sans-serif", marginBottom: 3 }}>{card.value}</div>
          <div style={{ fontSize: 11, color: C.textMuted }}>{card.sub}</div>
        </motion.div>
      ))}
    </div>
  );
}

// ─── KEYWORD CLOUD ────────────────────────────────────────────────────────────
function KeywordCloud() {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "4px 0" }}>
      {KEYWORDS.map((kw, i) => (
        <motion.div
          key={kw.word}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.05 * i, type: "spring", stiffness: 200 }}
          whileHover={{ scale: 1.1, boxShadow: `0 0 16px ${kw.color}55` }}
          style={{
            background: `${kw.color}18`,
            border: `1px solid ${kw.color}44`,
            color: kw.color,
            borderRadius: 20, padding: `${4 + kw.weight * 0.5}px ${10 + kw.weight}px`,
            fontSize: 10 + kw.weight * 0.5,
            fontWeight: 600, cursor: "pointer",
            fontFamily: "'Syne', sans-serif",
          }}
        >{kw.word}</motion.div>
      ))}
    </div>
  );
}

// ─── SUMMARY CARD ─────────────────────────────────────────────────────────────
function SummaryCard() {
  const points = [
    "Customer called regarding a rejected payment on their account.",
    "Issue caused by fraud detection flagging out-of-state travel transactions.",
    "Agent verified identity via account number and explained the root cause.",
    "Escalation submitted to resolution team; expected resolution in 24–48 hours.",
    "Call ended positively with customer satisfaction restored.",
  ];

  return (
    <GlassCard style={{ padding: 24 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 20 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18,
          boxShadow: `0 0 16px ${C.primaryGlow}`,
        }}>🧠</div>
        <div>
          <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase" }}>AI Summary</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: C.text, fontFamily: "'Syne', sans-serif" }}>Call Intelligence Report</div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <Badge color={C.green}>HIGH QUALITY</Badge>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {points.map((pt, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 + i * 0.1 }}
            style={{ display: "flex", gap: 10, alignItems: "flex-start" }}
          >
            <div style={{
              flexShrink: 0, marginTop: 3, width: 6, height: 6, borderRadius: "50%",
              background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
              boxShadow: `0 0 6px ${C.primaryGlow}`,
            }} />
            <span style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.6 }}>{pt}</span>
          </motion.div>
        ))}
      </div>
    </GlassCard>
  );
}

// ─── API DEBUG PANEL ──────────────────────────────────────────────────────────
function ApiPanel({ visible }) {
  if (!visible) return null;
  const logs = [
    { time: "12:04:22.001", type: "OUT", msg: "POST /api/v1/call-analytics", color: C.cyan },
    { time: "12:04:22.003", type: "HDR", msg: "x-api-key: sk-••••••••••••••", color: C.textMuted },
    { time: "12:04:22.005", type: "HDR", msg: "Content-Type: application/json", color: C.textMuted },
    { time: "12:04:28.441", type: "IN ", msg: "HTTP 200 OK", color: C.green },
    { time: "12:04:28.442", type: "IN ", msg: "Content-Length: 4821 bytes", color: C.green },
    { time: "12:04:28.443", type: "DBG", msg: "Response parsed in 2ms", color: C.amber },
    { time: "12:04:28.444", type: "DBG", msg: "Total round-trip: 6440ms", color: C.amber },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
    >
      <GlassCard style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.green, boxShadow: `0 0 6px ${C.green}` }} />
          <span style={{ fontSize: 11, color: C.textMuted, fontFamily: "monospace", letterSpacing: 1 }}>API DEBUG CONSOLE</span>
        </div>
        <div style={{ padding: 16, fontFamily: "monospace", fontSize: 11, lineHeight: 2 }}>
          {logs.map((log, i) => (
            <div key={i} style={{ display: "flex", gap: 16 }}>
              <span style={{ color: C.textDim }}>{log.time}</span>
              <span style={{ color: log.color, fontWeight: 700 }}>[{log.type}]</span>
              <span style={{ color: C.textMuted }}>{log.msg}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </motion.div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function App() {
  const [phase, setPhase] = useState("home"); // home | upload | processing | dashboard
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("English (US)");
  const [currentStage, setCurrentStage] = useState(0);
  const [stageProgress, setStageProgress] = useState(0);
  const [transcriptLines, setTranscriptLines] = useState([]);
  const [showDebug, setShowDebug] = useState(false);
  const [dashTab, setDashTab] = useState("overview");

  const runPipeline = async () => {
    setPhase("processing");
    setCurrentStage(0);
    setStageProgress(0);
    setTranscriptLines([]);

    // Simulate each stage
    for (let s = 0; s < STAGES.length; s++) {
      setCurrentStage(s);
      const duration = STAGES[s].duration;
      const steps = 60;
      for (let p = 0; p <= steps; p++) {
        setStageProgress((p / steps) * 100);
        await sleep(duration / steps);
        // Start streaming transcript during transcription stage
        if (s === 2 && p % 10 === 0) {
          const lineIdx = Math.floor((p / steps) * TRANSCRIPT_LINES.length);
          setTranscriptLines(TRANSCRIPT_LINES.slice(0, lineIdx + 1));
        }
      }
    }
    setTranscriptLines(TRANSCRIPT_LINES);
    await sleep(600);
    setPhase("dashboard");
  };

  return (
    <div style={{
      minHeight: "100vh", background: C.bg, color: C.text, overflowX: "hidden",
      fontFamily: "'DM Sans', sans-serif",
    }}>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 4px; }
        ::selection { background: ${C.primary}44; }
      `}</style>

      <NoiseBg />
      <GridBg />

      {/* Ambient orbs */}
      <GlowOrb x="10%" y="20%" color={C.primary} size={600} opacity={0.08} />
      <GlowOrb x="85%" y="10%" color={C.cyan} size={400} opacity={0.07} />
      <GlowOrb x="50%" y="80%" color={C.pink} size={500} opacity={0.06} />

      <div style={{ position: "relative", zIndex: 1 }}>

        {/* ── HEADER ─────────────────────────────────────────── */}
        <header style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "20px 40px",
          borderBottom: `1px solid ${C.border}`,
          backdropFilter: "blur(20px)",
          background: "rgba(8,8,18,0.7)",
          position: "sticky", top: 0, zIndex: 100,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 9,
              background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, boxShadow: `0 0 16px ${C.primaryGlow}`,
            }}>✦</div>
            <span style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 16 }}>
              Apex<span style={{ color: C.cyan }}>AI</span>
            </span>
            <Badge color={C.primary}>BETA</Badge>
          </div>

          <nav style={{ display: "flex", gap: 28 }}>
            {["Product", "Docs", "Pricing", "Enterprise"].map((item) => (
              <span key={item} style={{ color: C.textMuted, fontSize: 13, cursor: "pointer", transition: "color 0.2s" }}
                onMouseEnter={(e) => e.target.style.color = C.text}
                onMouseLeave={(e) => e.target.style.color = C.textMuted}
              >{item}</span>
            ))}
          </nav>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setShowDebug(!showDebug)} style={{
              background: "none", border: `1px solid ${C.border}`, color: C.textMuted,
              borderRadius: 8, padding: "6px 14px", fontSize: 12, cursor: "pointer",
            }}>Debug</button>
            <button style={{
              background: `linear-gradient(135deg, ${C.primary}, #4f46e5)`,
              border: "none", color: "#fff", borderRadius: 8, padding: "7px 18px",
              fontSize: 13, fontWeight: 600, cursor: "pointer",
              boxShadow: `0 0 20px ${C.primaryGlow}`,
            }}>Get Started</button>
          </div>
        </header>

        <AnimatePresence mode="wait">

          {/* ── PHASE: HOME ───────────────────────────────────── */}
          {phase === "home" && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: -20 }}>
              {/* HERO */}
              <div style={{ textAlign: "center", padding: "100px 40px 60px", maxWidth: 800, margin: "0 auto" }}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  style={{ marginBottom: 20 }}
                >
                  <Badge color={C.cyan}>✦ POWERED BY AI · REAL-TIME ANALYSIS</Badge>
                </motion.div>

                <motion.h1
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  style={{
                    fontFamily: "'Syne', sans-serif", fontWeight: 800,
                    fontSize: "clamp(40px, 6vw, 72px)", lineHeight: 1.1, marginBottom: 24,
                  }}
                >
                  <span style={{
                    background: `linear-gradient(135deg, ${C.text} 30%, ${C.primary} 60%, ${C.cyan} 100%)`,
                    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                  }}>AI Call Compliance
                  </span>
                  <br />
                  <span style={{ color: C.text }}>Intelligence</span>
                </motion.h1>

                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  style={{ color: C.textMuted, fontSize: 18, lineHeight: 1.7, marginBottom: 40, maxWidth: 540, margin: "0 auto 40px" }}
                >
                  Real-time multilingual call analysis powered by AI. SOP validation, sentiment detection, and compliance scoring — instant.
                </motion.p>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}
                >
                  <motion.button
                    whileHover={{ scale: 1.04, boxShadow: `0 0 40px ${C.primaryGlow}` }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => setPhase("upload")}
                    style={{
                      background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
                      border: "none", color: "#fff", borderRadius: 12,
                      padding: "14px 32px", fontSize: 15, fontWeight: 700,
                      cursor: "pointer", fontFamily: "'Syne', sans-serif",
                      boxShadow: `0 0 24px ${C.primaryGlow}`,
                    }}
                  >✦ Analyze Call →</motion.button>
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.97 }}
                    style={{
                      background: "none", border: `1px solid ${C.border}`,
                      color: C.textMuted, borderRadius: 12, padding: "14px 32px",
                      fontSize: 15, cursor: "pointer",
                    }}
                  >View Demo</motion.button>
                </motion.div>
              </div>

              {/* Feature strips */}
              <div style={{ display: "flex", gap: 16, padding: "0 40px", maxWidth: 1000, margin: "0 auto 80px", flexWrap: "wrap" }}>
                {[
                  { icon: "🌐", title: "8+ Languages", desc: "Multilingual transcription" },
                  { icon: "⚡", title: "< 10s Analysis", desc: "Near real-time processing" },
                  { icon: "🔒", title: "SOC2 Compliant", desc: "Enterprise-grade security" },
                  { icon: "📊", title: "99.2% Accuracy", desc: "Industry-leading STT" },
                ].map((f, i) => (
                  <motion.div
                    key={f.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + i * 0.1 }}
                    style={{ flex: "1 1 200px" }}
                  >
                    <GlassCard style={{ padding: "20px 22px" }}>
                      <div style={{ fontSize: 24, marginBottom: 10 }}>{f.icon}</div>
                      <div style={{ fontWeight: 700, color: C.text, fontFamily: "'Syne', sans-serif", marginBottom: 4 }}>{f.title}</div>
                      <div style={{ fontSize: 12, color: C.textMuted }}>{f.desc}</div>
                    </GlassCard>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ── PHASE: UPLOAD ─────────────────────────────────── */}
          {phase === "upload" && (
            <motion.div key="upload" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              style={{ maxWidth: 620, margin: "60px auto", padding: "0 24px" }}
            >
              <div style={{ marginBottom: 32, textAlign: "center" }}>
                <Badge color={C.cyan}>STEP 1 OF 1</Badge>
                <h2 style={{ fontFamily: "'Syne', sans-serif", fontSize: 28, fontWeight: 800, marginTop: 12, marginBottom: 8 }}>Upload Audio Recording</h2>
                <p style={{ color: C.textMuted, fontSize: 14 }}>Drag & drop your call recording to begin analysis</p>
              </div>

              <UploadZone onFileSelect={setFile} file={file} language={language} setLanguage={setLanguage} />

              {/* Language selector */}
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, color: C.textMuted, marginBottom: 8, letterSpacing: 1, textTransform: "uppercase" }}>Call Language</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {LANGUAGES.map((lang) => (
                    <motion.button
                      key={lang}
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => setLanguage(lang)}
                      style={{
                        background: language === lang ? `${C.primary}22` : C.surface,
                        border: `1px solid ${language === lang ? C.primary + "66" : C.border}`,
                        color: language === lang ? C.primary : C.textMuted,
                        borderRadius: 8, padding: "6px 14px", fontSize: 12,
                        cursor: "pointer", fontWeight: language === lang ? 600 : 400,
                        boxShadow: language === lang ? `0 0 12px ${C.primaryGlow}` : "none",
                      }}
                    >{lang}</motion.button>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 28, display: "flex", gap: 12 }}>
                <button onClick={() => setPhase("home")} style={{
                  flex: 1, background: "none", border: `1px solid ${C.border}`,
                  color: C.textMuted, borderRadius: 12, padding: "13px", fontSize: 14, cursor: "pointer",
                }}>← Back</button>
                <motion.button
                  whileHover={file ? { scale: 1.02, boxShadow: `0 0 32px ${C.primaryGlow}` } : {}}
                  whileTap={file ? { scale: 0.98 } : {}}
                  onClick={file ? runPipeline : undefined}
                  style={{
                    flex: 2, background: file
                      ? `linear-gradient(135deg, ${C.primary}, ${C.cyan})`
                      : C.surface,
                    border: file ? "none" : `1px solid ${C.border}`,
                    color: file ? "#fff" : C.textDim,
                    borderRadius: 12, padding: "13px", fontSize: 14, fontWeight: 700,
                    cursor: file ? "pointer" : "not-allowed",
                    fontFamily: "'Syne', sans-serif",
                    transition: "all 0.3s",
                  }}
                >✦ Begin Analysis →</motion.button>
              </div>
            </motion.div>
          )}

          {/* ── PHASE: PROCESSING ─────────────────────────────── */}
          {phase === "processing" && (
            <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              style={{ maxWidth: 760, margin: "40px auto", padding: "0 24px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}
            >
              {/* Left: timeline */}
              <div>
                <GlassCard style={{ padding: 24 }}>
                  <div style={{ marginBottom: 8 }}>
                    <Badge color={C.cyan}>LIVE PROCESSING</Badge>
                  </div>
                  <h3 style={{ fontFamily: "'Syne', sans-serif", fontSize: 18, fontWeight: 800, marginBottom: 4 }}>AI Pipeline</h3>
                  <p style={{ fontSize: 12, color: C.textMuted, marginBottom: 0 }}>
                    Stage {Math.min(currentStage + 1, STAGES.length)} of {STAGES.length}
                  </p>

                  <div style={{ margin: "16px 0 0" }}>
                    <Waveform active color={C.cyan} bars={30} height={36} />
                  </div>

                  <ProcessingTimeline currentStage={currentStage} stageProgress={stageProgress} />
                </GlassCard>
              </div>

              {/* Right: live transcript */}
              <div>
                <GlassCard style={{ padding: 24, height: "100%" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div>
                      <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>Live Transcript</div>
                      <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 16 }}>Stream</div>
                    </div>
                    <motion.div
                      animate={{ opacity: [1, 0, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                      style={{ display: "flex", alignItems: "center", gap: 6 }}
                    >
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.red, boxShadow: `0 0 8px ${C.red}` }} />
                      <span style={{ fontSize: 10, color: C.red, fontFamily: "monospace", letterSpacing: 1 }}>LIVE</span>
                    </motion.div>
                  </div>
                  <LiveTranscript lines={transcriptLines} active={currentStage === 2} />
                </GlassCard>
              </div>
            </motion.div>
          )}

          {/* ── PHASE: DASHBOARD ──────────────────────────────── */}
          {phase === "dashboard" && (
            <motion.div key="dashboard" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px 60px" }}
            >
              {/* Dashboard header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
                <div>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                    <Badge color={C.green}>✓ ANALYSIS COMPLETE</Badge>
                  </motion.div>
                  <motion.h2
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                    style={{ fontFamily: "'Syne', sans-serif", fontSize: 26, fontWeight: 800, marginTop: 8 }}
                  >Call Intelligence Dashboard</motion.h2>
                  <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
                    style={{ color: C.textMuted, fontSize: 13 }}>
                    {file?.name || "demo_call.mp3"} · {language} · Analyzed just now
                  </motion.p>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={() => { setPhase("upload"); setFile(null); setTranscriptLines([]); }} style={{
                    background: "none", border: `1px solid ${C.border}`, color: C.textMuted,
                    borderRadius: 10, padding: "8px 18px", fontSize: 13, cursor: "pointer",
                  }}>← New Analysis</button>
                  <button style={{
                    background: `linear-gradient(135deg, ${C.primary}, ${C.cyan})`,
                    border: "none", color: "#fff", borderRadius: 10, padding: "8px 18px", fontSize: 13, cursor: "pointer",
                  }}>Export Report ↓</button>
                </div>
              </div>

              {/* Tab bar */}
              <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: `1px solid ${C.border}`, paddingBottom: 0 }}>
                {["overview", "transcript", "compliance", "debug"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setDashTab(tab)}
                    style={{
                      background: "none", border: "none", color: dashTab === tab ? C.text : C.textMuted,
                      fontSize: 13, fontWeight: dashTab === tab ? 700 : 400,
                      padding: "10px 18px", cursor: "pointer", position: "relative",
                      textTransform: "capitalize", fontFamily: "'Syne', sans-serif",
                    }}
                  >
                    {tab}
                    {dashTab === tab && (
                      <motion.div layoutId="tab-underline" style={{
                        position: "absolute", bottom: -1, left: 0, right: 0,
                        height: 2, background: `linear-gradient(90deg, ${C.primary}, ${C.cyan})`,
                        borderRadius: 2,
                      }} />
                    )}
                  </button>
                ))}
              </div>

              <AnimatePresence mode="wait">
                {dashTab === "overview" && (
                  <motion.div key="overview" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    {/* Top row */}
                    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 16 }}>
                      <SummaryCard />
                      <GlassCard style={{ padding: 24 }}>
                        <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 16 }}>Compliance Score</div>
                        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
                          <CircularProgress value={86} size={130} label="Adherence" color={C.green} />
                        </div>
                        <div style={{ textAlign: "center" }}>
                          <Badge color={C.green}>COMPLIANT</Badge>
                          <div style={{ fontSize: 12, color: C.textMuted, marginTop: 8 }}>6/7 SOP steps passed</div>
                        </div>
                        <div style={{ marginTop: 16, padding: "12px", background: `${C.green}0a`, border: `1px solid ${C.green}22`, borderRadius: 10 }}>
                          <div style={{ fontSize: 11, color: C.green, fontWeight: 600 }}>↑ 4% vs last week</div>
                          <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>Above team average of 79%</div>
                        </div>
                      </GlassCard>
                    </div>

                    {/* Analytics cards */}
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 12 }}>Call Analytics</div>
                      <AnalyticsCards />
                    </div>

                    {/* Keyword cloud */}
                    <GlassCard style={{ padding: 24 }}>
                      <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 14 }}>Keyword Intelligence</div>
                      <KeywordCloud />
                    </GlassCard>
                  </motion.div>
                )}

                {dashTab === "transcript" && (
                  <motion.div key="transcript" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <GlassCard style={{ padding: 24 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                        <div>
                          <div style={{ fontSize: 11, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>Full Transcript</div>
                          <div style={{ fontFamily: "'Syne', sans-serif", fontSize: 18, fontWeight: 800 }}>{TRANSCRIPT_LINES.length} Utterances</div>
                        </div>
                        <Badge color={C.cyan}>{language}</Badge>
                      </div>
                      <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
                        <LiveTranscript lines={TRANSCRIPT_LINES} active={false} />
                      </div>
                    </GlassCard>
                  </motion.div>
                )}

                {dashTab === "compliance" && (
                  <motion.div key="compliance" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <SOPVisualizer />
                  </motion.div>
                )}

                {dashTab === "debug" && (
                  <motion.div key="debug" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <ApiPanel visible />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}
