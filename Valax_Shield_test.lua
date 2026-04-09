-- Lua VM Protector
-- Seed: 88801

local bit32=bit32 or {}
if not bit32.rshift then bit32.rshift=function(v,n)return math.floor((v%0x100000000)/(2^n))end end
if not bit32.lshift then bit32.lshift=function(v,n)return((v%0x100000000)*(2^n))%0x100000000 end end
if not bit32.band then bit32.band=function(...)local r=0xFFFFFFFF for _,v in ipairs({...})do r=r&(v%0x100000000)end return r end end
if not bit32.bor then bit32.bor=function(...)local r=0 for _,v in ipairs({...})do r=r|(v%0x100000000)end return r end end
if not bit32.bxor then bit32.bxor=function(a,b)return((a%0x100000000)~(b%0x100000000))%0x100000000 end end
if not bit32.bnot then bit32.bnot=function(v)return((~v)%0x100000000)end end

local d = "gMjAKcHJpbnQoeCkKcHJpbnQoIkhlbGxvIFdvcmxkIikKbG9jYWwgeCA9IDEwICs"
local k = 749935
local s = 88801

local function ihgr(c)
    local r = ""
    for i = 1, #c do
        local b = string.byte(c, i)
        r = r .. string.char((b - 97 + k + i) % 256 + 65)
    end
    return r
end

local function drbc()
    local t = {}
    local p = ihgr(d)
    for i = 1, #p do
        local b = string.byte(p, i)
        t[i] = string.char(b % 26 + 97)
    end
    return table.concat(t)
end

local slbk = {
    ptzs = {},
    running = true,
    fpdj = 1
}

local decoded = drbc()

for i = 1, #d do
    slbk.ptzs[i] = string.char(string.byte(d, i) % 128)
end

local i = 1
while slbk.running do
    local c = slbk.ptzs[i]
    if not c then
        slbk.running = false
        break
    end
    slbk.ptzs[i] = c
    i = i + 1
end

loadstring(decoded)()