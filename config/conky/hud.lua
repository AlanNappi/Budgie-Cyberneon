-- CyberNeon HUD drawing (cairo)
require 'cairo'
pcall(require, 'cairo_xlib')

local CY   = {0x5b/255, 0xee/255, 0xdc/255}
local DIM  = {0x1f/255, 0x4a/255, 0x4f/255}
local NAVY = {0x11/255, 0x1e/255, 0x29/255}
local RED  = {0xff/255, 0x2a/255, 0x4f/255}
local LABEL = '@HUD_LABEL@'

local function rgb(cr, c, a) cairo_set_source_rgba(cr, c[1], c[2], c[3], a or 1) end

local function poly(cr, pts)
    cairo_new_path(cr); cairo_move_to(cr, pts[1], pts[2])
    for i = 3, #pts, 2 do cairo_line_to(cr, pts[i], pts[i+1]) end
    cairo_close_path(cr)
end

local function text(cr, s, x, y, size, align, weight)
    cairo_select_font_face(cr, 'Chakra Petch', CAIRO_FONT_SLANT_NORMAL, weight or CAIRO_FONT_WEIGHT_BOLD)
    cairo_set_font_size(cr, size)
    local ext = cairo_text_extents_t:create()
    cairo_text_extents(cr, s, ext)
    if align == 'right' then x = x - ext.x_advance end
    cairo_move_to(cr, x, y); cairo_show_text(cr, s)
end

local function stat(cr, y, label, value, w)
    local pct = math.max(0, math.min(100, tonumber(value) or 0))
    rgb(cr, DIM); cairo_rectangle(cr, 0, y, w, 6); cairo_fill(cr)
    rgb(cr, CY);  cairo_rectangle(cr, 0, y, math.max(4, w * pct / 100), 6); cairo_fill(cr)
    rgb(cr, CY)
    text(cr, label, 3, y + 25, 15)
    text(cr, string.format('%.1f%%', pct), w, y + 25, 15, 'right')
end

function conky_hud()
    if conky_window == nil then return end
    local cs = cairo_xlib_surface_create(conky_window.display, conky_window.drawable,
                                         conky_window.visual, conky_window.width, conky_window.height)
    local cr = cairo_create(cs)
    local W = 330

    stat(cr, 4,  'Total CPU Usage',      conky_parse('${cpu cpu0}'), W)
    stat(cr, 48, 'Used Physical Memory', conky_parse('${memperc}'), W)
    stat(cr, 92, 'Root Filesystem',      conky_parse('${fs_used_perc /}'), W)

    -- hatched block with a chamfered bottom-left corner
    local top, bot = 134, 214
    cairo_save(cr)
    poly(cr, {0, top, W, top, W, bot, 42, bot, 0, bot - 42}); cairo_clip(cr)
    rgb(cr, CY, 0.92)
    for x = -120, W + 40, 26 do
        poly(cr, {x, bot, x + 13, bot, x + 13 + (bot - top), top, x + (bot - top), top}); cairo_fill(cr)
    end
    cairo_restore(cr)

    -- vertical name plate
    rgb(cr, CY); cairo_rectangle(cr, 350, 4, 12, bot - 4); cairo_fill(cr)
    poly(cr, {370, 4, 434, 4, 478, 48, 478, bot, 370, bot}); cairo_fill(cr)
    cairo_save(cr)
    cairo_translate(cr, 412, (bot + 4) / 2)
    cairo_rotate(cr, math.pi / 2)
    rgb(cr, NAVY)
    cairo_select_font_face(cr, 'Orbitron', CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL)
    cairo_set_font_size(cr, 40)
    local ext = cairo_text_extents_t:create()
    cairo_text_extents(cr, LABEL, ext)
    cairo_move_to(cr, -ext.x_advance / 2, ext.height / 2)
    cairo_show_text(cr, LABEL)
    cairo_restore(cr)

    -- red status pixel
    rgb(cr, RED); cairo_rectangle(cr, 455, bot - 22, 12, 12); cairo_fill(cr)

    cairo_destroy(cr)
    cairo_surface_destroy(cs)
end
