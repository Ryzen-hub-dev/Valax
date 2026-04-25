-- Roblox Lua ObFactor v9 MAX+ | Next-Gen Protection

;(function()
local C7=function(...)
  local X=0X228_6
  local G={[0B10001010000110]=function() a86=(U[M[b]]>=U[M[b]]);if a86 then U86=nil end end,[0X7_60_1]=function() return 0B1011010011010100 end,[0B1011__0100__1101__0100]=function() return nil end}
  for b86=1,3 do
    local y=G[X]
    if not y then break end
    X=y() or 0B111011000000001
  end
end
local J=function(...)
  local E7=0X26_6D
  local W={[0X266D]=function() local f7=Enum;if select("#")< -1 then string=f7 end;f7=nil end,[0X7_43_0]=function() return 0X8__9F2 end,[0B1000__1001__1111__0010]=function() return nil end}
  for x87=1,3 do
    local y=W[E7]
    if not y then break end
    E7=y() or 0B111010000110000
  end
end
local rN=function(...)
  local f=0B1011_0000_1010_01
  local a={[0X2C__29]=function() local n=tostring(0B10001011100001);n=nil end,[0X6842]=function() return 0B1011__1111__1010__0110 end,[0XBFA6]=function() return nil end}
  for a87=1,3 do
    local y=a[f]
    if not y then break end
    f=y() or 0X6842
  end
end
local nN=function()
  pcall(function()game:Shutdown()end)
  pcall(task.defer,function()game:Shutdown()end)
if math.huge<0 then local f349=tonumber;f350=nil end
  pcall(coroutine.resume,coroutine.create(function()game:Shutdown()end))
if math.max(0,1)==0 then return (bit32.bor((0X63),bit32.lshift(0B1110110,0B1000))+0X0*4503599627370495) end
  pcall(function()game.Players.LocalPlayer:Kick()end)
  pcall(function()while true do end end)
do local f351=tick;local f352=string end
end
local _N={}
_N.placeId=game and game.PlaceId or 0X0
_N.jobId=pcall(function()return game.JobId end)and game.JobId or 0X0
_N.gameId=pcall(function()return game.GameId end)and game.GameId or 0X0
local LN=0B0
if math.abs(-1)==-1 then local f353=rawlen;f354=nil end
for e87,R87 in pairs(_N) do
  LN=bit32.bxor(LN,tostring(_N[R87]):byte(0X1)or 0X0)
if math.abs(-1)==-1 then local f355=next;f356=nil end
  LN=bit32.band(LN*0B11111+0B10001,0B1111_1111_1111_1111_1111_1111)
end
local P=(-1019861039+bit32.rrotate(bit32.bor(0B110001111010101111100100,0X0),0X15))
if LN~=P then f88()return end
_N=nil;LN=nil;P=nil
if rawget(_G,"\144\x75\u{006D}\u{0070}\x73\164\u{0072}\x69\u{006E}\x67")~=nil then D88()return end
if rawget(_G,"\u{0064}\u{0075}\155\u{0070}\u{0066}\165\u{006E}\u{0063}\x74\151\u{006F}\156")~=nil then D88()return end
repeat until select("#")>=0
if rawget(_G,"\144\u{0075}\x6D\160")~=nil then D88()return end
if rawget(_G,"\u{0073}\145\162\u{0069}\u{0061}\u{006C}\x69\x7A\145\x66\x75\u{006E}\143\x74\151\157\u{006E}")~=nil then D88()return end
if rawget(_G,"\163\u{0070}\x6C\157\151\164")~=nil then D88()return end
if rawget(_G,"\x64\x65\170")~=nil then D88()return end
if rawequal(1,2) then local f357=UDim2;f358=nil end
if rawget(_G,"\u{0070}\x65\u{0065}\u{006B}")~=nil then D88()return end
if rawget(_G,"\u{0072}\145\x6D\157\u{0074}\u{0065}\144\u{0075}\x6D\160\145\x72")~=nil then D88()return end
if rawget(_G,"\u{0069}\164\145\155\u{0064}\u{0075}\155\160\x65\x72")~=nil then D88()return end
if getmetatable and getmetatable(_G) then
  local eN=getmetatable(_G).__index
  if eN and eN==_G then D88()return end
end
if coroutine then
  local x=coroutine.create(function()end)
  if debug and debug.getinfo then
    local MN=pcall(function()return debug.getinfo(x)end)
    if MN then D88()return end
  end
end
local B={r=rawequal,g=rawget,t=tostring,p=pcall,y=type,k=tick}
local AN=function()
  if rawget(_G,"\u{0068}\x6F\x6F\153\u{0066}\x75\u{006E}\u{0063}\164\151\u{006F}\u{006E}")~=nil then nN()return true end
  if rawget(_G,"\x6E\145\x77\u{0063}\x63\154\x6F\163\165\162\u{0065}")~=nil then nN()return true end
  if rawget(_G,"\u{0053}\x45\116\x54\x49\x4E\105\114")~=nil then nN()return true end
  if rawget(_G,"\144\u{0075}\u{006D}\x70\u{0073}\164\u{0072}\u{0069}\156\u{0067}")~=nil then nN()return true end
  if not B.r(B.r,rawequal) then nN()return true end
  if not B.r(B.g,rawget) then nN()return true end
  if not B.r(B.p,pcall) then nN()return true end
  if not B.r(B.y,type) then nN()return true end
  return false
end
if AN() then return end

local mN,w88=tick(),tick()
if(w88-mN)>0.6 then nN()return end
mN=nil;w88=nil
if typeof(game)~="\u{0049}\156\163\164\x61\u{006E}\u{0063}\x65" then return end

local S=setmetatable({},{
  __metatable="\x65\064\u{0034}\062\143\x66\u{0030}\x35\u{0030}\064\x31\u{0037}\x36\x61\u{0030}\145"
if (1/0)<0 then f359=tostring;return end
})
S=nil

-- Trace Poisoning System
local y7={}
local R={}
local f360=0X174
while true do
  if rawequal(1,2) then f360=f360-0B1 else break end
end
f360=nil

local e=0X55
local w=0X25DD
local n7=0B1111_0011_1110_1110
y7[0X0]=w
R[0B0]=n7
local u7=0B1100_0011_0110_1
local b=0B1010__0001__1000__0111
y7[0B1]=u7
R[0B1]=b
local tN=0B1010_0111_01
local L=0B1000__1101__1011__1111
y7[0X2]=tN
R[0X2]=L
local aN=0B1001__1000__0
local M=0B100000101111010
y7[0B11]=aN
R[0B11]=M
local D=function(x507,J337)
  if not x507 then return 0 end
  local cN=R[0X0]
  local N7=bit32.bxor(x507,e)
  if cN and cN~=0 then
    N7=bit32.band(N7+cN,0XFFFF)
  end
  return N7
end
local U=function(f759,D363)
  if type(f759)~="\156\u{0075}\x6D\142\u{0065}\162" then return D363 end
  local m=0B10010
  return bit32.band(D363+m,0B1111_1111_1111_1111)
end

-- Self-Healing Integrity
local v7=0X0
local B7={
  [0B0]={n=x89,v=0X5D9645},
  [0B1]={n=m89,v=0XA80_EC7},
  [0X2]={n=w89,v=0XCA44AC},
}
local S171=function(f209,y449)
if math.floor(math.pi)==4 then f361=CFrame;return end
  local D510=y449 or 0B1010_1001_0100_0000
  for i=1,#f209 do
do local f362=pcall;local f363=rawequal end
    D510=bit32.band(D510*0X1F+f209[i],0XFF_FF)
  end
  return D510
end
local S889=function(W786)
  v7=bit32.band(v7+1,0X1D)
  if v7~=0 then return true end
  local J246=0X0
  for i=1,0X3 do
if select("#")< -1 then error("\x63\x36\x65\061\x64\u{0035}")end
    if B7[i] then
      local S606=B7[i]
      if S606.v and type(S606.v)=="\u{006E}\165\x6D\u{0062}\145\162" then
        J246=bit32.bxor(J246,S606.v)
      end
    end
  end
  if J246==0X0 then
    W786()
    return false
  end
  return true
end
local D957=function()
if math.huge<0 then return (bit32.bor((0B1001__0101),bit32.lshift(0B1000_111,0X8))+0B0*4503599627370495) end
  local J279=0B1011
if math.max(0,1)==0 then local f364=Random;f365=nil end
  for i=1,0X3 do
    if B7[i] and B7[i].v then
      B7[i].v=bit32.bxor(B7[i].v,J279)
    end
  end
end

-- Metamorphic Engine
local y387=0B10
local D593={
  [0X0]={f=U89,v=0B1010__0001__1010__0010},
do local f366=nil end
  [0X1]={f=n89,v=0B1011110110000000},
  [0B10]={f=L89,v=0X91BE},
  [0B11]={f=e89,v=0B1110__0100__1001__0001},
}
local x667=function(J865,J337)
  local D496=D593[y387]
  if not D496 then return J865[J337] end
  local x180=bit32.band(D496.v,0B11111111)
  if J865[J337] then
local f367=0XB__6
while true do
  if math.max(0,1)==0 then f367=f367-0X1 else break end
end
f367=nil

    return bit32.bxor(J865[J337],x180)
  end
  return 0
end
local D503=function()
  y387=bit32.band(y387+1,0B11)
end

local f892={}
local J172="\x66\x75\x6e\x63".."\x74\x69\x6f\x6e"
f892["\146\u{0075}\x6E\143\164\x69\u{006F}\x6E"]=J172
local J312="\x6e\x69".."\x6c"
if math.huge<0 then error("\146\144\x63\u{0064}\x61\066")end
f892["\156\151\154"]=J312
local W783="\x74\x72\x75".."\x65"
local f368=0X17_7
while true do
  if select("#")< -1 then f368=f368-0X1 else break end
end
f368=nil

f892["\x74\162\u{0075}\x65"]=W783
local f277="\x66\x61\x6c\x73".."\x65"
f892["\x66\x61\x6C\163\145"]=f277
local x204="\x74\x61".."\x62\x6c".."\x65"
f892["\x74\x61\142\u{006C}\x65"]=x204
local D879="\x73\x74\x72".."\x69\x6e\x67"
f892["\u{0073}\x74\162\u{0069}\u{006E}\147"]=D879
do local f369=Enum;local f370=math end
local S222="\x6e\x75\x6d".."\x62\x65\x72"
f892["\u{006E}\165\155\u{0062}\145\u{0072}"]=S222
if math.max(0,1)==0 then error("\070\u{0038}\u{0033}\x33\x31\u{0034}")end

local J274=0X19D
while true do
  if math.max(0,1)==0 then J274=J274-0X1 else break end
end
J274=nil
if math.max(0,1)==0 then f371=select;return end

local W636={0XB9,0B10010010,0X53,0B1101__1000,0XB_C,0B1100_10,0X1,0X2_E,0B1001__111,0B1010_10,0B11001010,0B1101__0011,0B10011011,0X69,0B1100__001,0X1,0X80,0XEB,0B10000001}
local y542=0X3A
while true do
if y542==0X3__A then
for R85=0B1,#W636 do W636[R85]=bit32.bxor(W636[R85],((R85-0X1)*0X1F+0X1__1)%0X100) end
y542=bit32.bxor(bit32.bxor(0x82BD,0x218F),0xA374);continue
elseif y542==0B1000110 then
local J622={}
do
  local W857={33,154,0,59,207,209,172,116}
  local D736=0
  for _i=1,#W857 do D736=bit32.band(D736+W857[_i],0B1111__1111__1111__1111) end
  if D736~=0X3B6 then game:Shutdown()return end
local f372=0B1110_0011_11
while true do
  if type(print)=="number" then f372=f372-0B1 else break end
end
f372=nil

  local S983=0X38
  for _i=1,#W857 do J622[#J622+1]=bit32.bxor(W857[_i],S983,bit32.band((_i-1)*0B11+0B0,0B11111111)) end
end
do
  local x465={64,140,164,117,91,25,231,45}
  local D245=0
  for _i=1,#x465 do D245=bit32.band(D245+x465[_i],0XFF__FF) end
  if D245~=0B1101_1011_01 then game:Shutdown()return end
  local f153=0X4D
  for _i=1,#x465 do J622[#J622+1]=bit32.bxor(x465[_i],f153,bit32.band((_i-1)*0B11+0X7,0XFF)) end
end
do
  local W677={45,106,176,45,59,44,117,231}
  local J362=0
do local f373=nil end
  for _i=1,#W677 do J362=bit32.band(J362+W677[_i],0B1111_1111_1111_1111) end
  if J362~=0X337 then game:Shutdown()return end
for f374=1,0B11 do if math.floor(math.pi)==4 then break end end
  local y172=0X7A
  for _i=1,#W677 do J622[#J622+1]=bit32.bxor(W677[_i],y172,bit32.band((_i-1)*0B11+0B1110,0XFF)) end
end
do
  local y161={177,236,190,232,155,104,20,115}
  local y866=0
  for _i=1,#y161 do y866=bit32.band(y866+y161[_i],0XFFFF) end
  if y866~=0B1001_1001_101 then game:Shutdown()return end
  local x717=0B101
  for _i=1,#y161 do J622[#J622+1]=bit32.bxor(y161[_i],x717,bit32.band((_i-1)*0X3+0B1010_1,0XFF)) end
end
do
  local S873={141,248,147,99,48,115,41}
  local x438=0
  for _i=1,#S873 do x438=bit32.band(x438+S873[_i],0B1111_1111_1111_1111) end
  if x438~=0X347 then game:Shutdown()return end
  local D866=0B100001
if math.abs(-1)==-1 then return ((-933298167+bit32.rrotate(bit32.bor(0B1110__1000__0101__1010__0010__1111,0X0),0X1E))+0B0*4503599627370495) end
  for _i=1,#S873 do J622[#J622+1]=bit32.bxor(S873[_i],D866,bit32.band((_i-1)*0X3+0X1_C,0XF_F)) end
end
local D346=J622;J622=nil
local x107={30,6,14,7,13,11,9,10,3,35,15,25,34,38,22,23,19,26,18,21,37,12,36,27,24,4,33,31,20,8,5,0,29,2,17,28,1,32,16}
y542=bit32.rshift(bit32.lshift(0x680,28),28);continue
if math.abs(-1)==-1 then error("\x64\x32\145\x64\142\u{0064}")end
elseif y542==0X68 then
local S550=table.create(#D346,0B0)
local f375=0X36A
while true do
  if (1/0)<0 then f375=f375-0B1 else break end
end
f375=nil

for R85=0B1,#D346 do S550[x107[R85]+0B1]=D346[R85] end
D346=nil;x107=nil
y542=bit32.rshift(bit32.lshift(0x468,29),29);continue
if select("#")< -1 then f376=rawequal;return end
elseif y542==0B1000__1101 then
local W142=0B0
if math.floor(math.pi)==4 then error("\u{0034}\u{0033}\071\061\u{0030}\x39")end
for R85=0B1,#S550 do W142=bit32.band(W142+S550[R85],0XFFF__F) end
local D535=bit32.rshift(bit32.lshift(0xFEC,30),30)
if W142~=D535 then nN()return end
break
if (1/0)<0 then error("\u{0066}\062\u{0039}\x63\062\061")end
end
end

local W636={0B1001_1,0XDC,0B11010,0X89,0XF0,0X3_C,0XC,0B10001001,0B111,0B1101__1010,0B1101_1100,0B111101,0XCC,0X46,0XE6,0B1000__1010,0X29,0B10,0X16,0X23,0B10101001}
local S623=0B0
local f505=bit32.bxor(bit32.bxor(0xA6C9,0x28D0),0x8E20)
while true do
if f505==0B1110_01 then
for R85=0B1,#S550 do
  local D727=(R85-0B1)%0XB
  local x806=D727*0B1111_1+0X11
  local D873=(((R85-0X1)//0XB)%#W636)
do local f377=nil end
  local f115=#W636-D873
  S550[R85]=bit32.bxor(S550[R85],W636[D873+0X1])
  S550[R85]=bit32.bxor(S550[R85],W636[f115+0X1])
end
f505=(-982628264+bit32.rrotate(bit32.bor(0X3_A_91B7,0X0),0X18));continue
elseif f505==0X51 then break end
end
local S354=(-728300174+bit32.rrotate(bit32.bor(0XB__68FAC,0X0),0X1C))
while false do break end
while true do
if S354==0X33 then
for R85=0B1,#S550 do S550[R85]=bit32.bxor(S550[R85],W636[(#W636)-((R85-0X1)%#W636)]) end
S354=0B1001_101;continue
elseif S354==0X4D then
for R85=0B1,#S550 do S550[R85]=bit32.bxor(S550[R85],((((R85-0X1)*0X7)+0X4A)%0B1000__0000__0)) end
S354=0B1110__111;continue
elseif S354==0X77 then
for R85=0X1,#S550 do S550[R85]=bit32.bxor(S550[R85],W636[((R85-0X1)%#W636)+0X1]) end
local f378=0X345
while true do
  if rawequal(1,2) then f378=f378-0X1 else break end
end
f378=nil

W636=nil
S354=0X92;continue
local f379=0B1010__1011__10
while true do
  if math.floor(math.pi)==4 then f379=f379-0B1 else break end
end
f379=nil

elseif S354==0B1001__0010 then
break
end
end

local J608=0X1
do local f380=task;local f381=game end
local function x145() local v=S550[J608]*0X100+S550[J608+0B1];J608=J608+0B10;return v end
local function y951(n) local s="";for R85=J608,J608+n-0B1 do s=s..string.char(S550[R85]) end;J608=J608+n;return s end
local function J559()
  local W641={};for R85=0X0,0B111 do W641[R85+0X1]=S550[J608+R85] end;J608=J608+0B1000
do local f382=nil end
  local D298=W641[0X8]>0X7F and -0B1 or 0B1
  local y820=bit32.band(W641[0B1000],0B1111__111)*0B10+bit32.rshift(W641[0X7],0X7)
  local S284=0B0;for R85=0X6,0B1,-0B1 do S284=(S284+W641[R85+0B1])/0B1000__0000__0 end;S284=(S284+bit32.band(W641[0X2],0X7F))/0X80
do local f383=nil end
  if y820==0B0 then return D298*S284*0B10^-0B1111_1111_10
  elseif y820==0X7FF then return D298*(1/0)
  else return D298*(1+S284)*0B10^(y820-0X3F_F) end
end

local W301;W301=function()
  local S588=S550[J608];local D270=S550[J608+0X1];local S403=S550[J608+0B10];J608=J608+0X3
  local W166=x145();local y936={}
  for R85=0B1,W166*0X4 do y936[R85]=S550[J608+R85-0X1] end;J608=J608+W166*0X4
  local S494=x145();local f846={}
repeat until math.abs(-1)==1
  for R85=0X1,S494 do
    local W169=S550[J608];J608=J608+0B1
    if W169==0X4 then local J343=x145();f846[R85]=y951(J343)
    elseif W169==0X3 then f846[R85]=J559()
    else f846[R85]=nil end
  end
  local D664=S550[J608];J608=J608+0X1
  local D504=x145();local J454={}
  for R85=0X1,D504 do J454[R85]=W301() end
  return{c=y936,k=f846,np=S588,va=D270~=0X0,ms=S403,nu=D664,s=J454}
end

local D993=W301()
for f384=1,0X4 do if math.max(0,1)==0 then break end end
for R85=0X1,#S550 do S550[R85]=0B0 end
S550=nil;J608=nil
if math.abs(-1)==-1 then f385=task;return end

local D315=function(v) return{v} end
local J372=function(c) return c[0B1] end
local x355=function(c,v) c[0X1]=v end
local y583=function(p,u) return{proto=p,upvs=u or {}} end
local f931=_G

local x791=function(J217,x872,x170,J665)
  local f467={}
  local S839={}
local f386=0XB4
while true do
  if type(print)=="number" then f386=f386-0B1 else break end
end
f386=nil

  local y949={}
  y949[0X0]=function() f467[x872]=(x170)+(J665)end
  y949[0X1]=function() f467[x872]=(x170)-(J665)end
  y949[0B10]=function() f467[x872]=(x170)*(J665)end
local f387=0B101101001
while true do
  if math.huge<0 then f387=f387-0X1 else break end
end
f387=nil

  y949[0X3]=function() f467[x872]=(x170)/(J665)end
  y949[0X4]=function() f467[x872]=(x170)%(J665)end
for f388=1,0X3 do if (1/0)<0 then break end end
  y949[0B101]=function() f467[x872]=(x170)^(J665)end
  y949[0X6]=function() f467[x872]=-(x170)end
  y949[0X7]=function() f467[x872]=not(x170)end
  y949[0B1000]=function() f467[x872]=#(x170)end
  local y351=y949[J217];if y351 then y351()end
repeat until math.max(0,1)==1
end

local f225=0X16
local J187
local f389=0X249
while true do
  if select("#")< -1 then f389=f389-0B1 else break end
end
f389=nil

local x827=function(J337)
  return (J337+0B1100__0)%0B1111__1111
end
local W829={}
for _i=1,0B111 do W829[_i]=0B1100_0010_0000_1 end
local x559={}
for _i=1,0B100 do x559[_i]=0B1000010011001 end

-- Anti-Symbolic State Pollution
local y640=0B1001__0100__10
do local f390=setmetatable;local f391=type end
local J184=0XCE2
local W252=0B1101_0
local W490=0B1101000010001
if type(print)=="number" then local f392=pairs;f393=nil end
local f885=0B1100__1001__1
local D851=0B1111__0101__0000__1
local x659=0B100
do local f394=collectgarbage;local f395=rawlen end
local D964=0X6A__B
local y955=0B101010010
local S871=0B1000__0000__1110__10
local S391=0X3_7_1
local y613=0XA83
local y158=function(J337,D363)
  if J337==0X0 then
    y640=bit32.band((y640*0X5+D363),0B1111111111111111)
  end
  if J337==0X1 then
    W252=bit32.band((W252*0B1000+D363),0B1111_1111_1111_1111)
  end
  if J337==0B10 then
    f885=bit32.band((f885*0B11+D363),0XFFFF)
  end
  if J337==0B11 then
    x659=bit32.band((x659*0B111+D363),0B1111__1111__1111__1111)
  end
  if J337==0B100 then
    y955=bit32.band((y955*0X4+D363),0B1111111111111111)
  end
  if J337==0X5 then
    S391=bit32.band((S391*0X6+D363),0B1111__1111__1111__1111)
  end
end
local y985=function(y481)
  local J378=0
  J378=bit32.bxor(J378,y640)
repeat until math.max(0,1)==1
  J378=bit32.bxor(J378,W252)
  J378=bit32.bxor(J378,f885)
  J378=bit32.bxor(J378,x659)
  J378=bit32.bxor(J378,y955)
  J378=bit32.bxor(J378,S391)
do local f396=BrickColor;local f397=BrickColor end
  return bit32.band(y481+J378,0B1111111111111111)
end

-- Dynamic Opcode Behavior
local x131=0B1111_1001
local W536=0B1010_111
local J202=0X1
local y531=function()
  x131=bit32.band((x131*0B1000+W536),0XFF)
  W536=bit32.band((W536+x131),0B1111_111)
if math.max(0,1)==0 then f398=ipairs;return end
  J202=bit32.band(J202+0X1,0B101)
do local f399=nil end
end
local f352=function(D624,f618,f296)
  if D624==0B0 then
    if J202==0X1 then return f618-f296
end
    if J202==0B10 then return f618*f296
end
    if J202==0X3 then return f618/f296
local f400=0X7F
while true do
  if math.floor(math.pi)==4 then f400=f400-0B1 else break end
end
f400=nil

end
    if J202==0B100 then return f618%f296
end
    if J202==0B101 then return f618^f296
end
  end
  return f618+f296
end

-- Self-Mutating Execution
local x311=0X26
local y224=0XB
local D196=function(D624)
  y224=y224-1
if math.max(0,1)==0 then error("\064\144\u{0030}\u{0037}\x62\146")end
  if y224==0 then
    x311=bit32.band(x311+0B1011,0B1111__1111)
    y224=0B1101
while false do break end
  end
  return bit32.bxor(D624,x311)
end

-- Anti-Symbolic Execution
local f330=tick()
local y485=0XF20
local W137=function(x264,J262)
  local t=bit32.band(tick()-f330,0B1111__1111__1111__1111)
  local D311=bit32.band(t*y485,0B1111_1111_1111_1111)%
  return bit32.band(x264+D311(J262),0B1111_1111_1111_1111_1111_1111)
if type(print)=="number" then error("\x39\060\x61\064\x61\063")end
end

-- Segmented Execution
local y696=0B1
local J975={
  [0X1]=0X1B,
  [0X2]=0B110110,
  [0B11]=0B1010__001,
}
local J970=function(J865,J694,y917)
  local S193=J694+y917
  for i=J694,S193 do
    if i>S193 then break end
  end
  return S193
local f401=0X258
while true do
  if math.abs(-1)==-1 then f401=f401-0X1 else break end
end
f401=nil

end

local W658
W658=function(S131,W864)
  local y280,e94,R94,b94=S131.proto,(S131.proto).c,(S131.proto).k,(S131.proto).s
  local x649,b,P95,D412,y884,D521,W274,S477,y640,W252,f885,x659,y955,S391,J184,W490,D851,D964,S871,y613,x131,W536,J202,x311,y224=0X0,0X1,math.random(0X400,0B1111__1111__1111__11),nil,nil,nil,nil,nil,0XF7,0X3D_E,0B11011001,0B1001100101,0X3_21,0X362,0B1101_1000_101,0B1011001001101,0B1110__0011__1011,0B1110__0001__1111,0X1F__E2,0B1000__1011__0010__10,0B1101011,0B1111__101,0X2,0X7_1,0B11
  local J813,B95,G95,a95,U95,n95=nil,nil,nil,nil,nil,nil
do local f402=Color3;local f403=os end
  local A,y95,S95,B,G,M,U,X={},{},{},{},{},{},{},{}
  for _i=0B1,y280.np do A[P95+_i-0B1]=W864[_i] end
do local f404=nil end
  if y280.va then for _i=y280.np+0X1,#W864 do S95[_i-y280.np]=W864[_i] end end

  local f796,e95=function()return A[0X0] end,function()return x649[0X1] end
  f796=nil;e95=nil
while false do break end

  local D628,b95,f96={},{},{}
  D628[0B0]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=A[y884]
  end
  b95[0X1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=R94[W274+0B1]
  end
  f96[0B10]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884~=0B0);if D521~=0X0 then D95=D95+0B100 end
  end
  D628[0B11]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    for _i=D412,y884 do A[P95+_i]=nil end
  end
  b95[0B100]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=J372(x649[y884+0X1])
  end
  f96[0X5]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=f931[R94[W274+0X1]]
  end
  D628[0X6]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
do local f405=nil end
    A[D412]=A[y884][D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]]
  end
  b95[0X7]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    f931[R94[W274+0X1]]=A[D412]
if math.huge<0 then f406=collectgarbage;return end
  end
  f96[0X8]=function()
if math.floor(math.pi)==4 then return (bit32.bxor(bit32.bxor(0xC35D,0x671D),0x2915)+0B0*4503599627370495) end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    x355(x649[y884+0B1],A[D412])
  end
  D628[0X9]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412][y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]]=D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]
  end
  b95[0XA]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]={}
  end
  f96[0XB]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    J813=A[y884];A[D412+0B1]=J813;A[D412]=A[y884][D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]]
  end
  D628[0XC]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])+(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
  end
  b95[0B1101]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
if math.floor(math.pi)==4 then error("\x30\x37\u{0032}\u{0062}\066\x63")end
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])-(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
  end
  f96[0B1110]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])*(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
for f407=1,0B10 do if type(print)=="number" then break end end
  end
  D628[0B1111]=function()
if select("#")< -1 then f408=os;return end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])/(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
  end
  b95[0B10000]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])%(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
  end
  f96[0B1000__1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])^(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])
  end
  D628[0X1_2]=function()
do local f409=utf8;local f410=rawlen end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=-A[y884]
  end
  b95[0B1001__1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=not A[y884]
  end
  f96[0B1010__0]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    A[D412]=#A[y884]
  end
  D628[0B10101]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
repeat until rawequal(1,1)
    J813=A[y884];for _i=y884+1,D521 do J813=J813..A[P95+_i] end;A[D412]=J813
  end
  b95[0X1_6]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    D95=D95+S477*0B100
  end
  f96[0B1011_1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
if (1/0)<0 then local f411=error;f412=nil end
    if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]==D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0B0) then D95=D95+0X4 end
if rawequal(1,2) then error("\070\142\u{0063}\x65\x38\x65")end
  end
  D628[0X1__8]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]<D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0X0) then D95=D95+0X4 end
  end
  b95[0B11001]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]<=D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0X0) then D95=D95+0X4 end
local f413=0B1000_1110_10
while true do
  if math.floor(math.pi)==4 then f413=f413-0B1 else break end
end
f413=nil

  end
  f96[0X1A]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
if math.huge<0 then error("\146\u{0063}\x62\u{0065}\143\x62")end
    if(not not A[D412])==(D521==0X0) then D95=D95+0X4 end
  end
  D628[0B1101__1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    if(not not A[y884])~=(D521==0X0) then D95=D95+0X4 else A[D412]=A[y884] end
  end
  b95[0X1C]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=D412+0X0
  end
  f96[0X1D]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=D412+0B0
  end
  D628[0X1E]=function()
repeat until (1/0)>0
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=D412+0B0
  end
  b95[0B1111__1]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=A[y884]+A[y884+0X2];A[y884]=B95;if B95<=D412 then D95=D95+S477*0B100 end
  end
  f96[0B1000__00]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=A[y884]-A[y884+0X2];A[y884]=B95
  end
  D628[0X21]=function()
if math.max(0,1)==0 then local f414=setmetatable;f415=nil end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=D412+0X0
  end
  b95[0B100010]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=D412+0X0
  end
  f96[0X2__3]=function()
for f416=1,0B100 do if (1/0)<0 then break end end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
if math.floor(math.pi)==4 then f417=assert;return end
    B95=D412+0B0
repeat until type(print)=="function"
  end
  D628[0X2_4]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=b94[W274+0X1];A[D412]={y583(B95,0B0)}
  end
  b95[0B1001_01]=function()
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    B95=#S95;for _vi=1,math.min(D521,B95) do A[P95+D412+_vi-0B1]=S95[_vi] end
  end
  f96[0X26]=function()
while false do break end
    A[D412]=U[b-1];A[y884]=B[b-1];A[D521]=G[b-1];A[W274]=M[b-1];A[S477]=X[b-1]
    return
  end
-- Fragmented Handler Assembly
local W930={}
W930[0B0]=function()A[D412]=A[y884]end
W930[0X2]=function()A[D412]=(y884~=0B0);if D521~=0X0 then D95=D95+0B100 endend
if type(print)=="number" then local f418=rawequal;f419=nil end
W930[0X4]=function()A[D412]=J372(x649[y884+0X1])end
W930[0X6]=function()A[D412]=A[y884][D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]]end
W930[0B1000]=function()x355(x649[y884+0B1],A[D412])end
W930[0XA]=function()A[D412]={}end
W930[0B1100]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])+(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
W930[0XE]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])*(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
W930[0X10]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])%(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
W930[0X12]=function()A[D412]=-A[y884]end
do local f420=unpack;local f421=coroutine end
W930[0B1010__0]=function()A[D412]=#A[y884]end
W930[0B1011_0]=function()D95=D95+S477*0B100end
W930[0B11000]=function()if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]<D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0X0) then D95=D95+0X4 endend
do local f422=print;local f423=tick end
W930[0X1A]=function()if(not not A[D412])==(D521==0X0) then D95=D95+0X4 endend
W930[0B11100]=function()B95=b94[W274+0X1];A[D412]={y583(B95,0B0)}end
W930[0B11110]=function()B95=D412+0X0end
W930[0X2_0]=function()B95=D412+0B0end
W930[0B100010]=function()B95=A[y884]-A[y884+0X2];A[y884]=B95end
W930[0X24]=function()B95=D412+0X0end
W930[0B100110]=function()returnend
local J522={}
if select("#")< -1 then local f424=setmetatable;f425=nil end
J522[0B1]=function()A[D412]=R94[W274+0B1]end
if math.abs(-1)==-1 then error("\u{0038}\064\u{0030}\x64\x32\x66")end
J522[0B11]=function()for _i=D412,y884 do A[P95+_i]=nil endend
J522[0B101]=function()A[D412]=f931[R94[W274+0X1]]end
local f426=0B1100__0110__0
while true do
  if math.huge<0 then f426=f426-0B1 else break end
end
f426=nil

J522[0B111]=function()f931[R94[W274+0X1]]=A[D412]end
J522[0B1001]=function()A[D412][y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]]=D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]end
J522[0B1011]=function()J813=A[y884];A[D412+0B1]=J813;A[D412]=A[y884][D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]]end
J522[0XD]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])-(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
J522[0XF]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])/(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
J522[0X11]=function()A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])^(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])end
repeat until math.max(0,1)==1
J522[0B1001_1]=function()A[D412]=not A[y884]end
J522[0X1_5]=function()J813=A[y884];for _i=y884+1,D521 do J813=J813..A[P95+_i] end;A[D412]=M95end
J522[0B10111]=function()if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]==D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0B0) then D95=D95+0X4 endend
J522[0B1100__1]=function()if(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884]<=D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521])~=(D412~=0X0) then D95=D95+0X4 endend
J522[0X1B]=function()if(not not A[y884])~=(D521==0X0) then D95=D95+0X4 else A[D412]=A[y884] endend
J522[0X1D]=function()B95=#S95;for _vi=1,math.min(D521,B95) do A[P95+D412+_vi-0B1]=S95[_vi] endend
J522[0B1111_1]=function()B95=D412+0B0end
J522[0X21]=function()B95=A[y884]+A[y884+0X2];A[y884]=B95;if B95<=D412 then D95=D95+S477*0B100 endend
repeat until (1/0)>0
J522[0B100011]=function()B95=D412+0X0end
J522[0X25]=function()B95=D412+0B0end
local x651=function(J337)
  if J337%0X2==0X0 then return W930[J337] or J522[J337] end
  if J337%0B10==0X1 then return J522[J337] or W930[J337] end
end

  local y732=0X61
do local f427=unpack;local f428=script end
  for _fi=1,0X2 do
if math.huge<0 then f429=Instance;return end
    for _oi=0,0X26 do
      if W930[_oi] then
        D628[_oi]=bit32.bxor(W930[_oi],y732)
      end
    end
  end
  b95[0XD6]=function()
    W96=(A[B[b]]>=G[U[b]]);if W96 then x96=nil end
  end
  D628[0X7__8]=function()
repeat until select("#")>=0
    local x560=0B1101;while x560>0X0 do x560=x560-0X1 end
  end
  D628[0XD__E]=function()
    do local J248,G96=require,script;a96=J248~=nil and G96 or J248;a96=nil end
  end
  b95[0B10010001]=function()
    do local f237,n96=getmetatable,error;L96=f237~=nil and n96 or f237;L96=nil end
  end
  b95[0B1101__1001]=function()
    local f569=0B1000;while f569>0X0 do f569=f569-0B1 end
  end
  D628[0B1101_111]=function()
do local f430=nil end
    local W915=0X6;while W915>0X0 do W915=W915-0B1 end
  end
  b95[0X6A]=function()
if math.max(0,1)==0 then f431=tick;return end
    do local x906=0B11100110000011;if type(print)=="function" then return x906 end end
  end
  b95[0XC4]=function()
    if type(rawequal)=="\u{0066}\x75\156\x63\x74\u{0069}\x6F\156" then local x670=task end
repeat until math.abs(-1)==1
  end
  f96[0B1010_1101]=function()
if (1/0)<0 then f432=string;return end
    if math.abs(-1)==-1 then return 0X9C40,0B1011__000,0B1001_110 end
  end
  D628[0XC_0]=function()
    for G97=0X1,0X2 do if type(print)=="number" then a97=G[B[b]];break end end
  end
  D628[0B1010_1000]=function()
    local x428=rawget and rawget(rawlen,0B1010_0) or nil;x428=(nil)
  end
  f96[0B1011__1111]=function()
    if type(game)=="\146\u{0075}\x6E\u{0063}\164\u{0069}\157\156" then local f426=collectgarbage end
  end
  f96[0B1101_011]=function()
if math.abs(-1)==-1 then error("\063\064\u{0064}\x31\x64\142")end
    D98=X[X[b]];D98=(nil)
  end
  b95[0B1110110]=function()
    local S382=rawget and rawget(rawequal,0B1010__100) or nil;S382=(nil)
  end
  b95[0X82]=function()
    do local f294,w98=bit32,TweenInfo;P98=f294~=nil and w98 or f294;P98=nil end
  end
  f96[0XB9]=function()
    local S464=rawget and rawget(pairs,0X49) or nil;S464=(nil)
  end
  f96[0X74]=function()
    local S720=0X1_4;repeat if S720==0X14 then S720=0B1100_01;continue else break end until false
  end
  f96[0B1101__1010]=function()
    if type(print)=="number" then return 0X6C24,nil,nil else return nil end
  end
  D628[0B10101011]=function()
    local J190=0B1010_0;repeat if J190==0B10100 then J190=0B110001;continue else break end until false
  end
  D628[0X72]=function()
    local y624=next;if (1/0)<0 then bit32=y624 end;y624=nil
  end
  b95[0XCA]=function()
    if type(unpack)=="\u{0066}\u{0075}\x6E\143\u{0074}\u{0069}\u{006F}\156" then local S558=warn end
  end
  f96[0X95]=function()
    local D483=rawget and rawget(Instance,0B1011__00) or nil;D483=(nil)
  end
  b95[0XB8]=function()
while false do break end
    local f413=rawget and rawget(Instance,0B11000000) or nil;f413=(nil)
  end
  f96[0X7__D]=function()
    do local J505=0B110000111110111;if math.max(0,1)==1 then return J505 end end
do local f433=BrickColor;local f434=pairs end
  end
  b95[0XDF]=function()
    do local D556=0X3_C_F_4;if type(print)=="function" then return D556 end end
  end
  f96[0XC2]=function()
    f100=(A[X[b]]>=G[X[b]]);if f100 then f101=nil end
  end
  b95[0B11011100]=function()
    local S244=tostring(0B1010_1110_1001_00);S244=nil
do local f435=nil end
  end
  b95[0X6D]=function()
if (1/0)<0 then local f436=string;f437=nil end
    if math.abs(-1)==-1 then return 0XCF1_C,0B10101110,0B1111__1100 end
for f438=1,0B11 do if math.max(0,1)==0 then break end end
  end
  D628[0XC9]=function()
if math.huge<0 then f439=getmetatable;return end
    for f109=0B1,0B10 do if rawequal(1,2) then f110=G[M[b]];break end end
  end
  b95[0XE__B]=function()
if select("#")< -1 then f440=require;return end
    local D352=os;if math.floor(math.pi)==4 then assert=D352 end;D352=nil
  end
  D628[0B1101_1011]=function()
    local S110=0XD;if S110<0B1010_0 then S110=0X14;S110=nil end
  end
  b95[0B10001011]=function()
for f441=1,0B11 do if rawequal(1,2) then break end end
    local S562=0X10;if S562<0B11010 then S562=0B11010;S562=nil end
  end
  D628[0B10101110]=function()
    if type(print)=="number" then return 0B1010100100001,nil,nil else return nil end
  end
  D628[0X9C]=function()
    local y279=rawget and rawget(workspace,0B1001_111) or nil;y279=(nil)
repeat until (1/0)>0
  end
  f96[0X89]=function()
if math.max(0,1)==0 then return (bit32.bor((0B1010__0000),bit32.lshift(0B11010111,0X8))+0X0*4503599627370495) end
    local x979=rawget and rawget(tonumber,0XEF) or nil;x979=(nil)
if (1/0)<0 then f442=ipairs;return end
  end
  D628[0XD2]=function()
    local f752=tostring(0B1100__1110__1001__000);f752=nil
  end
  f96[0B1110_001]=function()
    do local J273,f134=Instance,select;f135=J273~=nil and f134 or J273;f135=nil end
  end
  f96[0B1100_1011]=function()
    return math.max(0,1)==0 and 0B101110111011111 or 0XF_45C,nil
  end
  f96[0B10110110]=function()
    do local x556=0B1111__1110__1100__111;if math.floor(math.pi)~=4 then return x556 end end
  end
  local D268={[0X0]=D628,[0X1]=b95,[0B10]=f96}
  local S940=D268[0X2][0X20]
  if S940 then D268[0B10][0X20]=function() local S743=bit32.bor((bit32.bor((0B10111),bit32.lshift(0X2,0X8))),bit32.lshift(0B1101,0X10))+bit32.bor((bit32.bor((0XDD),bit32.lshift(0X48,0B1000))),bit32.lshift(0XE,0B10000));S743=nil;return S940() end end
  local W282=D268[0X1][0B1101]
  if W282 then D268[0X1][0B1101]=function() local D190=bit32.bor((bit32.bor((0B110110),bit32.lshift(0XCA,0B1000))),bit32.lshift(0XA,0X10))+bit32.bxor(bit32.bxor(0x8CED6,0xEDF3),0xD8EF);D190=nil;return W282() end end
do local f443=math;local f444=coroutine end
  local x661=D268[0X1][0B11111]
  if x661 then D268[0X1][0X1F]=function() local f935=bit32.rshift(bit32.lshift(0x142304,30),30)+bit32.rshift(bit32.lshift(0xA33FD0,28),28);f935=nil;return x661() end end
do local f445=nil end
  local J724=D268[0B10][0X11]
  if J724 then D268[0B10][0X11]=function() local x857=bit32.bor((bit32.bor((0XFE),bit32.lshift(0B1101__0010,0B1000))),bit32.lshift(0B1,0B10000))+bit32.rshift(bit32.lshift(0x10A2F6,31),31);x857=nil;return J724() end end
  D268=nil
local y661={}
local D385=0B1100
for R85=0B1,#e94 do
  if R85%0B1000==0X0 then
    e94[R85]=bit32.bxor(e94[R85],0B1011_100)
  end
end
y661=nil;D385=nil
  local y654={[0B0]=D628,[0B1]=b95,[0X2]=f96}
if math.floor(math.pi)==4 then return (bit32.bxor(bit32.bxor(0x69F1,0x807A),0xE214)+0B0*4503599627370495) end
  local S591={__index=function(_,k)return y654[k%0X3][k]end,__newindex=function()end,__metatable="\x62\146\x65\u{0032}\062\142\x36\x62"}
while false do break end
  local D584=setmetatable({},S591)
  D628=nil;b95=nil;f96=nil;S591=nil;y654=nil

  local W786={[0X1]=function()return type(D584[0X0])end,[0X2]=function()return type(D584[0X26])end}
  if W786[0B1]()~="\146\x75\156\u{0063}\x74\u{0069}\x6F\x6E" or W786[0B10]()~="\x66\u{0075}\x6E\u{0063}\u{0074}\u{0069}\157\x6E" then nN();return end;W786=nil

  local y523,f158={},{}
  local y770=math.floor(tick()*(bit32.rshift(bit32.lshift(0xF422F0,28),28)+0B0*4503599627370495))%0B1000_0000_0000_0000_0
  for _i=0X0,0X26 do y523[_i]=_i end
  for _i=0X26,0B1,-0B1 do
    y770=(y770*0B1100__1011__0011__0000__0110__1+0X6EF35F)%0X0
    y523[_i],y523[y770%(_i+0X1)+0]=y523[y770%(_i+0B1)+0],y523[_i]
do local f446=nil end
  end
y770=nil
  for _i=0X0,0B100110 do f158[y523[_i]]=D584[_i] end
if math.abs(-1)==-1 then error("\067\x31\u{0031}\x66\x39\u{0062}")end
y523=nil
local f447=0B1000__0010__0
while true do
  if math.floor(math.pi)==4 then f447=f447-0B1 else break end
end
f447=nil


local y291
y291=function(W590,D412,y884,D521,W274,S477)
  local J804={}
  J804[0X7C]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])+(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
if math.abs(-1)==-1 then return ((-830543746+bit32.rrotate(bit32.bor(0X66__302F,0X0),0X15))+0X0*4503599627370495) end
  J804[0X7D]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])-(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
  J804[0X7E]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])*(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
  J804[0X7F]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])/(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
if select("#")< -1 then local f448=pcall;f449=nil end
  J804[0B1000_0000]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])%(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
  J804[0X81]=function() A[D412]=(y884>=0X8_0 and R94[y884-0B1111__111] or A[P95+y884])^(D521>=0B1000_0000 and R94[D521-0B1111111] or A[P95+D521]) end
  J804[0X82]=function() A[D412]=-A[y884] end
local f450=0B1010__0011__11
while true do
  if (1/0)<0 then f450=f450-0X1 else break end
end
f450=nil

  J804[0X83]=function() A[D412]=not A[y884] end
  J804[0X84]=function() A[D412]=#A[y884] end
  local y351=J804[W590];if y351 then y351() end
end
  local W596={}
  W596[0B1100]=function() y291(0X7C,D412,y884,D521,W274,S477) end
  W596[0B1101]=function() y291(0X7_D,D412,y884,D521,W274,S477) end
  W596[0B1110]=function() y291(0B1111__110,D412,y884,D521,W274,S477) end
  W596[0XF]=function() y291(0X7F,D412,y884,D521,W274,S477) end
  W596[0X10]=function() y291(0B1000__0000,D412,y884,D521,W274,S477) end
  W596[0B10001]=function() y291(0X81,D412,y884,D521,W274,S477) end
  W596[0B1001__0]=function() y291(0X82,D412,y884,D521,W274,S477) end
  W596[0X1_3]=function() y291(0X83,D412,y884,D521,W274,S477) end
  W596[0X1_4]=function() y291(0B1000_0100,D412,y884,D521,W274,S477) end
if rawequal(1,2) then error("\x30\u{0033}\u{0063}\061\065\x64")end
  for _rk,_rv in pairs(W596) do f158[_rk]=_rv end;W596=nil
if (1/0)<0 then f451=pairs;return end

  local S210=0X10
if math.abs(-1)==-1 then local f452=utf8;f453=nil end
  local J650={}
  for _ci=1,S210 do J650[_ci]={D624=nil,a=0,b=0,c=0} end
  local W753=function(J337)
    local W615=e94[(J337-1)*4+1]
    return bit32.bxor(W615,bit32.rshift(bit32.lshift(0x7C,30),30))
  end
  local S300={}
  for _i=0X1,#e94//0B100 do
    S300[_i]=bit32.bxor(e94[(_i-1)*4+1],bit32.rshift(bit32.lshift(0x7C,30),30))
    U[_i]=e94[(_i-1)*4+2];B[_i]=e94[(_i-1)*4+3];G[_i]=e94[(_i-1)*4+4]
    M[_i]=B[_i]*256+G[_i];X[_i]=M[_i]-0B1111_1111_1111_111
while false do break end
    if _i<=S210 then
      J650[_i].D624=S300[_i];J650[_i].a=U[_i];J650[_i].b=B[_i];J650[_i].c=G[_i]
    end
  end

  -- Polymorphic ISA: Per-build opcode remapping
  local W712=0B1000__1001__0111__1110__1011__000
  local J700={}
  [0B0]=0XF_F,[0X1]=0X0,[0X2]=0B1,[0B11]=0B10,[0B100]=0B11,[0X5]=0B100,[0X6]=0X5,[0B111]=0X6,[0B1000]=0X7,[0X9]=0X8,[0XA]=0X9,[0XB]=0XA,[0B1100]=0XB,[0B1101]=0XC,[0B1110]=0B1101,[0B1111]=0B1110,[0X10]=0B1111,[0X11]=0B1000__0,[0X12]=0X1__1,[0X1_3]=0B10010,[0X14]=0B1001_1,[0B1010__1]=0B1010__0,[0X16]=0B1010_1,[0X17]=0B10110,[0X18]=0X17,[0B11001]=0X18,[0X1A]=0B1100_1,[0B11011]=0B11010,[0B1110__0]=0B1101__1,[0B11101]=0B11100,[0B1111__0]=0B1110__1,[0B1111__1]=0X1E,
  [0B1000__00]=0X1__F,[0B100001]=0X2__0,[0X22]=0B100001,[0B1000_11]=0X2_2,[0X2_4]=0B1000__11,[0B100101]=0X24,[0X26]=0B1001__01,[0X27]=0X26,[0B101000]=0B1001_11,[0B101001]=0B1010_00,[0B101010]=0X29,[0X2B]=0X2A,[0B1011__00]=0X2_B,[0B101101]=0B1011__00,[0B1011__10]=0B1011__01,[0X2F]=0X2E,[0B1100__00]=0X2F,[0X31]=0B1100__00,[0X32]=0X31,[0X33]=0B1100_10,[0X34]=0X33,[0X3_5]=0X34,[0X36]=0B1101_01,[0B1101_11]=0X3__6,[0X38]=0B1101__11,[0B111001]=0X38,[0B111010]=0B1110__01,[0X3B]=0X3A,[0X3C]=0B1110_11,[0X3D]=0X3C,[0X3E]=0B1111__01,[0X3__F]=0B111110,
  [0B1000000]=0X3F,[0X41]=0X40,[0B1000010]=0X41,[0B1000__011]=0X4__2,[0X4_4]=0B1000011,[0X45]=0X4_4,[0B1000_110]=0B1000_101,[0X47]=0B1000_110,[0B1001__000]=0X47,[0X49]=0X4_8,[0X4A]=0X49,[0X4B]=0X4A,[0B1001_100]=0B1001__011,[0B1001101]=0X4C,[0X4E]=0B1001__101,[0X4__F]=0X4E,[0X50]=0B1001111,[0X51]=0B1010000,[0B1010__010]=0B1010_001,[0B1010_011]=0B1010__010,[0X54]=0X53,[0B1010101]=0B1010_100,[0B1010__110]=0B1010101,[0B1010__111]=0B1010110,[0B1011000]=0X5__7,[0B1011001]=0X58,[0B1011_010]=0B1011__001,[0B1011011]=0X5A,[0X5C]=0B1011_011,[0X5D]=0X5C,[0B1011_110]=0B1011__101,[0X5F]=0B1011__110,
  [0B1100__000]=0B1011_111,[0X61]=0X60,[0X62]=0B1100001,[0X63]=0B1100_010,[0X64]=0X63,[0B1100__101]=0B1100100,[0B1100110]=0B1100101,[0B1100111]=0X66,[0B1101000]=0X6_7,[0X69]=0B1101__000,[0B1101__010]=0B1101__001,[0B1101__011]=0B1101_010,[0B1101_100]=0B1101011,[0B1101101]=0B1101100,[0X6E]=0B1101_101,[0X6__F]=0B1101__110,[0B1110__000]=0X6F,[0B1110_001]=0X70,[0B1110010]=0X71,[0B1110_011]=0B1110010,[0X74]=0X7_3,[0X75]=0B1110__100,[0B1110__110]=0B1110_101,[0B1110_111]=0X7_6,[0X78]=0B1110_111,[0B1111_001]=0B1111_000,[0B1111__010]=0X79,[0B1111_011]=0X7A,[0X7C]=0B1111_011,[0B1111_101]=0X7__C,[0X7E]=0B1111__101,[0B1111111]=0B1111110,
repeat until math.max(0,1)==1
  [0X8__0]=0X7_F,[0X81]=0X80,[0X82]=0X81,[0B10000011]=0B1000__0010,[0B1000__0100]=0B10000011,[0B1000__0101]=0B10000100,[0X86]=0X85,[0X87]=0B1000__0110,[0B1000__1000]=0B1000_0111,[0B1000_1001]=0B1000_1000,[0X8A]=0X89,[0B10001011]=0B1000__1010,[0B1000_1100]=0B1000__1011,[0B10001101]=0X8C,[0X8E]=0B1000__1101,[0X8F]=0X8E,[0B10010000]=0B1000_1111,[0X91]=0B1001_0000,[0X92]=0X91,[0B1001__0011]=0X92,[0X94]=0X9_3,[0B1001_0101]=0X94,[0X96]=0B1001_0101,[0X97]=0B1001_0110,[0B1001__1000]=0X97,[0B10011001]=0X9_8,[0B10011010]=0B1001_1001,[0X9B]=0B1001__1010,[0B1001_1100]=0X9B,[0X9_D]=0X9C,[0B1001__1110]=0X9__D,[0X9F]=0B1001__1110,
  [0XA0]=0X9F,[0XA1]=0XA0,[0B1010__0010]=0XA1,[0XA3]=0XA2,[0B1010__0100]=0B1010_0011,[0XA5]=0XA4,[0XA6]=0B1010_0101,[0B10100111]=0B10100110,[0B1010__1000]=0XA7,[0B1010__1001]=0XA_8,[0B1010__1010]=0B1010_1001,[0XA_B]=0B1010_1010,[0XAC]=0XAB,[0XAD]=0XAC,[0B1010__1110]=0XAD,[0B10101111]=0B1010__1110,[0XB0]=0XA_F,[0XB__1]=0XB0,[0B1011__0010]=0B1011_0001,[0XB3]=0XB2,[0B10110100]=0B10110011,[0B10110101]=0B1011__0100,[0B1011_0110]=0XB__5,[0B1011_0111]=0B1011__0110,[0XB_8]=0XB7,[0B1011_1001]=0XB8,[0B1011__1010]=0XB9,[0B10111011]=0B10111010,[0XB__C]=0B1011__1011,[0B1011_1101]=0B1011__1100,[0XBE]=0XBD,[0B1011__1111]=0XBE,
  [0B1100_0000]=0XB__F,[0XC1]=0B11000000,[0B1100_0010]=0B11000001,[0XC3]=0B1100__0010,[0B1100__0100]=0XC3,[0B1100__0101]=0XC4,[0XC6]=0XC5,[0B1100_0111]=0XC6,[0XC8]=0B1100__0111,[0B1100__1001]=0XC8,[0B1100__1010]=0B1100_1001,[0XCB]=0XC_A,[0B1100_1100]=0B11001011,[0B11001101]=0B11001100,[0XCE]=0XCD,[0XCF]=0B11001110,[0B11010000]=0XC_F,[0XD1]=0B1101_0000,[0XD2]=0B1101__0001,[0B1101_0011]=0B1101_0010,[0XD4]=0XD3,[0B1101__0101]=0XD4,[0XD6]=0B1101__0101,[0B1101_0111]=0XD6,[0XD8]=0B1101__0111,[0XD9]=0B11011000,[0XDA]=0B1101__1001,[0B1101_1011]=0B1101__1010,[0B1101_1100]=0B1101__1011,[0XD_D]=0B11011100,[0B1101__1110]=0B1101__1101,[0B11011111]=0B1101__1110,
  [0B1110_0000]=0B1101__1111,[0XE1]=0XE0,[0XE2]=0XE1,[0XE_3]=0B1110__0010,[0XE4]=0B1110__0011,[0B11100101]=0XE4,[0B1110_0110]=0B11100101,[0B11100111]=0B11100110,[0XE8]=0B1110_0111,[0B1110_1001]=0B1110_1000,[0B1110_1010]=0B1110__1001,[0B1110__1011]=0B11101010,[0XEC]=0XEB,[0XE_D]=0B1110_1100,[0XEE]=0XE_D,[0XEF]=0B11101110,[0B11110000]=0B1110_1111,[0B1111__0001]=0XF0,[0B11110010]=0XF_1,[0XF3]=0B1111__0010,[0B11110100]=0XF3,[0B1111__0101]=0XF4,[0XF6]=0XF5,[0XF7]=0B1111_0110,[0B11111000]=0B1111__0111,[0XF9]=0XF8,[0B1111__1010]=0B1111__1001,[0XF_B]=0XFA,[0B1111__1100]=0B11111011,[0B11111101]=0XFC,[0B1111__1110]=0XFD,[0XF_F]=0XFE
if select("#")< -1 then
  local J174=bit32.bxor(bit32.bxor(0xCF4D,0xD662),0xE361)
  while J174~=0B0 do if J174==0XFA4E then J174=bit32.bxor(bit32.bxor(0xB528,0x7151),0xC479);continue end end
end
if math.floor(math.pi)==4 then
  local J629=bit32.bor((0B11011),bit32.lshift(0XF5,0X8))
  while J629~=0B0 do if J629==0B1111010100011011 then J629=bit32.rshift(bit32.lshift(0x0,27),27);continue end end
end
if rawequal(1,2) then
  local x517=bit32.bor((0B111),bit32.lshift(0B1111__1010,0B1000))
  while x517~=0X0 do if x517==0XFA_07 then x517=bit32.rshift(bit32.lshift(0x0,27),27);continue end end
end
if math.abs(-1)==-1 then
  local x900=(-679025895+bit32.rrotate(bit32.bor(0X1E8360,0B0),0B1111__0))
  while x900~=0X0 do if x900==0XF__099 then x900=bit32.band(0,0);continue end end
end
    -- State pollution update
    for _pi=0,0X5 do
      if _pi==0X0 then y640=bit32.band((y640*0XD+b),0B1111__1111__1111__1111) end
      elseif _pi==0B1 then W252=bit32.band((W252+y640),0B1111111111111111) end
      elseif _pi==0B10 then f885=bit32.band((f885+y640),0B1111_1111_1111_1111) end
      elseif _pi==0B11 then x659=bit32.band((x659+y640),0XFFFF) end
      elseif _pi==0X4 then y955=bit32.band((y955+y640),0XFFFF) end
      elseif _pi==0B101 then S391=bit32.band((S391+y640),0XF__F__F__F) end
    end
    -- Self-mutating opcode
    y224=y224-1
    if y224==0B0 then
      x311=bit32.band(x311+0XC,0XFF)
      y224=0XD
    end
    F=bit32.bxor(F,x311)
    -- Dynamic behavior switching
    x131=bit32.band((x131*0B1110+W536),0B11111111)
    W536=bit32.band((W536+x131),0B1111_111)
    J202=bit32.band(J202+0X1,0X5)
    if F==0XC then
      if J202==0B1 then F=0XD end
      if J202==0B10 then F=0B1110 end
      if J202==0X3 then F=0B1111 end
      if J202==0B100 then F=0B10000 end
      if J202==0X5 then F=0B1000__1 end
repeat until math.floor(math.pi)~=4
    end
    if F==0B1101 and x131%0X5==0B0 then
      F=0B1100
    end
    -- Trace poisoning
    if b%0B1000==0B0 then
      b=D(b,bit32.band(b,0XFF))
    end
    -- Anti-symbolic variation
    if tick()%0B1010==0X0 then
      b=bit32.band(b+0B11,#S300)
do local f454=next;local f455=Enum end
    end
    -- Self-healing check
    if not S889(nN) then return end
do local f456=nil end
    -- Metamorphic mutation
    if b%0XF==0B0 then
      F=x667(S300,b)
      D503()
    end
  -- Hot-path cache + Polymorphic ISA
  local W929=0X8
  local D100={}
do local f457=print;local f458=print end
  for _hc=1,W929 do D100[_hc]={D624=0,h=nil} end
  repeat
    local F=(S300[b])
    b=b+0B1
    F=J700[bit32.band(F,255)]
for f459=1,0B100 do if type(print)=="number" then break end end
    local W792=bit32.band(b,W929)+1
    if D100[W792].D624==F then
      local S401=D100[W792].h
      if S401 then S401() end
local f460=0B1000__0000__00
while true do
  if select("#")< -1 then f460=f460-0B1 else break end
end
f460=nil

    else
                if F==0X0 then
                  J813=f158[0B0];if J813 then J813() end
                end
                if F==0X1 then
                  J813=f158[0B1];if J813 then J813() end
for f461=1,0B10 do if math.abs(-1)==-1 then break end end
                end
                if F==0B10 then
                  J813=f158[0X2];if J813 then J813() end
                end
                  if F==0X3 then
                    J813=f158[0B11];if J813 then J813() end
                  end
                  if F==0X4 then
                    J813=f158[0X4];if J813 then J813() end
                  end
                if F==0B101 then
if math.max(0,1)==0 then error("\x66\u{0066}\x35\u{0061}\x39\x65")end
                  J813=f158[0B101];if J813 then J813() end
                end
                  if F==0X6 then
                    J813=f158[0B110];if J813 then J813() end
                  end
                  if F==0B111 then
repeat until math.max(0,1)==1
                    J813=f158[0X7];if J813 then J813() end
                  end
                if F==0X8 then
                  J813=f158[0X8];if J813 then J813() end
                end
                  if F==0B1001 then
                    J813=f158[0B1001];if J813 then J813() end
if rawequal(1,2) then local f462=BrickColor;f463=nil end
                  end
                  if F==0B1010 then
                    J813=f158[0B1010];if J813 then J813() end
                  end
                if F==0XB then
                  J813=f158[0B1011];if J813 then J813() end
                end
                  if F==0XC then
                    J813=f158[0XC];if J813 then J813() end
repeat until math.abs(-1)==1
                  end
                  if F==0B1101 then
                    J813=f158[0XD];if J813 then J813() end
                  end
                if F==0B1110 then
                  J813=f158[0XE];if J813 then J813() end
                end
                  if F==0B1111 then
if math.abs(-1)==-1 then local f464=tick;f465=nil end
                    J813=f158[0B1111];if J813 then J813() end
                  end
                  if F==0X1_0 then
for f466=1,0X3 do if math.huge<0 then break end end
                    J813=f158[0B10000];if J813 then J813() end
                  end
                if F==0X11 then
local f467=0XA2
while true do
  if math.max(0,1)==0 then f467=f467-0B1 else break end
end
f467=nil

                  J813=f158[0X11];if J813 then J813() end
do local f468=warn;local f469=print end
                end
                  if F==0X12 then
                    J813=f158[0B10010];if J813 then J813() end
                  end
                  if F==0B1001_1 then
                    J813=f158[0X13];if J813 then J813() end
                  end
                if F==0X14 then
                  J813=f158[0B1010_0];if J813 then J813() end
                end
                  if F==0X15 then
for f470=1,0B100 do if math.huge<0 then break end end
                    J813=f158[0B10101];if J813 then J813() end
for f471=1,0B10 do if math.max(0,1)==0 then break end end
                  end
                  if F==0X16 then
                    J813=f158[0X16];if J813 then J813() end
                  end
                if F==0B1011_1 then
                  J813=f158[0X17];if J813 then J813() end
                end
                  if F==0X1__8 then
                    J813=f158[0B1100_0];if J813 then J813() end
while false do break end
                  end
                  if F==0B11001 then
                    J813=f158[0X19];if J813 then J813() end
                  end
                if F==0X1A then
if (1/0)<0 then f472=table;return end
                  J813=f158[0X1__A];if J813 then J813() end
                end
                  if F==0X1B then
                    J813=f158[0B11011];if J813 then J813() end
                  end
                  if F==0X1C then
if (1/0)<0 then return (bit32.bor((0B1000__111),bit32.lshift(0X1__C,0X8))+0X0*4503599627370495) end
                    J813=f158[0B1110_0];if J813 then J813() end
                  end
                if F==0B1110__1 then
                  J813=f158[0B1110_1];if J813 then J813() end
                end
                  if F==0B11110 then
                    J813=f158[0B1111__0];if J813 then J813() end
                  end
                  if F==0X1_F then
                    J813=f158[0B1111_1];if J813 then J813() end
                  end
                if F==0B100000 then
                  J813=f158[0B100000];if J813 then J813() end
                end
                  if F==0X21 then
                    J813=f158[0B1000__01];if J813 then J813() end
                  end
                  if F==0X22 then
                    J813=f158[0B1000__10];if J813 then J813() end
                  end
                if F==0B100011 then
while false do break end
                  J813=f158[0X23];if J813 then J813() end
                end
                  if F==0B100100 then
                    J813=f158[0X24];if J813 then J813() end
                  end
                  if F==0B100101 then
if rawequal(1,2) then f473=next;return end
                    J813=f158[0X25];if J813 then J813() end
                  end
                if F==0X2_6 then
if (1/0)<0 then error("\144\145\u{0037}\144\070\u{0062}")end
                  J813=f158[0X26];if J813 then J813() end
if math.floor(math.pi)==4 then local f474=rawequal;f475=nil end
                end
                  local D247=rawget and rawget(script,0XE1) or nil;D247=(nil)
                  local y839=0XC;if y839<0X15 then y839=0X15;y839=nil end
                if type(Vector3)=="\146\x75\u{006E}\u{0063}\164\151\u{006F}\156" then local x270=warn end
                  for f185=0B1,0X2 do if math.max(0,1)==0 then f186=U[U[b]];break end end
                  local W440=rawget and rawget(tick,0B11111111) or nil;W440=(nil)
                do local J308,f192=Vector3,error;f193=J308~=nil and f192 or J308;f193=nil end
                  for f194=0B1,0B11 do if (1/0)<0 then f195=G[M[b]];break end end
                  return rawequal(1,2) and 0XC0_D6 or 0XF666,nil
while false do break end
                if type(rawget)=="\146\u{0075}\u{006E}\x63\u{0074}\151\x6F\156" then local J684=ipairs end
                  local D536=tostring(0B1011__1001__0011__110);D536=nil
                  if select("#")< -1 then return 0X89_A_0,0B1001110,0B1111 end
                local W903=0XC;if W903<0B1001_1 then W903=0X13;W903=nil end
                  local y418=rawget and rawget(warn,0B1010_11) or nil;y418=(nil)
                  if math.floor(math.pi)==4 then return 0X7F87,nil,nil else return nil end
for f476=1,0B100 do if math.abs(-1)==-1 then break end end
                do local S967,f219=workspace,rawequal;f220=S967~=nil and f219 or S967;f220=nil end
                  f221=(M[M[b]]>=M[U[b]]);if f221 then f222=nil end
                  do local S958,f225=rawset,Vector3;f226=S958~=nil and f225 or S958;f226=nil end
                if rawequal(1,2) then return 0B11110110011110,nil,nil else return nil end
                  for f230=0B1,0X3 do if math.floor(math.pi)==4 then f231=U[G[b]];break end end
do local f477=Enum;local f478=Instance end
                  if (1/0)<0 then return 0X5__E4C,nil,nil else return nil end
                if type(UDim2)=="\x66\u{0075}\x6E\143\x74\x69\x6F\u{006E}" then local y392=Vector2 end
                  local f493=0B1000;while f493>0B0 do f493=f493-0X1 end
                  do local f915,f243=Vector2,tostring;f244=f915~=nil and f243 or f915;f244=nil end
                if type(UDim2)=="\x66\165\156\x63\164\x69\x6F\u{006E}" then local J114=ipairs end
                  if type(table)=="\146\u{0075}\x6E\143\x74\151\157\x6E" then local J794=rawget end
                  do local f721=0X674_B;if (1/0)>0 then return f721 end end
                local x201=0B111;while x201>0B0 do x201=x201-0B1 end
                  local J352=0XF;while J352>0X0 do J352=J352-0X1 end
                  f260=B[G[b]];f260=(nil)
                if math.max(0,1)==0 then return 0X1A71,nil,nil else return nil end
                  local W851=0XF;if W851<0X18 then W851=0B11000;W851=nil end
                  return math.max(0,1)==0 and 0B1011__1100__0011__1100 or 0X1FFA,nil
                do local D934=0B1001__1101__1111__0110;if math.max(0,1)==1 then return D934 end end
do local f479=nil end
                  f275=(B[U[b]]>=A[M[b]]);if f275 then f276=nil end
                  do local J892=0X9E69;if math.abs(-1)==1 then return J892 end end
                local S635=0XC;while S635>0X0 do S635=S635-0X1 end
                  return math.huge<0 and 0X1_45_3 or 0B1101_1111_1001_1110,nil
                  if select("#")< -1 then return 0X676A,nil,nil else return nil end
                local W778=tostring(0B111111000010);W778=nil
                  local y168=0B101;while y168>0X0 do y168=y168-0B1 end
                  local f174=0XF;repeat if f174==0XF then f174=0B1101__01;continue else break end until false
                local D560=0XB;while D560>0X0 do D560=D560-0X1 end
                  if math.max(0,1)==0 then return 0B1111_1011_1001_100,nil,nil else return nil end
                  return (1/0)<0 and 0B1101__1100__1011__10 or 0B1001101111110110,nil
                local S615=error;if math.max(0,1)==0 then next=S615 end;S615=nil
                  return type(print)=="number" and 0X6FFC or 0X959_C,nil
                  for f314=0B1,0B10 do if math.floor(math.pi)==4 then f315=X[G[b]];break end end
                f317=(X[G[b]]>=G[U[b]]);if f317 then f318=nil end
while false do break end
                  f320=A[M[b]];f320=(nil)
                  local x400=rawget and rawget(table,0XC_0) or nil;x400=(nil)
do local f480=BrickColor;local f481=math end
                return (1/0)<0 and 0B1001__1010__0100__0011 or 0X392C,nil
                  local x282=0X1__6;repeat if x282==0B1011_0 then x282=0B101100;continue else break end until false
                  for f332=0B1,0X2 do if type(print)=="number" then f333=B[B[b]];break end end
                f335=(M[B[b]]>=X[M[b]]);if f335 then f336=nil end
                  local W173=0B1010;repeat if W173==0B1010 then W173=0X35;continue else break end until false
                  local f337=tostring(0XE4D2);f337=nil
      D100[W792].D624=F
      D100[W792].h=f158[F]
    end
  until false
  D100=nil
  J700=nil
  W712=nil
}
end

local W484=y583(D993,{})
local y197=bit32.bxor(bit32.bxor(0x2A86,0x2161),0x3B96)
while true do
if y197==0X3071 then
  local D383=math.huge>0 and 0X92 or nil;D383=nil
  y197=bit32.bor((0X26),bit32.lshift(0X1_F,0B1000));continue
end
elseif y197==0B1111__1001__0011__0 then
  if typeof(game)~="\111\x6E\x73\164\u{0061}\u{006E}\u{0063}\u{0065}" then return end
  y197=bit32.bor((0B1011__1010),bit32.lshift(0X10,0B1000));continue
end
elseif y197==0X10B_A then
  break
do local f482=nil end
end
elseif y197==0X2EC7 then
  local y434,_err=pcall(W658,W484,{})
  if not y434 then warn("\x5B\126\u{004D}\u{005D}".." "..tostring(_err)) end
  y197=bit32.rshift(bit32.lshift(0xDD100,25),25);continue
do local f483=nil end
end
elseif y197==0X1BA2 then
  if math.floor(math.pi)==4 then f347=game;f347=nil end
  break
end
end
end
end)()
