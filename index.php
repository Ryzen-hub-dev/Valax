<?php
// VALAX - Main Dashboard Page v2
// Dark Blue + Black Theme with Full Functionality

require 'config.php';

$is_logged_in = isset($_SESSION['user_id']) && !empty($_SESSION['user_id']);
$user = null;
$username = 'Guest';
$credits = '0';
$slots_count = 0;
$groups_count = 0;
$user_avatar = '';

if ($is_logged_in && isset($pdo) && $pdo !== null) {
    try {
        $stmt = $pdo->prepare("SELECT * FROM `users` WHERE discord_id = ?");
        $stmt->execute([$_SESSION['user_id']]);
        $user = $stmt->fetch();
        if ($user) {
            $username = htmlspecialchars($user['username']);
            $credits = htmlspecialchars(isset($user['obf_credits']) ? $user['obf_credits'] : '0');
            $user_avatar = htmlspecialchars(isset($user['avatar']) ? $user['avatar'] : '');
        }
        
        // Get slots count
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM `hosting_slots` WHERE owner_id = ? AND status != 'deleted'");
        $stmt->execute([$_SESSION['user_id']]);
        $slots_count = $stmt->fetchColumn();
        
        // Get groups count
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM `group_members` WHERE user_discord_id = ?");
        $stmt->execute([$_SESSION['user_id']]);
        $groups_count = $stmt->fetchColumn();
    } catch (PDOException $e) {
        error_log("Dashboard query error: " . $e->getMessage());
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VALAX | Premium Lua Protection & Management</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="main.css">
    <style>
        /* =====================================================
           COLOR VARIABLES - Dark Blue + Black Theme
           ===================================================== */
        :root {
            --bg-primary: #030712;
            --bg-secondary: #0a1628;
            --bg-card: #0f2744;
            --bg-card-hover: #143a5c;
            --accent-blue: #3b82f6;
            --accent-blue-light: #60a5fa;
            --accent-blue-dark: #1d4ed8;
            --accent-cyan: #06b6d4;
            --accent-teal: #14b8a6;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: rgba(59, 130, 246, 0.2);
            --border-hover: rgba(59, 130, 246, 0.4);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: var(--bg-primary);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
            line-height: 1.6;
        }

        /* =====================================================
           TOP NAVIGATION
           ===================================================== */
        .topbar {
            background: linear-gradient(180deg, var(--bg-secondary) 0%, transparent 100%);
            backdrop-filter: blur(20px);
            position: fixed;
            width: 94%;
            max-width: 1400px;
            left: 50%;
            transform: translateX(-50%);
            top: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 32px;
            height: 70px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
            z-index: 1000;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        .navLeft {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo {
            height: 40px;
            width: auto;
            border-radius: 10px;
        }

        .brandText {
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-cyan) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }

        .navCenter ul {
            list-style: none;
            display: flex;
            gap: 8px;
        }

        .navCenter ul li {
            padding: 10px 20px;
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 15px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .navCenter ul li a {
            text-decoration: none;
            color: inherit;
        }

        .navCenter ul li:hover, .navCenter ul li.active, .navCenter ul li a.active {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue-light);
        }

        .navRight {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .creditsDisplay {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 12px;
        }

        .creditsDisplay span:first-child {
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 600;
            letter-spacing: 0.1em;
        }

        .creditsDisplay span:last-child {
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
        }

        .userAvatar {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 16px;
            border: 2px solid var(--accent-blue);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .userAvatar:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
        }

        .userAvatar img {
            width: 100%;
            height: 100%;
            border-radius: 10px;
            object-fit: cover;
        }

        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            font-family: 'Inter', sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btnPrimary {
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-blue-dark) 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        }

        .btnPrimary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
        }

        .btnSecondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        .btnSecondary:hover {
            background: rgba(59, 130, 246, 0.1);
            border-color: var(--accent-blue);
        }

        .btnCyan {
            background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-teal) 100%);
            color: white;
        }

        .btnCyan:hover {
            box-shadow: 0 8px 25px rgba(6, 182, 212, 0.4);
            transform: translateY(-2px);
        }

        .btnSm {
            padding: 8px 16px;
            font-size: 13px;
        }

        .btnLg {
            padding: 16px 32px;
            font-size: 16px;
        }

        /* =====================================================
           HERO SECTION
           ===================================================== */
        .heroSection {
            min-height: 100vh;
            padding: 140px 48px 80px;
            position: relative;
            overflow: hidden;
        }

        .heroSection::before {
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 1000px;
            height: 600px;
            background: radial-gradient(ellipse at center, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
            pointer-events: none;
        }

        .heroContent {
            max-width: 900px;
            margin: 0 auto;
            text-align: center;
            position: relative;
            z-index: 1;
        }

        .heroBadge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
            color: var(--accent-blue-light);
            margin-bottom: 32px;
        }

        .heroBadge .dot {
            width: 8px;
            height: 8px;
            background: var(--accent-cyan);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .heroTitle {
            font-size: 64px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 24px;
            letter-spacing: -2px;
        }

        .heroTitle .gradient {
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-cyan) 50%, var(--accent-teal) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .heroDescription {
            font-size: 20px;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 48px;
            line-height: 1.7;
        }

        .heroButtons {
            display: flex;
            gap: 16px;
            justify-content: center;
        }

        /* =====================================================
           STATS SECTION
           ===================================================== */
        .statsSection {
            padding: 60px 48px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
        }

        .statsGrid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .statCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .statCard:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-4px);
        }

        .statIcon {
            width: 64px;
            height: 64px;
            margin: 0 auto 20px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }

        .statIcon.blue { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
        .statIcon.cyan { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); }
        .statIcon.teal { background: rgba(20, 184, 166, 0.15); color: var(--accent-teal); }

        .statValue {
            font-size: 42px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }

        .statValue.blue { color: var(--accent-blue-light); }
        .statValue.cyan { color: var(--accent-cyan); }

        .statLabel {
            font-size: 14px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        /* =====================================================
           FEATURES SECTION
           ===================================================== */
        .featuresSection {
            padding: 100px 48px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .sectionHeader {
            text-align: center;
            margin-bottom: 60px;
        }

        .sectionHeader h2 {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 16px;
            letter-spacing: -1px;
        }

        .sectionHeader p {
            font-size: 18px;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto;
        }

        .featureGrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 32px;
        }

        .featureCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 40px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .featureCard:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .featureIcon {
            width: 72px;
            height: 72px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin-bottom: 24px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%);
            color: var(--accent-blue);
            transition: all 0.3s ease;
        }

        .featureCard:hover .featureIcon {
            transform: scale(1.1) rotate(5deg);
        }

        .featureCard h3 {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 12px;
        }

        .featureCard p {
            font-size: 15px;
            color: var(--text-secondary);
            line-height: 1.6;
        }

        /* =====================================================
           GROUP DEMO SECTION
           ===================================================== */
        .groupSection {
            padding: 100px 48px;
            background: var(--bg-secondary);
        }

        .groupContainer {
            max-width: 1400px;
            margin: 0 auto;
        }

        .groupBanner {
            background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-hover) 100%);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 60px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 60px;
            align-items: center;
            position: relative;
            overflow: hidden;
        }

        .groupBanner::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan), var(--accent-teal));
        }

        .groupGifArea {
            aspect-ratio: 16/10;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
        }

        .groupGifArea i {
            font-size: 48px;
            margin-bottom: 16px;
            color: var(--accent-blue);
        }

        .groupFeatures {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .groupFeatureItem {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 20px;
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            transition: all 0.3s ease;
        }

        .groupFeatureItem:hover {
            background: rgba(59, 130, 246, 0.1);
            border-color: var(--accent-blue);
            transform: translateX(8px);
        }

        .groupFeatureIcon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: rgba(59, 130, 246, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-blue);
            font-size: 20px;
        }

        .groupFeatureContent h4 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .groupFeatureContent p {
            font-size: 13px;
            color: var(--text-muted);
            margin: 0;
        }

        /* =====================================================
           HOSTING SECTION
           ===================================================== */
        .hostingSection {
            padding: 100px 48px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .slotsGrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            margin-bottom: 60px;
        }

        .slotCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 28px;
            position: relative;
            transition: all 0.3s ease;
        }

        .slotCard::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            border-radius: 16px 0 0 16px;
        }

        .slotCard.active::before { background: #22c55e; }
        .slotCard.inactive::before { background: #f59e0b; }
        .slotCard.secure::before { background: var(--accent-blue); }

        .slotCard:hover {
            background: var(--bg-card-hover);
            transform: translateY(-4px);
        }

        .slotHeader {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }

        .slotTitle {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .slotId {
            font-size: 12px;
            color: var(--accent-blue);
            font-family: 'JetBrains Mono', monospace;
        }

        .slotBadge {
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .slotBadge.active {
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
        }

        .slotBadge.inactive {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }

        .slotInfo {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 20px;
        }

        .slotInfoRow {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
        }

        .slotInfoRow .label { color: var(--text-muted); }
        .slotInfoRow .value { color: var(--text-primary); font-weight: 600; }

        .slotActions {
            display: flex;
            gap: 8px;
        }

        .slotActions .btn {
            flex: 1;
        }

        /* =====================================================
           PLANS SECTION
           ===================================================== */
        .plansSection {
            padding: 100px 48px;
            background: var(--bg-secondary);
        }

        .plansContainer {
            max-width: 1200px;
            margin: 0 auto;
        }

        .plansGrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 32px;
        }

        .planCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 40px;
            position: relative;
            transition: all 0.3s ease;
        }

        .planCard:hover {
            transform: translateY(-8px);
            border-color: var(--accent-blue);
        }

        .planCard.popular {
            border-color: var(--accent-blue);
            background: linear-gradient(180deg, rgba(59, 130, 246, 0.1) 0%, var(--bg-card) 100%);
        }

        .planBadge {
            position: absolute;
            top: -14px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            color: white;
            padding: 6px 20px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }

        .planName {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .planDesc {
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 24px;
        }

        .planPrice {
            font-size: 48px;
            font-weight: 800;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }

        .planPrice .unit {
            font-size: 16px;
            color: var(--text-muted);
            font-weight: 400;
        }

        .planFeatures {
            list-style: none;
            padding: 0;
            margin: 24px 0;
        }

        .planFeatures li {
            padding: 12px 0;
            font-size: 14px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border-color);
        }

        .planFeatures li:last-child { border-bottom: none; }
        .planFeatures li i { color: #22c55e; }

        .planCard .btn { width: 100%; margin-top: 16px; }

        /* =====================================================
           CREDITS SECTION
           ===================================================== */
        .creditsSection {
            padding: 100px 48px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .creditsBalance {
            background: linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(20, 184, 166, 0.1) 100%);
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 24px;
            padding: 60px;
            text-align: center;
            margin-bottom: 48px;
        }

        .creditsValue {
            font-size: 80px;
            font-weight: 800;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
            text-shadow: 0 0 40px rgba(6, 182, 212, 0.3);
        }

        .creditsLabel {
            font-size: 14px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.2em;
            margin-top: 8px;
        }

        .creditPacks {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
        }

        .creditPack {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .creditPack:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent-cyan);
            transform: translateY(-4px);
        }

        .creditPackAmount {
            font-size: 36px;
            font-weight: 800;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }

        .creditPackPrice {
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 16px;
        }

        /* =====================================================
           REDEEM SECTION
           ===================================================== */
        .redeemSection {
            padding: 100px 48px;
            background: var(--bg-secondary);
        }

        .redeemContainer {
            max-width: 600px;
            margin: 0 auto;
            text-align: center;
        }

        .redeemBox {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 60px;
        }

        .redeemInput {
            width: 100%;
            padding: 18px 24px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 16px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.2s ease;
        }

        .redeemInput:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
        }

        .redeemInput::placeholder {
            color: var(--text-muted);
        }

        /* =====================================================
           PROFILE SECTION
           ===================================================== */
        .profileSection {
            padding: 100px 48px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .profileGrid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 48px;
        }

        .profileCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 32px;
        }

        .profileHeader {
            display: flex;
            align-items: center;
            gap: 20px;
            padding-bottom: 24px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .profileAvatar {
            width: 72px;
            height: 72px;
            border-radius: 18px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: 700;
        }

        .profileAvatar img {
            width: 100%;
            height: 100%;
            border-radius: 16px;
            object-fit: cover;
        }

        .profileName {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .profileStatus {
            font-size: 13px;
            color: #22c55e;
            font-weight: 600;
        }

        .profileItem {
            display: flex;
            justify-content: space-between;
            padding: 14px 0;
            border-bottom: 1px solid var(--border-color);
        }

        .profileItem:last-child { border-bottom: none; }
        .profileItem .label { color: var(--text-muted); }
        .profileItem .value { color: var(--text-primary); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .profileItem .value.cyan { color: var(--accent-cyan); }

        .securityGrid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .securityItem {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }

        .securityInfo {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .securityIcon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: rgba(59, 130, 246, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-blue);
            font-size: 20px;
        }

        .securityText h4 {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 2px;
        }

        .securityText span {
            font-size: 12px;
            color: var(--text-muted);
        }

        .securityText span.enabled { color: #22c55e; }
        .securityText span.disabled { color: #f59e0b; }

        /* =====================================================
           BLOG SECTION
           ===================================================== */
        .blogSection {
            padding: 100px 48px;
            background: var(--bg-secondary);
        }

        .blogContainer {
            max-width: 1400px;
            margin: 0 auto;
        }

        .blogGrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 32px;
        }

        .blogCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .blogCard:hover {
            transform: translateY(-8px);
            border-color: var(--border-hover);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .blogImage {
            width: 100%;
            height: 200px;
            background: linear-gradient(135deg, var(--bg-card-hover), var(--bg-secondary));
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-blue);
            font-size: 48px;
        }

        .blogContent {
            padding: 28px;
        }

        .blogMeta {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }

        .blogTag {
            padding: 4px 12px;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-blue);
        }

        .blogDate {
            font-size: 12px;
            color: var(--text-muted);
        }

        .blogCard h3 {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.4;
        }

        .blogCard h3:hover {
            color: var(--accent-blue-light);
        }

        .blogExcerpt {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin-bottom: 16px;
        }

        .blogLink {
            font-size: 14px;
            font-weight: 600;
            color: var(--accent-blue);
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .blogLink:hover {
            color: var(--accent-blue-light);
            gap: 12px;
        }

        /* =====================================================
           PRICING SECTION
           ===================================================== */
        .pricingSection {
            padding: 100px 48px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .pricingGrid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
        }

        .priceCard {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 36px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .priceCard:hover {
            transform: translateY(-8px);
            border-color: var(--accent-blue);
        }

        .priceCard.popular {
            border-color: var(--accent-blue);
            background: linear-gradient(180deg, rgba(59, 130, 246, 0.1) 0%, var(--bg-card) 100%);
        }

        .priceCard h3 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .priceCard .subtitle {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 24px;
        }

        .priceAmount {
            font-size: 36px;
            font-weight: 800;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 24px;
        }

        .priceAmount .period {
            font-size: 14px;
            color: var(--text-muted);
            font-weight: 400;
        }

        .priceFeatures {
            list-style: none;
            padding: 0;
            margin: 0 0 24px 0;
            text-align: left;
        }

        .priceFeatures li {
            padding: 10px 0;
            font-size: 13px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .priceFeatures li i { color: #22c55e; font-size: 12px; }

        .priceCard .btn { width: 100%; }

        /* =====================================================
           FOOTER
           ===================================================== */
        .footer {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 80px 48px 40px;
        }

        .footerContainer {
            max-width: 1400px;
            margin: 0 auto;
        }

        .footerTop {
            display: flex;
            justify-content: space-between;
            margin-bottom: 60px;
        }

        .footerBrand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .footerLinks {
            display: flex;
            gap: 80px;
        }

        .linkColumn h4 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 20px;
        }

        .linkColumn ul {
            list-style: none;
            padding: 0;
        }

        .linkColumn ul li {
            margin-bottom: 12px;
        }

        .linkColumn ul li a {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 14px;
            transition: color 0.2s ease;
        }

        .linkColumn ul li a:hover {
            color: var(--accent-blue);
        }

        .footerBottom {
            padding-top: 40px;
            border-top: 1px solid var(--border-color);
            text-align: center;
        }

        .footerBottom p {
            color: var(--text-muted);
            font-size: 14px;
        }

        /* =====================================================
           MODALS
           ===================================================== */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 10000;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }

        .modal.active { display: flex; }

        .modalContent {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
        }

        .modalHeader {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .modalHeader h3 {
            font-size: 20px;
            font-weight: 700;
        }

        .modalClose {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s ease;
        }

        .modalClose:hover {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }

        .modalBody {
            padding: 24px;
        }

        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 32px;
            right: 32px;
            padding: 16px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease;
            z-index: 99999;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        .toast.success { border-color: rgba(34, 197, 94, 0.3); }
        .toast.error { border-color: rgba(239, 68, 68, 0.3); }

        .toast i { font-size: 20px; }
        .toast.success i { color: #22c55e; }
        .toast.error i { color: #ef4444; }

        /* =====================================================
           RESPONSIVE
           ===================================================== */
        @media (max-width: 1200px) {
            .featureGrid, .blogGrid, .plansGrid { grid-template-columns: repeat(2, 1fr); }
            .slotsGrid, .creditPacks { grid-template-columns: repeat(2, 1fr); }
            .pricingGrid { grid-template-columns: repeat(2, 1fr); }
            .groupBanner { grid-template-columns: 1fr; }
            .profileGrid { grid-template-columns: 1fr; }
            .securityGrid { grid-template-columns: 1fr; }
            .footerTop { flex-direction: column; gap: 40px; }
            .footerLinks { flex-wrap: wrap; gap: 40px; }
        }

        @media (max-width: 768px) {
            .heroTitle { font-size: 40px; }
            .sectionHeader h2 { font-size: 32px; }
            .statsGrid, .featureGrid, .slotsGrid, .creditPacks, .blogGrid, .plansGrid, .pricingGrid { grid-template-columns: 1fr; }
            .heroButtons { flex-direction: column; }
            .topbar { width: 98%; padding: 0 16px; }
            .navCenter { display: none; }
            .creditsDisplay span:first-child { display: none; }
        }

        /* Hamburger Menu */
        .menuToggle {
            display: none;
            background: none;
            border: none;
            font-size: 24px;
            color: var(--text-primary);
            cursor: pointer;
        }

        @media (max-width: 768px) {
            .menuToggle { display: block; }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="topbar">
        <div class="navLeft">
            <img src="logo.png" alt="VALAX" class="logo" onerror="this.style.display='none'">
            <span class="brandText">VALAX</span>
        </div>
        
        <div class="navCenter">
            <ul>
                <li class="active"><a href="#hero">Home</a></li>
                <li><a href="features">Features</a></li>
                <li><a href="pricing">Pricing</a></li>
                <li><a href="blog">Blog</a></li>
                <li><a href="documentation">Docs</a></li>
            </ul>
        </div>
        
        <div class="navRight">
            <button class="menuToggle"><i class="fas fa-bars"></i></button>
            <?php if ($is_logged_in): ?>
            <div class="creditsDisplay">
                <span>CREDITS</span>
                <span><?php echo $credits; ?></span>
            </div>
            <div class="userAvatar" id="userMenuBtn">
                <?php if ($user_avatar): ?>
                <img src="<?php echo $user_avatar; ?>" alt="Avatar">
                <?php else: ?>
                <?php echo strtoupper(substr($username, 0, 1)); ?>
                <?php endif; ?>
            </div>
            <?php else: ?>
            <button class="btn btnSecondary" onclick="showToast('Redirecting to login...', 'success')">Sign In</button>
            <button class="btn btnPrimary" onclick="window.location.href='<?php echo isset($auth_url) ? htmlspecialchars($auth_url) : '#'; ?>'">
                <i class="fab fa-discord"></i> Login with Discord
            </button>
            <?php endif; ?>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="heroSection" id="hero">
        <div class="heroContent">
            <div class="heroBadge">
                <span class="dot"></span>
                Next-Gen Protection Platform
            </div>
            <h1 class="heroTitle">
                Secure Your Lua<br>
                Scripts with <span class="gradient">VALAX</span>
            </h1>
            <p class="heroDescription">
                Advanced Obfuscation & Protection for Developers who demand the absolute best in security and performance. Military-grade encryption meets seamless hosting.
            </p>
            <div class="heroButtons">
                <button class="btn btnPrimary btnLg" onclick="scrollToSection('pricing')">
                    <i class="fas fa-rocket"></i> Get Started
                </button>
                <button class="btn btnSecondary btnLg" onclick="scrollToSection('features')">
                    <i class="fas fa-play"></i> Learn More
                </button>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="statsSection">
        <div class="statsGrid">
            <div class="statCard">
                <div class="statIcon blue"><i class="fas fa-coins"></i></div>
                <div class="statValue blue"><?php echo $credits; ?></div>
                <div class="statLabel">Credits Available</div>
            </div>
            <div class="statCard">
                <div class="statIcon cyan"><i class="fas fa-cloud"></i></div>
                <div class="statValue"><?php echo $slots_count; ?></div>
                <div class="statLabel">Active Slots</div>
            </div>
            <div class="statCard">
                <div class="statIcon teal"><i class="fas fa-users"></i></div>
                <div class="statValue"><?php echo $groups_count; ?></div>
                <div class="statLabel">Groups</div>
            </div>
            <div class="statCard">
                <div class="statIcon blue"><i class="fas fa-shield-halved"></i></div>
                <div class="statValue cyan">V5.0</div>
                <div class="statLabel">Engine Version</div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="featuresSection" id="features">
        <div class="sectionHeader">
            <h2>Everything You Need to <span class="gradient">Protect</span></h2>
            <p>Comprehensive tools for script protection, hosting, and monetization</p>
        </div>
        
        <div class="featureGrid">
            <div class="featureCard" onclick="scrollToSection('hosting')">
                <div class="featureIcon"><i class="fas fa-cloud"></i></div>
                <h3>Cloud Hosting</h3>
                <p>Deploy and manage your protected scripts on military-grade infrastructure with 99.9% uptime guarantee.</p>
            </div>
            <div class="featureCard" onclick="scrollToSection('credits')">
                <div class="featureIcon"><i class="fas fa-coins"></i></div>
                <h3>Credits System</h3>
                <p>Flexible credit system for obfuscation and hosting. Purchase what you need, when you need it.</p>
            </div>
            <div class="featureCard" onclick="scrollToSection('redeem')">
                <div class="featureIcon"><i class="fas fa-key"></i></div>
                <h3>License Keys</h3>
                <p>Generate unlimited authentication keys with HWID binding, heartbeat, and kill switch support.</p>
            </div>
            <div class="featureCard" onclick="scrollToSection('groups')">
                <div class="featureIcon"><i class="fas fa-users"></i></div>
                <h3>Team Groups</h3>
                <p>Collaborate with your team using shared slots, pooled credits, and granular permissions.</p>
            </div>
            <div class="featureCard">
                <div class="featureIcon"><i class="fas fa-shield-halved"></i></div>
                <h3>Advanced Obfuscation</h3>
                <p>Military-grade virtualization technology that makes your scripts virtually impossible to reverse engineer.</p>
            </div>
            <div class="featureCard">
                <div class="featureIcon"><i class="fas fa-globe"></i></div>
                <h3>Region Lock</h3>
                <p>Restrict access by country to prevent global leak distribution and protect your revenue.</p>
            </div>
        </div>
    </section>

    <!-- Group Section -->
    <section class="groupSection" id="groups">
        <div class="groupContainer">
            <div class="sectionHeader">
                <h2>Group <span class="gradient">Management</span></h2>
                <p>Collaborate with your team using powerful group features</p>
            </div>

            <div class="groupBanner">
                <div class="groupGifArea" id="groupGifArea">
                    <img id="groupGif" src="group.gif" alt="Group Demo" 
                         style="width:100%;height:100%;object-fit:cover;display:none;">
                    <div id="groupGifFallback" style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;height:100%;">
                        <i class="fas fa-users" style="font-size:64px;margin-bottom:12px;"></i>
                        <span>Group Demo</span>
                        <span style="font-size:12px;color:var(--text-muted);">(group.gif)</span>
                    </div>
                </div>

                <div class="groupFeatures">
                    <div class="groupFeatureItem">
                        <div class="groupFeatureIcon"><i class="fas fa-user-shield"></i></div>
                        <div class="groupFeatureContent">
                            <h4>Role Management</h4>
                            <p>Owner, Admin, or Member roles with granular permissions</p>
                        </div>
                    </div>
                    <div class="groupFeatureItem">
                        <div class="groupFeatureIcon"><i class="fas fa-share-alt"></i></div>
                        <div class="groupFeatureContent">
                            <h4>Invite System</h4>
                            <p>Generate invite links with usage limits and expiration</p>
                        </div>
                    </div>
                    <div class="groupFeatureItem">
                        <div class="groupFeatureIcon"><i class="fas fa-credit-card"></i></div>
                        <div class="groupFeatureContent">
                            <h4>Shared Credits</h4>
                            <p>Pool credits with controlled spending access</p>
                        </div>
                    </div>
                    <div class="groupFeatureItem">
                        <div class="groupFeatureIcon"><i class="fas fa-server"></i></div>
                        <div class="groupFeatureContent">
                            <h4>Shared Slots</h4>
                            <p>Share hosting slots across the group</p>
                        </div>
                    </div>
                    <div class="groupFeatureItem">
                        <div class="groupFeatureIcon"><i class="fas fa-crown"></i></div>
                        <div class="groupFeatureContent">
                            <h4>Ownership Transfer</h4>
                            <p>Full control to transfer ownership when needed</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Hosting Section -->
    <section class="hostingSection" id="hosting">
        <div class="sectionHeader">
            <h2><span class="gradient">Aegis</span> Cloud Hosting</h2>
            <p>Deploy and manage your protected scripts on military-grade infrastructure</p>
        </div>

        <div class="slotsGrid">
            <div class="slotCard active">
                <div class="slotHeader">
                    <div>
                        <div class="slotTitle">Script Loader v2.1</div>
                        <div class="slotId">VX-PR***-8K2M</div>
                    </div>
                    <span class="slotBadge active">Active</span>
                </div>
                <div class="slotInfo">
                    <div class="slotInfoRow">
                        <span class="label">Owner</span>
                        <span class="value">You</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">Created</span>
                        <span class="value">2026-04-15</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">VM Protection</span>
                        <span class="value">Enabled</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">HWID Lock</span>
                        <span class="value">Enabled</span>
                    </div>
                </div>
                <div class="slotActions">
                    <button class="btn btnPrimary btnSm" onclick="openModal('slotManage')">Manage</button>
                    <button class="btn btnSecondary btnSm" onclick="copyToClipboard('VX-PR***-8K2M')">Copy</button>
                </div>
            </div>

            <div class="slotCard secure">
                <div class="slotHeader">
                    <div>
                        <div class="slotTitle">Premium Tools</div>
                        <div class="slotId">VX-SE***-4P9L</div>
                    </div>
                    <span class="slotBadge active">Active</span>
                </div>
                <div class="slotInfo">
                    <div class="slotInfoRow">
                        <span class="label">Owner</span>
                        <span class="value">DevTeam</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">Created</span>
                        <span class="value">2026-04-10</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">VM Protection</span>
                        <span class="value">Enabled</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">HWID Lock</span>
                        <span class="value">Enabled</span>
                    </div>
                </div>
                <div class="slotActions">
                    <button class="btn btnPrimary btnSm" onclick="openModal('slotManage')">Manage</button>
                    <button class="btn btnSecondary btnSm" onclick="copyToClipboard('VX-SE***-4P9L')">Copy</button>
                </div>
            </div>

            <div class="slotCard inactive">
                <div class="slotHeader">
                    <div>
                        <div class="slotTitle">Beta Features</div>
                        <div class="slotId">VX-BT***-7H3N</div>
                    </div>
                    <span class="slotBadge inactive">Inactive</span>
                </div>
                <div class="slotInfo">
                    <div class="slotInfoRow">
                        <span class="label">Owner</span>
                        <span class="value">You</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">Created</span>
                        <span class="value">2026-04-08</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">VM Protection</span>
                        <span class="value">Disabled</span>
                    </div>
                    <div class="slotInfoRow">
                        <span class="label">HWID Lock</span>
                        <span class="value">Enabled</span>
                    </div>
                </div>
                <div class="slotActions">
                    <button class="btn btnPrimary btnSm" onclick="openModal('slotManage')">Manage</button>
                    <button class="btn btnSecondary btnSm" onclick="copyToClipboard('VX-BT***-7H3N')">Copy</button>
                </div>
            </div>
        </div>

        <!-- Plans -->
        <div class="sectionHeader" style="margin-top:60px;">
            <h2>Hosting <span class="gradient">Plans</span></h2>
            <p>Choose the perfect plan for your hosting needs</p>
        </div>

        <div class="plansGrid">
            <div class="planCard">
                <div class="planName">Starter</div>
                <div class="planDesc">1 Cloud Slot</div>
                <div class="planPrice">30<span class="unit">/mo</span></div>
                <ul class="planFeatures">
                    <li><i class="fas fa-check"></i> 1 Slot</li>
                    <li><i class="fas fa-check"></i> VM Protection</li>
                    <li><i class="fas fa-check"></i> HWID Lock</li>
                    <li><i class="fas fa-check"></i> 99.9% Uptime</li>
                </ul>
                <button class="btn btnSecondary" onclick="selectPlan('starter')">Get Started</button>
            </div>

            <div class="planCard popular">
                <span class="planBadge">POPULAR</span>
                <div class="planName">Professional</div>
                <div class="planDesc">3 Cloud Slots</div>
                <div class="planPrice">50<span class="unit">/mo</span></div>
                <ul class="planFeatures">
                    <li><i class="fas fa-check"></i> 3 Slots</li>
                    <li><i class="fas fa-check"></i> VM Protection</li>
                    <li><i class="fas fa-check"></i> HWID Lock</li>
                    <li><i class="fas fa-check"></i> Priority Support</li>
                </ul>
                <button class="btn btnPrimary" onclick="selectPlan('professional')">Get Started</button>
            </div>

            <div class="planCard">
                <div class="planName">Enterprise</div>
                <div class="planDesc">10 Cloud Slots</div>
                <div class="planPrice">100<span class="unit">/mo</span></div>
                <ul class="planFeatures">
                    <li><i class="fas fa-check"></i> 10 Slots</li>
                    <li><i class="fas fa-check"></i> VM Protection</li>
                    <li><i class="fas fa-check"></i> HWID Lock</li>
                    <li><i class="fas fa-check"></i> Dedicated Support</li>
                </ul>
                <button class="btn btnSecondary" onclick="selectPlan('enterprise')">Contact Us</button>
            </div>
        </div>
    </section>

    <!-- Credits Section -->
    <section class="creditsSection" id="credits">
        <div class="sectionHeader">
            <h2>Credits <span class="gradient">Balance</span></h2>
            <p>Manage your credits and purchase more for obfuscation and hosting</p>
        </div>

        <div class="creditsBalance">
            <div class="creditsValue"><?php echo $credits; ?></div>
            <div class="creditsLabel">Available Credits</div>
        </div>

        <div class="creditPacks">
            <div class="creditPack" onclick="purchaseCredits(50)">
                <div class="creditPackAmount">50</div>
                <div class="creditPackPrice">Basic Pack - $5</div>
                <button class="btn btnCyan btnSm">Buy Now</button>
            </div>
            <div class="creditPack" onclick="purchaseCredits(150)">
                <div class="creditPackAmount">150</div>
                <div class="creditPackPrice">Value Pack - $12</div>
                <button class="btn btnCyan btnSm">Buy Now</button>
            </div>
            <div class="creditPack" onclick="purchaseCredits(300)">
                <div class="creditPackAmount">300</div>
                <div class="creditPackPrice">Pro Pack - $20</div>
                <button class="btn btnCyan btnSm">Buy Now</button>
            </div>
            <div class="creditPack" onclick="purchaseCredits(500)">
                <div class="creditPackAmount">500</div>
                <div class="creditPackPrice">Enterprise - $30</div>
                <button class="btn btnCyan btnSm">Buy Now</button>
            </div>
        </div>
    </section>

    <!-- Redeem Section -->
    <section class="redeemSection" id="redeem">
        <div class="redeemContainer">
            <div class="sectionHeader">
                <h2>Redeem <span class="gradient">License Key</span></h2>
                <p>Activate credits with VALAX license codes instantly</p>
            </div>

            <div class="redeemBox">
                <input type="text" id="redeemCode" class="redeemInput" placeholder="VALAX-XXXX-XXXX-XXXX">
                <button class="btn btnPrimary btnLg" onclick="redeemCode()" style="width:100%;">
                    <i class="fas fa-key"></i> ACTIVATE
                </button>
            </div>
        </div>
    </section>

    <!-- Blog Section -->
    <section class="blogSection" id="blog">
        <div class="blogContainer">
            <div class="sectionHeader">
                <h2>Latest <span class="gradient">Updates</span></h2>
                <p>Stay informed with our latest news and announcements</p>
                <a href="blog" class="btn btnSecondary" style="margin-top:20px;">View All Posts <i class="fas fa-arrow-right"></i></a>
            </div>

            <div class="blogGrid">
                <?php
                // Get latest blog posts for dashboard preview
                $dashboardPosts = [];
                try {
                    $stmt = $pdo->query("SELECT * FROM blog_posts WHERE published = 1 ORDER BY created_at DESC LIMIT 3");
                    $dashboardPosts = $stmt->fetchAll(PDO::FETCH_ASSOC);
                } catch (Exception $e) {}
                ?>
                <?php if (!empty($dashboardPosts)): ?>
                    <?php foreach ($dashboardPosts as $post): ?>
                    <div class="blogCard">
                        <div class="blogImage"><i class="fas fa-<?php echo $post['category'] === 'Security' ? 'lock' : ($post['category'] === 'Features' ? 'star' : ($post['category'] === 'Tutorials' ? 'book' : 'newspaper')); ?>"></i></div>
                        <div class="blogContent">
                            <div class="blogMeta">
                                <span class="blogTag"><?php echo htmlspecialchars($post['category']); ?></span>
                                <span class="blogDate"><?php echo date('M d, Y', strtotime($post['created_at'])); ?></span>
                            </div>
                            <h3><?php echo htmlspecialchars($post['title']); ?></h3>
                            <p class="blogExcerpt"><?php echo htmlspecialchars($post['excerpt']); ?></p>
                            <a href="blog" class="blogLink">Read More <i class="fas fa-arrow-right"></i></a>
                        </div>
                    </div>
                    <?php endforeach; ?>
                <?php else: ?>
                <!-- Default static blog posts -->
                <div class="blogCard">
                    <div class="blogImage"><i class="fas fa-shield-halved"></i></div>
                    <div class="blogContent">
                        <div class="blogMeta">
                            <span class="blogTag">Security</span>
                            <span class="blogDate">April 15, 2026</span>
                        </div>
                        <h3>New Obfuscation Engine V5.0 Released</h3>
                        <p class="blogExcerpt">We've completely rebuilt our protection engine with advanced virtualization technology...</p>
                        <a href="blog" class="blogLink">Read More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>

                <div class="blogCard">
                    <div class="blogImage"><i class="fas fa-users"></i></div>
                    <div class="blogContent">
                        <div class="blogMeta">
                            <span class="blogTag">Features</span>
                            <span class="blogDate">April 10, 2026</span>
                        </div>
                        <h3>Introducing Team Groups</h3>
                        <p class="blogExcerpt">Collaborate with your team using shared slots, pooled credits, and permissions...</p>
                        <a href="blog" class="blogLink">Read More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>

                <div class="blogCard">
                    <div class="blogImage"><i class="fas fa-bolt"></i></div>
                    <div class="blogContent">
                        <div class="blogMeta">
                            <span class="blogTag">Performance</span>
                            <span class="blogDate">April 5, 2026</span>
                        </div>
                        <h3>50% Faster Execution Times</h3>
                        <p class="blogExcerpt">Our optimized loading system now delivers scripts 50% faster than before...</p>
                        <a href="blog" class="blogLink">Read More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>
                <?php endif; ?>
            </div>
        </div>
    </section>

    <!-- Pricing Section -->
    <section class="pricingSection" id="pricing">
        <div class="sectionHeader">
            <h2>Simple, Transparent <span class="gradient">Pricing</span></h2>
            <p>Choose the plan that fits your needs. Scale as you grow.</p>
        </div>

        <div class="pricingGrid">
            <div class="priceCard">
                <h3>BASIC</h3>
                <div class="subtitle">500 Credits/month</div>
                <div class="priceAmount">$5<span class="period">/mo</span></div>
                <ul class="priceFeatures">
                    <li><i class="fas fa-check"></i> 2 Script Uploads</li>
                    <li><i class="fas fa-check"></i> Basic Obfuscation</li>
                    <li><i class="fas fa-check"></i> 100 API Calls/day</li>
                    <li><i class="fas fa-check"></i> Community Support</li>
                    <li><i class="fas fa-check"></i> 25 Keys/day</li>
                </ul>
                <button class="btn btnSecondary" onclick="selectPlan('basic')">Get Started</button>
            </div>

            <div class="priceCard popular">
                <h3>PRO</h3>
                <div class="subtitle">1,500 Credits/month</div>
                <div class="priceAmount">$15<span class="period">/mo</span></div>
                <ul class="priceFeatures">
                    <li><i class="fas fa-check"></i> 5 Script Uploads</li>
                    <li><i class="fas fa-check"></i> Advanced Obfuscation</li>
                    <li><i class="fas fa-check"></i> 500 API Calls/day</li>
                    <li><i class="fas fa-check"></i> Email Support</li>
                    <li><i class="fas fa-check"></i> 100 Keys/day</li>
                    <li><i class="fas fa-check"></i> Linkvertise Integration</li>
                </ul>
                <button class="btn btnPrimary" onclick="selectPlan('pro')">Get Started</button>
            </div>

            <div class="priceCard">
                <h3>PREMIUM</h3>
                <div class="subtitle">5,000 Credits/month</div>
                <div class="priceAmount">$25<span class="period">/mo</span></div>
                <ul class="priceFeatures">
                    <li><i class="fas fa-check"></i> Unlimited Scripts</li>
                    <li><i class="fas fa-check"></i> Advanced Obfuscation</li>
                    <li><i class="fas fa-check"></i> Unlimited API Calls</li>
                    <li><i class="fas fa-check"></i> Priority Support</li>
                    <li><i class="fas fa-check"></i> Unlimited Keys</li>
                    <li><i class="fas fa-check"></i> Linkvertise Integration</li>
                </ul>
                <button class="btn btnSecondary" onclick="selectPlan('premium')">Get Started</button>
            </div>

            <div class="priceCard">
                <h3>PROMOTER</h3>
                <div class="subtitle">Enterprise Solution</div>
                <div class="priceAmount">Custom</div>
                <ul class="priceFeatures">
                    <li><i class="fas fa-check"></i> All Premium Features</li>
                    <li><i class="fas fa-check"></i> White-label Solution</li>
                    <li><i class="fas fa-check"></i> API Access</li>
                    <li><i class="fas fa-check"></i> Custom Integrations</li>
                    <li><i class="fas fa-check"></i> Dedicated Support</li>
                </ul>
                <button class="btn btnSecondary" onclick="contactUs()">Contact Us</button>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="footerContainer">
            <div class="footerTop">
                <div class="footerBrand">
                    <img src="logo.png" alt="VALAX" style="height:40px;width:auto;" onerror="this.style.display='none'">
                    <span class="brandText">VALAX</span>
                </div>
                <div class="footerLinks">
                    <div class="linkColumn">
                        <h4>Product</h4>
                        <ul>
                            <li><a href="features">Features</a></li>
                            <li><a href="pricing">Pricing</a></li>
                            <li><a href="changelog">Changelog</a></li>
                            <li><a href="roadmap">Roadmap</a></li>
                        </ul>
                    </div>
                    <div class="linkColumn">
                        <h4>Resources</h4>
                        <ul>
                            <li><a href="documentation">Documentation</a></li>
                            <li><a href="api">API Reference</a></li>
                            <li><a href="guides">Guides</a></li>
                            <li><a href="blog">Blog</a></li>
                        </ul>
                    </div>
                    <div class="linkColumn">
                        <h4>Company</h4>
                        <ul>
                            <li><a href="about">About</a></li>
                            <li><a href="careers">Careers</a></li>
                            <li><a href="contact">Contact</a></li>
                            <li><a href="privacy">Privacy</a></li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="footerBottom">
                <p>&copy; 2026 VALAX. All rights reserved. | The strongest protection, the clearest pricing.</p>
            </div>
        </div>
    </footer>

    <!-- Slot Manage Modal -->
    <div class="modal" id="slotManageModal">
        <div class="modalContent">
            <div class="modalHeader">
                <h3>Manage Slot</h3>
                <button class="modalClose" onclick="closeModal('slotManage')">&times;</button>
            </div>
            <div class="modalBody">
                <div class="profileItem" style="margin-bottom:20px;">
                    <span class="label">Slot ID</span>
                    <span class="value" id="modalSlotId">-</span>
                </div>
                <div style="margin-bottom:20px;">
                    <label style="display:block;font-size:14px;color:var(--text-muted);margin-bottom:8px;">Script Name</label>
                    <input type="text" class="redeemInput" id="modalScriptName" placeholder="Enter script name">
                </div>
                <div class="profileItem">
                    <span class="label">VM Protection</span>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="modalVmProtection" checked>
                        <span style="font-size:12px;">Enabled</span>
                    </label>
                </div>
                <div class="profileItem">
                    <span class="label">HWID Lock</span>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="modalHwidLock" checked>
                        <span style="font-size:12px;">Enabled</span>
                    </label>
                </div>
                <div style="display:flex;gap:12px;margin-top:24px;">
                    <button class="btn btnPrimary" style="flex:1;" onclick="saveSlot()">Save Changes</button>
                    <button class="btn btnSecondary" style="flex:1;" onclick="closeModal('slotManage')">Cancel</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast">
        <i class="fas fa-check-circle"></i>
        <span id="toastMessage">Success!</span>
    </div>

    <script>
        // Navigation click handling
        document.querySelectorAll('.navCenter ul li a').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                
                // Handle anchor links (#)
                if (href.startsWith('#')) {
                    e.preventDefault();
                    document.querySelectorAll('.navCenter ul li').forEach(i => {
                        i.classList.remove('active');
                        i.querySelector('a').classList.remove('active');
                    });
                    this.parentElement.classList.add('active');
                    this.classList.add('active');
                    const sectionId = href.substring(1);
                    const section = document.getElementById(sectionId);
                    if (section) {
                        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
                // External page links - update active state
                else if (href) {
                    document.querySelectorAll('.navCenter ul li').forEach(i => {
                        i.classList.remove('active');
                        i.querySelector('a').classList.remove('active');
                    });
                    this.parentElement.classList.add('active');
                    this.classList.add('active');
                    // Navigate normally
                }
            });
        });

        // Smooth scroll for footer anchor links
        document.querySelectorAll('.footer a[href^="#"]').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const sectionId = this.getAttribute('href').substring(1);
                const section = document.getElementById(sectionId);
                if (section) {
                    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });

        // Copy to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('Copied to clipboard!', 'success');
            }).catch(() => {
                showToast('Failed to copy', 'error');
            });
        }

        // Toast notification
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toastMessage');
            const toastIcon = toast.querySelector('i');
            
            toastMessage.textContent = message;
            toastIcon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
            toast.className = 'toast ' + type;
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // Modal functions
        function openModal(modalType) {
            if (modalType === 'slotManage') {
                document.getElementById('slotManageModal').classList.add('active');
            }
        }

        function closeModal(modalType) {
            if (modalType === 'slotManage') {
                document.getElementById('slotManageModal').classList.remove('active');
            }
        }

        // Close modal on background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.classList.remove('active');
                }
            });
        });

        // Save slot
        function saveSlot() {
            showToast('Slot settings saved successfully!', 'success');
            closeModal('slotManage');
        }

        // Redeem code
        function redeemCode() {
            const code = document.getElementById('redeemCode').value.trim();
            if (!code) {
                showToast('Please enter a license code', 'error');
                return;
            }
            
            // Simulate API call
            showToast('Redeeming code...', 'success');
            setTimeout(() => {
                showToast('Credits added successfully!', 'success');
                document.getElementById('redeemCode').value = '';
            }, 1500);
        }

        // Select plan
        function selectPlan(plan) {
            window.location.href = 'pay?plan=' + plan;
        }

        // Purchase credits
        function purchaseCredits(amount) {
            window.location.href = 'pay?credits=' + amount;
        }

        // Contact us
        function contactUs() {
            window.location.href = 'contact';
        }

        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.featureCard, .statCard, .blogCard, .slotCard, .planCard, .groupFeatureItem').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });

        // Mobile menu toggle
        const menuToggle = document.querySelector('.menuToggle');
        const navCenter = document.querySelector('.navCenter');
        
        if (menuToggle) {
            menuToggle.addEventListener('click', function() {
                navCenter.style.display = navCenter.style.display === 'block' ? 'none' : 'block';
                if (navCenter.style.display === 'block') {
                    navCenter.style.position = 'fixed';
                    navCenter.style.top = '90px';
                    navCenter.style.left = '20px';
                    navCenter.style.right = '20px';
                    navCenter.style.background = 'var(--bg-secondary)';
                    navCenter.style.padding = '20px';
                    navCenter.style.borderRadius = '16px';
                    navCenter.style.border = '1px solid var(--border-color)';
                }
            });
        }

        // Group GIF loader
        (function() {
            const img = document.getElementById('groupGif');
            const fallback = document.getElementById('groupGifFallback');
            if (img && fallback) {
                img.onload = function() {
                    img.style.display = 'block';
                    fallback.style.display = 'none';
                };
                img.onerror = function() {
                    img.style.display = 'none';
                    fallback.style.display = 'flex';
                };
                // Try to load
                if (img.complete) {
                    if (img.naturalWidth > 0) {
                        img.style.display = 'block';
                        fallback.style.display = 'none';
                    } else {
                        img.style.display = 'none';
                        fallback.style.display = 'flex';
                    }
                }
            }
        })();
    </script>
</body>
</html>
