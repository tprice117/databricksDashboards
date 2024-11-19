def shade_hex_color(color, percent):
        '''
        Python fuction to shade a hex color by a percentage.
        From: https://github.com/PimpTrizkit/PJs/wiki/12.-Shade,-Blend-and-Convert-a-Web-Color-(pSBC.js)
        '''
        f = int(color[1:], 16)
        t = 0 if percent < 0 else 255
        p = abs(percent)
        R = f >> 16
        G = (f >> 8) & 0x00FF
        B = f & 0x0000FF
        new_color = '#{:02x}{:02x}{:02x}'.format(
            round((t - R) * p) + R,
            round((t - G) * p) + G,
            round((t - B) * p) + B
        )
        return new_color