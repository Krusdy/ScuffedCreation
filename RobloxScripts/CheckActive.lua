local StarterGui = game:GetService("StarterGui")
local MarketplaceService = game:GetService("MarketplaceService")

local placeName = "Unknown"

local success, result = pcall(function()
    return MarketplaceService:GetProductInfo(game.PlaceId).Name
end)

if success then
    placeName = result
end

StarterGui:SetCore("SendNotification", {
    Title = "Script Active",
    Text = placeName,
    Duration = 3
})
