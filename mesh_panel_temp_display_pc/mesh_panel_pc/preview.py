from __future__ import annotations
import tkinter as tk

from .models import DisplayConfig


# 3-column x 5-row digit bitmaps (each row uses 3 bits) - mirror firmware
DIGIT_BITMAPS = [
    [0b111, 0b101, 0b101, 0b101, 0b111],  # 0
    [0b010, 0b010, 0b010, 0b010, 0b010],  # 1
    [0b111, 0b001, 0b111, 0b100, 0b111],  # 2
    [0b111, 0b001, 0b111, 0b001, 0b111],  # 3
    [0b101, 0b101, 0b111, 0b001, 0b001],  # 4
    [0b111, 0b100, 0b111, 0b001, 0b111],  # 5
    [0b111, 0b100, 0b111, 0b101, 0b111],  # 6
    [0b111, 0b001, 0b010, 0b010, 0b010],  # 7
    [0b111, 0b101, 0b111, 0b101, 0b111],  # 8
    [0b111, 0b101, 0b111, 0b001, 0b111],  # 9
]

SUFFIX_BITMAPS = {
    'C': [0b000, 0b111, 0b100, 0b100, 0b111],
    'F': [0b000, 0b111, 0b100, 0b111, 0b100],
}


class DigitPreview(tk.Canvas):
    def __init__(self, master: tk.Misc, scale: int = 2, **kwargs) -> None:
        # scale: how many screen pixels per hardware pixel (2x by default)
        self.scale = max(1, int(scale))
        self.hw_width = 128
        self.hw_height = 64
        w = self.hw_width * self.scale
        h = self.hw_height * self.scale
        super().__init__(master, width=w, height=h, bg="#000000", highlightthickness=1, **kwargs)

    def render(self, cfg: DisplayConfig) -> None:
        # Clear previous drawing
        self.delete("all")

        # Background/foreground depending on invert flag
        if cfg.invert:
            bg = "#ffffff"
            fg = "#000000"
        else:
            bg = "#000000"
            fg = "#ffffff"
        try:
            self.configure(bg=bg)
        except tk.TclError:
            pass

        # radius from dot diameter (hardware pixels), then scale to canvas
        hw_radius = max(1, int(max(1.0, float(cfg.dot_diameter)) / 2.0))
        radius = hw_radius * self.scale

        # Start coordinates in hardware pixels
        start_x = float(cfg.start_x)
        start_y = float(cfg.start_y)

        # Number of digits to render (2..4)
        digit_count = int(cfg.digit_count) if int(cfg.digit_count) in (2, 3, 4) else 3

        # Advance between glyphs in columns: firmware uses 4 columns per glyph (3 cols + 1 spacing)
        glyph_advance_cols = 4

        # Draw each digit using firmware glyph bitmaps
        for glyph_idx in range(digit_count):
            glyph_origin_x = start_x + (glyph_idx * glyph_advance_cols * float(cfg.xx_spacing))
            glyph_origin_y = start_y

            pattern = DIGIT_BITMAPS[8]  # render '8' glyph for tuning preview
            for row in range(5):
                row_pattern = pattern[row]
                for col in range(3):
                    mask = 1 << (3 - 1 - col)  # mask for 3-bit pattern
                    if not (row_pattern & mask):
                        continue

                    # hardware coordinates using firmware math
                    x_hw = glyph_origin_x + (col * float(cfg.xx_spacing)) + (row * float(cfg.yx_spacing))
                    y_hw = glyph_origin_y + (col * float(cfg.xy_spacing)) + (row * float(cfg.yy_spacing))

                    # scale to canvas coords
                    x = int(round(x_hw * self.scale))
                    y = int(round(y_hw * self.scale))

                    # bounds check on canvas size
                    if x + radius < 0 or x - radius > self.hw_width * self.scale or y + radius < 0 or y - radius > self.hw_height * self.scale:
                        continue

                    self.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fg, outline="")

        # Draw decimal point for 3- and 4-digit modes at the appropriate digit
        if digit_count in (3, 4):
            # For digitCount=3 show xx.x -> decimal after glyph index 1
            # For digitCount=4 show xxx.x -> decimal after glyph index 2
            dec_glyph_idx = 1 if digit_count == 3 else 2
            glyph_origin_x = start_x + (dec_glyph_idx * glyph_advance_cols * float(cfg.xx_spacing))
            glyph_origin_y = start_y
            # Position decimal at column 3, row 4 relative to glyph origin per firmware note
            dec_x_hw = glyph_origin_x + (3 * float(cfg.xx_spacing))
            dec_y_hw = glyph_origin_y + (4 * float(cfg.yy_spacing))
            dx = int(round(dec_x_hw * self.scale))
            dy = int(round(dec_y_hw * self.scale))
            dp_radius = max(1, int(self.scale * 1.0))
            if 0 <= dx <= self.hw_width * self.scale and 0 <= dy <= self.hw_height * self.scale:
                self.create_oval(dx - dp_radius, dy - dp_radius, dx + dp_radius, dy + dp_radius, fill=fg, outline="")

        # Draw suffix (C/F) to the right of the last digit using firmware suffix glyphs
        suffix = (cfg.suffix or "").upper()
        if suffix in SUFFIX_BITMAPS:
            pattern = SUFFIX_BITMAPS[suffix]
            suffix_origin_x = start_x + ((digit_count) * glyph_advance_cols * float(cfg.xx_spacing))
            suffix_origin_y = start_y
            for row in range(5):
                row_pattern = pattern[row]
                for col in range(3):
                    mask = 1 << (3 - 1 - col)
                    if not (row_pattern & mask):
                        continue
                    x_hw = suffix_origin_x + (col * float(cfg.xx_spacing)) + (row * float(cfg.yx_spacing))
                    y_hw = suffix_origin_y + (col * float(cfg.xy_spacing)) + (row * float(cfg.yy_spacing))
                    x = int(round(x_hw * self.scale))
                    y = int(round(y_hw * self.scale))
                    if x + radius < 0 or x - radius > self.hw_width * self.scale or y + radius < 0 or y + radius > self.hw_height * self.scale:
                        continue
                    self.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fg, outline="")

        # Optional small note
        try:
            self.create_text(4 * self.scale, (self.hw_height - 6) * self.scale, anchor="w", fill=fg, font=("Segoe UI", int(6 * self.scale)), text=f"Preview {self.hw_width}x{self.hw_height} @{self.scale}x")
        except tk.TclError:
            pass
