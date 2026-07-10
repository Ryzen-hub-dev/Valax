"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Check,
  Code2,
  Cpu,
  Fingerprint,
  Key,
  Lock,
  Shield,
  Sparkles,
  Waves,
  X,
} from "lucide-react";
import PublicNav from "./components/PublicNav";
import PublicFooter from "./components/PublicFooter";
import WaveBackground from "./components/WaveBackground";
import config from "./config.json";
import pricingData from "./pricing.json";

const FEATURE_NODES = [
  { icon: Lock, eyebrow: "Obfuscation engine", title: "Multi-pass protection tuned for adversarial environments.", copy: "Valax layers code transformation, runtime verification, and encrypted delivery into one coherent defense surface." },
  { icon: Fingerprint, eyebrow: "Identity binding", title: "Device, session, and key validation operate together.", copy: "Access remains precise without adding friction, so legitimate users move quickly and unauthorized access stalls." },
  { icon: BarChart3, eyebrow: "Operational clarity", title: "A live system view for protection, usage, and trust.", copy: "Signals stay legible across analytics, key issuance, and execution patterns, helping teams act with confidence." },
  { icon: Key, eyebrow: "License control", title: "A key lifecycle that scales from launch to enforcement.", copy: "Create, revoke, segment, and monitor access with the precision expected from a premium security platform." },
  { icon: Code2, eyebrow: "Developer surface", title: "An API that feels designed, not bolted on.", copy: "Automate your workflow with clean primitives for scripts, users, keys, and events." },
  { icon: Waves, eyebrow: "Delivery", title: "Fast enough to disappear into the experience.", copy: "Edge-first delivery and lean interaction design keep the system responsive while the brand stays cinematic." },
];

const STORY = [
  { k: "01", t: "Signal", d: "A clean entry point establishes trust and sets up the Valax core as the visual anchor." },
  { k: "02", t: "Activation", d: "The protective network expands, suggesting layered defense and live system intelligence." },
  { k: "03", t: "Control", d: "Features emerge from the environment as the user scrolls through the operational stack." },
  { k: "04", t: "Commitment", d: "The journey resolves with a confident CTA that feels like the end of a story, not a sales pitch." },
];

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.55, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] } }),
};
const stagger = { visible: { transition: { staggerChildren: 0.08 } } };

function useCountUp(target, duration = 1300) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (target == null) return undefined;
    const start = performance.now();
    let raf = 0;
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(eased * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

function Stat({ icon: Icon, label, value, loading }) {
  const counted = useCountUp(loading ? null : value);
  return (
    <div className="stat-item">
      <div className="stat-icon"><Icon size={17} /></div>
      <div className="stat-value">{loading ? <span className="stat-skel" /> : counted.toLocaleString()}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function FeatureCard({ icon: Icon, eyebrow, title, copy, index }) {
  return (
    <motion.article variants={fadeUp} custom={index} className="feature-card">
      <div className="feature-card-glow" />
      <div className="feature-icon"><Icon size={18} /></div>
      <div className="feature-eyebrow">{eyebrow}</div>
      <h3>{title}</h3>
      <p>{copy}</p>
    </motion.article>
  );
}

function CompareIcon({ type, text }) {
  if (type === "check") return <span className="compare ok"><Check size={14} />{text}</span>;
  if (type === "cross") return <span className="compare no"><X size={14} />{text}</span>;
  return <span className="compare neutral">{text}</span>;
}

export default function HomeClient({ session }) {
  const [stats, setStats] = useState(null);
  const [mouse, setMouse] = useState({ x: 0.5, y: 0.5 });
  const heroRef = useRef(null);
  const mx = useMotionValue(0.5);
  const my = useMotionValue(0.5);
  const rx = useSpring(useTransform(my, [0, 1], [10, -10]), { stiffness: 120, damping: 18 });
  const ry = useSpring(useTransform(mx, [0, 1], [-12, 12]), { stiffness: 120, damping: 18 });

  useEffect(() => { fetch("/api/stats").then((r) => r.json()).then(setStats).catch(() => {}); }, []);

  return (
    <div className="page-shell">
      <style>{`
        :root { --bg:#04070f; --panel: rgba(255,255,255,.04); --line: rgba(180,210,255,.12); --text: rgba(245,249,255,.96); --muted: rgba(198,214,255,.62); --accent:#4b8dff; }
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body { background: var(--bg); }
        .page-shell { min-height: 100vh; background: radial-gradient(circle at 50% 0%, rgba(75,141,255,.14), transparent 36%), linear-gradient(180deg, #050810 0%, #03050a 100%); color: var(--text); overflow: hidden; }
        .content { position: relative; z-index: 2; }
        .hero { position: relative; padding: 148px 24px 92px; overflow: hidden; }
        .hero-inner { max-width: 1120px; margin: 0 auto; display: grid; grid-template-columns: 1.1fr .9fr; gap: 48px; align-items: center; }
        .eyebrow { display:inline-flex; align-items:center; gap:8px; padding: 8px 14px; border:1px solid var(--line); border-radius:999px; background: rgba(255,255,255,.03); color: var(--muted); font-size: 11px; letter-spacing:.18em; text-transform:uppercase; }
        .hero h1 { margin: 18px 0 18px; font-size: clamp(54px, 7vw, 96px); line-height: .94; letter-spacing: -.055em; max-width: 11ch; }
        .hero p { max-width: 56ch; color: var(--muted); font-size: 16px; line-height: 1.8; }
        .cta-row { display:flex; gap:12px; flex-wrap:wrap; margin-top: 32px; }
        .btn { display:inline-flex; align-items:center; gap:10px; padding: 15px 18px; border-radius: 999px; text-decoration:none; font-weight:700; border:1px solid transparent; transition: transform .2s ease, border-color .2s ease, background .2s ease; }
        .btn:hover { transform: translateY(-1px); }
        .btn-primary { background: linear-gradient(180deg, rgba(75,141,255,1), rgba(32,84,200,1)); color: white; box-shadow: 0 18px 50px rgba(75,141,255,.22); }
        .btn-secondary { border-color: var(--line); background: rgba(255,255,255,.03); color: var(--text); }
        .hero-visual { position: relative; height: 620px; display:flex; align-items:center; justify-content:center; perspective: 1200px; }
        .core { position: relative; width: 340px; height: 340px; transform-style: preserve-3d; filter: drop-shadow(0 0 60px rgba(75,141,255,.24)); }
        .ring { position:absolute; inset:0; border-radius: 50%; border: 1px solid rgba(120,170,255,.24); background: radial-gradient(circle at 50% 35%, rgba(80,145,255,.26), rgba(9,16,34,.12) 56%, transparent 68%); }
        .ring.r2 { inset: 26px; border-color: rgba(120,170,255,.34); transform: rotateX(68deg) rotateZ(24deg); }
        .ring.r3 { inset: 64px; border-color: rgba(120,170,255,.44); transform: rotateY(72deg) rotateZ(-12deg); }
        .mesh { position:absolute; inset: 42px; border-radius: 28px; border: 1px solid rgba(180,210,255,.12); background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.01)); transform: translateZ(38px) rotateX(12deg) rotateY(-16deg); }
        .mesh:before, .mesh:after { content:""; position:absolute; inset:0; border-radius: inherit; background-image: linear-gradient(rgba(120,170,255,.16) 1px, transparent 1px), linear-gradient(90deg, rgba(120,170,255,.16) 1px, transparent 1px); background-size: 28px 28px; mask: linear-gradient(180deg, rgba(0,0,0,.95), transparent); opacity:.75; }
        .mesh:after { inset: 18px; opacity: .4; transform: rotate(9deg); }
        .orb { position:absolute; width: 92px; height: 92px; border-radius: 50%; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,.92), rgba(75,141,255,.75) 34%, rgba(75,141,255,.08) 67%, transparent 72%); box-shadow: 0 0 50px rgba(75,141,255,.38); }
        .orb.one { top: 14%; left: 16%; }
        .orb.two { right: 14%; bottom: 18%; }
        .orb.three { bottom: 12%; left: 50%; transform: translateX(-50%); width: 54px; height: 54px; }
        .halo { position:absolute; inset: -10%; border-radius: 50%; border: 1px solid rgba(160,200,255,.14); transform: rotateX(72deg); }
        .halo.h2 { inset: 8%; }
        .halo.h3 { inset: 18%; }
        .section { padding: 0 24px 120px; }
        .section-inner { max-width: 1120px; margin: 0 auto; }
        .section-head { max-width: 760px; margin-bottom: 36px; }
        .section-head h2 { margin: 14px 0 12px; font-size: clamp(32px, 4.6vw, 58px); line-height: 1.02; letter-spacing: -.045em; }
        .section-head p { color: var(--muted); line-height: 1.8; max-width: 62ch; }
        .glass { background: rgba(255,255,255,.03); border: 1px solid var(--line); border-radius: 28px; backdrop-filter: blur(18px); }
        .stats { display:grid; grid-template-columns: repeat(3, 1fr); gap: 1px; overflow: hidden; }
        .stat-item { padding: 28px 24px; background: rgba(255,255,255,.02); text-align:center; }
        .stat-icon { width: 40px; height: 40px; margin: 0 auto 12px; border-radius: 50%; display:grid; place-items:center; background: rgba(75,141,255,.12); color: #9fc0ff; }
        .stat-value { font-size: 30px; font-weight: 800; letter-spacing: -.04em; }
        .stat-label { color: var(--muted); font-size: 13px; margin-top: 6px; }
        .stat-skel { display:block; width: 58px; height: 24px; margin: 0 auto; border-radius: 999px; background: rgba(255,255,255,.08); }
        .grid-3 { display:grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .grid-2 { display:grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
        .feature-card { position: relative; min-height: 260px; padding: 28px; border-radius: 24px; border: 1px solid var(--line); background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.022)); overflow:hidden; }
        .feature-card-glow { position:absolute; inset: -20% auto auto 45%; width: 240px; height: 240px; background: radial-gradient(circle, rgba(75,141,255,.16), transparent 62%); pointer-events:none; }
        .feature-icon { width: 42px; height: 42px; border-radius: 12px; display:grid; place-items:center; background: rgba(75,141,255,.12); color:#b8d0ff; margin-bottom: 18px; }
        .feature-eyebrow { color: #8fb1ff; font-size: 11px; letter-spacing:.16em; text-transform: uppercase; margin-bottom: 10px; }
        .feature-card h3 { font-size: 24px; line-height: 1.15; letter-spacing: -.03em; margin: 0 0 10px; max-width: 16ch; }
        .feature-card p { color: var(--muted); line-height: 1.75; margin: 0; max-width: 34ch; }
        .story { display:grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }
        .story-step { padding: 24px; border-radius: 22px; background: rgba(255,255,255,.03); border: 1px solid var(--line); min-height: 150px; }
        .story-step kbd { display:inline-flex; align-items:center; justify-content:center; width: 44px; height: 44px; border-radius: 14px; background: rgba(75,141,255,.12); color: #c6d9ff; border: 1px solid rgba(120,170,255,.2); font-weight: 800; margin-bottom: 18px; }
        .story-step h3 { margin: 0 0 10px; font-size: 19px; letter-spacing:-.02em; }
        .story-step p { margin:0; color: var(--muted); line-height: 1.75; }
        .compare-wrap { overflow:hidden; border-radius: 26px; border: 1px solid var(--line); background: rgba(255,255,255,.03); }
        .compare-head, .compare-row { display:grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 16px; padding: 18px 22px; }
        .compare-head { border-bottom: 1px solid var(--line); color: rgba(220,232,255,.45); font-size: 11px; text-transform: uppercase; letter-spacing: .16em; }
        .compare-row { border-bottom: 1px solid rgba(255,255,255,.06); }
        .compare-row:last-child { border-bottom: none; }
        .compare { display:inline-flex; align-items:center; gap:8px; }
        .compare.ok { color: #a9c7ff; }
        .compare.no { color: rgba(255,128,128,.85); }
        .compare.neutral { color: var(--muted); }
        .pricing-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .plan { padding: 28px; border-radius: 24px; border: 1px solid var(--line); background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02)); }
        .plan.featured { border-color: rgba(120,170,255,.28); box-shadow: 0 18px 60px rgba(75,141,255,.14); transform: translateY(-8px); }
        .plan h3 { margin: 0 0 6px; font-size: 22px; letter-spacing:-.03em; }
        .plan .sub { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
        .price { font-size: 54px; font-weight: 900; letter-spacing: -.05em; margin-bottom: 18px; }
        .plan ul { list-style:none; padding:0; margin:0 0 24px; display:grid; gap: 10px; }
        .plan li { display:flex; gap: 10px; color: rgba(232,240,255,.82); line-height: 1.5; }
        .final-cta { text-align:center; padding-bottom: 140px; }
        .final-cta .glass { padding: 44px 24px; max-width: 760px; margin: 0 auto; }
        .final-cta h2 { font-size: clamp(34px, 5vw, 62px); line-height: 1.02; letter-spacing:-.05em; margin: 14px auto 16px; max-width: 12ch; }
        .final-cta p { margin: 0 auto 30px; max-width: 56ch; color: var(--muted); line-height: 1.8; }
        .cursor-halo { position: fixed; inset: auto auto 0 0; width: 520px; height: 520px; pointer-events:none; background: radial-gradient(circle, rgba(75,141,255,.12), transparent 65%); filter: blur(10px); transform: translate(-50%, -50%); z-index: 1; }
        @media (max-width: 960px) {
          .hero-inner, .story, .grid-3, .grid-2, .pricing-grid { grid-template-columns: 1fr; }
          .hero { padding-top: 118px; }
          .hero-visual { height: 480px; }
          .hero h1 { max-width: 100%; }
          .plan.featured { transform: none; }
          .stats { grid-template-columns: 1fr; }
          .compare-head, .compare-row { grid-template-columns: 1.2fr 1fr 1fr; }
        }
      `}</style>

      <div className="cursor-halo" style={{ left: `${mouse.x * 100}%`, top: `${mouse.y * 100}%`, opacity: 0.75 }} />
      <WaveBackground opacity={0.14} />

      <div className="content">
        <PublicNav session={session} />

        <section className="hero" ref={heroRef} onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width; const y = (e.clientY - r.top) / r.height; setMouse({ x, y }); mx.set(x); my.set(y); }}>
          <div className="hero-inner">
            <motion.div initial="hidden" animate="visible" variants={stagger}>
              <motion.div variants={fadeUp} custom={0} className="eyebrow"><Sparkles size={12} /> Valax security platform</motion.div>
              <motion.h1 variants={fadeUp} custom={1}>Power, precision, and control for protected software.</motion.h1>
              <motion.p variants={fadeUp} custom={2}>{config.site.description}</motion.p>
              <motion.div variants={fadeUp} custom={3} className="cta-row">
                <Link href={session ? "/dashboard" : "/login"} className="btn btn-primary">Get started <ArrowRight size={16} /></Link>
                <a href="#story" className="btn btn-secondary">Explore the system</a>
              </motion.div>
            </motion.div>

            <div className="hero-visual">
              <motion.div className="core" style={{ rotateX: rx, rotateY: ry }}>
                <div className="halo" />
                <div className="halo h2" />
                <div className="halo h3" />
                <div className="ring" />
                <div className="ring r2" />
                <div className="ring r3" />
                <div className="mesh" />
                <div className="orb one" />
                <div className="orb two" />
                <div className="orb three" />
              </motion.div>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="section-inner">
            <div className="glass stats">
              <Stat icon={Shield} label="Scripts protected" value={stats?.scripts ?? 0} loading={!stats} />
              <Stat icon={Key} label="Keys issued" value={stats?.keys ?? 0} loading={!stats} />
              <Stat icon={Cpu} label="Executions tracked" value={stats?.executions ?? 0} loading={!stats} />
            </div>
          </div>
        </section>

        <section className="section" id="story">
          <div className="section-inner">
            <div className="section-head">
              <div className="eyebrow">Scroll narrative</div>
              <h2>The interface is built as a sequence, not a stack of blocks.</h2>
              <p>Each section advances the story: the Valax core appears, the protection network expands, and the product surface emerges with increasing clarity.</p>
            </div>
            <div className="story">
              {STORY.map((item) => (
                <div key={item.k} className="story-step">
                  <kbd>{item.k}</kbd>
                  <h3>{item.t}</h3>
                  <p>{item.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="features">
          <div className="section-inner">
            <div className="section-head">
              <div className="eyebrow">Platform capabilities</div>
              <h2>Security architecture that feels deliberate at every layer.</h2>
              <p>Valax keeps the visual language restrained while presenting a strong sense of depth, motion, and system intelligence.</p>
            </div>
            <motion.div className="grid-3" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }}>
              {FEATURE_NODES.map((node, i) => <FeatureCard key={node.title} {...node} index={i} />)}
            </motion.div>
          </div>
        </section>

        <section className="section" id="compare">
          <div className="section-inner">
            <div className="section-head">
              <div className="eyebrow">Competitive clarity</div>
              <h2>Quiet confidence, backed by operational depth.</h2>
              <p>Comparison is kept restrained and legible, letting the product story carry the emphasis rather than the table itself.</p>
            </div>
            <div className="compare-wrap">
              <div className="compare-head"><div>Capability</div><div>Valax</div><div>Luarmor</div></div>
              {[["Protection model", "Layered multi-pass", "Basic"], ["Identity binding", "Device + session controls", "Single factor"], ["Analytics", "Live system telemetry", "Limited"], ["Developer API", "Structured automation surface", "Partial"], ["Performance", "Edge-first delivery", "Standard"]].map((row) => (
                <div key={row[0]} className="compare-row">
                  <div>{row[0]}</div>
                  <div><CompareIcon type="check" text={row[1]} /></div>
                  <div><CompareIcon type={row[2] === "Basic" || row[2] === "Standard" || row[2] === "Partial" ? "cross" : "neutral"} text={row[2]} /></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="pricing">
          <div className="section-inner">
            <div className="section-head">
              <div className="eyebrow">Pricing</div>
              <h2>Transparent tiers for teams that want precision.</h2>
              <p>Plans are presented with a calm hierarchy, keeping the emphasis on value and decision-making clarity.</p>
            </div>
            <div className="pricing-grid">
              {pricingData.plans.map((plan) => (
                <div key={plan.id} className={`plan ${plan.popular ? "featured" : ""}`}>
                  <h3>{plan.name}</h3>
                  <div className="sub">{plan.subtitle}</div>
                  <div className="price">{plan.price === 0 ? "Free" : `$${plan.price}`}</div>
                  <ul>
                    {plan.features.filter((f) => f.included).slice(0, 5).map((feature) => (
                      <li key={feature.label}><Check size={16} style={{ color: "#9fc0ff", flexShrink: 0, marginTop: 2 }} /> <span>{feature.label}</span></li>
                    ))}
                  </ul>
                  <Link href={session ? "/dashboard/upgrade" : "/login"} className={plan.popular ? "btn btn-primary" : "btn btn-secondary"} style={{ width: "100%", justifyContent: "center" }}>{plan.cta}</Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section final-cta">
          <div className="glass">
            <div className="eyebrow" style={{ margin: "0 auto" }}>Final call</div>
            <h2>Bring the Valax core into your workflow.</h2>
            <p>{config.site.description}</p>
            <Link href={session ? "/dashboard" : "/login"} className="btn btn-primary">Begin the experience <ArrowRight size={16} /></Link>
          </div>
        </section>

        <PublicFooter />
      </div>
    </div>
  );
}
