local Config = {
    TeleportRange = 250,
    InputCooldown = 0,
    HeightOffset = 0.1
}

local uis = game:GetService("UserInputService")
local sg = game:GetService("StarterGui")
local players = game:GetService("Players")
local runService = game:GetService("RunService")

local player = players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local humanoidRootPart = character:WaitForChild("HumanoidRootPart")
local humanoid = character:WaitForChild("Humanoid")

local enabled = false
local stopped = false
local savedCFrame = nil
local deathNotified = false
local teleportConnection = nil
local debounce = false

sg:SetCore("SendNotification", {
    Title = "Auto Location",
    Text = "- Control + ]: Toggle",
    Duration = 5
})

local function updatePosition()
    if not enabled or stopped or not humanoidRootPart or not savedCFrame then return end

    local distance = (humanoidRootPart.Position - savedCFrame.Position).Magnitude
    
    if distance <= Config.TeleportRange then
        humanoidRootPart.CFrame = savedCFrame + Vector3.new(0, Config.HeightOffset, 0)
    end
end

local function startTeleport()
    if teleportConnection then teleportConnection:Disconnect() end
    savedCFrame = humanoidRootPart.CFrame
    teleportConnection = runService.Heartbeat:Connect(updatePosition)
end

local function stopTeleport()
    if teleportConnection then
        teleportConnection:Disconnect()
        teleportConnection = nil
    end
end

uis.InputBegan:Connect(function(input, gameProcessed)
    if gameProcessed or stopped or debounce then return end
    
    if input.KeyCode == Enum.KeyCode.RightBracket then
        if uis:IsKeyDown(Enum.KeyCode.LeftControl) then
            debounce = true
            enabled = not enabled
            
            if enabled then
                startTeleport()
                sg:SetCore("SendNotification", {
                    Title = "Script Status",
                    Text = "Auto Location Enabled!",
                    Duration = 2
                })
            else
                stopTeleport()
                sg:SetCore("SendNotification", {
                    Title = "Script Status",
                    Text = "Auto Location Disabled!",
                    Duration = 2
                })
            end
            
            task.wait(Config.InputCooldown)
            debounce = false
            
        elseif uis:IsKeyDown(Enum.KeyCode.LeftAlt) then
            stopped = true
            enabled = false
            stopTeleport()
            
            sg:SetCore("SendNotification", {
                Title = "Script Stopped",
                Text = "Auto Location fully closed successfully!",
                Duration = 2
            })
        end
    end
end)

humanoid.Died:Connect(function()
    if not deathNotified then
        deathNotified = true
        enabled = false
        stopTeleport()
        
        sg:SetCore("SendNotification", {
            Title = "Script Status",
            Text = "Auto Location disabled due to death!",
            Duration = 2
        })
    end
end)

player.CharacterAdded:Connect(function(newCharacter)
    character = newCharacter
    humanoidRootPart = character:WaitForChild("HumanoidRootPart")
    humanoid = character:WaitForChild("Humanoid")
    deathNotified = false
end)
