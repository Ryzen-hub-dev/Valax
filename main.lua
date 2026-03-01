-- [[ Valax Hub v1 - 99 Nights In The Forest ]]
-- [[ Final Stable Version - Core Modification ]]

-- 确保游戏完全加载
if not game:IsLoaded() then game.Loaded:Wait() end

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LocalPlayer = Players.LocalPlayer

-- 加载 WindUI 框架
local WindUI = loadstring(game:HttpGet("https://github.com/Footagesus/WindUI/releases/latest/download/main.lua"))()

-- [[ 核心功能配置表 ]]
getgenv().ValaxV1 = {
    GodMode = false,
    OneHitKill = false,
    InstantInteract = false,
    InfItems = false,
    OHK_Multiplier = 25 -- 秒杀强度
}

-- [[ 核心 Hook 逻辑 - 修复 setreadonly 报错 ]]
local function SecureHook()
    local mt = (debug and debug.getmetatable or getmetatable)(game)
    if type(mt) ~= "table" then return end
    
    -- 智能寻找执行器支持的读写权限修改函数
    local set_writeable = make_writeable or setreadonly or (function(t, b) 
        if setrawmetatable then setrawmetatable(t, b) end 
    end)
    
    if set_writeable then
        pcall(function()
            set_writeable(mt, false)
            local oldNamecall = mt.__namecall
            
            mt.__namecall = newcclosure(function(self, ...)
                local args = {...}
                local method = getnamecallmethod()
                
                if not checkcaller() then
                    -- 【核心功能：一击必杀】
                    -- 原理：在客户端发送伤害请求时，瞬间倍增数据包发往服务器
                    if method == "FireServer" and getgenv().ValaxV1.OneHitKill then
                        local rName = tostring(self)
                        if rName:find("Hit") or rName:find("Attack") or rName:find("Damage") then
                            for i = 1, getgenv().ValaxV1.OHK_Multiplier do
                                task.spawn(function() oldNamecall(self, unpack(args)) end)
                            end
                        end
                    end
                    
                    -- 【核心功能：无限物品】
                    -- 原理：掐断所有发往服务器的“减少/消耗物品”信号
                    if method == "FireServer" and getgenv().ValaxV1.InfItems then
                        local rName = tostring(self)
                        if rName:find("Consume") or rName:find("Use") or rName:find("Reduce") then
                            return nil 
                        end
                    end
                end
                return oldNamecall(self, ...)
            end)
            set_writeable(mt, true)
        end)
    end
end

-- 执行注入
SecureHook()

-- [[ 核心上帝模式 - 状态锁定 ]]
-- 使用 Heartbeat 以确保每一帧物理模拟前锁定状态，防止瞬间死亡
RunService.Heartbeat:Connect(function()
    if getgenv().ValaxV1.GodMode then
        local char = LocalPlayer.Character
        local hum = char and char:FindFirstChildOfClass("Humanoid")
        if hum then
            -- 强制锁定血量为最大值
            if hum.Health < hum.MaxHealth then
                hum.Health = hum.MaxHealth
            end
            -- 强制绕过死亡状态检查
            if hum:GetState() == Enum.HumanoidStateType.Dead then
                hum:ChangeState(Enum.HumanoidStateType.GettingUp)
                hum.Health = hum.MaxHealth
            end
        end
    end
end)

-- [[ 核心快速交互 ]]
-- 原理：直接调用底层交互触发，跳过 UI 进度条
ProximityPromptService.PromptButtonHoldBegan:Connect(function(prompt)
    if getgenv().ValaxV1.InstantInteract then
        fireproximityprompt(prompt)
    end
end)

-- [[ UI 绘制逻辑 ]]
local Window = WindUI:CreateWindow({
    Title = "Valax Hub",
    Icon = "rbxassetid://84501312005643",
    Author = "Valax Premium v1",
    Folder = "Valax_Forest_V1",
    Size = UDim2.fromOffset(480, 420),
    Transparent = true,
    Theme = "Dark",
    HideSearchBar = true,
})

local Godly = Window:Tab({ Title = "Exclusive & Godly", Icon = "crown" })

-- 第一部分：核心生存修改
Godly:Section({ Title = "🛡️ Core Immortality" })

Godly:Toggle({
    Title = "Absolute God Mode",
    Desc = "Force Health Lock & State Persistence",
    Value = false,
    Callback = function(state) 
        getgenv().ValaxV1.GodMode = state 
        if state then WindUI:Notify({Title = "Core", Content = "God Mode Injected!"}) end
    end
})

-- 第二部分：核心战斗修改
Godly:Section({ Title = "⚔️ Divine Offense" })

Godly:Toggle({
    Title = "One Hit Kill",
    Desc = "Server-Side Damage Multiplication",
    Value = false,
    Callback = function(state) getgenv().ValaxV1.OneHitKill = state end
})

Godly:Slider({
    Title = "OHK Intensity",
    Desc = "Packets per click (Higher = Deadlier)",
    Min = 1, Max = 100, Default = 25,
    Callback = function(v) getgenv().ValaxV1.OHK_Multiplier = v end
})

-- 第三部分：核心功能辅助
Godly:Section({ Title = "💎 Divine Utility" })

Godly:Toggle({
    Title = "Instant Interaction",
    Desc = "Zero-second Chest/Item collection",
    Value = false,
    Callback = function(state) getgenv().ValaxV1.InstantInteract = state end
})

Godly:Toggle({
    Title = "Infinite Consumption",
    Desc = "Prevents items from being subtracted",
    Value = false,
    Callback = function(state) getgenv().ValaxV1.InfItems = state end
})

-- 高级服务器功能
Godly:Button({
    Title = "Fast Server Hop",
    Desc = "Teleport to a new forest server",
    Callback = function()
        local Http = game:GetService("HttpService")
        local Servers = Http:JSONDecode(game:HttpGet("https://games.roblox.com/v1/games/" .. game.PlaceId .. "/servers/Public?sortOrder=Asc&limit=100"))
        for _, v in pairs(Servers.data) do
            if v.playing < v.maxPlayers and v.id ~= game.JobId then
                game:GetService("TeleportService"):TeleportToPlaceInstance(game.PlaceId, v.id, LocalPlayer)
                break
            end
        end
    end
})

-- 加载完成通知
WindUI:Notify({
    Title = "Valax Hub Loaded",
    Content = "Exclusive v1 functions are ready.",
    Duration = 5
})
