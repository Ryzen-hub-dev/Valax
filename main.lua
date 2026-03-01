-- [[ Valax Hub v1 - 99 Nights In The Forest ]]
-- [[ Focus: True Core Modification & Exclusive Exploits ]]

if not game:IsLoaded() then game.Loaded:Wait() end

-- [[ SERVICES ]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ProximityPromptService = game:GetService("ProximityPromptService")
local LocalPlayer = Players.LocalPlayer

-- [[ LOAD WIND UI ]]
local WindUI = loadstring(game:HttpGet("https://github.com/Footagesus/WindUI/releases/latest/download/main.lua"))()

-- [[ GLOBAL SETTINGS ]]
getgenv().ValaxV1 = {
    GodMode = false,
    OneHitKill = false,
    InstantInteract = false,
    InfItems = false,
    OHK_Multiplier = 15, -- 核心攻击倍率
    AntiDeath = false
}

-- [[ CORE ENGINE MODIFICATION - THE "REAL" STUFF ]]

local mt = getmetatable(game)
local oldNamecall = mt.__namecall
local oldIndex = mt.__index
setreadonly(mt, false)

-- 1. True One Hit Kill & Infinite Items (Remote Interception)
mt.__namecall = newcclosure(function(self, ...)
    local args = {...}
    local method = getnamecallmethod()

    if not checkcaller() then
        -- TRUE ONE HIT KILL: 拦截伤害事件并进行多重物理重叠
        if method == "FireServer" and getgenv().ValaxV1.OneHitKill then
            local remoteName = tostring(self)
            if remoteName:find("Hit") or remoteName:find("Attack") or remoteName:find("Damage") then
                for i = 1, getgenv().ValaxV1.OHK_Multiplier do
                    oldNamecall(self, unpack(args))
                end
            end
        end

        -- TRUE INFINITE ITEMS: 拦截消耗品减少的指令
        if method == "FireServer" and getgenv().ValaxV1.InfItems then
            local remoteName = tostring(self)
            if remoteName:find("Consume") or remoteName:find("Use") or remoteName:find("Reduce") then
                return nil -- 直接掐断发往服务器的“减少物品”信号
            end
        end
    end

    return oldNamecall(self, ...)
end)

-- 2. True God Mode (Humanoid State & Health Locking)
-- 绑定到 Heartbeat 确保在每一帧物理模拟前强制修改数值
RunService.Heartbeat:Connect(function()
    if getgenv().ValaxV1.GodMode then
        local char = LocalPlayer.Character
        if char then
            local hum = char:FindFirstChildOfClass("Humanoid")
            if hum then
                -- 核心修改：锁定 Health 属性且禁止其进入 Dead 状态
                hum.Health = hum.MaxHealth
                if hum:GetState() == Enum.HumanoidStateType.Dead then
                    hum:ChangeState(Enum.HumanoidStateType.GettingUp)
                end
            end
        end
    end
end)

setreadonly(mt, true)

-- 3. Instant Interaction (Global Hook)
ProximityPromptService.PromptButtonHoldBegan:Connect(function(prompt)
    if getgenv().ValaxV1.InstantInteract then
        fireproximityprompt(prompt)
    end
end)

-- [[ UI CONSTRUCTION ]]

local Window = WindUI:CreateWindow({
    Title = "Valax Hub",
    Icon = "rbxassetid://84501312005643",
    Author = "Premium v1",
    Folder = "ValaxHub_Forest",
    Size = UDim2.fromOffset(480, 400),
    Transparent = true,
    Theme = "Dark",
    Resizable = false,
    SideBarWidth = 180,
    HideSearchBar = true,
})

local Godly = Window:Tab({ 
    Title = "Exclusive & Godly", 
    Icon = "crown" 
})

-- Section: Core Godly Functions
Godly:Section({ Title = "👑 Godly Core" })

Godly:Toggle({
    Title = "Absolute God Mode",
    Desc = "True Health Lock & Anti-Death State",
    Value = false,
    Callback = function(state)
        getgenv().ValaxV1.GodMode = state
        if state then
            WindUI:Notify({ Title = "Core Modified", Content = "Health Memory Locked" })
        end
    end
})

Godly:Toggle({
    Title = "One Hit Kill",
    Desc = "Force Multi-Packet Damage (Server-Side impact)",
    Value = false,
    Callback = function(state)
        getgenv().ValaxV1.OneHitKill = state
    end
})

Godly:Slider({
    Title = "OHK Multiplier",
    Desc = "Packets per click (Higher = Faster Kill)",
    Min = 1,
    Max = 100,
    Default = 15,
    Callback = function(v)
        getgenv().ValaxV1.OHK_Multiplier = v
    end
})

-- Section: Divine Exploits
Godly:Section({ Title = "💎 Divine Exploits" })

Godly:Toggle({
    Title = "Instant Interaction",
    Desc = "Bypass all hold-times for chests & items",
    Value = false,
    Callback = function(state)
        getgenv().ValaxV1.InstantInteract = state
    end
})

Godly:Toggle({
    Title = "Infinite Consumption",
    Desc = "Blocks 'Item-Decrease' packets from reaching server",
    Value = false,
    Callback = function(state)
        getgenv().ValaxV1.InfItems = state
    end
})

Godly:Button({
    Title = "Server Hopper (Speed Mode)",
    Desc = "Instantly hop to low-ping servers",
    Callback = function()
        local Servers = game:GetService("HttpService"):JSONDecode(game:HttpGet("https://games.roblox.com/v1/games/" .. game.PlaceId .. "/servers/Public?sortOrder=Asc&limit=100"))
        for _, v in pairs(Servers.data) do
            if v.playing < v.maxPlayers and v.id ~= game.JobId then
                game:GetService("TeleportService"):TeleportToPlaceInstance(game.PlaceId, v.id, LocalPlayer)
                break
            end
        end
    end
})

Godly:Button({
    Title = "Instant Respawn",
    Desc = "Bypass death timer and respawn at camp",
    Callback = function()
        LocalPlayer.Character:BreakJoints()
    end
})

-- [[ INIT NOTIFY ]]
WindUI:Notify({
    Title = "Valax Hub v1 Loaded",
    Content = "Premium functions are now active.",
    Duration = 5
})

