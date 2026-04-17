<?php
/**
 * VALAX-SHIELD - ENHANCED DASHBOARD v3.0
 * Multi-User Slot Hosting System with Groups, 2FA, and Credits
 */

require 'config.php';

// =====================================================
// 登录检查 - 未登录直接显示 Landing 页面
// =====================================================
$is_logged_in = isset($_SESSION['user_id']) && !empty($_SESSION['user_id']);
$user = null;
$user_db_id = null;
$user_groups = [];
$current_group_id = null;
$slots = [];
$db_error = false;

// 如果 session 存在但数据库查询失败，仍使用 session 数据
if ($is_logged_in) {
    $session_user = [
        'id' => null,
        'username' => $_SESSION['username'] ?? 'User',
        'avatar' => $_SESSION['avatar'] ?? '',
        'obf_credits' => '0',
        'twofa_enabled' => false
    ];
    
    if (isset($pdo) && $pdo !== null) {
        try {
            $stmt = $pdo->prepare("SELECT * FROM users WHERE discord_id = ?");
            $stmt->execute([$_SESSION['user_id']]);
            $user = $stmt->fetch();
            
            if ($user) {
                $user_db_id = (string)($user['discord_id'] ?? $_SESSION['user_id']);
                
                // 直接获取 Hosting Slots - 不依赖 groups 表
                $stmt = $pdo->prepare("
                    SELECT s.*, u.username as owner_name
                    FROM hosting_slots s
                    LEFT JOIN users u ON s.owner_id = u.discord_id
                    WHERE s.owner_id = ?
                    AND s.status != 'deleted'
                    ORDER BY s.created_at DESC
                ");
                $stmt->execute([$user_db_id]);
                $slots = $stmt->fetchAll();
                
                // 获取用户所在的 Groups
                try {
                    $stmt = $pdo->prepare("
                        SELECT g.*, ug.role, 
                               (SELECT COUNT(*) FROM user_groups WHERE group_id = g.id) as member_count
                        FROM groups g
                        INNER JOIN user_groups ug ON g.id = ug.group_id
                        WHERE ug.user_id = ?
                        ORDER BY ug.role = 'owner' DESC, g.created_at DESC
                    ");
                    $stmt->execute([$user_db_id]);
                    $user_groups = $stmt->fetchAll();
                    
                    // 获取待处理邀请数量
                    $stmt = $pdo->prepare("
                        SELECT COUNT(*) as count 
                        FROM pending_invites 
                        WHERE invited_discord_id = ? AND status = 'pending'
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ");
                    $stmt->execute([$user_db_id]);
                    $pending_invite_count = $stmt->fetch()['count'] ?? 0;
                } catch (Exception $e) {
                    $user_groups = [];
                    $pending_invite_count = 0;
                    error_log("Groups query error: " . $e->getMessage());
                }
                
                // 设置当前 Group
                $current_group_id = $_GET['group_id'] ?? ($user_groups[0]['id'] ?? null);
            } else {
                $db_error = true;
            }
        } catch (PDOException $e) {
            $db_error = true;
            error_log("Dashboard DB Error: " . $e->getMessage());
        }
    } else {
        $db_error = true;
    }
    
    // 数据库没有数据或出错时，使用 session 数据
    if (!isset($user) || !$user) {
        $user = $session_user;
    }
}

$username = $user ? htmlspecialchars($user['username']) : htmlspecialchars($_SESSION['username'] ?? '');
$avatar = $user ? htmlspecialchars($user['avatar']) : htmlspecialchars($_SESSION['avatar'] ?? '');
$credits = $user ? htmlspecialchars($user['obf_credits'] ?? '0') : '0';
$twofa_enabled = $user ? ($user['twofa_enabled'] ?? false) : false;
$pending_invite_count = $pending_invite_count ?? 0;

// Group 创建费用
$group_cost = 10;

// Plan 价格配置
$plan_prices = [
    'starter' => ['name' => 'Starter', 'price' => 30, 'slots' => 1, 'color' => '#6b7280'],
    'professional' => ['name' => 'Professional', 'price' => 50, 'slots' => 3, 'color' => '#7c4dff'],
    'enterprise' => ['name' => 'Enterprise', 'price' => 100, 'slots' => 10, 'color' => '#CABB55']
];

// 如果未登录，重定向到 landing
if (!$is_logged_in) {
    // 显示 Landing 页面内容
    $show_landing = true;
} else {
    $show_landing = false;
}
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
        /* =====================================================
           全局变量 - 沿用原有配色
           ===================================================== */
        :root {
            --gold: #CABB55;
            --gold-light: #E5D87D;
            --purple: #7c4dff;
            --purple-dark: #6b70ff;
            --cyan: #3bcaff;
            --bg-dark: #13151E;
            --sidebar-width: 260px;
            --topbar-height: 70px;
        }

        /* =====================================================
           自定义滚动条
           ===================================================== */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.12); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.25); }

        /* =====================================================
           整体布局
           ===================================================== */
        body {
            margin: 0;
            padding: 0;
            background-color: var(--bg-dark);
            scroll-behavior: smooth;
            font-family: 'Space Grotesk', -apple-system, sans-serif;
        }

        .app-wrapper {
            display: flex;
            min-height: 100vh;
        }

        /* =====================================================
           LANDING 页面样式（未登录时显示）
           ===================================================== */
        .landing-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: var(--bg-dark);
            z-index: 900;
            overflow-y: auto;
        }

        body:not(.logged-in) .landing-overlay {
            display: block;
        }

        body:not(.logged-in) .app-wrapper,
        body:not(.logged-in) .sidebar,
        body:not(.logged-in) .topbar {
            display: none;
        }

        .landing-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
            background: 
                radial-gradient(ellipse at 50% 0%, rgba(124, 77, 255, 0.12) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(202, 187, 85, 0.05) 0%, transparent 40%),
                var(--bg-dark);
        }

        .landing-content {
            width: 100%;
            max-width: 480px;
            animation: fadeInUp 0.5s ease;
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .landing-logo-wrapper {
            text-align: center;
            margin-bottom: 32px;
        }

        .landing-logo-icon {
            width: 72px;
            height: 72px;
            margin: 0 auto 16px;
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(124, 77, 255, 0.3);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }

        .landing-logo-icon img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .landing-brand {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 50%, var(--gold) 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shine 4s linear infinite;
        }

        @keyframes shine {
            to { background-position: 200% center; }
        }

        .landing-hero {
            text-align: center;
            margin-bottom: 32px;
        }

        .landing-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(202, 187, 85, 0.1);
            border: 1px solid rgba(202, 187, 85, 0.2);
            border-radius: 20px;
            font-size: 12px;
            color: var(--gold);
            font-weight: 600;
            margin-bottom: 20px;
        }

        .landing-badge .dot {
            width: 8px;
            height: 8px;
            background: var(--gold);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .landing-hero h1 {
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }

        .landing-hero .gradient {
            background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .landing-subtitle {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.6);
            line-height: 1.6;
        }

        .btn-discord {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 16px 32px;
            background: #5865F2;
            color: #fff;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.25s ease;
            box-shadow: 0 4px 20px rgba(88, 101, 242, 0.35);
            border: none;
            cursor: pointer;
            font-family: inherit;
        }

        .btn-discord:hover {
            background: #4752C4;
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(88, 101, 242, 0.5);
        }

        .btn-secondary-outline {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 14px 24px;
            background: transparent;
            color: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.25s ease;
            cursor: pointer;
            font-family: inherit;
        }

        .btn-secondary-outline:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.15);
        }

        .landing-buttons {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 40px;
        }

        .landing-features-grid {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-bottom: 24px;
        }

        .landing-feature-card {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            transition: all 0.3s ease;
            text-align: left;
        }

        .landing-feature-card:hover {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(124, 77, 255, 0.3);
            transform: translateX(4px);
        }

        .landing-feature-icon {
            width: 48px;
            height: 48px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, rgba(124, 77, 255, 0.2) 0%, rgba(124, 77, 255, 0.1) 100%);
            border: 1px solid rgba(124, 77, 255, 0.3);
            border-radius: 12px;
        }

        .landing-feature-icon svg {
            width: 24px;
            height: 24px;
            color: var(--purple);
        }

        .landing-feature-content h3 {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
            color: #fff;
        }

        .landing-feature-content p {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            line-height: 1.5;
            margin: 0;
        }

        /* =====================================================
           侧边栏
           ===================================================== */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: var(--sidebar-width);
            height: 100vh;
            background: linear-gradient(180deg, rgba(15, 17, 28, 0.98) 0%, rgba(11, 13, 22, 0.98) 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.04);
            display: flex;
            flex-direction: column;
            z-index: 1001;
            backdrop-filter: blur(20px);
            overflow: hidden;
        }

        .sidebar-logo {
            padding: 20px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .sidebar-logo .logo-icon {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            overflow: hidden;
        }

        .sidebar-logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .sidebar-logo span {
            font-size: 22px;
            font-weight: 800;
            background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 50%, var(--gold) 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .sidebar-nav {
            flex: 1;
            padding: 16px 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            overflow-y: auto;
        }

        .sidebar-section-title {
            font-size: 11px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.4);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 16px 16px 8px;
            margin-top: 8px;
        }

        .nav-link {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.25s ease;
            position: relative;
            color: rgba(255, 255, 255, 0.6);
            font-weight: 500;
            font-size: 14px;
            border: 1px solid transparent;
            text-decoration: none;
        }

        .nav-link:hover {
            background: rgba(202, 187, 85, 0.08);
            color: #fff;
            border-color: rgba(202, 187, 85, 0.15);
        }

        .nav-link.active {
            background: linear-gradient(135deg, rgba(124, 77, 255, 0.15) 0%, rgba(124, 77, 255, 0.05) 100%);
            color: #fff;
            border-color: rgba(124, 77, 255, 0.3);
        }

        .nav-link.active::before {
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 3px;
            height: 60%;
            background: linear-gradient(180deg, var(--purple) 0%, var(--purple-dark) 100%);
            border-radius: 0 3px 3px 0;
        }

        .nav-link svg {
            width: 20px;
            height: 20px;
            flex-shrink: 0;
        }

        .sidebar-footer {
            padding: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
        }

        .logout-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 12px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 10px;
            color: #ef4444;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            font-family: inherit;
            font-size: 14px;
            text-decoration: none;
        }

        .logout-btn:hover {
            background: rgba(239, 68, 68, 0.2);
            border-color: #ef4444;
            transform: translateY(-1px);
        }

        /* =====================================================
           主内容区
           ===================================================== */
        .main-area {
            flex: 1;
            margin-left: var(--sidebar-width);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        .topbar {
            position: sticky;
            top: 0;
            height: var(--topbar-height);
            background: rgba(5, 5, 8, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 30px;
            z-index: 1000;
        }

        .topbar-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .topbar-title {
            font-size: 18px;
            font-weight: 700;
            color: #fff;
        }

        /* Group Dropdown */
        .group-selector {
            position: relative;
        }

        .group-dropdown {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.25s ease;
            min-width: 180px;
        }

        .group-dropdown:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(124, 77, 255, 0.3);
        }

        .group-dropdown .group-icon {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            color: #fff;
        }

        .group-dropdown .group-name {
            flex: 1;
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .group-dropdown .dropdown-arrow {
            width: 16px;
            height: 16px;
            color: rgba(255, 255, 255, 0.4);
            transition: transform 0.2s;
        }

        .group-dropdown.active .dropdown-arrow {
            transform: rotate(180deg);
        }

        .group-dropdown-menu {
            position: absolute;
            top: calc(100% + 8px);
            left: 0;
            width: 220px;
            background: rgba(20, 23, 34, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 8px;
            display: none;
            z-index: 100;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }

        .group-dropdown-menu.show {
            display: block;
        }

        .group-dropdown-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            color: rgba(255, 255, 255, 0.7);
        }

        .group-dropdown-item:hover {
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
        }

        .group-dropdown-item.active {
            background: rgba(124, 77, 255, 0.2);
            color: #fff;
        }

        .group-dropdown-item .group-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(124, 77, 255, 0.3);
            color: var(--purple);
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .credits-display {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 10px 20px;
            border-radius: 12px;
        }

        .credits-label {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 600;
            letter-spacing: 0.1em;
        }

        .credits-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--gold);
            font-family: 'JetBrains Mono', monospace;
        }

        .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
        }

        .user-avatar {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: 2px solid var(--purple);
            object-fit: cover;
        }

        .user-name {
            font-size: 14px;
            font-weight: 700;
            color: #fff;
        }

        .user-status {
            font-size: 10px;
            color: #10b981;
            font-weight: 700;
        }

        /* =====================================================
           页面容器
           ===================================================== */
        .page-container {
            flex: 1;
            padding: 30px;
        }

        .page {
            display: none;
        }

        .page.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .page-header {
            margin-bottom: 28px;
        }

        .page-header h1 {
            font-size: 26px;
            font-weight: 800;
            margin-bottom: 6px;
            color: #fff;
        }

        .page-header p {
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
        }

        .page-header h1 .gradient {
            background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* =====================================================
           卡片系统
           ===================================================== */
        .card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 20px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .card-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 15px;
            font-weight: 700;
            color: #fff;
        }

        .card-title svg {
            width: 18px;
            height: 18px;
            color: var(--purple);
        }

        /* =====================================================
           按钮系统
           ===================================================== */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
            border: none;
            text-decoration: none;
        }

        .btn svg {
            width: 15px;
            height: 15px;
            flex-shrink: 0;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
            color: #fff;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(124, 77, 255, 0.35);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #fff;
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .btn-action {
            background: linear-gradient(135deg, var(--purple), var(--purple-dark));
            color: #fff;
        }

        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(124, 77, 255, 0.35);
        }

        .btn-gold {
            background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%);
            color: #0B0D14;
        }

        .btn-gold:hover {
            box-shadow: 0 6px 20px rgba(202, 187, 85, 0.4);
            transform: translateY(-2px);
        }

        /* =====================================================
           Dashboard 统计卡片
           ===================================================== */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            padding: 20px;
            animation-delay: calc(0.1s * var(--i, 1));
        }

        .stat-card .stat-icon {
            margin-bottom: 12px;
        }

        .stat-card .stat-value {
            font-size: 28px;
            font-weight: 800;
            color: var(--gold);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }

        .stat-card .stat-label {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* =====================================================
           功能导航卡片
           ===================================================== */
        .feature-nav-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }

        .feature-card {
            cursor: pointer;
            text-align: center;
            padding: 30px 20px;
        }

        .feature-card:hover {
            transform: translateY(-4px);
        }

        .feature-card .f-icon {
            width: 56px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
            border-radius: 14px;
            margin: 0 auto 16px;
        }

        .feature-card .f-icon svg {
            width: 28px;
            height: 28px;
            color: #fff;
        }

        .feature-card h3 {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #fff;
        }

        .feature-card p {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
            line-height: 1.5;
        }

        /* =====================================================
           HOSTING 页面
           ===================================================== */
        .hosting-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }

        .hosting-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }

        .slot-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .slot-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
        }

        .slot-card.status-active::before { background: #10b981; }
        .slot-card.status-expired::before { background: #ef4444; }
        .slot-card.status-inactive::before { background: #f59e0b; }
        .slot-card.status-unconfigured::before { background: var(--purple); }

        .slot-card:hover {
            transform: translateY(-4px);
            border-color: rgba(124, 77, 255, 0.3);
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
        }

        .slot-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }

        .slot-card-title {
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 4px;
        }

        .slot-card-id {
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--purple);
        }

        .slot-status-badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .slot-status-badge.active {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }

        .slot-status-badge.expired {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }

        .slot-status-badge.inactive,
        .slot-status-badge.unconfigured {
            background: rgba(124, 77, 255, 0.2);
            color: var(--purple);
        }

        .slot-card-info {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }

        .slot-info-item {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }

        .slot-info-item .label {
            color: rgba(255, 255, 255, 0.5);
        }

        .slot-info-item .value {
            font-weight: 600;
            color: #fff;
        }

        .slot-card-actions {
            display: flex;
            gap: 8px;
        }

        .slot-card-actions .btn {
            flex: 1;
            padding: 10px;
            font-size: 12px;
        }

        .empty-slots {
            text-align: center;
            padding: 60px 20px;
            color: rgba(255, 255, 255, 0.5);
        }

        .empty-slots svg {
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        /* =====================================================
           Buy Slot / Plans Section
           ===================================================== */
        .buy-slot-section {
            margin-top: 24px;
        }

        .plans-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 20px;
        }

        .plan-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 28px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .plan-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
        }

        .plan-card.starter::before { background: linear-gradient(90deg, #6b7280, #9ca3af); }
        .plan-card.professional::before { background: linear-gradient(90deg, var(--purple), var(--purple-dark)); }
        .plan-card.enterprise::before { background: linear-gradient(90deg, var(--gold), var(--gold-light)); }

        .plan-card:hover {
            transform: translateY(-6px);
            border-color: rgba(124, 77, 255, 0.3);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }

        .plan-card.popular {
            border-color: rgba(124, 77, 255, 0.4);
            background: rgba(124, 77, 255, 0.05);
        }

        .plan-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .plan-card.starter .plan-badge {
            background: rgba(107, 114, 128, 0.2);
            color: #9ca3af;
        }

        .plan-card.professional .plan-badge {
            background: rgba(124, 77, 255, 0.2);
            color: var(--purple);
        }

        .plan-card.enterprise .plan-badge {
            background: rgba(202, 187, 85, 0.2);
            color: var(--gold);
        }

        .plan-name {
            font-size: 22px;
            font-weight: 800;
            color: #fff;
            margin-bottom: 8px;
        }

        .plan-desc {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 20px;
        }

        .plan-price {
            font-size: 32px;
            font-weight: 800;
            color: var(--gold);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }

        .plan-price .unit {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 400;
        }

        .plan-features {
            list-style: none;
            padding: 0;
            margin: 20px 0;
        }

        .plan-features li {
            padding: 8px 0;
            font-size: 13px;
            color: rgba(255, 255, 255, 0.7);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .plan-features li svg {
            width: 16px;
            height: 16px;
            color: #10b981;
        }

        .plan-card .btn {
            width: 100%;
            padding: 12px;
        }

        /* =====================================================
           Credits 页面
           ===================================================== */
        .credits-balance-card {
            background: linear-gradient(135deg, rgba(202, 187, 85, 0.1) 0%, rgba(202, 187, 85, 0.02) 100%);
            border: 1px solid rgba(202, 187, 85, 0.2);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
        }

        .credits-balance-value {
            font-size: 64px;
            font-weight: 800;
            color: var(--gold);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }

        .credits-balance-label {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .recharge-options {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }

        .recharge-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 24px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .recharge-card:hover {
            border-color: rgba(124, 77, 255, 0.3);
            transform: translateY(-4px);
        }

        .recharge-amount {
            font-size: 28px;
            font-weight: 800;
            color: var(--gold);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }

        .recharge-price {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 12px;
        }

        .recharge-card .btn {
            width: 100%;
            padding: 10px;
            font-size: 12px;
            opacity: 0.5;
            pointer-events: none;
        }

        /* =====================================================
           Profile 页面
           ===================================================== */
        .profile-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .profile-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .profile-item:last-child {
            border-bottom: none;
        }

        .profile-item label {
            color: rgba(255, 255, 255, 0.5);
            font-size: 13px;
        }

        .profile-item span {
            font-weight: 600;
            font-size: 13px;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
        }

        .security-section {
            margin-top: 24px;
        }

        .security-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            margin-bottom: 12px;
        }

        .security-item-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .security-item-icon {
            width: 40px;
            height: 40px;
            background: rgba(124, 77, 255, 0.2);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .security-item-icon svg {
            width: 20px;
            height: 20px;
            color: var(--purple);
        }

        .security-item-title {
            font-weight: 600;
            color: #fff;
            margin-bottom: 2px;
        }

        .security-item-desc {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
        }

        /* =====================================================
           Toast 通知
           ===================================================== */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 20px;
            background: rgba(20, 23, 34, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.35s ease;
            z-index: 99999;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        .toast.success { border-color: rgba(16, 185, 129, 0.3); }
        .toast.error { border-color: rgba(239, 68, 68, 0.3); }

        .toast-icon {
            width: 18px;
            height: 18px;
        }

        .toast.success .toast-icon { color: #10b981; }
        .toast.error .toast-icon { color: #ef4444; }

        /* =====================================================
           Modal 样式
           ===================================================== */
        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 9999;
            overflow-y: auto;
            padding: 40px 20px;
        }

        .modal-container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(20, 23, 34, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            overflow: hidden;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 18px 24px;
            background: rgba(0, 0, 0, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .modal-header h3 {
            margin: 0;
            color: #fff;
        }

        .modal-body {
            padding: 24px;
        }

        /* =====================================================
           响应式设计
           ===================================================== */
        @media (max-width: 1200px) {
            .plans-grid { grid-template-columns: repeat(2, 1fr); }
            .recharge-options { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .sidebar.open { transform: translateX(0); }
            .main-area { margin-left: 0; }
            .stats-row { grid-template-columns: repeat(2, 1fr); }
            .feature-nav-grid { grid-template-columns: 1fr; }
            .plans-grid { grid-template-columns: 1fr; }
            .profile-grid { grid-template-columns: 1fr; }
            .topbar { padding: 0 16px; }
            .page-container { padding: 20px; }
            .group-dropdown { min-width: 140px; }
            .hosting-grid { grid-template-columns: 1fr; }
        }

        /* Hidden utility */
        .hidden { display: none !important; }
    </style>
</head>
<body class="<?php echo $is_logged_in ? 'logged-in' : ''; ?>">

    <!-- =====================================================
         LANDING 页面（未登录时显示）
         ===================================================== -->
    <div class="landing-overlay">
        <div class="landing-container">
            <div class="landing-content">
                <div class="landing-logo-wrapper">
                    <div class="landing-logo-icon">
                        <img src="logo.png" alt="VALAX">
                    </div>
                    <span class="landing-brand">VALAX</span>
                </div>

                <div class="landing-hero">
                    <div class="landing-badge">
                        <span class="dot"></span>
                        Next-Gen Protection Platform
                    </div>
                    <h1><span class="gradient">VALAX</span> Protection</h1>
                    <p class="landing-subtitle">
                        Military-grade script security & cloud hosting. Protect your code with advanced obfuscation.
                    </p>
                </div>

                <div class="landing-buttons">
                    <a href="<?php echo htmlspecialchars($auth_url ?? '#'); ?>" class="btn-discord">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
                            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
                        </svg>
                        Login with Discord
                    </a>
                    <a href="#features" class="btn-secondary-outline">
                        View Features
                    </a>
                </div>

                <div class="landing-features-grid">
                    <div class="landing-feature-card">
                        <div class="landing-feature-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                            </svg>
                        </div>
                        <div class="landing-feature-content">
                            <h3>Obfuscation Engine</h3>
                            <p>Military-grade virtualization technology</p>
                        </div>
                    </div>
                    <div class="landing-feature-card">
                        <div class="landing-feature-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                            </svg>
                        </div>
                        <div class="landing-feature-content">
                            <h3>Cloud Hosting</h3>
                            <p>Deploy scripts globally with one click</p>
                        </div>
                    </div>
                    <div class="landing-feature-card">
                        <div class="landing-feature-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                            </svg>
                        </div>
                        <div class="landing-feature-content">
                            <h3>License System</h3>
                            <p>HWID locks, heartbeat & kill switch</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- =====================================================
         主应用界面
         ===================================================== -->
    <div class="app-wrapper">
        <!-- 侧边栏 -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-logo">
                <div class="logo-icon"><img src="logo.png" alt="VALAX"></div>
                <span>VALAX</span>
            </div>

            <nav class="sidebar-nav">
                <span class="sidebar-section-title">Main</span>
                <a href="#" class="nav-link active" data-page="homePage">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="7" height="9" rx="1"/>
                        <rect x="14" y="3" width="7" height="5" rx="1"/>
                        <rect x="14" y="12" width="7" height="9" rx="1"/>
                        <rect x="3" y="16" width="7" height="5" rx="1"/>
                    </svg>
                    Dashboard
                </a>
                <a href="#" class="nav-link" data-page="hostingPage">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                    </svg>
                    Hosting
                </a>
                <a href="#" class="nav-link" data-page="creditsPage">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
                        <path d="M12 18V6"/>
                    </svg>
                    Credits
                </a>
                <a href="#" class="nav-link" data-page="redeemPage">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                    </svg>
                    Redeem
                </a>
                <a href="#" class="nav-link" data-page="profilePage">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    Profile
                </a>
            </nav>

            <div class="sidebar-footer">
                <a href="logout.php" class="logout-btn">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                        <polyline points="16 17 21 12 16 7"/>
                        <line x1="21" y1="12" x2="9" y2="12"/>
                    </svg>
                    Logout
                </a>
            </div>
        </aside>

        <!-- 主内容区 -->
        <div class="main-area">
            <!-- 顶部栏 -->
            <header class="topbar">
                <div class="topbar-left">
                    <h2 class="topbar-title" id="topbar-title">Dashboard</h2>
                    
                    <!-- Group 切换下拉菜单 -->
                    <?php if (!empty($user_groups)): ?>
                    <div class="group-selector">
                        <div class="group-dropdown" id="groupDropdown">
                            <div class="group-icon"><?php echo substr(htmlspecialchars($user_groups[0]['name'] ?? 'G'), 0, 1); ?></div>
                            <span class="group-name"><?php echo htmlspecialchars($user_groups[0]['name'] ?? 'Select Group'); ?></span>
                            <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="6 9 12 15 18 9"/>
                            </svg>
                        </div>
                        <div class="group-dropdown-menu" id="groupDropdownMenu">
                            <?php foreach ($user_groups as $group): ?>
                            <a href="?group_id=<?php echo $group['id']; ?>" class="group-dropdown-item <?php echo ($group['id'] == $current_group_id) ? 'active' : ''; ?>" data-group-id="<?php echo $group['id']; ?>">
                                <div class="group-icon" style="width:28px;height:28px;font-size:11px;"><?php echo substr(htmlspecialchars($group['name']), 0, 1); ?></div>
                                <span><?php echo htmlspecialchars($group['name']); ?></span>
                                <?php if ($group['role'] == 'owner'): ?>
                                <span class="group-badge">Owner</span>
                                <?php endif; ?>
                            </a>
                            <?php endforeach; ?>
                        </div>
                    </div>
                    <?php endif; ?>
                </div>
                
                <div class="topbar-right">
                    <div class="credits-display">
                        <span class="credits-label">CREDITS</span>
                        <span class="credits-value" id="user-credits"><?php echo $credits; ?></span>
                    </div>
                    <div class="user-info">
                        <img src="<?php echo $avatar ?: 'logo.png'; ?>" alt="Avatar" class="user-avatar">
                        <div>
                            <div class="user-name"><?php echo $username; ?></div>
                            <div class="user-status">&#9632; AUTHORIZED</div>
                        </div>
                    </div>
                </div>
            </header>

            <!-- 页面容器 -->
            <div class="page-container">
                
                <!-- ==================== HOME SECTION ==================== -->
                <section id="homePage" class="page active">
                    <div class="page-header">
                        <h1>Welcome back, <span class="gradient"><?php echo $username; ?></span></h1>
                        <p>Your command center for script protection and cloud hosting</p>
                    </div>

                    <div class="stats-row">
                        <div class="card stat-card" style="--i: 1">
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="var(--gold)" stroke-width="2" width="32" height="32">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
                                    <path d="M12 18V6"/>
                                </svg>
                            </div>
                            <div class="stat-value" id="stat-credits"><?php echo $credits; ?></div>
                            <div class="stat-label">Credits</div>
                        </div>
                        <div class="card stat-card" style="--i: 2">
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2" width="32" height="32">
                                    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                                </svg>
                            </div>
                            <div class="stat-value" id="stat-slots"><?php echo count($slots); ?></div>
                            <div class="stat-label">Active Slots</div>
                        </div>
                        <div class="card stat-card" style="--i: 3">
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2" width="32" height="32">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="9" cy="7" r="4"/>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                </svg>
                            </div>
                            <div class="stat-value"><?php echo count($user_groups); ?></div>
                            <div class="stat-label">Groups</div>
                        </div>
                        <div class="card stat-card" style="--i: 4">
                            <div class="stat-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2" width="32" height="32">
                                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                </svg>
                            </div>
                            <div class="stat-value">V5.0</div>
                            <div class="stat-label">Engine Version</div>
                        </div>
                    </div>

                    <div class="feature-nav-grid">
                        <div class="card feature-card" data-page="hostingPage">
                            <div class="f-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                                </svg>
                            </div>
                            <h3>Cloud Hosting</h3>
                            <p>Deploy and manage your protected scripts globally</p>
                        </div>
                        <div class="card feature-card" data-page="creditsPage">
                            <div class="f-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
                                    <path d="M12 18V6"/>
                                </svg>
                            </div>
                            <h3>Credits</h3>
                            <p>Purchase credits for obfuscation and hosting</p>
                        </div>
                        <div class="card feature-card" data-page="redeemPage">
                            <div class="f-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                                </svg>
                            </div>
                            <h3>Redeem Code</h3>
                            <p>Activate credits with license keys</p>
                        </div>
                    </div>
                </section>

                <!-- ==================== HOSTING SECTION ==================== -->
                <section id="hostingPage" class="page">
                    <div class="page-header">
                        <h1><span class="gradient">Aegis</span> Cloud Hosting</h1>
                        <p>Deploy and manage your protected scripts on military-grade infrastructure</p>
                    </div>
                    
                    <!-- Debug Info (remove in production) -->
                    <?php if (isset($user_db_id)): ?>
                    <div style="background:#1a1a2e;padding:10px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#888;">
                        <strong>Debug:</strong> User ID: <?php echo htmlspecialchars($user_db_id); ?> | 
                        Slots Found: <?php echo count($slots); ?> |
                        DB Error: <?php echo $db_error ? 'Yes' : 'No'; ?>
                    </div>
                    <?php endif; ?>

                    <div class="hosting-header">
                        <div>
                            <h3 style="margin:0;color:#fff;">Your Slots</h3>
                            <p style="margin:4px 0 0 0;font-size:13px;color:rgba(255,255,255,0.5);">
                                Slot Count: <?php echo count($slots); ?>
                            </p>
                        </div>
                        <div style="display:flex;gap:12px;">
                            <button class="btn btn-secondary" id="inviteMemberBtn">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
                                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="8.5" cy="7" r="4"/>
                                    <line x1="20" y1="8" x2="20" y2="14"/>
                                    <line x1="23" y1="11" x2="17" y2="11"/>
                                </svg>
                                Invite Member
                            </button>
                            <button class="btn btn-gold" id="buySlotBtn">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15">
                                    <circle cx="12" cy="12" r="10"/>
                                    <line x1="12" y1="8" x2="12" y2="16"/>
                                    <line x1="8" y1="12" x2="16" y2="12"/>
                                </svg>
                                Buy Slot
                            </button>
                        </div>
                    </div>

                    <!-- Plans 选择区域（默认隐藏） -->
                    <div class="buy-slot-section hidden" id="plansSection">
                        <div class="card">
                            <div class="card-header">
                                <span class="card-title">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                                    </svg>
                                    Select a Plan
                                </span>
                                <button class="btn btn-secondary" id="closePlansBtn" style="padding:6px 12px;font-size:11px;">Close</button>
                            </div>
                            <p style="color:rgba(255,255,255,0.5);font-size:13px;margin-bottom:20px;">
                                Choose a subscription plan. Credits will be deducted monthly based on your plan.
                            </p>
                            
                            <div class="plans-grid">
                                <?php foreach ($plan_prices as $key => $plan): ?>
                                <div class="plan-card <?php echo $key; ?> <?php echo ($key == 'professional') ? 'popular' : ''; ?>">
                                    <?php if ($key == 'professional'): ?>
                                    <span class="popular-badge" style="position:absolute;top:12px;right:12px;background:var(--purple);color:#fff;font-size:10px;padding:4px 8px;border-radius:4px;font-weight:700;">POPULAR</span>
                                    <?php endif; ?>
                                    <span class="plan-badge"><?php echo $plan['name']; ?></span>
                                    <div class="plan-name"><?php echo $plan['name']; ?></div>
                                    <div class="plan-desc"><?php echo $plan['slots']; ?> Cloud Slot<?php echo ($plan['slots'] > 1) ? 's' : ''; ?></div>
                                    <div class="plan-price">
                                        <?php echo $plan['price']; ?>
                                        <span class="unit">credits/mo</span>
                                    </div>
                                    <ul class="plan-features">
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                                            <?php echo $plan['slots']; ?> Slot<?php echo ($plan['slots'] > 1) ? 's' : ''; ?>
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                                            VM Protection
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                                            HWID Lock
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                                            99.9% Uptime
                                        </li>
                                    </ul>
                                    <button class="btn btn-primary select-plan-btn" data-plan="<?php echo $key; ?>" data-cost="<?php echo $plan['price']; ?>">
                                        Select <?php echo $plan['name']; ?>
                                    </button>
                                </div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                    </div>

                    <!-- Slots 列表 -->
                    <div class="hosting-grid" id="slotsGrid">
                        <?php if (empty($slots)): ?>
                        <div class="empty-slots" style="grid-column: 1/-1;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                            </svg>
                            <h3 style="margin:0 0 8px 0;">No Slots Yet</h3>
                            <p>Purchase a slot to start hosting your scripts</p>
                        </div>
                        <?php else: ?>
                        <?php foreach ($slots as $slot): ?>
                        <div class="slot-card status-<?php echo strtolower($slot['status'] ?? 'active'); ?>">
                            <div class="slot-card-header">
                                <div>
                                    <div class="slot-card-title"><?php echo htmlspecialchars($slot['script_name'] ?? ($slot['owner_name'] ?? 'Unnamed Script')); ?></div>
                                    <div class="slot-card-id"><?php echo htmlspecialchars($slot['slot_id'] ?? 'VX-UNKNOWN'); ?></div>
                                </div>
                                <span class="slot-status-badge <?php echo strtolower($slot['status'] ?? 'active'); ?>">
                                    <?php echo htmlspecialchars($slot['status'] ?? 'ACTIVE'); ?>
                                </span>
                            </div>
                            <div class="slot-card-info">
                                <div class="slot-info-item">
                                    <span class="label">Owner</span>
                                    <span class="value"><?php echo htmlspecialchars($slot['owner_name'] ?? 'You'); ?></span>
                                </div>
                                <div class="slot-info-item">
                                    <span class="label">Created</span>
                                    <span class="value"><?php echo date('Y-m-d', strtotime($slot['created_at'] ?? 'now')); ?></span>
                                </div>
                                <div class="slot-info-item">
                                    <span class="label">VM Protection</span>
                                    <span class="value"><?php echo ($slot['vm_protection'] ?? 0) ? 'Enabled' : 'Disabled'; ?></span>
                                </div>
                                <div class="slot-info-item">
                                    <span class="label">HWID Lock</span>
                                    <span class="value"><?php echo ($slot['hwid_lock'] ?? 1) ? 'Enabled' : 'Disabled'; ?></span>
                                </div>
                            </div>
                            <div class="slot-card-actions">
                                <button class="btn btn-primary manage-slot-btn" data-slot-id="<?php echo htmlspecialchars($slot['slot_id'] ?? ''); ?>">Manage</button>
                                <button class="btn btn-secondary copy-loader-btn" data-slot-id="<?php echo htmlspecialchars($slot['slot_id'] ?? ''); ?>">Copy</button>
                            </div>
                        </div>
                        <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </section>

                <!-- ==================== CREDITS SECTION ==================== -->
                <section id="creditsPage" class="page">
                    <div class="page-header">
                        <h1>Credits <span class="gradient">Balance</span></h1>
                        <p>Manage your credits and purchase more</p>
                    </div>

                    <div class="credits-balance-card">
                        <div class="credits-balance-value" id="creditsBalance"><?php echo $credits; ?></div>
                        <div class="credits-balance-label">Available Credits</div>
                    </div>

                    <div class="card" style="margin-bottom:24px;">
                        <div class="card-header">
                            <span class="card-title">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
                                    <path d="M12 18V6"/>
                                </svg>
                                Purchase Credits
                            </span>
                        </div>
                        <p style="color:rgba(255,255,255,0.5);font-size:13px;margin-bottom:20px;">
                            Select a credit package. Payment processing coming soon.
                        </p>

                        <div class="recharge-options">
                            <div class="recharge-card">
                                <div class="recharge-amount">50</div>
                                <div class="recharge-price">Basic Pack</div>
                                <button class="btn btn-primary" disabled>Coming Soon</button>
                            </div>
                            <div class="recharge-card">
                                <div class="recharge-amount">150</div>
                                <div class="recharge-price">Value Pack</div>
                                <button class="btn btn-primary" disabled>Coming Soon</button>
                            </div>
                            <div class="recharge-card">
                                <div class="recharge-amount">300</div>
                                <div class="recharge-price">Pro Pack</div>
                                <button class="btn btn-primary" disabled>Coming Soon</button>
                            </div>
                            <div class="recharge-card">
                                <div class="recharge-amount">500</div>
                                <div class="recharge-price">Enterprise</div>
                                <button class="btn btn-primary" disabled>Coming Soon</button>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <polyline points="12 6 12 12 16 14"/>
                                </svg>
                                Credit Usage
                            </span>
                        </div>
                        <div class="profile-item">
                            <label>Obfuscation (per file)</label>
                            <span>1 Credit</span>
                        </div>
                        <div class="profile-item">
                            <label>Slot - Starter Plan</label>
                            <span>30 Credits / Month</span>
                        </div>
                        <div class="profile-item">
                            <label>Slot - Professional Plan</label>
                            <span>50 Credits / Month</span>
                        </div>
                        <div class="profile-item">
                            <label>Slot - Enterprise Plan</label>
                            <span>100 Credits / Month</span>
                        </div>
                    </div>
                </section>

                <!-- ==================== REDEEM SECTION ==================== -->
                <section id="redeemPage" class="page">
                    <div class="page-header">
                        <h1>Redeem <span class="gradient">License Key</span></h1>
                        <p>Activate credits with VALAX license codes</p>
                    </div>

                    <div class="card" style="max-width:480px;margin:0 auto;text-align:center;">
                        <div style="margin-bottom:20px;">
                            <svg viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="1.5" width="56" height="56" style="opacity:0.8;">
                                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                            </svg>
                        </div>
                        <h2 style="margin-bottom:8px;color:#fff;">Enter License Code</h2>
                        <p style="color:rgba(255,255,255,0.5);font-size:14px;margin-bottom:24px;">
                            Enter your VALAX license code to activate credits
                        </p>
                        
                        <div style="margin-bottom:16px;">
                            <input type="text" id="cdk_input" class="input-field" placeholder="VALAX-XXXX-XXXX-XXXX" 
                                   style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:14px 16px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;text-align:center;">
                        </div>
                        
                        <button id="redeem_btn" class="btn btn-action" style="width:100%;padding:14px;">
                            ACTIVATE
                        </button>
                        
                        <div id="result_info" class="redeem-result" style="margin-top:12px;min-height:20px;"></div>
                    </div>
                </section>

                <!-- ==================== PROFILE SECTION ==================== -->
                <section id="profilePage" class="page">
                    <div class="page-header">
                        <h1>Profile <span class="gradient">Settings</span></h1>
                        <p>Manage your account information and security</p>
                    </div>

                    <div class="profile-grid">
                        <div class="card">
                            <div class="card-header">
                                <span class="card-title">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                                        <circle cx="12" cy="7" r="4"/>
                                    </svg>
                                    Account Information
                                </span>
                            </div>
                            <div class="profile-item">
                                <label>Username</label>
                                <span><?php echo $username; ?></span>
                            </div>
                            <div class="profile-item">
                                <label>Discord ID</label>
                                <span><?php echo htmlspecialchars($_SESSION['user_id'] ?? 'N/A'); ?></span>
                            </div>
                            <div class="profile-item">
                                <label>Credits Balance</label>
                                <span style="color:var(--gold);"><?php echo $credits; ?></span>
                            </div>
                            <div class="profile-item">
                                <label>Groups Joined</label>
                                <span><?php echo count($user_groups); ?></span>
                            </div>
                            <div class="profile-item">
                                <label>Account Status</label>
                                <span style="color:#10b981;">Active</span>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <span class="card-title">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                        <circle cx="9" cy="7" r="4"/>
                                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                    </svg>
                                    My Groups
                                </span>
                                <?php if (intval($credits) >= $group_cost): ?>
                                <button class="btn btn-gold" id="createGroupBtn" style="padding:6px 12px;font-size:11px;">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                                        <line x1="12" y1="5" x2="12" y2="19"/>
                                        <line x1="5" y1="12" x2="19" y2="12"/>
                                    </svg>
                                    Create (<?php echo $group_cost; ?> Credits)
                                </button>
                                <?php else: ?>
                                <span style="font-size:11px;color:rgba(255,255,255,0.4);">Need <?php echo $group_cost; ?> Credits</span>
                                <?php endif; ?>
                            </div>
                            
                            <?php if (empty($user_groups)): ?>
                            <div style="text-align:center;padding:20px;color:rgba(255,255,255,0.5);">
                                <p>You haven't joined any groups yet.</p>
                                <p style="font-size:12px;margin-top:8px;">Create one for <?php echo $group_cost; ?> credits or use an invite link!</p>
                            </div>
                            <?php else: ?>
                            <?php foreach ($user_groups as $group): ?>
                            <div class="profile-item" style="flex-wrap:wrap;gap:8px;">
                                <div style="flex:1;min-width:150px;">
                                    <label style="font-weight:600;color:#fff;"><?php echo htmlspecialchars($group['name']); ?></label>
                                    <div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:4px;">
                                        <?php echo $group['member_count']; ?> members
                                    </div>
                                </div>
                                <span style="font-size:11px;padding:2px 8px;border-radius:4px;background:rgba(124,77,255,0.2);color:var(--purple);">
                                    <?php echo ucfirst($group['role']); ?>
                                </span>
                            </div>
                            <?php endforeach; ?>
                            <?php endif; ?>
                            
                            <?php if ($pending_invite_count > 0): ?>
                            <div style="margin-top:12px;padding:12px;background:rgba(124,77,255,0.1);border:1px solid rgba(124,77,255,0.3);border-radius:8px;">
                                <span style="color:var(--purple);font-size:12px;">
                                    You have <?php echo $pending_invite_count; ?> pending group invitation(s)!
                                </span>
                            </div>
                            <?php endif; ?>
                        </div>
                    </div>

                    <div class="security-section">
                        <h3 style="color:#fff;margin-bottom:16px;">Security</h3>
                        
                        <div class="security-item">
                            <div class="security-item-info">
                                <div class="security-item-icon">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                                        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                                    </svg>
                                </div>
                                <div>
                                    <div class="security-item-title">Two-Factor Authentication</div>
                                    <div class="security-item-desc">
                                        <?php if ($twofa_enabled): ?>
                                        <span style="color:#10b981;">Enabled</span>
                                        <?php else: ?>
                                        <span style="color:#f59e0b;">Not Enabled</span>
                                        <?php endif; ?>
                                    </div>
                                </div>
                            </div>
                            <a href="2fa" class="btn btn-secondary" style="padding:8px 16px;font-size:12px;">
                                <?php echo $twofa_enabled ? 'Manage 2FA' : 'Enable 2FA'; ?>
                            </a>
                        </div>

                        <div class="security-item">
                            <div class="security-item-info">
                                <div class="security-item-icon">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                                    </svg>
                                </div>
                                <div>
                                    <div class="security-item-title">Invite Link</div>
                                    <div class="security-item-desc">Share to invite others to your group</div>
                                </div>
                            </div>
                            <button class="btn btn-secondary" id="copyInviteBtn" style="padding:8px 16px;font-size:12px;">Copy Link</button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    </div>

    <!-- Toast 通知 -->
    <div id="toast" class="toast">
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span id="toast-message">Success!</span>
    </div>

    <!-- Invite Modal -->
    <div id="inviteModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h3>Invite Member</h3>
                <button class="btn btn-secondary" id="closeInviteModal" style="padding:6px 12px;font-size:11px;">Close</button>
            </div>
            <div class="modal-body">
                <div style="margin-bottom:16px;">
                    <label style="display:block;font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:8px;">Select Group</label>
                    <select id="inviteGroupSelect" style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;color:#fff;font-size:13px;">
                        <?php foreach ($user_groups as $group): ?>
                        <?php if ($group['role'] === 'owner' || $group['role'] === 'admin'): ?>
                        <option value="<?php echo $group['id']; ?>"><?php echo htmlspecialchars($group['name']); ?> (<?php echo ucfirst($group['role']); ?>)</option>
                        <?php endif; ?>
                        <?php endforeach; ?>
                    </select>
                </div>
                <p style="color:rgba(255,255,255,0.6);margin-bottom:16px;">
                    Share this invite link with others to join your group:
                </p>
                <div style="display:flex;gap:8px;margin-bottom:20px;">
                    <input type="text" id="inviteLinkInput" readonly 
                           style="flex:1;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:12px;" 
                           value="">
                    <button class="btn btn-primary" id="copyInviteLinkBtn">Copy</button>
                    <button class="btn btn-secondary" id="regenerateLinkBtn" title="Regenerate Link">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                            <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                        </svg>
                    </button>
                </div>
                <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0;">
                <p style="color:rgba(255,255,255,0.4);font-size:12px;margin-bottom:12px;">
                    Or invite by Discord ID:
                </p>
                <div style="display:flex;gap:8px;">
                    <input type="text" id="manualDiscordId" placeholder="Enter Discord ID..." 
                           style="flex:1;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;color:#fff;font-size:13px;">
                    <button class="btn btn-secondary" id="addDiscordIdBtn">Invite</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Create Group Modal -->
    <div id="createGroupModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h3>Create New Group</h3>
                <button class="btn btn-secondary" id="closeCreateGroupModal" style="padding:6px 12px;font-size:11px;">Close</button>
            </div>
            <div class="modal-body">
                <div style="background:rgba(202,187,85,0.1);border:1px solid rgba(202,187,85,0.3);border-radius:8px;padding:12px;margin-bottom:20px;">
                    <p style="color:var(--gold);font-size:13px;">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" style="vertical-align:middle;margin-right:6px;">
                            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        Creating a group costs <strong><?php echo $group_cost; ?> credits</strong>
                    </p>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="display:block;font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:8px;">Group Name</label>
                    <input type="text" id="newGroupName" placeholder="My Awesome Group" maxlength="50"
                           style="width:100%;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:14px 16px;color:#fff;font-size:14px;">
                </div>
                <button class="btn btn-primary btn-full" id="confirmCreateGroupBtn" style="padding:14px;">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                        <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Create Group
                </button>
            </div>
        </div>
    </div>

    <!-- Pending Invites Modal -->
    <div id="pendingInvitesModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h3>Group Invitations</h3>
                <button class="btn btn-secondary" id="closePendingInvitesModal" style="padding:6px 12px;font-size:11px;">Close</button>
            </div>
            <div class="modal-body">
                <div id="pendingInvitesList">
                    <div style="text-align:center;padding:20px;color:rgba(255,255,255,0.5);">
                        <p>Loading invitations...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    console.log("JS LOADED - dashboard.php");

    // =====================================================
    // 全局变量
    // =====================================================
    var CURRENT_GROUP_ID = <?php echo json_encode($current_group_id); ?>;
    var USER_GROUPS = <?php echo json_encode($user_groups); ?>;
    var PLAN_PRICES = <?php echo json_encode(array_column($plan_prices, 'price', null)); ?>;
    var PENDING_INVITE_COUNT = <?php echo json_encode($pending_invite_count); ?>;
    var GROUP_COST = <?php echo json_encode($group_cost); ?>;

    // =====================================================
    // Cookie 工具函数
    // =====================================================
    function setCookie(name, value, days) {
        var expires = "";
        if (days) {
            var date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "") + expires + "; path=/";
    }

    function getCookie(name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
        }
        return null;
    }

    // =====================================================
    // Toast 通知
    // =====================================================
    function showToast(msg, type) {
        type = type || 'success';
        var toast = document.getElementById('toast');
        if (toast) {
            document.getElementById('toast-message').textContent = msg;
            toast.className = 'toast ' + type + ' show';
            setTimeout(function() { toast.classList.remove('show'); }, 3000);
        }
    }

    // =====================================================
    // 页面切换系统 (稳定版本)
    // =====================================================
    document.addEventListener("DOMContentLoaded", function () {
        console.log("Dashboard Init OK");

        // 获取所有导航按钮和页面
        const buttons = document.querySelectorAll("[data-page]");
        const pages = document.querySelectorAll(".page");

        // 页面切换函数
        function switchPage(pageId) {
            // 隐藏所有页面
            pages.forEach(function(p) {
                p.classList.remove("active");
                p.style.display = "none";
            });

            // 显示目标页面
            const target = document.getElementById(pageId);
            if (target) {
                target.style.display = "block";
                target.classList.add("active");
            } else {
                console.error("Page not found:", pageId);
            }

            // 更新导航高亮
            buttons.forEach(function(btn) {
                btn.classList.remove("active");
                if (btn.getAttribute("data-page") === pageId) {
                    btn.classList.add("active");
                }
            });

            // 更新标题
            const pageTitles = {
                'homePage': 'Dashboard',
                'hostingPage': 'Hosting',
                'creditsPage': 'Credits',
                'redeemPage': 'Redeem',
                'profilePage': 'Profile'
            };
            const titleEl = document.getElementById('topbar-title');
            if (titleEl && pageTitles[pageId]) {
                titleEl.textContent = pageTitles[pageId];
            }

            console.log("Switch to:", pageId);
        }

        // 绑定按钮点击
        buttons.forEach(function(btn) {
            btn.addEventListener("click", function(e) {
                e.preventDefault();
                const page = this.getAttribute("data-page");
                if (page) {
                    switchPage(page);
                }
            });
        });

        // 初始化（只显示 active）
        pages.forEach(function(p) {
            p.style.display = "none";
        });
        const activePage = document.querySelector(".page.active");
        if (activePage) {
            activePage.style.display = "block";
        } else if (pages.length > 0) {
            pages[0].style.display = "block";
            pages[0].classList.add("active");
        }

        console.log("Pages found:", pages.length);
        console.log("Buttons found:", buttons.length);
    });

        // =====================================================
        // Group Dropdown
        // =====================================================
        const groupDropdown = document.getElementById('groupDropdown');
        const groupDropdownMenu = document.getElementById('groupDropdownMenu');

        if (groupDropdown && groupDropdownMenu) {
            groupDropdown.addEventListener('click', () => {
                groupDropdown.classList.toggle('active');
                groupDropdownMenu.classList.toggle('show');
            });

            document.addEventListener('click', (e) => {
                if (!groupDropdown.contains(e.target)) {
                    groupDropdown.classList.remove('active');
                    groupDropdownMenu.classList.remove('show');
                }
            });
        }

        // =====================================================
        // Buy Slot Button - 显示/隐藏 Plans
        // =====================================================
        const buySlotBtn = document.getElementById('buySlotBtn');
        const plansSection = document.getElementById('plansSection');
        const closePlansBtn = document.getElementById('closePlansBtn');

        if (buySlotBtn && plansSection) {
            buySlotBtn.addEventListener('click', () => {
                plansSection.classList.toggle('hidden');
                buySlotBtn.innerHTML = plansSection.classList.contains('hidden') 
                    ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg> Buy Slot'
                    : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Hide Plans';
            });
        }

        if (closePlansBtn && plansSection) {
            closePlansBtn.addEventListener('click', () => {
                plansSection.classList.add('hidden');
                if (buySlotBtn) {
                    buySlotBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg> Buy Slot';
                }
            });
        }

        // Plan 选择按钮
        document.querySelectorAll('.select-plan-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const plan = btn.dataset.plan;
                const cost = parseInt(btn.dataset.cost);
                const currentCredits = parseInt(document.getElementById('user-credits').textContent);

                if (currentCredits < cost) {
                    showToast('Insufficient credits!', 'error');
                    return;
                }

                if (!confirm(`Purchase ${plan} plan for ${cost} credits?`)) return;

                btn.disabled = true;
                btn.textContent = 'Processing...';

                try {
                    const fd = new FormData();
                    fd.append('action', 'purchase_slot');
                    fd.append('plan_type', plan);
                    fd.append('group_id', CURRENT_GROUP_ID);

                    const res = await fetch('hosting_action', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.status === 'success') {
                        showToast('Slot purchased successfully!', 'success');
                        // 更新 credits 显示
                        document.getElementById('user-credits').textContent = data.new_balance;
                        document.getElementById('stat-credits').textContent = data.new_balance;
                        // 刷新页面
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showToast(data.message || 'Purchase failed', 'error');
                    }
                } catch (e) {
                    showToast('Connection error', 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = `Select ${plan.charAt(0).toUpperCase() + plan.slice(1)}`;
                }
            });
        });

        // =====================================================
        // Manage Slot 按钮
        // =====================================================
        document.querySelectorAll('.manage-slot-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const slotId = btn.dataset.slotId;
                window.location.href = 'hosting_action?action=manage&slot_id=' + encodeURIComponent(slotId);
            });
        });

        // Copy Loader 按钮
        document.querySelectorAll('.copy-loader-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const slotId = btn.dataset.slotId;
                // 使用本地 fetch.php 端点
                const loaderCmd = `loadstring(game:HttpGet("https://valaxscrub.shop/fetch?id=${slotId}"))()`;
                navigator.clipboard.writeText(loaderCmd);
                showToast('Loader copied!', 'success');
            });
        });

        // =====================================================
        // Redeem 功能
        // =====================================================
        const redeemBtn = document.getElementById('redeem_btn');
        const cdkInput = document.getElementById('cdk_input');
        const resultInfo = document.getElementById('result_info');

        if (redeemBtn) {
            redeemBtn.addEventListener('click', async () => {
                const val = cdkInput.value.trim();
                if (!val) return;

                redeemBtn.disabled = true;
                redeemBtn.textContent = 'VERIFYING...';

                try {
                    const fd = new FormData();
                    fd.append('cdk_code', val);

                    const res = await fetch('redeem', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.status === 'success') {
                        resultInfo.textContent = 'SUCCESS: +' + data.details.added_credits + ' Credits!';
                        resultInfo.style.color = '#10b981';
                        document.getElementById('user-credits').textContent = data.new_total;
                        document.getElementById('stat-credits').textContent = data.new_total;
                        cdkInput.value = '';
                        showToast('Credits added!', 'success');
                    } else {
                        resultInfo.textContent = 'ERROR: ' + data.message;
                        resultInfo.style.color = '#ef4444';
                        showToast(data.message, 'error');
                    }
                } catch (e) {
                    resultInfo.textContent = 'ERROR: Connection failed';
                    resultInfo.style.color = '#ef4444';
                    showToast('Connection failed', 'error');
                } finally {
                    redeemBtn.disabled = false;
                    redeemBtn.textContent = 'ACTIVATE';
                }
            });
        }

        // =====================================================
        // Create Group Modal
        // =====================================================
        const createGroupBtn = document.getElementById('createGroupBtn');
        const createGroupModal = document.getElementById('createGroupModal');
        const closeCreateGroupModal = document.getElementById('closeCreateGroupModal');
        const confirmCreateGroupBtn = document.getElementById('confirmCreateGroupBtn');
        const newGroupNameInput = document.getElementById('newGroupName');

        if (createGroupBtn && createGroupModal) {
            createGroupBtn.addEventListener('click', () => {
                createGroupModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                newGroupNameInput.focus();
            });
        }

        if (closeCreateGroupModal && createGroupModal) {
            closeCreateGroupModal.addEventListener('click', () => {
                createGroupModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            });
        }

        if (confirmCreateGroupBtn) {
            confirmCreateGroupBtn.addEventListener('click', async () => {
                const name = newGroupNameInput.value.trim();
                if (!name || name.length < 2) {
                    showToast('Group name must be at least 2 characters', 'error');
                    return;
                }

                confirmCreateGroupBtn.disabled = true;
                confirmCreateGroupBtn.textContent = 'Creating...';

                try {
                    const fd = new FormData();
                    fd.append('action', 'create');
                    fd.append('name', name);

                    const res = await fetch('group', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.success) {
                        showToast('Group created successfully!', 'success');
                        createGroupModal.style.display = 'none';
                        document.body.style.overflow = 'auto';
                        newGroupNameInput.value = '';
                        // 刷新页面
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showToast(data.error || 'Failed to create group', 'error');
                    }
                } catch (e) {
                    showToast('Connection error', 'error');
                } finally {
                    confirmCreateGroupBtn.disabled = false;
                    confirmCreateGroupBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Create Group';
                }
            });
        }

        // =====================================================
        // Pending Invites Modal
        // =====================================================
        const pendingInvitesModal = document.getElementById('pendingInvitesModal');
        const closePendingInvitesModal = document.getElementById('closePendingInvitesModal');
        const pendingInvitesList = document.getElementById('pendingInvitesList');

        // 点击待处理邀请区域打开 Modal
        const pendingInviteNotice = document.querySelector('[id="pendingInvitesModal"], .pending-invite-notice');
        if (pendingInvitesModal) {
            // 通过 AJAX 加载并显示待处理邀请
            async function loadPendingInvites() {
                try {
                    const res = await fetch('group?action=get_pending_invites');
                    const data = await res.json();
                    
                    if (data.success && data.invites && data.invites.length > 0) {
                        let html = '';
                        data.invites.forEach(invite => {
                            const date = new Date(invite.created_at).toLocaleDateString();
                            html += `
                                <div style="background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:16px;margin-bottom:12px;">
                                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                                        <div>
                                            <div style="color:#fff;font-weight:600;">${escapeHtml(invite.group_name)}</div>
                                            <div style="color:rgba(255,255,255,0.5);font-size:12px;margin-top:4px;">
                                                Invited by ${escapeHtml(invite.inviter_name || 'Unknown')}
                                            </div>
                                        </div>
                                        <span style="font-size:11px;color:rgba(255,255,255,0.4);">${date}</span>
                                    </div>
                                    <div style="display:flex;gap:8px;">
                                        <button class="btn btn-primary accept-invite-btn" data-invite-id="${invite.id}" style="flex:1;padding:10px;font-size:12px;">Accept</button>
                                        <button class="btn btn-secondary decline-invite-btn" data-invite-id="${invite.id}" style="flex:1;padding:10px;font-size:12px;">Decline</button>
                                    </div>
                                </div>
                            `;
                        });
                        pendingInvitesList.innerHTML = html;

                        // 绑定按钮事件
                        pendingInvitesList.querySelectorAll('.accept-invite-btn').forEach(btn => {
                            btn.addEventListener('click', async () => {
                                const inviteId = btn.dataset.inviteId;
                                btn.disabled = true;
                                btn.textContent = '...';
                                
                                try {
                                    const fd = new FormData();
                                    fd.append('action', 'respond_invite');
                                    fd.append('invite_id', inviteId);
                                    fd.append('response', 'accept');
                                    
                                    const res = await fetch('group', { method: 'POST', body: fd });
                                    const data = await res.json();
                                    
                                    if (data.success) {
                                        showToast(data.message, 'success');
                                        loadPendingInvites(); // 重新加载
                                        setTimeout(() => window.location.reload(), 1000);
                                    } else {
                                        showToast(data.error, 'error');
                                        btn.disabled = false;
                                        btn.textContent = 'Accept';
                                    }
                                } catch (e) {
                                    showToast('Connection error', 'error');
                                    btn.disabled = false;
                                    btn.textContent = 'Accept';
                                }
                            });
                        });

                        pendingInvitesList.querySelectorAll('.decline-invite-btn').forEach(btn => {
                            btn.addEventListener('click', async () => {
                                const inviteId = btn.dataset.inviteId;
                                btn.disabled = true;
                                btn.textContent = '...';
                                
                                try {
                                    const fd = new FormData();
                                    fd.append('action', 'respond_invite');
                                    fd.append('invite_id', inviteId);
                                    fd.append('response', 'decline');
                                    
                                    const res = await fetch('group', { method: 'POST', body: fd });
                                    const data = await res.json();
                                    
                                    if (data.success) {
                                        showToast(data.message, 'success');
                                        loadPendingInvites(); // 重新加载
                                    } else {
                                        showToast(data.error, 'error');
                                        btn.disabled = false;
                                        btn.textContent = 'Decline';
                                    }
                                } catch (e) {
                                    showToast('Connection error', 'error');
                                    btn.disabled = false;
                                    btn.textContent = 'Decline';
                                }
                            });
                        });
                    } else {
                        pendingInvitesList.innerHTML = '<div style="text-align:center;padding:20px;color:rgba(255,255,255,0.5);"><p>No pending invitations</p></div>';
                    }
                } catch (e) {
                    pendingInvitesList.innerHTML = '<div style="text-align:center;padding:20px;color:#ef4444;"><p>Failed to load invitations</p></div>';
                }
            }

            // 页面加载时检查并显示通知
            if (PENDING_INVITE_COUNT > 0) {
                // 创建通知气泡
                const noticeHtml = '<div id="pendingInviteBanner" style="background:linear-gradient(135deg,rgba(124,77,255,0.2),rgba(124,77,255,0.1));border:1px solid rgba(124,77,255,0.4);border-radius:12px;padding:16px;margin-bottom:20px;cursor:pointer;" onclick="openPendingInvites()"><div style="display:flex;align-items:center;gap:12px;"><div style="width:40px;height:40px;background:rgba(124,77,255,0.3);border-radius:10px;display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2" width="20" height="20"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg></div><div style="flex:1;"><div style="color:#fff;font-weight:600;">You have ' + PENDING_INVITE_COUNT + ' Group Invitation(s)!</div><div style="color:rgba(255,255,255,0.6);font-size:12px;margin-top:2px;">Click to view and respond</div></div><svg viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2" width="20" height="20"><polyline points="9 18 15 12 9 6"/></svg></div></div>';
                const hostingSection = document.getElementById('page-hosting');
                if (hostingSection) {
                    const header = hostingSection.querySelector('.page-header');
                    if (header) {
                        header.insertAdjacentHTML('afterend', noticeHtml);
                    }
                }
            }

            // 全局函数用于打开待处理邀请
            window.openPendingInvites = function() {
                pendingInvitesModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                loadPendingInvites();
            };
        }

        if (closePendingInvitesModal && pendingInvitesModal) {
            closePendingInvitesModal.addEventListener('click', () => {
                pendingInvitesModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            });
        }

        // =====================================================
        // Invite Modal - Updated
        // =====================================================
        const inviteMemberBtn = document.getElementById('inviteMemberBtn');
        const inviteModal = document.getElementById('inviteModal');
        const closeInviteModal = document.getElementById('closeInviteModal');
        const copyInviteLinkBtn = document.getElementById('copyInviteLinkBtn');
        const copyInviteBtn = document.getElementById('copyInviteBtn');
        const inviteGroupSelect = document.getElementById('inviteGroupSelect');
        const regenerateLinkBtn = document.getElementById('regenerateLinkBtn');

        async function loadInviteLink(groupId) {
            try {
                const fd = new FormData();
                fd.append('action', 'invite_by_link');
                fd.append('group_id', groupId);

                const res = await fetch('group', { method: 'POST', body: fd });
                const data = await res.json();

                if (data.success) {
                    document.getElementById('inviteLinkInput').value = data.invite_link;
                } else {
                    showToast(data.error || 'Failed to get invite link', 'error');
                }
            } catch (e) {
                showToast('Connection error', 'error');
            }
        }

        if (inviteMemberBtn && inviteModal) {
            inviteMemberBtn.addEventListener('click', () => {
                inviteModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                
                // 加载当前选中的组的邀请链接
                const selectedGroup = inviteGroupSelect ? inviteGroupSelect.value : CURRENT_GROUP_ID;
                if (selectedGroup) {
                    loadInviteLink(selectedGroup);
                }
            });
        }

        if (inviteGroupSelect) {
            inviteGroupSelect.addEventListener('change', () => {
                loadInviteLink(inviteGroupSelect.value);
            });
        }

        if (regenerateLinkBtn) {
            regenerateLinkBtn.addEventListener('click', async () => {
                regenerateLinkBtn.disabled = true;
                regenerateLinkBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" style="animation:spin 1s linear infinite;"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>';
                
                try {
                    const fd = new FormData();
                    fd.append('action', 'regenerate_link');
                    fd.append('group_id', inviteGroupSelect.value);

                    const res = await fetch('group', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.success) {
                        document.getElementById('inviteLinkInput').value = data.invite_link;
                        showToast('Link regenerated!', 'success');
                    } else {
                        showToast(data.error || 'Failed to regenerate', 'error');
                    }
                } catch (e) {
                    showToast('Connection error', 'error');
                } finally {
                    regenerateLinkBtn.disabled = false;
                    regenerateLinkBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>';
                }
            });
        }

        if (closeInviteModal && inviteModal) {
            closeInviteModal.addEventListener('click', () => {
                inviteModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            });
        }

        inviteModal && inviteModal.addEventListener('click', (e) => {
            if (e.target === inviteModal) {
                inviteModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });

        if (copyInviteLinkBtn) {
            copyInviteLinkBtn.addEventListener('click', () => {
                const link = document.getElementById('inviteLinkInput').value;
                if (link) {
                    navigator.clipboard.writeText(link);
                    showToast('Invite link copied!', 'success');
                }
            });
        }

        if (copyInviteBtn) {
            copyInviteBtn.addEventListener('click', () => {
                const link = document.getElementById('inviteLinkInput').value;
                if (link) {
                    navigator.clipboard.writeText(link);
                    showToast('Invite link copied!', 'success');
                }
            });
        }

        // =====================================================
        // Add Discord ID to group - Updated
        // =====================================================
        const addDiscordIdBtn = document.getElementById('addDiscordIdBtn');
        const manualDiscordId = document.getElementById('manualDiscordId');

        if (addDiscordIdBtn) {
            addDiscordIdBtn.addEventListener('click', async () => {
                const discordId = manualDiscordId.value.trim();
                if (!discordId || !/^\d+$/.test(discordId)) {
                    showToast('Please enter a valid Discord ID', 'error');
                    return;
                }

                addDiscordIdBtn.disabled = true;
                addDiscordIdBtn.textContent = 'Inviting...';

                try {
                    const fd = new FormData();
                    fd.append('action', 'invite_by_discord_id');
                    fd.append('group_id', inviteGroupSelect.value);
                    fd.append('discord_id', discordId);

                    const res = await fetch('group', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.success) {
                        showToast('Invitation sent!', 'success');
                        manualDiscordId.value = '';
                    } else {
                        showToast(data.error || 'Failed to send invitation', 'error');
                    }
                } catch (e) {
                    showToast('Connection error', 'error');
                } finally {
                    addDiscordIdBtn.disabled = false;
                    addDiscordIdBtn.textContent = 'Invite';
                }
            });
        }

        // =====================================================
        // Helper Functions
        // =====================================================
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 添加 spin 动画
        const style = document.createElement('style');
        style.textContent = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
        document.head.appendChild(style);
    });
</body>
</html>
