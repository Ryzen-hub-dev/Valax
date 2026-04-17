<?php
/* VALAX-SHIELD - DUAL-MODE DASHBOARD */

require 'config.php';

$is_logged_in = isset($_SESSION['user_id']);
$user = null;

if ($is_logged_in && isset($pdo) && $pdo !== null) {
    try {
        $stmt = $pdo->prepare("SELECT * FROM users WHERE discord_id = ?");
        $stmt->execute([$_SESSION['user_id']]);
        $user = $stmt->fetch();
        
        if (!$user) {
            $is_logged_in = false;
            session_regenerate_id(true);
        }
    } catch (PDOException $e) {
        $is_logged_in = false;
        $user = null;
    }
}

$username = $user ? htmlspecialchars($user['username']) : '';
$avatar = $user ? htmlspecialchars($user['avatar']) : '';
$credits = $user ? htmlspecialchars($user['obf_credits']) : '0';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VALAX | Protection Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        /* ========== MODE-SPECIFIC OVERRIDES ========== */
        
        /* Landing Mode - Hide dashboard elements */
        body.mode-landing .dashboard-header { display: none !important; }
        body.mode-landing .dashboard-content { display: none !important; }
        body.mode-landing .dashboard-nav { display: none !important; }
        
        /* Dashboard Mode - Hide landing elements */
        body.mode-dashboard .landing-hero { display: none !important; }
        body.mode-dashboard .landing-features { display: none !important; }
        body.mode-dashboard .landing-pricing { display: none !important; }
        body.mode-dashboard .landing-cta { display: none !important; }
        body.mode-dashboard .landing-footer { display: none !important; }
        body.mode-dashboard .header .nav-buttons .btn-signin { display: none !important; }
        body.mode-dashboard .header .nav-buttons .btn-primary-nav { display: none !important; }
        
        /* ========== DASHBOARD HEADER ========== */
        .dashboard-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 40px;
            background: rgba(5,5,8,0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--h);
        }
        
        .dashboard-header .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 20px;
            font-weight: 800;
        }
        
        .dashboard-header .logo-icon {
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .dashboard-header .logo-icon img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        /* Shield Icon SVG */
        .icon-shield {
            width: 28px;
            height: 28px;
            display: inline-block;
        }
        
        .icon-shield-small {
            width: 20px;
            height: 20px;
            display: inline-block;
        }
        
        .icon-shield-large {
            width: 64px;
            height: 64px;
            display: inline-block;
        }
        
        .dashboard-nav {
            display: flex;
            gap: 8px;
        }
        
        .dashboard-nav-btn {
            padding: 10px 20px;
            background: transparent;
            border: 1px solid transparent;
            color: var(--g);
            font-size: 14px;
            font-weight: 600;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s var(--m);
            font-family: inherit;
        }
        
        .dashboard-nav-btn:hover {
            color: var(--f);
            background: var(--i);
        }
        
        .dashboard-nav-btn.active {
            color: var(--f);
            background: linear-gradient(135deg,var(--a),var(--c));
            box-shadow: 0 4px 15px var(--l);
        }
        
        .dashboard-user-area {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .credits-display {
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--i);
            border: 1px solid var(--h);
            padding: 10px 20px;
            border-radius: 12px;
        }
        
        .credits-label {
            font-size: 11px;
            color: var(--g);
            font-weight: 600;
            letter-spacing: 0.1em;
        }
        
        .credits-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--b);
            font-family: 'JetBrains Mono', monospace;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 16px;
            background: var(--i);
            border: 1px solid var(--h);
            border-radius: 12px;
        }
        
        .user-avatar {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: 2px solid var(--a);
        }
        
        .user-name {
            font-size: 14px;
            font-weight: 700;
        }
        
        .user-status {
            font-size: 10px;
            color: var(--j);
            font-weight: 700;
        }
        
        /* ========== DASHBOARD CONTENT ========== */
        .dashboard-content {
            padding-top: 100px;
            min-height: 100vh;
        }
        
        .dashboard-section {
            display: none;
            padding: 40px;
            max-width: 1400px;
            margin: 0 auto;
            animation: fadeInUp 0.5s var(--m);
        }
        
        .dashboard-section.active {
            display: block;
        }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* ========== WELCOME HERO ========== */
        .welcome-hero {
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 24px;
            padding: 50px 60px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, rgba(124,77,255,0.1) 0%, transparent 100%);
        }
        
        .welcome-text h1 {
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -0.02em;
        }
        
        .welcome-text p {
            font-size: 16px;
            color: var(--g);
        }
        
        /* ========== STATS ROW ========== */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            transition: all 0.4s var(--m);
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            border-color: var(--a);
            box-shadow: 0 20px 40px rgba(124,77,255,0.15);
        }
        
        .stat-card .stat-icon {
            font-size: 32px;
            margin-bottom: 15px;
        }
        
        .stat-card .stat-value {
            font-size: 36px;
            font-weight: 800;
            color: var(--b);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }
        
        .stat-card .stat-label {
            font-size: 13px;
            color: var(--g);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* ========== FEATURE CARDS (Dashboard Nav) ========== */
        .feature-nav-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .feature-nav-card {
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 24px;
            padding: 40px 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.4s var(--m);
        }
        
        .feature-nav-card:hover {
            transform: translateY(-8px);
            border-color: var(--a);
            box-shadow: 0 20px 60px rgba(124,77,255,0.2);
        }
        
        .feature-nav-card .f-icon {
            width: 70px;
            height: 70px;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg,var(--a),var(--c));
            border-radius: 18px;
            font-size: 28px;
            box-shadow: 0 8px 25px var(--l);
        }
        
        .feature-nav-card h3 {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .feature-nav-card p {
            font-size: 14px;
            color: var(--g);
        }
        
        /* ========== OBFUSCATOR SECTION ========== */
        .obfuscator-layout {
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 30px;
        }
        
        .upload-box {
            background: var(--d);
            border: 2px dashed var(--h);
            border-radius: 24px;
            padding: 60px 40px;
            text-align: center;
            transition: all 0.4s var(--m);
        }
        
        .upload-box:hover {
            border-color: var(--a);
            box-shadow: 0 20px 60px rgba(124,77,255,0.1);
        }
        
        .upload-box.drag-over {
            border-color: var(--j);
            background: rgba(16, 185, 129, 0.05);
        }
        
        .upload-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .upload-box h3 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .upload-box p {
            color: var(--g);
            margin-bottom: 30px;
        }
        
        .upload-box .btn {
            margin-top: 20px;
        }
        
        .terminal-box {
            background: rgba(0,0,0,0.5);
            border: 1px solid var(--h);
            border-radius: 16px;
            padding: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--g);
            height: 100%;
            overflow-y: auto;
        }
        
        .terminal-box .log-line {
            margin-bottom: 8px;
            line-height: 1.5;
        }
        
        .terminal-box .log-time {
            color: var(--g);
            opacity: 0.6;
        }
        
        .terminal-box .log-accent { color: var(--a); }
        .terminal-box .log-success { color: var(--j); }
        .terminal-box .log-error { color: var(--k); }
        
        /* ========== HOSTING SECTION ========== */
        .hosting-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
        }
        
        .hosting-header h2 {
            font-size: 28px;
            font-weight: 800;
        }
        
        .hosting-header p {
            color: var(--g);
            margin-top: 5px;
        }
        
        .hosting-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .hosting-slot-card {
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 20px;
            padding: 30px;
            border-left: 4px solid var(--j);
            transition: all 0.4s var(--m);
        }
        
        .hosting-slot-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 20px 50px rgba(124,77,255,0.15);
        }
        
        .hosting-slot-card.status-disabled {
            border-left-color: var(--k);
        }
        
        .hosting-slot-card.status-unconfigured {
            border-left-color: var(--a);
        }
        
        .slot-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .slot-header svg {
            color: var(--a);
        }
        
        .slot-status {
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 6px;
            background: var(--j);
            color: #fff;
        }
        
        .slot-status.disabled {
            background: var(--k);
        }
        
        .slot-status.unconfigured {
            background: var(--a);
        }
        
        .slot-name {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .slot-id {
            font-size: 11px;
            color: var(--a);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 20px;
        }
        
        /* ========== REDEEM SECTION ========== */
        .redeem-container {
            max-width: 600px;
            margin: 60px auto;
            text-align: center;
        }
        
        .redeem-box {
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 24px;
            padding: 60px 50px;
        }
        
        .redeem-box h2 {
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 15px;
        }
        
        .redeem-box p {
            color: var(--g);
            margin-bottom: 40px;
        }
        
        .redeem-input-group {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .redeem-input {
            flex: 1;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--h);
            border-radius: 14px;
            padding: 16px 20px;
            color: var(--b);
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            font-weight: 700;
            transition: all 0.3s var(--m);
        }
        
        .redeem-input:focus {
            outline: none;
            border-color: var(--a);
            box-shadow: 0 0 20px var(--l);
        }
        
        .redeem-input::placeholder {
            color: var(--g);
            font-weight: 400;
        }
        
        .redeem-result {
            font-size: 14px;
            font-weight: 700;
            min-height: 24px;
        }
        
        .redeem-result.success { color: var(--j); }
        .redeem-result.error { color: var(--k); }
        
        /* ========== RESPONSIVE ========== */
        @media (max-width: 1200px) {
            .obfuscator-layout { grid-template-columns: 1fr; }
            .stats-row { grid-template-columns: repeat(2, 1fr); }
        }
        
        @media (max-width: 1024px) {
            .feature-nav-grid { grid-template-columns: repeat(2, 1fr); }
            .welcome-hero { flex-direction: column; text-align: center; gap: 30px; }
            .dashboard-header { padding: 15px 20px; }
            .dashboard-nav { display: none; }
        }
        
        @media (max-width: 768px) {
            .stats-row { grid-template-columns: 1fr 1fr; }
            .feature-nav-grid { grid-template-columns: 1fr; }
            .redeem-input-group { flex-direction: column; }
            .hosting-grid { grid-template-columns: 1fr; }
        }
        
        @media (max-width: 480px) {
            .dashboard-content { padding-top: 80px; }
            .stats-row { grid-template-columns: 1fr; }
            .welcome-hero { padding: 30px; }
            .dashboard-user-area .credits-display { display: none; }
        }
        
        /* ========== MANAGEMENT MODAL ========== */
        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            z-index: 9999;
            overflow-y: auto;
            padding: 40px 20px;
        }
        
        .modal-content {
            max-width: 1100px;
            margin: 0 auto;
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 24px;
            overflow: hidden;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid var(--h);
        }
        
        .modal-body {
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 30px;
        }
        
        .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid var(--h);
        }
        
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        
        .switch input { opacity: 0; width: 0; height: 0; }
        
        .slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: #2d3748;
            transition: 0.4s;
            border-radius: 24px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background: white;
            transition: 0.4s;
            border-radius: 50%;
        }
        
        input:checked + .slider { background: var(--a); }
        input:checked + .slider:before { transform: translateX(20px); }
        
        .loader-box {
            background: #000;
            padding: 15px;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--j);
            border: 1px solid var(--h);
            word-break: break-all;
            margin-bottom: 15px;
        }
        
        /* Editor Modal */
        .editor-modal {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            z-index: 10000;
            align-items: center;
            justify-content: center;
        }
        
        .editor-container {
            width: 90%;
            height: 85vh;
            background: var(--d);
            border: 1px solid var(--h);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 25px;
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid var(--h);
        }
        
        .editor-body {
            flex: 1;
            padding: 20px;
        }
        
        .editor-body textarea {
            width: 100%;
            height: 100%;
            background: #0f172a;
            color: #a5b4fc;
            border: none;
            padding: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            outline: none;
            resize: none;
            border-radius: 12px;
        }
    </style>
</head>
<body class="mode-<?php echo $is_logged_in ? 'dashboard' : 'landing'; ?>">
    <div class="grain"></div>
    
    <!-- ==================== LANDING HEADER ==================== -->
    <header class="header">
        <a href="dashboard.php" class="logo">
            <div class="logo-icon"><img src="logo.png" alt="VALAX"></div>
            <span>VALAX</span>
        </a>
        
        <nav class="nav-links">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="#security">Security</a>
        </nav>
        
        <div class="nav-buttons">
            <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-signin">Sign In</a>
            <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-primary-nav btn-glow">Connect Discord</a>
        </div>
        
        <div class="mobile-menu">
            <span></span><span></span><span></span>
        </div>
    </header>
    
    <!-- ==================== LANDING CONTENT ==================== -->
    <main class="landing-content">
        <!-- HERO -->
        <section class="hero landing-hero">
            <div class="hero-badge">
                <span class="dot"></span>
                Next-Gen Protection Platform
            </div>
            
            <h1>
                <span class="gradient">VALAX</span> Protection Platform
            </h1>
            
            <p class="hero-subtitle">
                Next-gen script security & cloud hosting. Protect your code with military-grade obfuscation and deploy globally.
            </p>
            
            <div class="hero-buttons">
                <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-action">
                    Connect Discord
                </a>
                <a href="#features" class="btn btn-secondary">
                    View Features
                </a>
            </div>
            
            <div class="scroll-indicator">
                <span>Explore More</span>
                <div class="arrow"></div>
            </div>
        </section>
        
        <!-- FEATURES -->
        <section class="features landing-features" id="features">
            <div class="section-header">
                <h2>Why Choose <span class="gradient">VALAX</span>?</h2>
                <p>Enterprise-grade security meets developer-friendly tools</p>
            </div>
            
            <div class="features-grid">
                <div class="f-card">
                    <div class="f-icon">
                        <svg class="icon-shield-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                    </div>
                    <h3>Obfuscation Engine</h3>
                    <p>Military-grade virtualization technology. Transform your Lua scripts into unreadable bytecode that's impossible to reverse engineer.</p>
                </div>
                
                <div class="f-card">
                    <div class="f-icon">
                        <svg class="icon-shield-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                        </svg>
                    </div>
                    <h3>Cloud Hosting</h3>
                    <p>Deploy your protected scripts globally with one click. Automatic updates, zero downtime, and instant distribution worldwide.</p>
                </div>
                
                <div class="f-card">
                    <div class="f-icon">
                        <svg class="icon-shield-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                        </svg>
                    </div>
                    <h3>License System</h3>
                    <p>Full control over your script distribution. HWID locks, heartbeat protection, and kill switches built-in.</p>
                </div>
            </div>
        </section>
        
        <!-- PRICING -->
        <section class="pricing landing-pricing" id="pricing">
            <div class="section-header">
                <h2>Simple <span class="gradient">Pricing</span></h2>
                <p>Choose the plan that fits your needs</p>
            </div>
            
            <div class="pricing-grid">
                <div class="p-card">
                    <h4>Trial</h4>
                    <div class="p-price"><span class="currency">$</span>2<span class="period">/one-time</span></div>
                    <p class="p-credits">1 Encryption Credit</p>
                    <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-select">Get Started</a>
                </div>
                
                <div class="p-card pro">
                    <span class="popular-badge">Most Popular</span>
                    <h4>Standard</h4>
                    <div class="p-price"><span class="currency">$</span>5<span class="period">/one-time</span></div>
                    <p class="p-credits">3 Encryption Credits</p>
                    <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-select">Purchase Now</a>
                </div>
                
                <div class="p-card">
                    <h4>Studio</h4>
                    <div class="p-price"><span class="currency">$</span>8<span class="period">/one-time</span></div>
                    <p class="p-credits">10 Encryption Credits</p>
                    <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-select">Get Studio</a>
                </div>
            </div>
        </section>
        
        <!-- CTA -->
        <section class="cta-section landing-cta">
            <h2>Ready to <span class="gradient">Secure Your Code</span>?</h2>
            <p>Join thousands of developers who trust VALAX for their script protection</p>
            <a href="<?php echo htmlspecialchars(isset($auth_url) ? $auth_url : '#'); ?>" class="btn-action btn-glow">
                Get Started Free
            </a>
        </section>
        
        <!-- FOOTER -->
        <footer class="footer landing-footer">
            <div class="footer-content">
                <div class="footer-top">
                    <div class="footer-brand">
                        <div class="logo">
                            <div class="logo-icon"><img src="logo.png" alt="VALAX"></div>
                            <span>VALAX</span>
                        </div>
                        <p>Next-generation script security and cloud hosting platform. Protecting developers worldwide since 2024.</p>
                    </div>
                </div>
                <div class="footer-bottom">
                    <p class="footer-copyright">© 2024 VALAX. All rights reserved.</p>
                    <div class="footer-social">
                        <a href="#" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
                            </svg>
                        </a>
                        <a href="#" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
                            </svg>
                        </a>
                        <a href="#" style="text-decoration: none; display: flex; align-items: center; justify-content: center;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    </main>
    
    <!-- ==================== DASHBOARD HEADER ==================== -->
    <header class="dashboard-header">
        <a href="dashboard.php" class="logo">
            <div class="logo-icon"><img src="logo.png" alt="VALAX"></div>
            <span>VALAX</span>
        </a>
        
        <nav class="dashboard-nav">
            <button class="dashboard-nav-btn active" data-section="home">Dashboard</button>
            <button class="dashboard-nav-btn" data-section="obfuscator">Obfuscator</button>
            <button class="dashboard-nav-btn" data-section="hosting">Hosting</button>
            <button class="dashboard-nav-btn" data-section="redeem">Redeem</button>
        </nav>
        
        <div class="dashboard-user-area">
            <div class="credits-display">
                <span class="credits-label">CREDITS</span>
                <span class="credits-value" id="user-credits"><?php echo $credits; ?></span>
            </div>
            
            <div class="user-info">
                <img src="<?php echo $avatar; ?>" alt="Avatar" class="user-avatar">
                <div>
                    <div class="user-name"><?php echo $username; ?></div>
                    <div class="user-status">■ AUTHORIZED</div>
                </div>
            </div>
            
            <a href="logout.php" class="btn btn-secondary" style="padding: 10px 20px; font-size: 13px; background: var(--k);">Logout</a>
        </div>
    </header>
    
    <!-- ==================== DASHBOARD CONTENT ==================== -->
    <main class="dashboard-content">
        <!-- HOME SECTION -->
        <section id="home" class="dashboard-section active">
            <div class="welcome-hero">
                <div class="welcome-text">
                    <h1>Welcome back, <span class="gradient"><?php echo $username; ?></span></h1>
                    <p>Your command center for script protection and cloud hosting</p>
                </div>
            </div>
            
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 6v6l4 2"/>
                        </svg>
                    </div>
                    <div class="stat-value" id="stat-credits"><?php echo $credits; ?></div>
                    <div class="stat-label">Credits</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                        </svg>
                    </div>
                    <div class="stat-value" id="stat-slots">0</div>
                    <div class="stat-label">Active Slots</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 3v18h18"/>
                            <path d="M18 17V9M13 17V5M8 17v-3"/>
                        </svg>
                    </div>
                    <div class="stat-value" id="stat-usage">0</div>
                    <div class="stat-label">Total Usage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                    </div>
                    <div class="stat-value">V5.0</div>
                    <div class="stat-label">Engine Version</div>
                </div>
            </div>
            
            <div class="feature-nav-grid">
                <div class="feature-nav-card" data-navigate="obfuscator">
                    <div class="f-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                    </div>
                    <h3>Obfuscator Engine</h3>
                    <p>Protect your scripts with military-grade virtualization</p>
                </div>
                
                <div class="feature-nav-card" data-navigate="hosting">
                    <div class="f-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                        </svg>
                    </div>
                    <h3>Cloud Hosting</h3>
                    <p>Deploy and manage your protected scripts globally</p>
                </div>
                
                <div class="feature-nav-card" data-navigate="redeem">
                    <div class="f-icon">
                        <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                        </svg>
                    </div>
                    <h3>Redeem Code</h3>
                    <p>Activate credits with license keys</p>
                </div>
            </div>
        </section>
        
        <!-- OBFUSCATOR SECTION -->
        <section id="obfuscator" class="dashboard-section">
            <div class="welcome-hero" style="background: linear-gradient(135deg, rgba(124,77,255,0.15) 0%, transparent 100%);">
                <div class="welcome-text">
                    <h1><span class="gradient">Virtualizer</span> Engine</h1>
                    <p>Upload your Lua script for military-grade obfuscation</p>
                </div>
            </div>
            
            <div class="obfuscator-layout">
                <div class="upload-box" id="obf-upload-zone">
                    <div class="upload-icon">
                        <svg class="icon-shield-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                    </div>
                    <h3 id="obf-file-name">Drop your file here</h3>
                    <p>Supported formats: .lua, .txt</p>

                    <!-- Protection Level Selector -->
                    <div class="protection-selector" style="margin: 20px 0; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 12px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                            <div style="display: flex; align-items: center; gap: 20px;">
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="radio" name="protection_level" value="ultra" checked>
                                    <span style="font-weight: 600;">🛡️ Ultra Protection</span>
                                </label>
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="radio" name="protection_level" value="lite">
                                    <span style="font-weight: 600;">⚡ Lite Protection</span>
                                </label>
                            </div>
                            <div style="font-size: 0.85rem; opacity: 0.7; max-width: 400px;">
                                <span id="ultra-desc">Max security (VM + Anti-debug + Flattening + Opaque predicates). Larger output size.</span>
                                <span id="lite-desc" style="display: none;">Lightweight obfuscation (String encryption + Variable renaming). Small output size.</span>
                            </div>
                        </div>
                    </div>

                    <input type="file" id="file_input" accept=".lua,.txt" style="display: none;">
                    <button class="btn btn-primary" id="upload-btn">UPLOAD SOURCE</button>

                    <button class="btn btn-action" id="run-btn" style="width: 100%; margin-top: 30px; padding: 20px;">
                        START ENCRYPTION
                    </button>
                </div>
                
                <div class="terminal-box" id="log_output">
                    <div class="log-line">
                        <span class="log-time">[<?php echo date('H:i:s'); ?>]</span>
                        <span class="log-accent">[SYSTEM]</span> VALAX V5.0 initialized...
                    </div>
                    <div class="log-line">
                        <span class="log-time">[<?php echo date('H:i:s'); ?>]</span>
                        <span>[WAIT]</span> Waiting for file input...
                    </div>
                </div>
            </div>
        </section>
        
        <!-- HOSTING SECTION -->
        <section id="hosting" class="dashboard-section">
            <div class="hosting-header">
                <div>
                    <h2><span class="gradient">Aegis</span> Cloud Slots</h2>
                    <p>Securely host your scripts on military-grade infrastructure</p>
                </div>
                <button id="buy-btn" class="btn btn-action" style="background: var(--j); padding: 14px 24px;">
                    + PURCHASE SLOT (2 Credits)
                </button>
            </div>
            
            <div id="hosting-slots-grid" class="hosting-grid">
                <!-- Slots loaded via JS -->
            </div>
        </section>
        
        <!-- REDEEM SECTION -->
        <section id="redeem" class="dashboard-section">
            <div class="redeem-container">
                <div class="redeem-box">
                    <div style="margin-bottom: 20px;">
                        <svg class="icon-shield-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color: var(--a);">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                        </svg>
                    </div>
                    <h2>Redeem License Key</h2>
                    <p>Enter your VALAX license code to activate credits</p>
                    
                    <div class="redeem-input-group">
                        <input type="text" id="cdk_input" class="redeem-input" placeholder="VALAX-XXXX-XXXX-XXXX">
                    </div>
                    
                    <button id="redeem_btn" class="btn btn-action" style="width: 100%;">ACTIVATE</button>
                    
                    <div id="result_info" class="redeem-result"></div>
                </div>
            </div>
        </section>
    </main>
    
    <!-- ==================== MANAGEMENT MODAL ==================== -->
    <div id="management-page" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-header">
                <button id="close-manage-btn" class="btn btn-secondary" style="padding: 8px 16px; font-size: 12px;">
                    ← Back to Dashboard
                </button>
                <div style="text-align: right;">
                    <div id="manage-slot-id" style="font-family: 'JetBrains Mono'; color: var(--a); font-size: 12px;">ID: VX-UNKNOWN</div>
                    <h3 id="manage-slot-name" style="margin: 5px 0 0 0; font-size: 20px;">Unconfigured Slot</h3>
                    <span id="status-badge" style="font-size: 10px; padding: 3px 10px; border-radius: 4px; background: #333; margin-top: 5px; display: inline-block;">UNKNOWN</span>
                </div>
            </div>
            
            <div class="modal-body">
                <div style="display: flex; flex-direction: column; gap: 25px;">
                    <!-- Script Identity -->
                    <div class="f-card" style="padding: 25px;">
                        <h3 style="margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="color: var(--a);">01</span> Script Identity
                        </h3>
                        <input type="text" id="script_name_input" placeholder="Enter script name..." 
                               style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--h); color: var(--f); padding: 14px; border-radius: 10px; font-size: 14px;">
                    </div>
                    
                    <!-- Source Code -->
                    <div class="f-card" style="padding: 25px;">
                        <h3 style="margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="color: var(--a);">02</span> Source Code
                        </h3>
                        <p style="color: var(--g); font-size: 13px; margin-bottom: 20px;">Upload your Lua script. It will be secured automatically.</p>
                        
                        <div id="source-drop-zone" style="border: 2px dashed var(--h); border-radius: 14px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.3s var(--m);">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 10px; color: var(--a);">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                            </svg>
                            <p id="file-name-display" style="margin: 0; font-weight: 600; color: var(--g);">Click to select .lua file</p>
                            <input type="file" id="source_upload" accept=".lua,.txt" style="display: none;">
                        </div>
                    </div>
                    
                    <!-- Security Config -->
                    <div class="f-card" style="padding: 25px;">
                        <h3 style="margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="color: var(--a);">03</span> Security Configuration
                        </h3>
                        
                        <div class="setting-item">
                            <div>
                                <div style="font-weight: 700;">VM Protection</div>
                                <div style="font-size: 11px; color: var(--g);">Enable virtualization obfuscation</div>
                            </div>
                            <label class="switch"><input type="checkbox" id="vm_obfuscation"><span class="slider"></span></label>
                        </div>
                        
                        <div class="setting-item">
                            <div>
                                <div style="font-weight: 700;">HWID Lock</div>
                                <div style="font-size: 11px; color: var(--g);">Bind to first user's hardware</div>
                            </div>
                            <label class="switch"><input type="checkbox" id="hwid_lock"><span class="slider"></span></label>
                        </div>
                        
                        <div class="setting-item" style="border-bottom: none;">
                            <div>
                                <div style="font-weight: 700;">Heartbeat Protection</div>
                                <div style="font-size: 11px; color: var(--g);">Anti-tamper heartbeat check</div>
                            </div>
                            <label class="switch"><input type="checkbox" id="heartbeat_protection"><span class="slider"></span></label>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; flex-direction: column; gap: 25px;">
                    <!-- Loader -->
                    <div class="f-card" style="border-color: var(--a); background: rgba(124,77,255,0.05); padding: 25px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 16px;">Loader Command</h3>
                        <p style="font-size: 11px; color: var(--g); margin-bottom: 15px;">Share this with your users:</p>
                        <div id="loader-box" class="loader-box">-- Upload script to generate loader --</div>
                        <button id="copy-loader-btn" class="btn btn-secondary" style="width: 100%; font-size: 12px;">COPY TO CLIPBOARD</button>
                    </div>
                    
                    <!-- Quick Actions -->
                    <div class="f-card" style="padding: 25px;">
                        <h3 style="margin: 0 0 15px 0; font-size: 16px;">Quick Actions</h3>
                        
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <button id="open-editor-btn" class="btn btn-secondary" style="text-align: left; font-size: 13px;">EDIT Online Source Editor</button>
                            <button id="download-backup-btn" class="btn btn-secondary" style="text-align: left; font-size: 13px;">DOWNLOAD Backup</button>
                            <button id="kill-switch-btn" class="btn" style="text-align: left; font-size: 13px; background: var(--k);">KILL-SWITCH Activate</button>
                            <button id="delete-hosting-btn" class="btn" style="text-align: left; font-size: 13px; background: #1a1a1a; color: var(--k); border: 1px solid var(--k);">DELETE Hosting</button>
                        </div>
                    </div>
                    
                    <!-- Deploy -->
                    <button id="deploy-btn" class="btn btn-action" style="width: 100%;">DEPLOY & LOCK SOURCE</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- ==================== EDITOR MODAL ==================== -->
    <div id="editor-modal" class="editor-modal">
        <div class="editor-container">
            <div class="editor-header">
                <h3 style="margin: 0;">Source Code Editor</h3>
                <div style="display: flex; gap: 10px;">
                    <button id="save-editor-btn" class="btn btn-primary" style="padding: 8px 16px; font-size: 12px;">SAVE CHANGES</button>
                    <button id="close-editor-btn" class="btn btn-secondary" style="padding: 8px 16px; font-size: 12px;">CLOSE</button>
                </div>
            </div>
            <div class="editor-body">
                <textarea id="code-editor-area" placeholder="Your source code will appear here..."></textarea>
            </div>
        </div>
    </div>

    <script>
    // =====================================================
    // SECTION NAVIGATION
    // =====================================================
    function showSection(id) {
        document.querySelectorAll('.dashboard-section').forEach(el => {
            el.classList.remove('active');
            el.style.display = 'none';
        });
        
        document.querySelectorAll('.dashboard-nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.section === id) {
                btn.classList.add('active');
            }
        });
        
        const target = document.getElementById(id);
        if (target) {
            target.style.display = 'block';
            target.classList.add('active');
        }
    }
    
    // Navigation button clicks
    document.querySelectorAll('.dashboard-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            showSection(btn.dataset.section);
        });
    });
    
    // Feature card navigation
    document.querySelectorAll('.feature-nav-card').forEach(card => {
        card.addEventListener('click', () => {
            const section = card.dataset.navigate;
            showSection(section);
        });
    });

    // =====================================================
    // PROTECTION LEVEL SELECTOR
    // =====================================================
    document.querySelectorAll('input[name="protection_level"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const ultraDesc = document.getElementById('ultra-desc');
            const liteDesc = document.getElementById('lite-desc');
            if (this.value === 'ultra') {
                ultraDesc.style.display = 'inline';
                liteDesc.style.display = 'none';
            } else {
                ultraDesc.style.display = 'none';
                liteDesc.style.display = 'inline';
            }
        });
    });

    // =====================================================
    // OBFUSCATOR LOGIC
    // =====================================================
    const uploadZone = document.getElementById('obf-upload-zone');
    const fileInput = document.getElementById('file_input');
    const uploadBtn = document.getElementById('upload-btn');
    const runBtn = document.getElementById('run-btn');
    const logOutput = document.getElementById('log_output');
    const fileNameDisplay = document.getElementById('obf-file-name');
    
    uploadBtn.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) {
            fileNameDisplay.textContent = 'Selected: ' + fileInput.files[0].name;
            fileNameDisplay.style.color = 'var(--j)';
            addLog('[UPLOAD] File selected: ' + fileInput.files[0].name, 'success');
        }
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = 'Selected: ' + e.dataTransfer.files[0].name;
            fileNameDisplay.style.color = 'var(--j)';
            addLog('[UPLOAD] File dropped: ' + e.dataTransfer.files[0].name, 'success');
        }
    });
    
    runBtn.addEventListener('click', () => {
        if (!fileInput.files[0]) {
            alert('Please select a file first!');
            return;
        }

        runBtn.disabled = true;
        runBtn.textContent = 'PROCESSING...';
        addLog('[ENGINE] Initiating virtualization tunnel...', 'accent');

        const fd = new FormData();
        fd.append('file', fileInput.files[0]);

        // Add protection level to form data
        const protectionLevel = document.querySelector('input[name="protection_level"]:checked').value;
        fd.append('protection_level', protectionLevel);
        addLog('[CONFIG] Protection level: ' + protectionLevel.toUpperCase(), 'accent');

        fetch('obfuscate', { method: 'POST', body: fd })
            .then(r => {
                // 检查 HTTP 状态码
                if (!r.ok) {
                    throw new Error('HTTP ' + r.status + ': ' + r.statusText);
                }
                // 尝试解析 JSON
                return r.json().catch(() => {
                    // 如果 JSON 解析失败，可能是服务器返回了 HTML 或纯文本
                    return r.text().then(text => {
                        throw new Error('Non-JSON response: ' + text.substring(0, 200));
                    });
                });
            })
            .then(data => {
                if (data.status === 'success') {
                    addLog('[DONE] Protection applied successfully.', 'success');
                    document.getElementById('user-credits').textContent = data.new_balance;
                    document.getElementById('stat-credits').textContent = data.new_balance;
                    window.location.href = 'download_gate?token=' + data.download_token;
                } else {
                    addLog('[FAIL] ' + data.message, 'error');
                }
            })
            .catch((err) => {
                // 增强的错误日志
                console.error('Obfuscate error:', err);
                addLog('[ERROR] Connection failed: ' + err.message, 'error');
            })
            .finally(() => {
                runBtn.disabled = false;
                runBtn.textContent = 'START ENCRYPTION';
            });
    });
    
    function addLog(msg, type = '') {
        const time = new Date().toLocaleTimeString();
        const typeClass = type === 'accent' ? 'log-accent' : type === 'success' ? 'log-success' : type === 'error' ? 'log-error' : '';
        logOutput.innerHTML += `<div class="log-line"><span class="log-time">[${time}]</span> <span class="${typeClass}">${msg}</span></div>`;
        logOutput.scrollTop = logOutput.scrollHeight;
    }
    
    // =====================================================
    // REDEEM LOGIC
    // =====================================================
    const redeemBtn = document.getElementById('redeem_btn');
    const cdkInput = document.getElementById('cdk_input');
    const resultInfo = document.getElementById('result_info');
    
    redeemBtn.addEventListener('click', () => {
        const val = cdkInput.value.trim();
        if (!val) return;
        
        redeemBtn.disabled = true;
        redeemBtn.textContent = 'VERIFYING...';
        
        const fd = new FormData();
        fd.append('cdk_code', val);
        
        fetch('redeem', { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    resultInfo.textContent = 'SUCCESS: +' + data.details.added_credits + ' Credits!';
                    resultInfo.className = 'redeem-result success';
                    document.getElementById('user-credits').textContent = data.new_total;
                    document.getElementById('stat-credits').textContent = data.new_total;
                    cdkInput.value = '';
                } else {
                    resultInfo.textContent = 'ERROR: ' + data.message;
                    resultInfo.className = 'redeem-result error';
                }
            })
            .catch(() => {
                resultInfo.textContent = 'ERROR: Connection failed';
                resultInfo.className = 'redeem-result error';
            })
            .finally(() => {
                redeemBtn.disabled = false;
                redeemBtn.textContent = 'ACTIVATE';
            });
    });
    
    // =====================================================
    // HOSTING LOGIC
    // =====================================================
    let currentSlotId = '';
    let currentSlotData = null;
    let mySlotsData = [];
    
    // Load slots on page load
    document.addEventListener('DOMContentLoaded', loadMySlots);
    
    function loadMySlots() {
        const container = document.getElementById('hosting-slots-grid');
        if (!container) return;
        
        fetch('get_hosting_slots?v=' + Date.now())
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    mySlotsData = data.slots;
                    document.getElementById('stat-slots').textContent = data.slots.length;
                    
                    if (data.slots.length === 0) {
                        container.innerHTML = '<div class="f-card" style="grid-column: 1/-1; text-align: center; padding: 60px;"><p style="color: var(--g);">No slots found. Purchase one to get started!</p></div>';
                        return;
                    }
                    
                    container.innerHTML = '';
                    data.slots.forEach(slot => {
                        let statusColor = '#10b981';
                        let statusClass = '';
                        let borderClass = '';
                        
                        if (slot.status === 'DISABLED') {
                            statusColor = '#ef4444';
                            statusClass = 'disabled';
                            borderClass = 'status-disabled';
                        } else if (slot.status === 'UNCONFIGURED') {
                            statusColor = '#7c4dff';
                            statusClass = 'unconfigured';
                            borderClass = 'status-unconfigured';
                        }
                        
                        const name = slot.script_name || 'Empty Slot';
                        
                        container.innerHTML += `
                            <div class="hosting-slot-card ${borderClass}">
                                <div class="slot-header">
                                    <svg class="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                    </svg>
                                    <span class="slot-status ${statusClass}" style="background: ${statusColor}">${slot.status}</span>
                                </div>
                                <h3 class="slot-name" title="${name}">${name}</h3>
                                <div class="slot-id">${slot.slot_id}</div>
                                <button class="btn btn-primary manage-slot-btn" data-slot-id="${slot.slot_id}" style="width: 100%; font-size: 12px;">MANAGE HOSTING</button>
                            </div>`;
                    });
                    
                    // Attach event listeners to manage buttons
                    document.querySelectorAll('.manage-slot-btn').forEach(btn => {
                        btn.addEventListener('click', () => openManagePage(btn.dataset.slotId));
                    });
                }
            })
            .catch(err => console.error(err));
    }
    
    // Purchase slot
    document.getElementById('buy-btn').addEventListener('click', async () => {
        const btn = document.getElementById('buy-btn');
        btn.disabled = true;
        btn.textContent = 'VERIFYING CREDITS...';
        
        const fd = new FormData();
        fd.append('action', 'purchase_slot');
        
        try {
            const res = await fetch('hosting_action', { method: 'POST', body: fd });
            const data = await res.json();
            
            if (data.status === 'success') {
                alert('New Hosting Slot Assigned!');
                loadMySlots();
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert('Transaction failed. Check connection.');
        } finally {
            btn.disabled = false;
            btn.textContent = '+ PURCHASE SLOT (2 Credits)';
        }
    });
    
    // Open manage page
    function openManagePage(id) {
        currentSlotId = id;
        currentSlotData = mySlotsData.find(s => s.slot_id === id);
        
        if (!currentSlotData) return;
        
        document.getElementById('manage-slot-id').textContent = 'ID: ' + id;
        document.getElementById('manage-slot-name').textContent = currentSlotData.script_name || 'Unconfigured Slot';
        document.getElementById('script_name_input').value = currentSlotData.script_name || '';
        
        const badge = document.getElementById('status-badge');
        badge.textContent = currentSlotData.status;
        badge.style.color = currentSlotData.status === 'ACTIVE' ? '#10b981' : currentSlotData.status === 'DISABLED' ? '#ef4444' : '#fff';
        
        document.getElementById('vm_obfuscation').checked = currentSlotData.vm_protection == 1;
        document.getElementById('hwid_lock').checked = currentSlotData.hwid_lock == 1;
        document.getElementById('heartbeat_protection').checked = currentSlotData.heartbeat == 1;
        
        if (currentSlotData.status !== 'UNCONFIGURED') {
            document.getElementById('loader-box').textContent = `loadstring(game:HttpGet("https://api.valaxscrub.shop/fetch?id=${id}"))()`;
        } else {
            document.getElementById('loader-box').textContent = '-- Upload script to generate loader --';
        }
        
        updateKillSwitchButtonUI();
        
        document.getElementById('management-page').style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
    
    // Close manage page
    document.getElementById('close-manage-btn').addEventListener('click', () => {
        document.getElementById('management-page').style.display = 'none';
        document.body.style.overflow = 'auto';
        loadMySlots();
    });
    
    // File upload in management
    const sourceDropZone = document.getElementById('source-drop-zone');
    const sourceUpload = document.getElementById('source_upload');
    
    sourceDropZone.addEventListener('click', () => sourceUpload.click());
    
    sourceDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        sourceDropZone.style.borderColor = 'var(--a)';
    });
    
    sourceDropZone.addEventListener('dragleave', () => {
        sourceDropZone.style.borderColor = 'var(--h)';
    });
    
    sourceDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        sourceDropZone.style.borderColor = 'var(--h)';
        if (e.dataTransfer.files[0]) {
            sourceUpload.files = e.dataTransfer.files;
            updateFileNameDisplay(sourceUpload);
        }
    });
    
    sourceUpload.addEventListener('change', () => updateFileNameDisplay(sourceUpload));
    
    function updateFileNameDisplay(input) {
        const display = document.getElementById('file-name-display');
        const nameInput = document.getElementById('script_name_input');
        
        if (input.files && input.files[0]) {
            const fileName = input.files[0].name;
            display.textContent = 'SELECTED: ' + fileName;
            display.style.color = '#10b981';
            display.style.fontWeight = 'bold';
            
            if (nameInput && !nameInput.value) {
                nameInput.value = fileName.replace(/\.[^/.]+$/, '');
            }
        }
    }
    
    // Copy loader
    document.getElementById('copy-loader-btn').addEventListener('click', () => {
        const text = document.getElementById('loader-box').textContent;
        navigator.clipboard.writeText(text);
        alert('Loader copied!');
    });
    
    // Kill switch
    document.getElementById('kill-switch-btn').addEventListener('click', async () => {
        if (!currentSlotId || !currentSlotData) return;
        
        const isActive = currentSlotData.status === 'ACTIVE';
        const action = isActive ? 'DISABLED' : 'ACTIVE';
        
        const msg = isActive 
            ? 'WARNING: This will KICK all users immediately and disable the script.'
            : 'Re-activate this script?';
        
        if (!confirm(msg)) return;
        
        const fd = new URLSearchParams();
        fd.append('action', 'toggle_status');
        fd.append('slot_id', currentSlotId);
        fd.append('target_status', action);
        
        try {
            const res = await fetch('hosting_action', { method: 'POST', body: fd });
            const data = await res.json();
            
            if (data.status === 'success') {
                currentSlotData.status = action;
                updateKillSwitchButtonUI();
                
                const badge = document.getElementById('status-badge');
                badge.textContent = action;
                badge.style.color = action === 'ACTIVE' ? '#10b981' : '#ef4444';
                
                alert(action === 'ACTIVE' ? 'Script is now ONLINE.' : 'Kill-Switch Active.');
            } else {
                alert('Action failed: ' + data.message);
            }
        } catch (e) {
            alert('Network error');
        }
    });
    
    function updateKillSwitchButtonUI() {
        const btn = document.getElementById('kill-switch-btn');
        if (currentSlotData.status === 'ACTIVE') {
            btn.innerHTML = 'KILL-SWITCH Activate';
            btn.style.background = 'var(--k)';
        } else if (currentSlotData.status === 'DISABLED') {
            btn.innerHTML = 'RESTART Script';
            btn.style.background = '#10b981';
        } else {
            btn.innerHTML = 'CONFIGURE First';
            btn.style.background = '#333';
        }
    }
    
    // Delete hosting
    document.getElementById('delete-hosting-btn').addEventListener('click', async () => {
        if (!currentSlotId) return;
        
        const confirmDel = prompt('DANGER ZONE\nType DELETE to erase this hosting slot.');
        if (confirmDel !== 'DELETE') return;
        
        const fd = new URLSearchParams();
        fd.append('action', 'delete_slot');
        fd.append('slot_id', currentSlotId);
        
        try {
            const res = await fetch('hosting_action', { method: 'POST', body: fd });
            const data = await res.json();
            
            if (data.status === 'success') {
                alert('Hosting slot deleted.');
                document.getElementById('close-manage-btn').click();
            } else {
                alert('Delete failed: ' + data.message);
            }
        } catch (e) {
            alert('Network error');
        }
    });
    
    // Deploy config
    document.getElementById('deploy-btn').addEventListener('click', async () => {
        const nameInput = document.getElementById('script_name_input');
        const vmObf = document.getElementById('vm_obfuscation').checked;
        const hwidLock = document.getElementById('hwid_lock').checked;
        const heartbeat = document.getElementById('heartbeat_protection').checked;
        
        if (!currentSlotId) return alert('Error: No slot selected.');
        if (!nameInput.value.trim()) return alert('Please enter a script name.');
        
        const btn = document.getElementById('deploy-btn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'SHIELDING & DEPLOYING...';
        
        const sendData = async (luaContent = null) => {
            const fd = new URLSearchParams();
            fd.append('action', 'update_config');
            fd.append('slot_id', currentSlotId);
            fd.append('script_name', nameInput.value);
            fd.append('vm_obfuscation', vmObf ? '1' : '0');
            fd.append('hwid_lock', hwidLock ? '1' : '0');
            fd.append('heartbeat', heartbeat ? '1' : '0');
            
            if (luaContent !== null) {
                fd.append('lua_content', luaContent);
            }
            
            try {
                const res = await fetch('hosting_action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: fd
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    alert('Settings & Protection Synchronized!');
                    loadMySlots();
                } else {
                    alert('Failed: ' + data.message);
                }
            } catch (error) {
                alert('Connection error.');
            }
        };
        
        if (sourceUpload.files.length > 0) {
            const reader = new FileReader();
            reader.onload = (e) => sendData(e.target.result);
            reader.readAsText(sourceUpload.files[0]);
        } else {
            sendData(null);
        }
        
        btn.disabled = false;
        btn.textContent = originalText;
    });
    
    // Editor functions
    document.getElementById('open-editor-btn').addEventListener('click', () => {
        if (!currentSlotData || !currentSlotData.source_code) {
            alert('No source code found. Upload a file first.');
            return;
        }
        document.getElementById('code-editor-area').value = currentSlotData.source_code;
        document.getElementById('editor-modal').style.display = 'flex';
    });
    
    document.getElementById('close-editor-btn').addEventListener('click', () => {
        document.getElementById('editor-modal').style.display = 'none';
    });
    
    document.getElementById('save-editor-btn').addEventListener('click', () => {
        const newCode = document.getElementById('code-editor-area').value;
        if (!newCode) return alert('Code cannot be empty');
        
        currentSlotData.source_code = newCode;
        document.getElementById('editor-modal').style.display = 'none';
        alert('Code updated! Click DEPLOY to save changes.');
    });
    
    // Download backup
    document.getElementById('download-backup-btn').addEventListener('click', () => {
        if (!currentSlotData || !currentSlotData.source_code) {
            alert('No source code available.');
            return;
        }
        
        const a = document.createElement('a');
        const file = new Blob([currentSlotData.source_code], { type: 'text/plain' });
        a.href = URL.createObjectURL(file);
        a.download = (currentSlotData.script_name || 'script_backup') + '.lua';
        a.click();
    });
    
    // =====================================================
    // MOBILE MENU
    // =====================================================
    const mobileMenu = document.querySelector('.mobile-menu');
    const mobileNav = document.querySelector('.mobile-nav');
    
    if (mobileMenu) {
        mobileMenu.addEventListener('click', () => {
            mobileMenu.classList.toggle('active');
            if (mobileNav) mobileNav.classList.toggle('active');
        });
    }
    
    // Initialize mobile nav if not exists
    if (!document.querySelector('.mobile-nav') && window.innerWidth <= 1024) {
        const nav = document.createElement('nav');
        nav.className = 'mobile-nav';
        nav.innerHTML = `
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="${document.querySelector('.btn-primary-nav')?.href || '#'}">Connect Discord</a>
        `;
        document.querySelector('.header').after(nav);
        
        document.querySelector('.mobile-menu').addEventListener('click', () => {
            nav.classList.toggle('active');
        });
    }
    
    // =====================================================
    // SCROLL ANIMATIONS
    // =====================================================
    const revealElements = document.querySelectorAll('.reveal');
    
    function checkReveal() {
        revealElements.forEach(el => {
            const windowHeight = window.innerHeight;
            const elementTop = el.getBoundingClientRect().top;
            const revealPoint = 150;
            
            if (elementTop < windowHeight - revealPoint) {
                el.classList.add('active');
            }
        });
    }
    
    window.addEventListener('scroll', checkReveal);
    checkReveal();
    </script>
</body>
</html>
