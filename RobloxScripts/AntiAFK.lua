-- create.roblox.com/docs/reference/engine/enums/KeyCode
local Config = {
    Key = Enum.KeyCode.Space,
    IntervalMinutes = 15,
    FrameSize = UDim2.new(0, 220, 0, 200),
    FramePosition = UDim2.new(1, -230, 1, -210),
    TitleColor = Color3.fromRGB(255, 255, 255),
    OffColor = Color3.fromRGB(255, 80, 80),
    OnColor = Color3.fromRGB(80, 255, 80),
    TimerColor = Color3.fromRGB(200, 200, 200),
    BgColor = Color3.fromRGB(30, 30, 30),
    ToggleBtnColor = Color3.fromRGB(60, 60, 60),
    CloseBtnColor = Color3.fromRGB(200, 50, 50)
}

local VirtualInput = game:GetService("VirtualInputManager")

local gui = Instance.new("ScreenGui", game.CoreGui)

local frame = Instance.new("Frame", gui)
frame.Size = Config.FrameSize
frame.Position = Config.FramePosition
frame.BackgroundColor3 = Config.BgColor
frame.Active = true
frame.Draggable = true

local title = Instance.new("TextLabel", frame)
title.Size = UDim2.new(1, -20, 0, 30)
title.Position = UDim2.new(0, 10, 0, 10)
title.BackgroundTransparency = 1
title.Text = "Auto Presser"
title.TextColor3 = Config.TitleColor
title.TextScaled = true
title.Font = Enum.Font.GothamBold
title.TextXAlignment = Enum.TextXAlignment.Left

local status = Instance.new("TextLabel", frame)
status.Size = UDim2.new(1, -20, 0, 30)
status.Position = UDim2.new(0, 10, 0, 45)
status.BackgroundTransparency = 1
status.Text = "Status: OFF"
status.TextColor3 = Config.OffColor
status.TextScaled = true
status.Font = Enum.Font.GothamBold
status.TextXAlignment = Enum.TextXAlignment.Left

local timerLabel = Instance.new("TextLabel", frame)
timerLabel.Size = UDim2.new(1, -20, 0, 30)
timerLabel.Position = UDim2.new(0, 10, 0, 80)
timerLabel.BackgroundTransparency = 1
timerLabel.Text = "Next: --:--"
timerLabel.TextColor3 = Config.TimerColor
timerLabel.TextScaled = true
timerLabel.Font = Enum.Font.Gotham
timerLabel.TextXAlignment = Enum.TextXAlignment.Left

local toggleBtn = Instance.new("TextButton", frame)
toggleBtn.Size = UDim2.new(1, -20, 0, 40)
toggleBtn.Position = UDim2.new(0, 10, 0, 120)
toggleBtn.BackgroundColor3 = Config.ToggleBtnColor
toggleBtn.TextColor3 = Color3.new(1, 1, 1)
toggleBtn.Text = "Toggle Script"
toggleBtn.TextScaled = true
toggleBtn.Font = Enum.Font.GothamBold
toggleBtn.AutoButtonColor = true

local closeBtn = Instance.new("TextButton", frame)
closeBtn.Size = UDim2.new(1, -20, 0, 35)
closeBtn.Position = UDim2.new(0, 10, 0, 165)
closeBtn.BackgroundColor3 = Config.CloseBtnColor
closeBtn.TextColor3 = Color3.new(1, 1, 1)
closeBtn.Text = "Close & Stop"
closeBtn.TextScaled = true
closeBtn.Font = Enum.Font.GothamBold

local active = false
local running = false

local function formatTime(seconds)
    local m = math.floor(seconds / 60)
    local s = seconds % 60
    return string.format("%02d:%02d", m, s)
end

local function pressKey()
    VirtualInput:SendKeyEvent(true, Config.Key, false, game)
    task.wait(0.05)
    VirtualInput:SendKeyEvent(false, Config.Key, false, game)
end

local function loop()
    pressKey()
    local timeLeft = Config.IntervalMinutes * 60
    while active do
        timerLabel.Text = "Next: " .. formatTime(timeLeft)
        task.wait(1)
        timeLeft = timeLeft - 1
        if timeLeft <= 0 then
            pressKey()
            timeLeft = Config.IntervalMinutes * 60
        end
    end
    timerLabel.Text = "Next: --:--"
    running = false
end

toggleBtn.MouseButton1Click:Connect(function()
    active = not active
    if active then
        status.Text = "Status: ON"
        status.TextColor3 = Config.OnColor
        if not running then
            running = true
            task.spawn(loop)
        end
    else
        status.Text = "Status: OFF"
        status.TextColor3 = Config.OffColor
    end
end)

closeBtn.MouseButton1Click:Connect(function()
    active = false
    gui:Destroy()
end)
