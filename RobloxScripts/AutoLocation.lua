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
local debounce = false
local savedCFrame = nil
local teleportRadius = 200
local deathNotified = false

sg:SetCore("SendNotification", {
    Title = "Auto Location",
    Text = "- Control + ]: Toggle",
    Duration = 5
})

local function teleportBack()
    while enabled and not stopped do
        if humanoidRootPart and savedCFrame then
            local distance = (humanoidRootPart.Position - savedCFrame.Position).Magnitude
            if distance <= teleportRadius then
                humanoidRootPart.CFrame = savedCFrame + Vector3.new(0, 0.1, 0)
            end
        end
        task.wait(0.01)
    end
end

uis.InputBegan:Connect(function(input, gameProcessed)
    if gameProcessed or stopped or debounce then return end
    
    if input.KeyCode == Enum.KeyCode.RightBracket then
        if uis:IsKeyDown(Enum.KeyCode.LeftControl) then
            debounce = true
            enabled = not enabled
            
            if enabled then
                savedCFrame = humanoidRootPart.CFrame
            end
            
            sg:SetCore("SendNotification", {
                Title = "Script Status",
                Text = "Auto Location " .. (enabled and "Enabled!" or "Disabled!"),
                Duration = 2
            })
            
            task.wait(0.5)
            debounce = false
            
            if enabled then
                teleportBack()
            end
        elseif uis:IsKeyDown(Enum.KeyCode.LeftAlt) then
            debounce = true
            stopped = true
            enabled = false
            
            sg:SetCore("SendNotification", {
                Title = "Script Stopped",
                Text = "Auto Location fully closed successfully!",
                Duration = 2
            })
            
            task.wait(0.5)
            debounce = false
        end
    end
end)

humanoid.Died:Connect(function()
    if not deathNotified then
        deathNotified = true
        enabled = false
        
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

--Auto Location made by Krusdy using ChadSkibidi.
