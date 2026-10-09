local M = {}

function M.feather(base, quality)
    quality = tonumber(quality) or 1
    if quality ~= quality or quality == math.huge or quality == -math.huge then quality = 1 end
    -- The engine stores effect magnitudes as signed 32-bit integers.
    return math.max(0, math.min(2147483647, math.floor(base * math.max(0, quality) + .5 + 1e-9)))
end

return M
