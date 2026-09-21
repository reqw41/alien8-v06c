; Alien 8 (ZX Spectrum, Ultimate 1985)
; Автоперевод листинга tcdev v0.9a1 (ASxxxx) в синтаксис sjasmplus.
; Сделано tools/a8_lst2asm.py — руками не править.
        DEVICE ZXSPECTRUM48

        ; +--------------------------------------------------+
        ; | ZX Spectrum Alien 8 Disassembly v0.9a1           |
        ; |    - by tcdev (msmcdoug@gmail.com)               |
        ; +--------------------------------------------------+
        ;
        ; Memory Map:
        ;
        ; $4000-$57FF - spectrum video memory
        ; $5800-$5AFF - spectrum attribute memory
        ; $5B00-$6287 - variables
        ; $6288-$D1EA - code and data
        ; $D200-$D9FF - video buffer
        ;       $F0FF - stack
        ; $F100-$FFFF - bit-shift & bit-reverse lookup tables
        ;             - (built at run-time)
        ; Processor       : z80 []
        ; Target assembler: ASxxxx by Alan R. Baldwin v1.5
        ; this is needed only for HD64180
        ; ===========================================================================
        ; Segment type: Regular
        ORG 0x4000
zxvram:
        DS 0x1800
        ; end of 'ZXVRAM'
        ; ===========================================================================
        ; Segment type: Regular
        ORG 0x5800
zxaram:
        DS 0x300
        ; end of 'ZXARAM'
        ; ===========================================================================
        ; Segment type: Regular
        ORG 0x5B00
seed_1:
        DS 1
        DS 1
seed_2:
        DS 2
user_input_method:
        DS 1
seed_3:
        DS 1
tmp_input_method:
        DS 1
        DS 1
        ;
        ; variables from here are zeroed each game
        ;
objs_wiped_cnt:
        DS 1
tmp_SP:
        DS 2
room_size_X:
        DS 1
room_size_Y:
        DS 1
curr_room_attrib:
        DS 1
room_size_Z:
        DS 1
        DS 1
        DS 1
        DS 1
not_1st_screen:
        DS 1
pickup_drop_pressed:
        DS 1
objects_carried_changed:
        DS 1
user_input:
        DS 1
tmp_attrib:
        DS 1
render_status_info:
        DS 1
suppress_border:
        DS 1
unk_5B19:
        DS 1
lives:
        DS 1
tmp_XYZ:
        DS 1
        DS 1
        DS 1
rendered_objs_cnt:
        DS 1
        DS 1
block_type_tbl_base:
        DS 1
tmp_dZ:
        DS 1
        DS 1
byte_5B23:
        DS 1
byte_5B24:
        DS 1
byte_5B25:
        DS 1
        DS 1
gfxbase_8x8:
        DS 2
        DS 1
        DS 1
tmp_objects_to_draw:
        DS 2
render_obj_1:
        DS 2
render_obj_2:
        DS 2
audio_played:
        DS 1
directional:
        DS 1
cant_drop:
        DS 1
word_5B34:
        DS 2
unk_5B36:
        DS 1
        DS 1
unk_5B38:
        DS 1
unk_5B39:
        DS 1
unk_5B3A:
        DS 1
byte_5B3B:
        DS 1
unk_5B3C:
        DS 1
unk_5B3D:
        DS 1
unk_5B3E:
        DS 1
unk_5B3F:
        DS 1
unk_5B40:
        DS 1
byte_5B41:
        DS 1
unk_5B42:
        DS 1
byte_5B43:
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
        DS 1
scrn_visited:
        DS 32
inventory:
        DS 4
byte_5B7C:
        DS 4
byte_5B80:
        DS 4
byte_5B84:
        DS 3
end_of_objects_carried:
        DS 1
graphic_objs_tbl:
        DS 32
        DS 32
special_objs_here:
        DS 32
byte_5BE8:
        DS 32
other_objs_here:
        DS 1664
        ; end of 'SCRATCH'
        ; font
        ; ===========================================================================
        ; Segment type: Regular
        ORG 0x6288
font:
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0xDB, 2, 0x4D, 0, 0xDB
        DB 2, 0x4D, 0, 0x78, 0x5A, 0x68, 0, 0xE0
        DB 0x57, 0xDB, 2, 0xDB, 2, 0x4D, 0, 0xDB
        DB 2, 0x4D, 0, 0x8E, 0x54, 0xF3, 0xD, 0xCE
        DB 0xB, 0xE2, 0x50, 0xCE, 0xB, 0xE3, 0x50, 0x1E
        DB 0x17, 0xDC, 0xA, 0xCE, 0xB, 0xE4, 0x50, 0x1D
        DB 0x17, 0xDB, 2, 0x4D, 0, 0xDB, 2, 0x4D
        DB 0, 0xD9, 0xD, 0xF3, 0xD, 0xCE, 0xB, 0xC6
        DB 0x50, 0x1B, 2, 0xDC, 0xA, 0xB1, 0x33, 0x70
        DB 0x5D, 0xDB, 2, 0x4D, 0, 0xA4, 0x5D, 0
        DB 0, 0x9F, 0x5D, 0x5C, 0, 0x3E, 0x1F, 0x76
        DB 0x1B, 3, 0x13, 0, 0x3E, 0, 0, 0
        DB 0xF3, 0x31, 0, 0xF1, 0, 0xC3, 0x31, 0xA6
ascii_chars:
        DB 0x7E, 0x42, 0x42, 0x46, 0x46, 0x46, 0x7E, 0   ; '0'
        DB 8, 8, 8, 0x18, 0x18, 0x18, 0x18, 0   ; '1'
        DB 0x7E, 2, 2, 0x7E, 0x60, 0x60, 0x7E, 0   ; '2'
        DB 0x7C, 0x44, 4, 0x1E, 6, 0x46, 0x7E, 0   ; '3'
        DB 0x78, 0x48, 0x48, 0x48, 0x7E, 0x18, 0x18, 0   ; '4'
        DB 0x7E, 0x40, 0x40, 0x7E, 6, 0x46, 0x7E, 0   ; '5'
        DB 0x7E, 0x42, 0x40, 0x7E, 0x62, 0x62, 0x7E, 0   ; '6'
        DB 0x7E, 2, 2, 6, 6, 6, 6, 0   ; '7'
        DB 0x3C, 0x24, 0x24, 0x7E, 0x46, 0x46, 0x7E, 0   ; '8'
        DB 0x7E, 0x42, 0x42, 0x7E, 6, 6, 6, 0   ; '9'
        DB 0x7E, 0x42, 0x42, 0x46, 0x46, 0x46, 0x7E, 0   ; '0'
        DB 0, 0, 0, 0, 0, 0x18, 0x18, 0   ; '.'
        DB 0, 0, 0x7E, 0x7E, 0, 0, 0, 0   ; '-'
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0x3C, 0x42, 0x99, 0xA1, 0xA1, 0x99, 0x42, 0x3C   ; (c)
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0
        DB 0x3C, 0x24, 0x24, 0x7E, 0x62, 0x62, 0x62, 0   ; 'A'
        DB 0x7C, 0x44, 0x44, 0x7E, 0x62, 0x62, 0x7E, 0   ; 'B'
        DB 0x7E, 0x42, 0x40, 0x60, 0x60, 0x62, 0x7E, 0   ; 'C'
        DB 0x7E, 0x42, 0x42, 0x62, 0x62, 0x62, 0x7E, 0   ; 'D'
        DB 0x7E, 0x40, 0x40, 0x7E, 0x60, 0x60, 0x7E, 0   ; 'E'
        DB 0x7E, 0x40, 0x40, 0x7E, 0x60, 0x60, 0x60, 0   ; 'F'
        DB 0x7E, 0x42, 0x40, 0x66, 0x62, 0x62, 0x7E, 0   ; 'G'
        DB 0x42, 0x42, 0x42, 0x7E, 0x62, 0x62, 0x62, 0   ; 'H'
        DB 0x10, 0x10, 0x10, 0x18, 0x18, 0x18, 0x18, 0   ; 'I'
        DB 4, 4, 4, 6, 0x46, 0x46, 0x7E, 0   ; 'J'
        DB 0x44, 0x44, 0x44, 0x7E, 0x62, 0x62, 0x62, 0   ; 'K'
        DB 0x40, 0x40, 0x40, 0x60, 0x60, 0x60, 0x7E, 0   ; 'L'
        DB 0x7E, 0x4A, 0x4A, 0x6A, 0x6A, 0x6A, 0x6A, 0   ; 'M'
        DB 0x7E, 0x42, 0x42, 0x62, 0x62, 0x62, 0x62, 0   ; 'N'
        DB 0x7E, 0x46, 0x42, 0x42, 0x42, 0x42, 0x7E, 0   ; 'O'
        DB 0x7E, 0x42, 0x42, 0x7E, 0x60, 0x60, 0x60, 0   ; 'P'
        DB 0x7E, 0x42, 0x42, 0x42, 0x42, 0x4E, 0x7E, 0   ; 'Q'
        DB 0x7C, 0x44, 0x44, 0x7E, 0x62, 0x62, 0x62, 0   ; 'R'
        DB 0x7E, 0x40, 0x40, 0x7E, 6, 6, 0x7E, 0   ; 'S'
        DB 0x7E, 0x10, 0x10, 0x18, 0x18, 0x18, 0x18, 0   ; 'T'
        DB 0x42, 0x42, 0x42, 0x62, 0x62, 0x62, 0x7E, 0   ; 'U'
        DB 0x62, 0x62, 0x62, 0x62, 0x24, 0x24, 0x3C, 0   ; 'V'
        DB 0x4A, 0x4A, 0x4A, 0x6A, 0x6A, 0x6A, 0x7E, 0   ; 'W'
        DB 0x42, 0x42, 0x42, 0x3C, 0x62, 0x62, 0x62, 0   ; 'X'
        DB 0x42, 0x42, 0x42, 0x7E, 0x18, 0x18, 0x18, 0   ; 'Y'
        DB 0x7E, 0x42, 2, 0x7E, 0x60, 0x62, 0x7F, 0   ; 'Z'
        ; room sizes
room_size_tbl:
        DB 64, 64, 64
        DB 32, 64, 64
        DB 64, 32, 64
        ; Location (Room) Table
        ; +0 Location ID
        ; +1 Entry size (bytes)
        ; +2 Size and Attributes
        ; +3... bg objects until $FF
        ; fg objects until (entry size) bytes
location_tbl:
        DB 2, 32, 48   ; id=2
        DB 0, 0xA, 0xC, 4, 7, 0xFF, 0xF, 0x40, 0x88, 0x78, 0xB0, 0xE7, 0xDF, 0xE8, 0xD0, 9
        DB 0, 0x38, 0, 0x30, 0xB, 0x20, 0x18, 0x19, 0x21, 0x33, 0x22, 0x23, 0x1A, 0x1B
        DB 3, 23, 32   ; id=3
        DB 0, 3, 0xA, 0xC, 6, 7, 0xFF, 0x5F, 0x24, 0x1C, 0x65, 0x5D, 0xA6, 0x9E, 0xE7, 0xDF
        DB 0x3B, 0x22, 0x23, 0x1A, 0x1B
        DB 4, 25, 40   ; id=4
        DB 0, 1, 3, 6, 7, 0xFF, 0xB, 0x1C, 0x23, 0x1A, 0x13, 0x38, 0x1B, 0x7B, 0x63, 0x5A, 0x5C
        DB 0x53, 0xBB, 0x12, 0x14, 0x22, 0x24
        DB 5, 26, 24   ; id=5
        DB 0, 3, 6, 7, 0xFF, 0xF, 0x22, 0x24, 0x12, 0x14, 0x63, 0x5C, 0x53, 0x5A, 9, 0x9B, 0xDB
        DB 0, 0x30, 0xB, 0x1B, 0x5B, 0x9B, 0x1C
        DB 10, 33, 24   ; id=10
        DB 0, 1, 4, 7, 0xFF, 0xB5, 0x38, 0x39, 0x3A, 0x3D, 0x3E, 0x3F, 0xF, 0x23, 0x24, 0x1B
        DB 0x1C, 0, 0x40, 0x80, 0xC0, 0x10, 0x63, 0x18, 0xA3, 0, 0x30, 8, 0, 0xD8, 0x40
        DB 11, 35, 40   ; id=11
        DB 0, 1, 3, 6, 7, 0xFF, 0xBF, 0x3D, 0x3E, 0x3F, 0x35, 0x36, 0x37, 0x2D, 0x2E, 0xB9
        DB 0x2F, 0xBF, 0xF1, 0x76, 0x31, 0xF8, 0, 0x28, 9, 8, 8, 0x10, 0x11, 0x18, 0xA, 0x20
        DB 1
        DB 12, 39, 32   ; id=12
        DB 0, 1, 3, 6, 7, 0xFF, 0xAA, 0, 8, 0x10, 0xB2, 0x3D, 0x3E, 0x3F, 0xBB, 0x63, 0x65
        DB 0x53, 0x55, 0xF, 0x1D, 0x1B, 0x24, 0x14, 0x5B, 0x64, 0x5D, 0x54, 0xC0, 0x1C, 0, 0x30
        DB 0xA3, 0xA4, 0x94, 0x9B, 0x9D
        DB 13, 33, 48   ; id=13
        DB 0, 3, 6, 7, 0xFF, 0xA, 0x5B, 0x9C, 0xE4, 0x4A, 0x12, 0x13, 0x14, 0x42, 0x15, 0x1D
        DB 0x25, 0x5A, 0x2D, 0x2C, 0x2B, 0x52, 0x2A, 0x22, 0x1A, 0x38, 0x23, 0, 0x30, 8, 0x23
        DB 18, 28, 40   ; id=18
        DB 1, 0xB, 0xD, 4, 5, 0xFF, 9, 0xC3, 0xC4, 0x38, 0, 0x2A, 0x3A, 0x79, 0xB8, 0x54, 0xF0
        DB 0xE8, 0xE0, 0xD8, 0xD0, 0, 0x30, 0x31, 0, 0x40
        DB 19, 32, 24   ; id=19
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xBF, 0x3A, 0x32, 0x2A, 0x29, 0x28, 0x10, 0x11, 0x12, 0xBF
        DB 0xA, 2, 0x3D, 0x35, 0x2D, 0x2E, 0x2F, 0x17, 0xBB, 0x16, 0x15, 0xD, 5
        DB 20, 37, 48   ; id=20
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0x2F, 0x2E, 0x26, 0x1E, 0x16, 0x17, 0x28, 0x29, 0xB
        DB 0x21, 0x19, 0x11, 0x10, 0x7F, 0x68, 0x69, 0x61, 0x59, 0x51, 0x50, 0x57, 0x56, 0x7B
        DB 0x5E, 0x66, 0x6E, 0x6F
        DB 21, 28, 40   ; id=21
        DB 2, 3, 5, 6, 0xFF, 0x37, 0x3C, 0x74, 0x27, 0x66, 0xC, 0x54, 0x21, 0x62, 0x34, 0xAC
        DB 0xA5, 0xA3, 0x9C, 0xE4, 0x3C, 0x23, 0x2C, 0x25, 0x1C, 0x24
        DB 26, 28, 40   ; id=26
        DB 0xA, 0xB, 0xC, 0xD, 4, 5, 0xFF, 0x3B, 0x23, 0x24, 0x1C, 0x1B, 0x45, 0xC3, 0xC4, 0x8B
        DB 0x8C, 0x53, 0x54, 0x5D, 0xDF, 0xE7, 0x9E, 0xA6, 0x5D, 0x65
        DB 27, 26, 48   ; id=27
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0x34, 0x55, 0x95, 0x94, 0xD4, 0xDC, 0xBB, 0x1C, 0x1D, 0x14
        DB 0x15, 0, 0x30, 0x32, 0x1C, 0x1D, 0x5D
        DB 28, 33, 24   ; id=28
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0x23, 0x63, 0x25, 0x65, 0x13, 0x53, 0x15, 0x55, 0xF
        DB 0xA4, 0xE4, 0x9D, 0xDD, 0x94, 0xD4, 0x9B, 0xDB, 0x10, 0x1C, 0x18, 0x5C, 0xA0, 0xDC
        DB 29, 43, 40   ; id=29
        DB 2, 3, 5, 6, 0xFF, 0xAA, 0, 8, 0x10, 0xB, 0xFF, 6, 0xE, 0xF, 0x20, 0xF8, 0x3F, 0x30
        DB 0x31, 0x39, 0xFE, 0xF7, 0x46, 0x4F, 0x4E, 0x57, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xEF
        DB 0xE7, 0xDF, 0x51, 0xD7, 0xCF, 0, 0x30, 0xD0, 0x3F
        DB 32, 26, 40   ; id=32
        DB 0, 4, 7, 0xFF, 0xF, 0x1A, 0x5A, 0x9A, 0xDA, 0x1D, 0x5D, 0x9D, 0xDD, 9, 0, 7, 0x39
        DB 0x1B, 0x1C, 0x31, 0xDB, 0xDC, 0x80, 0x40
        DB 35, 35, 112   ; id=35
        DB 0, 2, 8, 0xFF, 0xF, 0x22, 0x23, 0x24, 0x25, 0x1A, 0x1B, 0x1C, 0x1D, 0x52, 0x2B, 0x2C
        DB 0x2D, 0x42, 0x13, 0x14, 0x15, 0x61, 0x2A, 0x12, 0x7F, 0x62, 0x63, 0x64, 0x65, 0x5A
        DB 0x5B, 0x5C, 0x5D
        DB 36, 15, 96   ; id=36
        DB 0, 2, 8, 0xFF, 0x7F, 0x35, 0x2C, 0x2B, 0x22, 0xA, 0x13, 0x14, 0x1D
        DB 39, 34, 48   ; id=39
        DB 0, 1, 4, 7, 0xFF, 0xF, 0, 8, 0x48, 0x10, 0x50, 0x90, 0x18, 0x58, 9, 0x21, 0x61, 0x35
        DB 0xD8, 0xA0, 0x28, 0x68, 0xA8, 0xE8, 0x39, 0x98, 0xA1, 0, 0x30, 0x31, 0x28, 0x68
        DB 40, 45, 48   ; id=40
        DB 0, 3, 6, 7, 0xFF, 0xA9, 0, 8, 0xF, 0x46, 0x47, 6, 7, 0x86, 0x87, 0xC6, 0xC7, 0xF
        DB 0x1E, 0x1F, 0x5E, 0x5F, 0x9E, 0x9F, 0xDE, 0xDF, 0xC, 0x1D, 0x5D, 0x9D, 0xDD, 0xD5
        DB 0xC0, 0x17, 0x10, 0x31, 0, 0x30, 0xB, 0x16, 0x17, 0xE, 0xF
        DB 43, 5, 96   ; id=43
        DB 0, 2, 8
        DB 44, 5, 112   ; id=44
        DB 0, 2, 8
        DB 47, 34, 40   ; id=47
        DB 0, 4, 7, 0xFF, 0xB, 0x1A, 0x5A, 0x9A, 0x9D, 0xF, 0x5D, 0x1D, 0x1B, 0x1C, 0x28, 8
        DB 0xF, 0x2F, 0x33, 0x9E, 0x9F, 0x98, 0x99, 0x7D, 0x68, 0x48, 0x4F, 0x6F, 0x5B, 0x5C
        DB 0x88, 0x50
        DB 48, 22, 24   ; id=48
        DB 0, 1, 2, 4, 7, 0xFF, 0xE, 0, 0x40, 0xF8, 0x20, 0x18, 0x60, 0x58, 0x71, 0xE8, 0xC8
        DB 0x79, 0xA0, 0x98
        DB 49, 34, 32   ; id=49
        DB 0, 3, 6, 7, 0xFF, 0xB5, 0x38, 0x39, 0x3A, 0x3D, 0x3E, 0x3F, 0xA, 0x1C, 0x5C, 0x9C
        DB 0x33, 0x64, 0x5D, 0x54, 0x5B, 0xBF, 0x23, 0x24, 0x25, 0x1B, 0x1D, 0x13, 0x14, 0x15
        DB 0xD0, 0xDC
        DB 51, 20, 104   ; id=51
        DB 0, 2, 8, 0xFF, 0xF, 0x1A, 0x1B, 0x1C, 0x1D, 0x5A, 0x5D, 0x9A, 0x9D, 0x7B, 0xDA, 0xDD
        DB 0x5B, 0x5C
        DB 52, 37, 88   ; id=52
        DB 0, 2, 8, 0xFF, 0xF, 0x3A, 0x7A, 0x22, 0x1A, 0x5A, 0x12, 0x52, 0x92, 0xC, 0xA, 0x33
        DB 0x4A, 0xBA, 0x2B, 0x63, 0x2A, 0x62, 0x9A, 0xD2, 0x7A, 0xFA, 0x73, 0x6B, 0, 0x30
        DB 0x7B, 0x32, 0x6A, 0xA2, 0xDA
        DB 54, 34, 32   ; id=54
        DB 0, 1, 4, 7, 0xFF, 0xF, 0x3D, 0x35, 0x2D, 0x25, 0x1D, 0x5D, 0x1A, 0x5A, 9, 0x18, 0x19
        DB 0x21, 0xDC, 0x5B, 0xB9, 0x1B, 0x1C, 0x7F, 0x7D, 0x75, 0x6D, 0x65, 0x9D, 0x9A, 0x58
        DB 0x59
        DB 55, 29, 40   ; id=55
        DB 0, 2, 3, 6, 7, 0xFF, 0xF, 0xF, 6, 0x46, 0xE, 0x2F, 0x67, 0x9F, 0xD7, 0xBC, 0x17
        DB 7, 0x16, 0x4E, 0x86, 0, 0x30, 8, 0xF, 0x18, 0x4F
        DB 56, 36, 40   ; id=56
        DB 0, 1, 2, 4, 7, 0xFF, 0xF, 5, 0xD, 0x15, 0x1C, 0x23, 0x2A, 0x32, 0x38, 0xB, 2, 0xB
        DB 0x12, 0x19, 0x7F, 0x45, 0x4D, 0x55, 0x5C, 0x63, 0x6A, 0x72, 0x78, 0x7B, 0x42, 0x4B
        DB 0x52, 0x59
        DB 57, 21, 32   ; id=57
        DB 0, 3, 6, 7, 0xFF, 0xE, 7, 0x1F, 0x57, 0x8F, 4, 0x45, 0x86, 0x38, 0x47, 0, 0x30, 0x20
        DB 0xC7
        DB 59, 39, 88   ; id=59
        DB 0, 0xB, 0xD, 8, 0xFF, 0xF, 0x23, 0x24, 0x63, 0x64, 0xA3, 0xA4, 0xE3, 0xE4, 9, 0x2B
        DB 0x2C, 0x4A, 0xC4, 0xCC, 0xD4, 0x5A, 0xC3, 0xCB, 0xD3, 0x31, 0xDB, 0xDC, 0x7F, 2
        DB 0xA, 0x12, 0x1A, 5, 0xD, 0x15, 0x1D
        DB 60, 11, 104   ; id=60
        DB 0, 2, 8, 0xFF, 0x69, 0x2B, 0x13, 0x80, 0x23
        DB 62, 42, 32   ; id=62
        DB 0, 1, 4, 7, 0xFF, 0x37, 0x54, 0x55, 0x95, 0x5D, 0x9D, 0xDD, 0x65, 0xA5, 0x36, 0xE5
        DB 0x64, 0xA4, 0xE4, 0x63, 0xA3, 0xE3, 0x3F, 0x23, 0x24, 0x25, 0x1B, 0x1D, 0x13, 0x14
        DB 0x15, 0, 0x30, 0x35, 0x25, 0x24, 0x64, 0x23, 0x63, 0xA3
        DB 63, 34, 24   ; id=63
        DB 0, 0xB, 0xD, 3, 6, 7, 0xFF, 0xF, 0xE3, 0xE4, 0xDB, 0xDC, 0xDD, 0x95, 0x4D, 5, 9
        DB 0xC3, 0xC4, 0, 0x30, 0x37, 0x13, 0x14, 0x1A, 0x22, 0x1D, 0x25, 0x2B, 0x2C, 0xE0
        DB 0x63
        DB 64, 27, 48   ; id=64
        DB 0xA, 2, 0xC, 4, 5, 0xFF, 0xD, 0x20, 0x68, 0xB0, 0xFF, 0xE7, 0xDF, 0x4A, 0xF8, 0xF9
        DB 0xFA, 0x31, 0xFB, 0xFC, 0x3B, 0x3F, 0x3E, 0x3D, 0x3B
        DB 65, 40, 40   ; id=65
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xAA, 0, 8, 0x10, 0xB2, 0x3D, 0x3E, 0x3F, 0xB, 0x23, 0x63
        DB 0xA3, 0xE3, 0x12, 0x12, 0x2D, 0x92, 0x1A, 0x52, 0x6D, 0xD2, 0xBA, 6, 7, 0xF, 0, 0x30
        DB 8, 0x23, 0xC8, 0x63
        DB 66, 22, 152   ; id=66
        DB 1, 3, 9, 0xFF, 0xB, 0x2A, 0x2D, 0x12, 0x15, 0xBF, 0x6D, 0x65, 0x5D, 0x55, 0x6A, 0x62
        DB 0x5A, 0x52, 0xE0, 0x23
        DB 67, 41, 32   ; id=67
        DB 0xB, 0xD, 3, 5, 6, 0xFF, 0xF, 0xC3, 0xC4, 0x23, 0x24, 0x63, 0x64, 0xA3, 0xA4, 9
        DB 0x25, 0x22, 0x61, 0x2B, 0x2C, 0x7F, 0x62, 0x65, 0x1B, 0x1C, 0x13, 0x14, 0xB, 0xC
        DB 0x49, 0xDC, 0xD4, 0x59, 0xDB, 0xD3, 0x31, 0xCB, 0xCC
        DB 68, 53, 48   ; id=68
        DB 0, 1, 2, 4, 7, 0xFF, 0x37, 0x62, 0xA2, 0xE2, 0x5B, 0x9B, 0xDB, 0x52, 0x92, 0x35
        DB 0xD2, 0x59, 0x99, 0xD9, 0x5A, 0x9A, 0x10, 0xE, 0, 0x30, 8, 0x1A, 0, 0, 0xF0, 0xDA
        DB 0xF8, 0, 0x28, 0x1A, 8, 0x19, 0x10, 0x22, 0x18, 0x1B, 0x20, 0x12, 0x35, 0x2E, 0x2F
        DB 0x25, 0x1D, 0x16, 0x17
        DB 69, 25, 168   ; id=69
        DB 1, 3, 9, 0xFF, 0xB, 0x15, 0x2D, 0x2A, 0x12, 0x31, 0xAB, 0xAC, 0x7F, 0x55, 0x1D, 0x25
        DB 0x6D, 0x6A, 0x22, 0x1A, 0x52, 0xE0, 0x23
        DB 70, 34, 24   ; id=70
        DB 0, 2, 3, 6, 7, 0xFF, 0xF, 0x27, 0x67, 0xA7, 0xE7, 0x1F, 0x5F, 0x9F, 0xDF, 0xD, 0x2E
        DB 0x2F, 0x25, 0x1D, 0x16, 0x17, 0x7D, 0x6E, 0x6F, 0x65, 0x5D, 0x56, 0x57, 0x31, 0x26
        DB 0x1E
        DB 71, 5, 96   ; id=71
        DB 0, 2, 8
        DB 72, 37, 96   ; id=72
        DB 0, 2, 8, 0xFF, 0xD, 0x3A, 0x32, 0x72, 2, 0xA, 0x4A, 0x31, 0xA2, 0x9A, 0x49, 0xAA
        DB 0x92, 0x7F, 0x2A, 0x2B, 0x2C, 0x2D, 0x22, 0x23, 0x24, 0x25, 0x7F, 0x1A, 0x1B, 0x1C
        DB 0x1D, 0x12, 0x13, 0x14, 0x15
        DB 73, 15, 24   ; id=73
        DB 0, 2, 0xA, 0xC, 4, 7, 0xFF, 0x11, 0x25, 0x65, 9, 0xDF, 0xE7
        DB 74, 27, 168   ; id=74
        DB 0xA, 3, 0xC, 9, 0xFF, 9, 0xE7, 0xDF, 0x4F, 0x19, 0x21, 0x22, 0x1A, 0x24, 0x1C, 0x25
        DB 0x1D, 0x3B, 0x1B, 0x23, 0x26, 0x1E, 0x21, 0xE6, 0x5E
        DB 75, 48, 48   ; id=75
        DB 0, 2, 3, 6, 7, 0xFF, 0xAD, 0, 8, 0x10, 0x28, 0x30, 0x38, 0xF, 0xFF, 0xBF, 0x7F, 0x3F
        DB 0x37, 0x77, 0xB7, 0x2F, 0xC, 0x6F, 0xAF, 0x27, 0x67, 0x1F, 0x11, 0xF, 0x8F, 0x19
        DB 0x4F, 0xCF, 0xBC, 0xEF, 0xA7, 0x5F, 0x17, 0xF7, 0, 0x30, 0xD0, 0x3F, 0x10, 0xF
        DB 76, 43, 32   ; id=76
        DB 0xA, 0xB, 0xC, 0xD, 4, 5, 0xFF, 0xD, 0xC3, 0xC4, 0xE7, 0xDF, 0xC0, 0xF8, 0x37, 0xD8
        DB 0xE0, 0xE8, 0xFA, 0xFD, 0xEF, 0x7B, 0x7C, 0x31, 0xF0, 0xF9, 0x3E, 0x33, 0x34, 0x18
        DB 0x20, 0x28, 0x3A, 0x3D, 0, 0x30, 8, 0x7F, 0x31, 0x3E, 0x37
        DB 77, 9, 152   ; id=77
        DB 1, 3, 9, 0xFF, 0xE1, 0x23, 0x1C
        DB 78, 32, 40   ; id=78
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0x3A, 0x32, 0x2A, 0x29, 0x28, 0x3D, 0x35, 0x2D, 0xF
        DB 0x2E, 0x2F, 0x17, 0x16, 0x15, 0xD, 5, 2, 0xB, 0xA, 0x10, 0x11, 0x12
        DB 79, 36, 48   ; id=79
        DB 2, 3, 5, 6, 0xFF, 0xAD, 0, 8, 0x10, 0x38, 0x30, 0x28, 0xF, 5, 0x45, 6, 0x46, 0x86
        DB 7, 0x47, 0x87, 9, 0xC7, 0xFF, 0x39, 0x37, 0x2F, 0x71, 0xEF, 0xCF, 0, 0x30, 0xD8
        DB 0x3F
        DB 81, 5, 96   ; id=81
        DB 0, 2, 8
        DB 84, 32, 104   ; id=84
        DB 0, 2, 8, 0xFF, 0xD, 0x3A, 0x3D, 0x33, 2, 5, 0xB, 0x50, 0x34, 0x40, 0xC, 0x7D, 0x42
        DB 0x45, 0x4B, 0x73, 0x7A, 0x7D, 0x3B, 0x2C, 0x24, 0x1C, 0x14, 0x21, 0xE4, 0x5C
        DB 86, 47, 48   ; id=86
        DB 2, 4, 5, 0xFF, 9, 0x7A, 0x7D, 0x79, 0xBA, 0xBD, 0xF0, 9, 0xF8, 0, 0x28, 0xE, 0x10
        DB 0x16, 0x18, 0xF, 0x20, 6, 8, 0xD, 0x35, 0x38, 0x39, 0x3A, 0x3D, 0x3E, 0x3F, 0x37
        DB 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x2A, 0x2B, 0x33, 0x2C, 0x2D, 0x23, 0x24
        DB 87, 18, 88   ; id=87
        DB 0, 2, 8, 0xFF, 0xB, 0xB, 0xC, 0x33, 0x34, 0x3B, 0xA, 0xD, 0x32, 0x35, 0x80, 0x1C
        DB 88, 44, 88   ; id=88
        DB 0, 2, 8, 0xFF, 0xF, 0x12, 0x13, 0x14, 0x15, 0x1A, 0x1B, 0x1C, 0x1D, 0xF, 0x22, 0x23
        DB 0x24, 0x25, 0x2A, 0x2B, 0x2C, 0x2D, 0, 0x30, 0xA7, 0x12, 0x13, 0x14, 0x15, 0x1A
        DB 0x1B, 0x1C, 0x1D, 0xA7, 0x22, 0x23, 0x24, 0x25, 0x2A, 0x2B, 0x2C, 0x2D
        DB 89, 28, 48   ; id=89
        DB 0xB, 0xD, 4, 5, 0xFF, 0xB, 0xC3, 0xC4, 7, 0x46, 8, 0x85, 0x3C, 0x1C, 0x1B, 0x1D
        DB 0x24, 0x14, 0x32, 0x5C, 0x9C, 0xDC, 0, 0x30, 0x30, 0x1C
        DB 91, 25, 104   ; id=91
        DB 0, 2, 8, 0xFF, 0x43, 0x12, 0x13, 0x14, 0x15, 0x53, 0x2A, 0x2B, 0x2C, 0x2D, 0x3F
        DB 0x1A, 0x1B, 0x1C, 0x1D, 0x22, 0x23, 0x24, 0x25
        DB 94, 8, 96   ; id=94
        DB 0, 2, 8, 0xFF, 0xE8, 0x24
        DB 97, 41, 48   ; id=97
        DB 1, 0xB, 0xD, 4, 5, 0xFF, 0xF, 0xC3, 0xC4, 0x1A, 0x5A, 0x9A, 0xDA, 0x16, 0x56, 9
        DB 0x96, 0xD6, 0x11, 0x36, 0xB6, 0x19, 0x76, 0xF6, 0xBA, 6, 7, 0xF, 0, 0x30, 8, 0x36
        DB 0x68, 0x1A, 0x70, 0x16, 0x79, 0x56, 0x5A
        DB 98, 41, 24   ; id=98
        DB 0, 3, 6, 7, 0xFF, 0xB2, 0x3D, 0x3E, 0x3F, 0xF, 0x23, 0x24, 0x25, 0x1B, 0x1D, 0x13
        DB 0x14, 0x15, 0xA, 0x9C, 0xDC, 9, 0xBF, 0x63, 0x64, 0x65, 0x5B, 0x5D, 0x53, 0x54, 0x55
        DB 0x10, 0x49, 0x18, 0x89, 0, 0x30, 0xC8, 0x1C
        DB 100, 43, 32   ; id=100
        DB 0, 1, 2, 4, 7, 0xFF, 0xF, 0x30, 0x28, 0x68, 0xA8, 0x20, 0x60, 0xA0, 0xE0, 0xC, 0x90
        DB 0xD1, 0xD9, 0xC9, 0x98, 0x32, 0x80, 0xC0, 0x88, 0x39, 0x18, 8, 0, 0x30, 0xD, 0x20
        DB 0x58, 0x48, 0x19, 0x11, 9, 0x32, 0, 0x40, 0x50
        DB 101, 38, 40   ; id=101
        DB 0, 3, 6, 7, 0xFF, 0xA9, 0x7A, 0x72, 0xB1, 0x68, 0x69, 0xF, 2, 0x41, 0x80, 0xC8, 0x2F
        DB 0x77, 0xBF, 0xFE, 0xF, 0x28, 0x29, 0x2A, 0x32, 0x3A, 0x70, 0x71, 0x78, 0xB, 0x79
        DB 0xB0, 0xB1, 0xB9, 0xD8, 0xB8
        DB 103, 18, 112   ; id=103
        DB 0, 2, 8, 0xFF, 0xB, 0x2A, 0x2D, 0x12, 0x15, 0xBB, 0x6A, 0x6D, 0x52, 0x55, 0x88, 0x62
        DB 104, 5, 112   ; id=104
        DB 0, 2, 8
        DB 106, 49, 40   ; id=106
        DB 0, 1, 4, 7, 0xFF, 0xF, 0x19, 0x59, 0x12, 0x52, 9, 0x49, 0x10, 0x50, 9, 0x11, 0x51
        DB 0xF0, 0xE, 0xF8, 0, 0x37, 0x3A, 0x32, 0x39, 0x31, 0x2B, 0x2C, 0x23, 0x24, 0x35, 0x3D
        DB 0x35, 0x3E, 0x36, 0x2D, 0x2A, 0x28, 0x91, 8, 0x90, 0x10, 0x99, 0x18, 0x92, 0x20
        DB 0x89
        DB 107, 43, 32   ; id=107
        DB 0, 2, 3, 6, 7, 0xFF, 0xF, 0x3F, 0x7F, 0xBF, 0xFF, 0x3A, 0x32, 0x33, 0x34, 9, 0x35
        DB 0x3D, 0x7D, 0x7A, 0x72, 0x73, 0x74, 0x75, 0x7D, 0xF0, 7, 0x10, 0x47, 0xF8, 0, 0x28
        DB 9, 8, 8, 0x10, 0x11, 0x18, 0xA, 0x20, 1
        DB 109, 6, 24   ; id=109
        DB 0, 1, 4, 7
        DB 110, 46, 48   ; id=110
        DB 2, 3, 5, 6, 0xFF, 0xAB, 0, 0x10, 0x28, 0x38, 0xD, 0x15, 0x55, 0x14, 0x54, 0x94, 0xD4
        DB 8, 0xFC, 0x33, 0xB4, 0xAC, 0xA4, 0x9C, 0xBD, 0x3D, 0x3E, 0x3B, 0x3A, 0x39, 0x3F
        DB 0xBF, 0x35, 0x2D, 0x25, 0x1D, 0x33, 0x2B, 0x23, 0x1B, 0, 0x30, 0xC8, 0x3C
        DB 114, 44, 40   ; id=114
        DB 0, 2, 4, 7, 0xFF, 0xE1, 0x27, 0x18, 0xF8, 0, 0x37, 8, 9, 0xA, 0x10, 0x11, 0x12, 0x1B
        DB 0x1C, 0x37, 0xD, 0xE, 0xF, 0x15, 0x16, 0x17, 0x23, 0x24, 0x37, 0x28, 0x29, 0x2A
        DB 0x30, 0x31, 0x32, 0x2D, 0x2E, 0x33, 0x2F, 0x35, 0x36, 0x37
        DB 116, 52, 24   ; id=116
        DB 1, 2, 4, 5, 0xFF, 0xF, 0x38, 0x30, 0x28, 0x29, 0x2A, 0x32, 0x33, 0x34, 0xF, 0x2C
        DB 0x24, 0x1C, 0x25, 0x1D, 0x26, 0x1E, 0x2E, 0xA, 0x16, 0x2F, 0x17, 0xF0, 0x78, 0xF8
        DB 0, 0x37, 0x6F, 0x57, 0x6E, 0x56, 0x66, 0x5E, 0x65, 0x5D, 0x28, 9, 8, 8, 0x10, 0x11
        DB 0x18, 0xA, 0x20, 1
        DB 117, 40, 48   ; id=117
        DB 1, 2, 3, 5, 6, 0xFF, 0xF, 0x2B, 0x6B, 0xAB, 0xEB, 0x2C, 0x6C, 0xAC, 0xEC, 0xF, 0x22
        DB 0x62, 0xA2, 0x25, 0x65, 0xA5, 0x1B, 0x5B, 9, 0x1C, 0x5C, 0x31, 0xA3, 0xA4, 0x39
        DB 0x23, 0x24, 0, 0x30, 9, 0x2B, 0x2C
        DB 118, 34, 160   ; id=118
        DB 1, 3, 9, 0xFF, 0x53, 0x6A, 0x6B, 0x6C, 0x6D, 0x43, 0x52, 0x53, 0x54, 0x55, 0x3F
        DB 0x2A, 0x2B, 0x2C, 0x2D, 0x22, 0x23, 0x24, 0x25, 0x3F, 0x1A, 0x1B, 0x1C, 0x1D, 0x12
        DB 0x13, 0x14, 0x15
        DB 119, 46, 40   ; id=119
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0x16, 0xD, 0xA, 0x11, 0x29, 0x32, 0x35, 0x2E, 0xF, 0x3F
        DB 0x38, 0, 7, 0x23, 0x24, 0x1B, 0x1C, 0x3B, 0x7F, 0x78, 0x47, 0x40, 0x7F, 0x72, 0x69
        DB 0x51, 0x4A, 0x4D, 0x56, 0x6E, 0x75, 0x7B, 0x63, 0x64, 0x5B, 0x5C
        DB 120, 28, 40   ; id=120
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0, 0x40, 0x38, 0x78, 0x3F, 0x7F, 7, 0x47, 0xB, 0x23
        DB 0x24, 0x1B, 0x1C, 0x79, 0x80, 0xBF, 0x80, 0x5C
        DB 121, 5, 160   ; id=121
        DB 1, 3, 9
        DB 122, 33, 48   ; id=122
        DB 1, 2, 3, 5, 6, 0xFF, 0xAA, 0, 8, 0x10, 0xB4, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0xD, 0x24
        DB 0x14, 0x1B, 0x1C, 0x1D, 0xDC, 0x10, 0x5C, 0x18, 0x9C, 0, 0x30, 0xC0, 0x1C
        DB 123, 28, 24   ; id=123
        DB 2, 3, 5, 6, 0xFF, 0xE, 0xF, 0x4F, 0x27, 0x67, 0xA7, 0x16, 0x1E, 0xB, 0x5E, 0x56
        DB 0x9E, 0x96, 0x32, 0x5F, 0x57, 0x8F, 0x98, 0xDF, 0xB8, 0xE
        DB 125, 30, 40   ; id=125
        DB 0, 2, 4, 7, 0xFF, 0x7F, 0, 0x11, 0x19, 0x21, 2, 0x1A, 0x32, 0x3A, 0x7F, 0x2B, 0x1B
        DB 0x14, 0x2C, 0x3D, 0x25, 0x15, 0xD, 0x7B, 5, 0x36, 0x26, 0x17
        DB 130, 34, 32   ; id=130
        DB 0xA, 0xB, 0xC, 0xD, 4, 5, 0xFF, 0xF, 0xC3, 0xC4, 0xEF, 0xE7, 0xDF, 0xFE, 0xFB, 0xF8
        DB 9, 0x31, 0xD0, 0x29, 0xFC, 0xC0, 0x30, 0xD8, 0x98, 0x40, 0x18, 0x80, 0, 0x30, 8
        DB 0x3B
        DB 131, 7, 48   ; id=131
        DB 0, 1, 3, 6, 7
        DB 132, 29, 40   ; id=132
        DB 0, 1, 3, 6, 7, 0xFF, 0xAA, 0, 8, 0x10, 0xE, 0x1C, 0x5C, 0x9C, 0x24, 0x14, 0x1B, 0x1D
        DB 0xD0, 0xDC, 0, 0x30, 0xA3, 0xE4, 0xDB, 0xDD, 0xD4
        DB 133, 5, 152   ; id=133
        DB 1, 3, 9
        DB 134, 31, 176   ; id=134
        DB 1, 3, 9, 0xFF, 0xD, 0x2C, 0x6C, 0xAC, 0x14, 0x54, 0x94, 0x7F, 0x2D, 0x25, 0x1D, 0x15
        DB 0x2B, 0x23, 0x1B, 0x13, 0x79, 0xEC, 0xD4, 0x39, 0x24, 0x1C, 0x21, 0xDC, 0xE4
        DB 135, 45, 32   ; id=135
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xF, 0x33, 0x34, 0x26, 0x1E, 0xB, 0xC, 0x21, 0x19, 0x37
        DB 0x2B, 0x6B, 0x2C, 0x6C, 0x25, 0x65, 0x1D, 0x5D, 0x37, 0x13, 0x53, 0x14, 0x54, 0x22
        DB 0x62, 0x1A, 0x5A, 0x33, 0xA3, 0xA4, 0x9B, 0x9C, 0x3A, 0x1B, 0x1C, 0x24
        DB 136, 32, 32   ; id=136
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0x3F, 0x3A, 0x32, 0x2A, 0x29, 0x28, 0x10, 0x11, 0x12, 0x3F
        DB 0xA, 2, 5, 0xD, 0x15, 0x16, 0x17, 0x2F, 0x3B, 0x2E, 0x2D, 0x35, 0x3D
        DB 137, 8, 176   ; id=137
        DB 1, 3, 9, 0xFF, 0x88, 0x5A
        DB 138, 17, 152   ; id=138
        DB 1, 3, 9, 0xFF, 0x3F, 0x2A, 0x22, 0x1A, 0x12, 0x2D, 0x25, 0x1D, 0x15, 0x88, 0x6B
        DB 139, 36, 40   ; id=139
        DB 0, 1, 3, 6, 7, 0xFF, 0xF0, 0xE, 0xF8, 0, 0x28, 9, 8, 8, 0x10, 0x11, 0x18, 0xA, 0x20
        DB 1, 0x37, 0x3A, 0x7A, 0x32, 0x72, 0x2B, 0x6B, 0x2C, 0x6C, 0x33, 0x35, 0x75, 0x3D
        DB 0x7D
        DB 140, 33, 48   ; id=140
        DB 0, 1, 3, 6, 7, 0xFF, 0xAA, 0, 8, 0x10, 0xB2, 0x3D, 0x3E, 0x3F, 0xB, 0xE, 0x4E, 0x8E
        DB 0xCE, 0x10, 0xA, 0x18, 0x4A, 0, 0x30, 0xA, 0xE, 0xF, 6, 0xD8, 0x4E
        DB 141, 42, 32   ; id=141
        DB 2, 3, 5, 6, 0xFF, 0xAA, 0x10, 8, 0, 0xF, 0x38, 0x39, 0x79, 0x3A, 0x7A, 0xBA, 0x7F
        DB 0x17, 0xC, 0x57, 0x97, 0xF, 0x4F, 7, 0xBF, 0x3B, 0x3C, 0x3D, 0x35, 0x2D, 0x36, 0x3E
        DB 0x2E, 0xBB, 0x37, 0x2F, 0x27, 0x1F, 0xD0, 0xBF
        DB 147, 41, 24   ; id=147
        DB 0xA, 0xB, 0xC, 0xD, 4, 5, 0xFF, 0xF, 3, 0x43, 0x83, 0xC3, 4, 0x44, 0x84, 0xC4, 0xF
        DB 0x1F, 0x5F, 0x9F, 0xDF, 0x27, 0x67, 0xA7, 0xE7, 0x60, 0x23, 9, 0xCB, 0xE6, 0x3F
        DB 0x2A, 0x2B, 0x2C, 0x1A, 0x1B, 0x1C, 0x22, 0x24
        DB 148, 33, 32   ; id=148
        DB 0, 2, 3, 6, 7, 0xFF, 0xAD, 0, 8, 0x10, 0x28, 0x30, 0x38, 0xC, 0x8E, 0x16, 0xD, 0xF
        DB 6, 0x33, 0x56, 0x4F, 0x46, 0x4D, 0xBB, 0x15, 0x17, 5, 7, 0xD0, 0xCE
        DB 149, 21, 48   ; id=149
        DB 0, 1, 4, 7, 0xFF, 9, 0x1A, 0x5A, 0x28, 0x99, 0x32, 0x92, 0x9B, 0xA2, 0x3B, 0x19
        DB 0x1B, 0x22, 0x12
        DB 150, 47, 24   ; id=150
        DB 0, 3, 6, 7, 0xFF, 0xAA, 0x28, 0x30, 0x38, 0xB2, 0x3D, 0x3E, 0x3F, 0xF, 0x88, 0x40
        DB 0, 5, 0x45, 0xCD, 0xD6, 0xCE, 0xB, 0xE, 0x4E, 0x17, 0x57, 0x4B, 0xC9, 0xCA, 0xCB
        DB 0xCC, 0xBC, 0x85, 0x8E, 0x97, 0x86, 0x8F, 0xC8, 7, 0, 0x30, 0x11, 0xD, 0x16
        DB 151, 17, 88   ; id=151
        DB 0, 2, 8, 0xFF, 0xF8, 0, 0x3F, 0x12, 0x13, 0x14, 0x15, 0x2A, 0x2B, 0x2C, 0x2D
        DB 152, 24, 88   ; id=152
        DB 0, 2, 8, 0xFF, 0xF, 0x1D, 0x13, 0x14, 0x15, 0x22, 0x2A, 0x2B, 0x2C, 0x7F, 0x5D, 0x55
        DB 0x54, 0x53, 0x62, 0x6A, 0x6B, 0x6C
        DB 153, 39, 24   ; id=153
        DB 0, 1, 4, 7, 0xFF, 0xAF, 0, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 9, 0x17, 0x57
        DB 0xB8, 0x97, 0x11, 0x15, 0x95, 0x19, 0x55, 0xD5, 0, 0x30, 0x10, 0x15, 0x18, 0x55
        DB 0xA, 0x95, 0x96, 0x97, 0xC0, 0xD7
        DB 154, 27, 48   ; id=154
        DB 0, 3, 6, 7, 0xFF, 0xF, 0x3F, 0x7F, 0xBF, 0xFF, 0x2D, 0x6D, 0xAD, 0x24, 9, 0x64, 0x1B
        DB 0x32, 0xF6, 0xF7, 0xFE, 0xBA, 0x3E, 0x36, 0x37
        DB 155, 7, 32   ; id=155
        DB 0, 1, 2, 4, 7
        DB 156, 29, 24   ; id=16
        DB 2, 3, 5, 6, 0xFF, 0xD, 0x3E, 0x3F, 0xFE, 0x37, 0x77, 0xB7, 0x3A, 0x3C, 0x35, 0x36
        DB 0x13, 0x23, 0x24, 0x1B, 0x1C, 0x28, 0xFD, 0x30, 0xFF, 0x80, 0x7E
        DB 164, 44, 48   ; id=164
        DB 1, 0xB, 0xD, 4, 5, 0xFF, 0x29, 0x6B, 0x6C, 0xF, 0x13, 0x14, 0xB, 0xC, 0x53, 0x54
        DB 0x4B, 0x4C, 0xB, 0x8B, 0x8C, 0xC3, 0xC4, 0x37, 0x23, 0x63, 0x24, 0x64, 0x1B, 0x5B
        DB 0x1C, 0x5C, 0x33, 0x9B, 0xDB, 0x9C, 0xDC, 0x7B, 0x93, 0x94, 0xCB, 0xCC
        DB 165, 45, 24   ; id=165
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xA9, 0, 8, 0xB1, 0x3E, 0x3F, 0xF, 0x12, 0x52, 0x92, 0xD2
        DB 0x15, 0x55, 0x2D, 0x6D, 0xC, 0xAD, 0x2A, 0x6A, 0xAA, 0xEA, 0xBF, 0x22, 0x1A, 0x2B
        DB 0x2C, 0x25, 0x1D, 0x13, 0x14, 0, 0x30, 8, 0x12, 0xC0, 0x52
        DB 166, 17, 40   ; id=166
        DB 0xB, 0xD, 3, 5, 6, 0xFF, 9, 0xC4, 0xC3, 0x62, 7, 6, 0x85, 0x90, 0x87
        DB 167, 27, 112   ; id=167
        DB 0, 2, 8, 0xFF, 0xD, 0xA, 0xB, 0xC, 0xD, 0x3A, 0x3D, 0x3F, 0x1A, 0x1B, 0x1C, 0x1D
        DB 0x5B, 0x5C, 0x23, 0x24, 0x31, 0x5A, 0x5D, 0x80, 0x25
        DB 168, 5, 112   ; id=168
        DB 0, 2, 8
        DB 169, 25, 40   ; id=169
        DB 1, 2, 4, 5, 0xFF, 0xE0, 0x2A, 0xF8, 0, 0x3F, 0x32, 0x33, 0x34, 0x2D, 0x25, 0x1D
        DB 0x14, 0x13, 0x3B, 0x12, 0x19, 0x21, 0x29
        DB 170, 36, 24   ; id=170
        DB 0, 1, 2, 3, 6, 7, 0xFF, 0xB5, 0x3F, 0x3E, 0x3D, 0x3A, 0x39, 0x38, 0xF, 0x1B, 0x5B
        DB 0x1D, 0x5D, 0x24, 0x64, 0x14, 0x54, 8, 0x1C, 0x33, 0xA4, 0x9B, 0x9D, 0x94, 0x10
        DB 0xDC, 0xC8, 0x5C
        DB 171, 33, 48   ; id=171
        DB 2, 3, 5, 6, 0xFF, 0xF, 0xBE, 0xB7, 0xAF, 0xA7, 0xF6, 0xEE, 0xE6, 0x1E, 0xC, 0x16
        DB 0xE, 0xF, 0x27, 0x67, 0x7B, 0x5E, 0x56, 0x4E, 0x4F, 0x28, 0xFF, 0, 0x30, 0x88, 0x37
        DB 181, 45, 40   ; id=181
        DB 0xA, 2, 0xC, 4, 5, 0xFF, 0xF, 0xF8, 0xE8, 0xFA, 0xFF, 0xE7, 0xDF, 0xEF, 0xFD, 9
        DB 0xFA, 0xFC, 0x2C, 0, 0x48, 0x90, 0xD8, 0xFB, 0x34, 0xE0, 0xF0, 0xF9, 0xFE, 0xF7
        DB 0xBC, 0x38, 0x30, 0x39, 0x3F, 0x37, 0, 0x30, 0xBB, 0x28, 0x3A, 0x3D, 0x2F
        DB 182, 28, 32   ; id=182
        DB 0, 3, 6, 7, 0xFF, 0xAA, 0x10, 8, 0, 0xB2, 0x3D, 0x3E, 0x3F, 0x3D, 0xF, 0x4F, 0x8F
        DB 6, 0x46, 0x86, 0xC0, 7, 0x10, 0x31, 0x30, 0xC7
        DB 183, 18, 104   ; id=183
        DB 0, 2, 8, 0xFF, 9, 0x1B, 0x1C, 0xF8, 0, 0x3D, 0x13, 0x14, 0x1A, 0x1D, 0x23, 0x24
        DB 184, 33, 104   ; id=184
        DB 0, 2, 8, 0xFF, 0x37, 5, 0x4C, 0x93, 0xDA, 0xE2, 0xAB, 0x74, 0x3D, 0x7F, 0x2A, 0x2C
        DB 0x23, 0x25, 0x1A, 0x1C, 0x13, 0x15, 0x7F, 0x2B, 0x2D, 0x22, 0x24, 0x1B, 0x1D, 0x12
        DB 0x14
        DB 185, 27, 32   ; id=185
        DB 0, 0xA, 0xC, 4, 7, 0xFF, 0xB, 0xE7, 0xDF, 0xF8, 0xFA, 0x29, 0x90, 0xFF, 0x20, 0xF0
        DB 0x39, 8, 0x30, 0, 0x30, 8, 0x3D, 0x28, 0x20
        DB 186, 39, 40   ; id=186
        DB 2, 3, 5, 6, 0xFF, 0xAD, 0, 8, 0x10, 0x28, 0x30, 0x38, 0xF, 0xBF, 0xBE, 0x7D, 0x3C
        DB 0xC7, 0x47, 0x87, 7, 0xBB, 0xB7, 0xAF, 0xA7, 0x9F, 0x10, 0xF7, 0, 0x30, 0x10, 0x77
        DB 0x19, 0x37, 0xB7, 0xD8, 7
        DB 198, 42, 24   ; id=198
        DB 0, 2, 4, 7, 0xFF, 0xF, 0x18, 0x58, 0x98, 0x19, 0x59, 0x1A, 0x5A, 0x9A, 0xF, 0x1D
        DB 0x5D, 0x9D, 0x1E, 0x5E, 0x1F, 0x5F, 0x9F, 0xB, 0x32, 0x35, 0xA, 0xD, 0x21, 0xDB
        DB 0x5C, 0xBF, 0xD8, 0x99, 0xDA, 0x1B, 0x1C, 0xDD, 0x9E, 0xDF
        DB 199, 27, 48   ; id=199
        DB 0, 0xB, 0xD, 4, 7, 0xFF, 0xB, 0xC3, 0xC4, 0xD0, 0xE8, 0x3E, 0, 0x28, 0x68, 0xA8
        DB 0x29, 0x69, 0x2A, 0x34, 0xA9, 0x6A, 0x2B, 0xC0, 0x80
        DB 200, 28, 48   ; id=200
        DB 0, 2, 4, 7, 0xFF, 0xD, 0x3F, 0x3D, 0x35, 0x2D, 0x2E, 0x2F, 0x10, 0x31, 0x18, 0x71
        DB 0x3A, 0x3E, 0x36, 0x37, 0xBC, 0x7D, 0x75, 0x6D, 0x6E, 0x6F
        DB 201, 38, 24   ; id=201
        DB 0, 0xB, 0xD, 4, 7, 0xFF, 9, 0xC3, 0xC4, 0x47, 0xE3, 0xE4, 0x9B, 0x9C, 0xA3, 0xA4
        DB 0xDB, 0xDC, 0x47, 0x2B, 0x6B, 0x2C, 0x6C, 0x25, 0x65, 0x1D, 0x5D, 0x47, 0x13, 0x53
        DB 0x14, 0x54, 0x22, 0x62, 0x1A, 0x5A
        DB 214, 33, 32   ; id=214
        DB 1, 2, 4, 5, 0xFF, 0xAD, 0x28, 0x20, 0x18, 0x10, 8, 0, 0xB5, 0x3A, 0x3B, 0x3C, 0x3D
        DB 0x3E, 0x3F, 0xA, 0x39, 0x31, 0x30, 0x60, 0xF8, 0xC8, 0x38, 0, 0x30, 0x78, 0x38
        DB 215, 29, 40   ; id=215
        DB 0, 2, 3, 6, 7, 0xFF, 0x7F, 0x3D, 0x35, 0x2D, 0x25, 0x1D, 0x15, 0xD, 5, 0x7F, 0x3A
        DB 0x32, 0x2A, 0x29, 0x28, 0x10, 0x11, 0x12, 0x79, 0xA, 2
        DB 216, 17, 40   ; id=216
        DB 0, 1, 2, 4, 7, 0xFF, 0xB, 0x23, 0x24, 0x1B, 0x1C, 0xE8, 0x63, 0xE0, 0x15
        DB 217, 39, 32   ; id=217
        DB 2, 3, 5, 6, 0xFF, 0xF0, 0x1B, 0xF8, 0, 0x28, 9, 8, 8, 0x10, 0x11, 0x18, 0xA, 0x20
        DB 1, 0x37, 0x3B, 0x3C, 0x3D, 0x3E, 0x34, 0x35, 0x36, 0x37, 0x37, 0x2C, 0x2D, 0x2E
        DB 0x2F, 0x25, 0x26, 0x27, 0x1F
        DB 231, 31, 112   ; id=231
        DB 0, 2, 8, 0xFF, 0xF, 0x1A, 0x1B, 0x1C, 0x1D, 0x5A, 0x5B, 0x5C, 0x5D, 9, 0x2B, 0x2C
        DB 0x7B, 0x9A, 0x9B, 0x9C, 0x9D, 0x21, 0xCC, 0xB, 0, 0x30, 0x39, 0x6B, 0x6C
        DB 232, 5, 112   ; id=232
        DB 0, 2, 8
        DB 247, 31, 24   ; id=247
        DB 0xA, 0xB, 0xC, 0xD, 4, 5, 0xFF, 0xF, 0xC3, 0xC4, 0x85, 0x46, 7, 0xDF, 0xE7, 0xF8
        DB 0x41, 0xEF, 0xEE, 0x70, 0xF3, 0, 0x30, 0x30, 0x28, 0x28, 0x18, 0x48, 0x40
        DB 248, 31, 24   ; id=248
        DB 2, 3, 5, 6, 0xFF, 0xAD, 0x38, 0x30, 0x28, 0x10, 8, 0, 9, 0x36, 0x76, 0x31, 0x3D
        DB 0x2F, 0xD8, 0xB6, 0xBD, 0x3C, 0x27, 0x2C, 0x25, 0x26, 0x35, 0x88, 0x6D
block_type_tbl:
        DW 0
        DW block   ; block
        DW rhombus_fat_btm   ; rhombus block fat bottom
        DW rhombus_fat_top   ; rhombus block fat top
        DW block_UD   ; block moving up and down
        DW block_fall   ; block fall on contact
        DW block_collapse   ; block_collapse
        DW broken_egg   ; broken egg - killer
        DW block_slide_N
        DW block_slide_E
        DW block_slide_S
        DW block_slide_W
        DW block_plyr_UD
        DW block_move_EW
        DW block_move_NS
        DW pyramid
        DW stars
        DW mouse_move_circuit
        DW mouse_move_EW
        DW mouse_move_NS
        DW broken_egg_top
        DW cryonaught_look_E
        DW cryonaught_look_S
        DW tubes
        DW obj_dropoff_cylinder
        DW obj_dropoff_square
        DW obj_dropoff_pyramid
        DW obj_dropoff_semisphere
        DW clockwork_mouse
        DW cylinder
        DW remote_ctrl_robot
        DW 0
        DW 0
        DW remote_ctrl_arrow_W
        DW remote_ctrl_arrow_N
        DW remote_ctrl_arrow_E
        DW remote_ctrl_arrow_S
        DW remote_ctrl_block
        DW spikey_dome
        DW land_mine
block:
        DB 0x1E, 8, 8, 0xC, 0x10, 0
rhombus_fat_btm:
        DB 0x1C, 7, 7, 0xC, 0x14, 0
rhombus_fat_top:
        DB 0x1D, 7, 7, 0xC, 0x14, 0
block_UD:
        DB 0x1F, 8, 8, 0xC, 0x14, 0
block_fall:
        DB 0x2C, 8, 8, 0xC, 0x10, 0
block_collapse:
        DB 0x2D, 8, 8, 0xC, 0x10, 0
broken_egg:
        DB 0x2E, 8, 8, 0xC, 0x10, 0
block_slide_N:
        DB 0x44, 8, 8, 0xC, 0x10, 0
block_slide_E:
        DB 0x45, 8, 8, 0xC, 0x10, 0
block_slide_S:
        DB 0x46, 8, 8, 0xC, 0x10, 0
block_slide_W:
        DB 0x47, 8, 8, 0xC, 0x10, 0
block_plyr_UD:
        DB 0x2F, 8, 8, 0xC, 0x14, 0
block_move_EW:
        DB 0x42, 8, 8, 0xC, 0x10, 0
block_move_NS:
        DB 0x43, 8, 8, 0xC, 0x10, 0
pyramid:
        DB 0x48, 8, 8, 0xC, 0x10, 0
stars:
        DB 0x4C, 8, 8, 0xC, 0x10, 0
mouse_move_EW:
        DB 0x56, 7, 7, 0xC, 0x10, 0xB, 7, 7, 0xC, 0x10, 0
mouse_move_NS:
        DB 0x57, 7, 7, 0xC, 0x50, 0xB, 7, 7, 0xC, 0x50, 0
mouse_move_circuit:
        DB 0x5E, 7, 7, 0xC, 0x10, 0xB, 7, 7, 0xC, 0x10, 0
broken_egg_top:
        DB 0x49, 8, 8, 0xC, 0x14, 0
cryonaught_look_E:
        DB 0x4A, 8, 8, 0x18, 0x10, 0
cryonaught_look_S:
        DB 0x4A, 8, 8, 0x18, 0x50, 0
tubes:
        DB 0x4B, 8, 8, 0xC, 0x14, 0
obj_dropoff_cylinder:
        DB 0x70, 8, 8, 0xC, 0x10, 0x6C, 8, 8, 0xC, 0x12, 0
obj_dropoff_square:
        DB 0x71, 8, 8, 0xC, 0x10, 0x6D, 8, 8, 0xC, 0x12, 0
obj_dropoff_pyramid:
        DB 0x72, 8, 8, 0xC, 0x10, 0x6E, 8, 8, 0xC, 0x12, 0
obj_dropoff_semisphere:
        DB 0x73, 8, 8, 0xC, 0x10, 0x6F, 8, 8, 0xC, 0x12, 0
clockwork_mouse:
        DB 0x74, 7, 7, 0xC, 0x10, 0
cylinder:
        DB 0x78, 6, 6, 0xC, 0x10, 0
remote_ctrl_robot:
        DB 0x7C, 7, 7, 0xC, 0x10, 0
remote_ctrl_arrow_W:
        DB 0x7A, 8, 8, 0xC, 0x10, 0
remote_ctrl_arrow_N:
        DB 0x7A, 8, 8, 0xC, 0x50, 0
remote_ctrl_arrow_E:
        DB 0x7B, 8, 8, 0xC, 0x10, 0
remote_ctrl_arrow_S:
        DB 0x7B, 8, 8, 0xC, 0x50, 0
remote_ctrl_block:
        DB 0x80, 8, 8, 0xC, 0x10, 0
spikey_dome:
        DB 0x81, 7, 7, 0xC, 0x14, 0
land_mine:
        DB 0x82, 8, 8, 0xC, 0x10, 0
background_type_tbl:
        DW door_N
        DW door_E
        DW door_S
        DW door_W
        DW long_full_wall_W
        DW long_full_wall_N
        DW long_with_opening_W
        DW long_with_opening_N
        DW thin_room_long_W
        DW thin_room_long_N
        DW high_door_E
        DW high_door_S
        DW high_door_platform_E
        DW high_door_platform_S
door_N:
        DB 2, 0x8D, 0xC5, 0x40, 3, 6, 0x30, 0x50
        DB 3, 0x73, 0xC5, 0x40, 3, 6, 0x30, 0x50
        DB 0
door_E:
        DB 2, 0xC5, 0x73, 0x40, 6, 3, 0x30, 0x10
        DB 3, 0xC5, 0x8D, 0x40, 6, 3, 0x30, 0x10
        DB 0
high_door_E:
        DB 2, 0xC5, 0x73, 0x70, 6, 3, 0x30, 0x10
        DB 3, 0xC5, 0x8D, 0x70, 6, 3, 0x30, 0x10
        DB 0
high_door_platform_E:
        DB 0x1E, 0xC8, 0x78, 0x64, 8, 8, 0xC, 0x10
        DB 0x1E, 0xC8, 0x88, 0x64, 8, 8, 0xC, 0x10
        DB 0
door_S:
        DB 2, 0x8D, 0x3B, 0x40, 3, 6, 0x30, 0x50
        DB 3, 0x73, 0x3B, 0x40, 3, 6, 0x30, 0x50
        DB 0
high_door_S:
        DB 2, 0x8D, 0x3B, 0x70, 3, 6, 0x30, 0x50
        DB 3, 0x73, 0x3B, 0x70, 3, 6, 0x30, 0x50
        DB 0
high_door_platform_S:
        DB 0x1E, 0x78, 0x38, 0x64, 8, 8, 0xC, 0x10
        DB 0x1E, 0x88, 0x38, 0x64, 8, 8, 0xC, 0x10
        DB 0
door_W:
        DB 2, 0x3B, 0x73, 0x40, 6, 3, 0x30, 0x10
        DB 3, 0x3B, 0x8D, 0x40, 6, 3, 0x30, 0x10
        DB 0
long_full_wall_W:
        DB 0xE, 0x40, 0x44, 0x40, 0, 4, 0x30, 0x50
        DB 0xD, 0x40, 0x54, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0x6C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0x84, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0x9C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0xB4, 0x40, 0, 0xC, 0x30, 0x50
        DB 0
long_full_wall_N:
        DB 0xD, 0x4C, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x64, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x7C, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x94, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0xAC, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xE, 0xBC, 0xC0, 0x40, 4, 0, 0x30, 0x10
        DB 0
long_with_opening_W:
        DB 0xD, 0x40, 0x4C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0x64, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0x9C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x40, 0xB4, 0x40, 0, 0xC, 0x30, 0x50
        DB 0
long_with_opening_N:
        DB 0xD, 0x4C, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x64, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x9C, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0xB4, 0xC0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0
thin_room_long_W:
        DB 0xE, 0x60, 0x44, 0x40, 0, 4, 0x30, 0x50
        DB 0xD, 0x60, 0x54, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x60, 0x6C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x60, 0x84, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x60, 0x9C, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xD, 0x60, 0xB4, 0x40, 0, 0xC, 0x30, 0x50
        DB 0xF, 0x68, 0xC0, 0x40, 4, 0, 0x30, 0x10
        DB 0xF, 0x98, 0xC0, 0x40, 4, 0, 0x30, 0x10
        DB 0
thin_room_long_N:
        DB 0xD, 0x4C, 0xA0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x64, 0xA0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x7C, 0xA0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0x94, 0xA0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xD, 0xAC, 0xA0, 0x40, 0xC, 0, 0x30, 0x10
        DB 0xE, 0xBC, 0xA0, 0x40, 4, 0, 0x30, 0x10
        DB 0xF, 0x40, 0x68, 0x40, 0, 4, 0x30, 0x50
        DB 0xF, 0x40, 0x98, 0x40, 0, 4, 0x30, 0x50
        DB 0
        ; Special objects
        ; +0 object graphic no (dynamic $60-$67)
        ; +1 start X position (0x46-0xba)
        ; +2 start Y position (0x40-0x70 +/-0x0c)
        ; +3 start Z position (0x46-0xba)
        ; +4 start screen
        ; +5 current X
        ; +6 current Y
        ; +7 current Z
        ; +8 current screen
special_objs_tbl:
        DB 0, 0x78, 0x78, 0x4C, 4, 0, 0, 0, 0
        DB 0, 0x78, 0x78, 0x94, 5, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x64, 0xB, 0, 0, 0, 0
        DB 0, 0x78, 0x88, 0x7C, 0xD, 0, 0, 0, 0
        DB 0, 0x88, 0x88, 0x70, 0x15, 0, 0, 0, 0
        DB 0, 0x98, 0x78, 0x88, 0x1B, 0, 0, 0, 0
        DB 0, 0x88, 0x78, 0x58, 0x1C, 0, 0, 0, 0
        DB 0, 0x80, 0x78, 0x70, 0x20, 0, 0, 0, 0
        DB 0, 0x48, 0x88, 0x40, 0x27, 0, 0, 0, 0
        DB 0, 0xB8, 0x78, 0x64, 0x2F, 0, 0, 0, 0
        DB 0, 0x48, 0xB8, 0x70, 0x30, 0, 0, 0, 0
        DB 0, 0x68, 0xA8, 0x40, 0x34, 0, 0, 0, 0
        DB 0, 0xB8, 0x58, 0x4C, 0x37, 0, 0, 0, 0
        DB 0, 0xB8, 0x48, 0x58, 0x39, 0, 0, 0, 0
        DB 0, 0x78, 0x88, 0x94, 0x3E, 0, 0, 0, 0
        DB 0, 0x80, 0x98, 0x64, 0x45, 0, 0, 0, 0
        DB 0, 0xB8, 0x80, 0x70, 0x46, 0, 0, 0, 0
        DB 0, 0x80, 0xB8, 0x40, 0x56, 0, 0, 0, 0
        DB 0, 0x80, 0x80, 0x4C, 0x58, 0, 0, 0, 0
        DB 0, 0x88, 0x78, 0x7C, 0x59, 0, 0, 0, 0
        DB 0, 0xA8, 0xA8, 0x7C, 0x61, 0, 0, 0, 0
        DB 0, 0x48, 0x78, 0x64, 0x64, 0, 0, 0, 0
        DB 0, 0x48, 0x48, 0x40, 0x6A, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x70, 0x6B, 0, 0, 0, 0
        DB 0, 0x80, 0x98, 0x7C, 0x75, 0, 0, 0, 0
        DB 0, 0xB8, 0x68, 0x40, 0x7B, 0, 0, 0, 0
        DB 0, 0x78, 0x88, 0x40, 0x87, 0, 0, 0, 0
        DB 0, 0x80, 0x80, 0x40, 0x8A, 0, 0, 0, 0
        DB 0, 0x68, 0x78, 0x58, 0x95, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x70, 0x9A, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x4C, 0x9C, 0, 0, 0, 0
        DB 0, 0x78, 0x88, 0x40, 0xA9, 0, 0, 0, 0
        DB 0, 0xB8, 0x78, 0x40, 0xAB, 0, 0, 0, 0
        DB 0, 0x80, 0x78, 0x4C, 0xB7, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x4C, 0xC8, 0, 0, 0, 0
        DB 0, 0xB8, 0xB8, 0x40, 0xD9, 0, 0, 0, 0
sprite_tbl:
        DW spr_00, spr_00, spr_22, spr_23, spr_26, spr_28, spr_27, spr_2A, spr_2B
        DW spr_2C, spr_29, spr_18, spr_2E, spr_24, spr_41, spr_25, spr_3B, spr_3D
        DW spr_3F, spr_3D, spr_35, spr_37, spr_39, spr_37, spr_31, spr_2F, spr_33
        DW spr_33, spr_1D, spr_1E, spr_1F, spr_1F, spr_3C, spr_3E, spr_40, spr_3E
        DW spr_36, spr_38, spr_3A, spr_38, spr_32, spr_30, spr_34, spr_34, spr_1F
        DW spr_1F, spr_1A, spr_1F, spr_47, spr_46, spr_47, spr_46, spr_45, spr_44
        DW spr_43, spr_42, spr_42, spr_43, spr_44, spr_45, spr_46, spr_47, spr_46
        DW spr_47, spr_47, spr_46, spr_1F, spr_1F, spr_1F, spr_1F, spr_1F, spr_1F
        DW spr_2D, spr_19, spr_1B, spr_21, spr_47, spr_46, spr_45, spr_46, spr_13
        DW spr_12, spr_11, spr_14, spr_17, spr_02, spr_1C, spr_20, spr_15, spr_16
        DW spr_2F, spr_30, spr_2F, spr_30, spr_1C, spr_20, spr_49, spr_4A, spr_4B
        DW spr_4C, spr_49, spr_4A, spr_4B, spr_4C, spr_49, spr_4A, spr_4B, spr_4C
        DW spr_45, spr_46, spr_47, spr_46, spr_48, spr_48, spr_48, spr_48, spr_0C
        DW spr_0D, spr_0B, spr_0E, spr_0F, spr_10, spr_09, spr_0A, spr_05, spr_06
        DW spr_07, spr_08, spr_1F, spr_04, spr_03, spr_01
spr_00:
        DB 0, 0
spr_01:
        DB 3, 20
        DB 3, 0, 0xFF, 0x7E, 0xC0, 0, 0xF, 3, 0xFF
        DB 0x81, 0xF0, 0xC0, 0x1F, 0xC, 0xFF, 0x7E, 0xF8, 0x30
        DB 0x3F, 0x13, 0xFF, 0xFF, 0xFC, 0xC8, 0x7F, 0x23, 0xFF
        DB 0xFF, 0xFE, 0xF4, 0x7F, 0x11, 0xFF, 0xFF, 0xFE, 0xF8
        DB 0x7F, 0x39, 0xFF, 0xFF, 0xFE, 0xFC, 0x3F, 0x1C, 0xFF
        DB 0xC3, 0xFC, 0xF8, 0x3F, 0xF, 0xFF, 0x3C, 0xF8, 0xF0
        DB 0xF, 4, 0xFF, 0xFF, 0xF0, 0x60, 7, 2, 0xFF
        DB 0xFF, 0xE0, 0x80, 7, 2, 0xFF, 0xFF, 0xE0, 0xC0
        DB 7, 2, 0xFF, 0xC3, 0xE0, 0xC0, 7, 2, 0xFF
        DB 0x3C, 0xE0, 0xC0, 7, 2, 0xFF, 0xFF, 0xE0, 0x40
        DB 7, 1, 0xFF, 0xBD, 0xE0, 0x80, 7, 3, 0xFF
        DB 0x3C, 0xE0, 0xC0, 3, 1, 0xFF, 0xE7, 0xC0, 0x80
        DB 1, 0, 0xFF, 0xE7, 0x80, 0, 0, 0, 0xFF
        DB 0x3C, 0, 0
spr_02:
        DB 5, 35
        DB 0, 0, 0x78, 0, 0, 0, 0x1E, 0, 0
        DB 0, 0, 0, 0xFC, 0x78, 0, 0, 0x3F, 0x1E
        DB 0, 0, 0, 0, 0xFC, 0x78, 0, 0, 0x3F
        DB 0x1E, 0, 0, 0, 0, 0x7E, 0x3C, 0, 0
        DB 0x7E, 0x3C, 0, 0, 0, 0, 0x3F, 0x1E, 0xFF
        DB 0, 0xFC, 0x78, 0, 0, 0, 0, 0x3F, 0x11
        DB 0xFF, 0xDF, 0xFF, 0x88, 0, 0, 0, 0, 0x3F
        DB 0xF, 0xFF, 0x3F, 0xFC, 0xF0, 0, 0, 0, 0
        DB 0xFF, 0x3E, 0xFF, 0x7F, 0xFF, 0xFC, 0, 0, 1
        DB 0, 0xFF, 0xFC, 0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0
        DB 3, 1, 0xFF, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xC0
        DB 0x80, 7, 3, 0xFF, 0xF3, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xE0, 0xC0, 0xF, 7, 0xFF, 0xE7, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0xF, 7, 0xFF, 0xC7, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xF0, 0xE0, 0x1F, 0xF, 0xFF, 0x87, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xF8, 0xF0, 0x1F, 0xF, 0xFF, 0x8F
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xF0, 0x1F, 0xF, 0xFF
        DB 0x8F, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xF0, 0x3F, 0x1F
        DB 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xF8, 0x3F
        DB 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xF8
        DB 0x3F, 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC
        DB 0xF8, 0x3F, 0x1F, 0xFF, 0xC, 0xFF, 0x61, 0xFF, 0xF
        DB 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xB, 0xFF, 0x33, 0xFF
        DB 0x3F, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xB, 0xFF, 0x33
        DB 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xB, 0xFF
        DB 0x33, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xB
        DB 0xFF, 0x33, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF
        DB 0xC, 0xFF, 0x61, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1F
        DB 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xF8, 0x3F
        DB 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xF8
        DB 0x3F, 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC
        DB 0xF8, 0x3F, 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFC, 0xF8, 0x3F, 0x1E, 0xFF, 0xF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFC, 0xF8, 0x7F, 0x3E, 0xFF, 0xF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFE, 0xFC, 0x7F, 0x3C, 0xFF, 0x1F
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xFC, 0xFF, 0x7F, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x7F, 0
        DB 0xFF, 0, 0xFF, 0, 0xFF, 0, 0xFE, 0
spr_03:
        DB 4, 23
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 3, 1, 0xC0, 0x80, 0, 0, 1, 0
        DB 3, 1, 0xC0, 0x80, 0x80, 0, 3, 1, 0x83
        DB 1, 0xC1, 0x80, 0xC0, 0x80, 3, 1, 0xCF, 0x81
        DB 0xF3, 0x81, 0xC0, 0x80, 3, 1, 0xFF, 0xCD, 0xFF
        DB 0xB3, 0xC0, 0x80, 3, 1, 0xFF, 0xED, 0xFF, 0xB7
        DB 0xC0, 0x80, 0x3F, 1, 0xFF, 0xED, 0xFF, 0xB7, 0xFC
        DB 0x80, 0x7F, 0x3E, 0xFF, 0xED, 0xFF, 0xB7, 0xFE, 0x7C
        DB 0x7F, 0x3F, 0xFF, 0x6D, 0xFF, 0xB6, 0xFE, 0xFC, 0x7F
        DB 0x3F, 0xFF, 0x28, 0xFF, 4, 0xFE, 0xFC, 0x7F, 0x3F
        DB 0xFF, 0x47, 0xFF, 0xE2, 0xFE, 0xFC, 0x7F, 0x3F, 0xFF
        DB 0x3F, 0xFF, 0xFC, 0xFE, 0xFC, 0x7F, 0x3F, 0xFF, 0x7F
        DB 0xFF, 0xFE, 0xFE, 0xFC, 0x3F, 0, 0xFF, 0x7F, 0xFF
        DB 0xFE, 0xFC, 0, 3, 1, 0xFF, 0xBF, 0xFF, 0xFD
        DB 0xC0, 0x80, 3, 1, 0xFF, 0xE7, 0xFF, 0xE7, 0xC0
        DB 0x80, 3, 1, 0xE7, 0xC0, 0xF7, 3, 0xC0, 0x80
        DB 3, 1, 0xC3, 0x81, 0xC3, 0x81, 0xC0, 0x80, 3
        DB 1, 0x83, 1, 0xC1, 0x80, 0xC0, 0x80, 1, 0
        DB 3, 1, 0xC0, 0x80, 0x80, 0, 0, 0, 3
        DB 1, 0xC0, 0x80, 0, 0, 0, 0, 1, 0
        DB 0x80, 0, 0, 0
spr_04:
        DB 3, 25
        DB 0, 0, 0x7E, 0, 0, 0, 3, 0, 0xFF
        DB 0x7E, 0xC0, 0, 0xF, 3, 0xFF, 0xFF, 0xF0, 0xC0
        DB 0x1F, 3, 0xFF, 0xFF, 0xF8, 0xF0, 0x3F, 3, 0xFF
        DB 0xFF, 0xFC, 0xF8, 0x7F, 0x23, 0xFF, 0xFF, 0xFE, 0xFC
        DB 0xFF, 0x63, 0xFF, 0xFF, 0xFF, 0xFE, 0xFF, 0x71, 0xFF
        DB 0xFF, 0xFF, 0xFE, 0x7F, 0x31, 0xFF, 0xFF, 0xFE, 0xFC
        DB 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xFC, 0x3F, 0x1C, 0xFF
        DB 0xE7, 0xFC, 0xF8, 0x1F, 0xE, 0xFF, 0x5B, 0xF8, 0xF0
        DB 0xF, 7, 0xFF, 0xAD, 0xF0, 0xE0, 0x1F, 9, 0xFF
        DB 0xAD, 0xF8, 0x90, 0x1F, 0xA, 0xFF, 0x24, 0xF8, 0x70
        DB 0x3F, 0x17, 0xFF, 0x18, 0xFC, 0xB8, 0x7F, 0x2E, 0x7E
        DB 0x3C, 0xFE, 0x5C, 0xFE, 0x5C, 0x7E, 0x18, 0x7F, 0x2A
        DB 0xFC, 0x68, 0x7E, 0x24, 0x3F, 0x16, 0x78, 0x30, 0x7E
        DB 0x2C, 0x1E, 0xC, 0x30, 0, 0x7E, 0x2C, 0xC, 0
        DB 0, 0, 0x7E, 8, 0, 0, 0, 0, 0x7E
        DB 0x24, 0, 0, 0, 0, 0x3C, 0x18, 0, 0
        DB 0, 0, 0x18, 0, 0, 0
spr_05:
        DB 3, 0x18
        DB 0, 0, 0xFF, 0, 0, 0, 7, 0, 0xFF
        DB 0xFF, 0xE0, 0, 0x1F, 7, 0xFF, 0xF8, 0xF8, 0xE0
        DB 0x3F, 0x19, 0xFF, 0xF8, 0xFC, 0x78, 0x7F, 0x31, 0xFF
        DB 0xF8, 0xFE, 0x7C, 0xFF, 0x71, 0xFF, 0xFF, 0xFF, 0x7A
        DB 0xFF, 0x77, 0xFF, 0, 0xFF, 0xFA, 0xFF, 0x7B, 0xFF
        DB 0xFF, 0xFF, 0x1A, 0xFF, 0x61, 0xFF, 0xFF, 0xFF, 0xE6
        DB 0xFF, 0x51, 0xFF, 0, 0xFF, 0xFA, 0x7F, 0x38, 0xFF
        DB 0xFF, 0xFE, 0x3C, 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xDC
        DB 0x3F, 0x14, 0xFF, 0xFF, 0xFC, 0xE8, 0x1F, 0xC, 0xFF
        DB 0x7F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF, 0x7F, 0xF8, 0xF0
        DB 0xF, 6, 0xFF, 0x3F, 0xF0, 0xE0, 0xF, 7, 0xFF
        DB 0x1F, 0xF0, 0xE0, 7, 2, 0xFF, 0xFF, 0xE0, 0xC0
        DB 7, 3, 0xFF, 0xE7, 0xE0, 0xC0, 0x1F, 4, 0xFF
        DB 0x7E, 0xF8, 0x20, 0x3C, 0x18, 0x7E, 0, 0x3C, 0x18
        DB 0x3C, 0x18, 0, 0, 0x3C, 0x18, 0x18, 0, 0
        DB 0, 0x18, 0, 0, 0, 0, 0, 0, 0
spr_06:
        DB 3, 24
        DB 0, 0, 0xFF, 0, 0, 0, 7, 0, 0xFF
        DB 0xFF, 0xE0, 0, 0x1F, 7, 0xFF, 0x7E, 0xF8, 0xE0
        DB 0x3F, 0x18, 0xFF, 0x7E, 0xFC, 0x18, 0x7F, 0x38, 0xFF
        DB 0x7E, 0xFE, 0x1C, 0xFF, 0x78, 0xFF, 0xFF, 0xFF, 0x1E
        DB 0xFF, 0x7F, 0xFF, 0, 0xFF, 0xFE, 0xFF, 0x78, 0xFF
        DB 0xFF, 0xFF, 0x1E, 0xFF, 0x61, 0xFF, 0xFF, 0xFF, 0xE6
        DB 0xFF, 0x51, 0xFF, 0, 0xFF, 0xFA, 0x7F, 0x38, 0xFF
        DB 0xFF, 0xFE, 0x3C, 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xDC
        DB 0x3F, 0x14, 0xFF, 0xFF, 0xFC, 0xE8, 0x1F, 0xC, 0xFF
        DB 0x7F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF, 0x7F, 0xF8, 0xF0
        DB 0xF, 6, 0xFF, 0x3F, 0xF0, 0xE0, 0xF, 7, 0xFF
        DB 0x1F, 0xF0, 0xE0, 7, 2, 0xFF, 0xFF, 0xE0, 0xC0
        DB 0x1F, 3, 0xFF, 0xE7, 0xF8, 0xC0, 0x3F, 0x1C, 0xFF
        DB 0x7E, 0xFC, 0x38, 0x7E, 0x3C, 0x7E, 0, 0x7E, 0x3C
        DB 0x7E, 0x3C, 0, 0, 0x7E, 0x3C, 0x3C, 0x1C, 0
        DB 0, 0x3C, 0x18, 0x18, 0, 0, 0, 0x18, 0
spr_07:
        DB 3, 24
        DB 0, 0, 0xFF, 0, 0, 0, 7, 0, 0xFF
        DB 0xFF, 0xE0, 0, 0x1F, 7, 0xFF, 0x1F, 0xF8, 0xE0
        DB 0x3F, 0x1E, 0xFF, 0x1F, 0xFC, 0x98, 0x7F, 0x3E, 0xFF
        DB 0x1F, 0xFE, 0x8C, 0xFF, 0x5E, 0xFF, 0xFF, 0xFF, 0x8E
        DB 0xFF, 0x5F, 0xFF, 0, 0xFF, 0xEE, 0xFF, 0x58, 0xFF
        DB 0xFF, 0xFF, 0x1E, 0xFF, 0x61, 0xFF, 0xFF, 0xFF, 0xE6
        DB 0xFF, 0x51, 0xFF, 0, 0xFF, 0xFA, 0x7F, 0x38, 0xFF
        DB 0xFF, 0xFE, 0x3C, 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xDC
        DB 0x3F, 0x14, 0xFF, 0xFF, 0xFC, 0xE8, 0x1F, 0xC, 0xFF
        DB 0x7F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF, 0x7F, 0xF8, 0xF0
        DB 0xF, 6, 0xFF, 0x3F, 0xF0, 0xE0, 0xF, 7, 0xFF
        DB 0x1F, 0xF0, 0xE0, 7, 2, 0xFF, 0xFF, 0xE0, 0xC0
        DB 0x1F, 3, 0xFF, 0xE7, 0xF8, 0xC0, 0x3F, 0x1C, 0xFF
        DB 0x7E, 0xFC, 0x38, 0x7E, 0x3C, 0x7E, 0, 0x7E, 0x3C
        DB 0x7E, 0x3C, 0, 0, 0x7E, 0x3C, 0x3C, 0x1C, 0
        DB 0, 0x3C, 0x38, 0x18, 0, 0, 0, 0x18, 0
spr_08:
        DB 3, 24
        DB 0, 0, 0xFF, 0, 0, 0, 7, 0, 0xFF
        DB 0xFF, 0xE0, 0, 0x1F, 7, 0xFF, 0xC7, 0xF8, 0xE0
        DB 0x3F, 0x1F, 0xFF, 0xC7, 0xFC, 0xF8, 0x7F, 0x2F, 0xFF
        DB 0xC7, 0xFE, 0xEC, 0xFF, 0x67, 0xFF, 0xFF, 0xFF, 0xE6
        DB 0xFF, 0x67, 0xFF, 0, 0xFF, 0xE6, 0xFF, 0x78, 0xFF
        DB 0xFF, 0xFF, 0x1E, 0xFF, 0x61, 0xFF, 0xFF, 0xFF, 0xE6
        DB 0xFF, 0x51, 0xFF, 0, 0xFF, 0xFA, 0x7F, 0x38, 0xFF
        DB 0xFF, 0xFE, 0x3C, 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xDC
        DB 0x3F, 0x14, 0xFF, 0xFF, 0xFC, 0xE8, 0x1F, 0xC, 0xFF
        DB 0x7F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF, 0x7F, 0xF8, 0xF0
        DB 0xF, 6, 0xFF, 0x3F, 0xF0, 0xE0, 0xF, 7, 0xFF
        DB 0x1F, 0xF0, 0xE0, 7, 2, 0xFF, 0xFF, 0xE0, 0xC0
        DB 7, 3, 0xFF, 0xE7, 0xE0, 0xC0, 0x1F, 4, 0xFF
        DB 0x7E, 0xF8, 0x20, 0x3C, 0x18, 0x7E, 0, 0x3C, 0x18
        DB 0x3C, 0x18, 0, 0, 0x3C, 0x18, 0x18, 0, 0
        DB 0, 0x18, 0, 0, 0, 0, 0, 0, 0
spr_09:
        DB 4, 29
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 1, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x1F, 2, 0xF8, 0x60, 0, 0, 0, 0, 0x7F
        DB 0x15, 0xFE, 0x78, 0, 0, 1, 0, 0xFF, 0x2A
        DB 0xFF, 0x7E, 0x80, 0, 7, 1, 0xFF, 0x55, 0xFF
        DB 0x7F, 0xE0, 0x80, 0x1F, 2, 0xFF, 0xAA, 0xFF, 0x7F
        DB 0xF8, 0xE0, 0x7F, 0x15, 0xFF, 0x55, 0xFF, 0x7F, 0xFE
        DB 0xF8, 0xFF, 0x2A, 0xFF, 0xAA, 0xFF, 0x7F, 0xFF, 0xFE
        DB 0xFF, 0x55, 0xFF, 0x55, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF
        DB 0x2A, 0xFF, 0xAA, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF, 0x55
        DB 0xFF, 0x55, 0xFF, 0xFF, 0xFF, 0xFE, 0xFF, 0x2A, 0xFF
        DB 0xAA, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF, 0x55, 0xFF, 0x51
        DB 0xFF, 0x9F, 0xFF, 0xFE, 0xFF, 0x2A, 0xFF, 0xA7, 0xFF
        DB 0xE7, 0xFF, 0xFE, 0xFF, 0x55, 0xFF, 0x1F, 0xFF, 0xF9
        DB 0xFF, 0xFE, 0xFF, 0x2E, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF
        DB 0x7E, 0xFF, 0x51, 0xFF, 0xE7, 0xFF, 0x9F, 0xFF, 0x9E
        DB 0xFF, 0x27, 0xFF, 0xE1, 0xFF, 7, 0xFF, 0xE6, 0xFF
        DB 0x5F, 0xFF, 0xE0, 0xFF, 3, 0xF, 0xFA, 0xFF, 0x7F
        DB 0xFF, 0xE0, 0xFF, 0xF, 0xFF, 0xFE, 0x7F, 0x1F, 0xFF
        DB 0xE0, 0xFF, 0x1F, 0xFE, 0xF8, 0x1F, 7, 0xFF, 0xE0
        DB 0xFF, 7, 0xF8, 0xE0, 7, 1, 0xFF, 0xE0, 0xFF
        DB 3, 0xE0, 0x80, 1, 0, 0xFF, 0x7F, 0xFF, 0xFE
        DB 0x80, 0, 0, 0, 0x7F, 0x1F, 0xFE, 0xF8, 0
        DB 0, 0, 0, 0x1F, 7, 0xF8, 0xE0, 0, 0
        DB 0, 0, 7, 1, 0xE0, 0x80, 0, 0, 0
        DB 0, 1, 0, 0x80, 0, 0, 0
spr_0A:
        DB 4, 29
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 1, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x1F, 6, 0xF8, 0x40, 0, 0, 0, 0, 0x7F
        DB 0x1E, 0xFE, 0xA8, 0, 0, 1, 0, 0xFF, 0x7E
        DB 0xFF, 0x54, 0x80, 0, 7, 1, 0xFF, 0xFE, 0xFF
        DB 0xAA, 0xE0, 0x80, 0x1F, 7, 0xFF, 0xFE, 0xFF, 0x55
        DB 0xF8, 0x40, 0x7F, 0x1F, 0xFF, 0xFE, 0xFF, 0xAA, 0xFE
        DB 0xA8, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF, 0x55, 0xFF, 0x54
        DB 0xFF, 0x7F, 0xFF, 0xFE, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF
        DB 0x7F, 0xFF, 0xFE, 0xFF, 0x55, 0xFF, 0x54, 0xFF, 0x7F
        DB 0xFF, 0xFF, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF, 0x7F, 0xFF
        DB 0xFE, 0xFF, 0x55, 0xFF, 0x54, 0xFF, 0x7F, 0xFF, 0xF9
        DB 0xFF, 0x8A, 0xFF, 0xAA, 0xFF, 0x7F, 0xFF, 0xE7, 0xFF
        DB 0xE5, 0xFF, 0x54, 0xFF, 0x7F, 0xFF, 0x9F, 0xFF, 0xF8
        DB 0xFF, 0xAA, 0xFF, 0x7E, 0xFF, 0x7F, 0xFF, 0xFE, 0xFF
        DB 0x54, 0xFF, 0x79, 0xFF, 0xC0, 0xFF, 7, 0xFF, 0x8A
        DB 0xFF, 0x67, 0xFF, 0xE0, 0xFF, 7, 0xFF, 0xE4, 0xFF
        DB 0x5F, 0xFF, 0xF8, 0xFF, 7, 0xFF, 0xF8, 0xFF, 0x7F
        DB 0xFF, 0xF0, 0xFF, 7, 0xFF, 0xFE, 0x7F, 0x1F, 0xFF
        DB 0xC0, 0xFF, 7, 0xFE, 0xF8, 0x1F, 7, 0xFF, 0xE0
        DB 0xFF, 0x87, 0xF8, 0xE0, 7, 1, 0xFF, 0xF9, 0xFF
        DB 0xE7, 0xE0, 0x80, 1, 0, 0xFF, 0x7F, 0xFF, 0xFE
        DB 0x80, 0, 0, 0, 0x7F, 0x1F, 0xFE, 0xF8, 0
        DB 0, 0, 0, 0x1F, 7, 0xF8, 0xE0, 0, 0
        DB 0, 0, 7, 1, 0xE0, 0x80, 0, 0, 0
        DB 0, 1, 0, 0x80, 0, 0, 0
spr_0B:
        DB 3, 26
        DB 0, 0, 0, 0, 0x48, 0, 0, 0, 0xF8
        DB 0, 0xFE, 0x48, 3, 0, 0xFF, 0xF8, 0xFF, 0xAA
        DB 0xF, 3, 0xFF, 7, 0xFE, 0x20, 0x1F, 0xC, 0xFF
        DB 0xF8, 0xFF, 0xD6, 0x3F, 0x13, 0xFF, 0xFF, 0xFF, 0xFE
        DB 0x7F, 0x2F, 0xFF, 0xFF, 0xFE, 0xDC, 0xFF, 0x57, 0xFF
        DB 0xFF, 0xFC, 0xC8, 0x7F, 0x27, 0xFF, 0xFD, 0xFC, 0xF8
        DB 0x7F, 0x27, 0xFF, 0xFD, 0xF8, 0xF0, 0xFF, 0x67, 0xFF
        DB 0xFD, 0xFC, 0xB8, 0xFF, 0x73, 0xFF, 0xFD, 0xFC, 0x58
        DB 0xFF, 0x73, 0xFF, 0xFE, 0xFC, 0xC8, 0x7F, 0x39, 0xFF
        DB 0xFF, 0xC8, 0x80, 0x7F, 0x3E, 0xFF, 0x9F, 0xC0, 0x80
        DB 0x3F, 0x1F, 0xFF, 0x6F, 0x80, 0, 0x7F, 0x28, 0xFF
        DB 0x6E, 0, 0, 0xFF, 0x47, 0xFE, 0x68, 0, 0
        DB 0x5F, 0xF, 0xF8, 0xE0, 0, 0, 0x1F, 0xC, 0xFE
        DB 0xF8, 0, 0, 0x1F, 0xC, 0xFF, 0xFE, 0, 0
        DB 0xF, 7, 0xFF, 0xE6, 0, 0, 7, 3, 0xFF
        DB 0xE6, 0, 0, 3, 0, 0xFF, 0x3E, 0, 0
        DB 0, 0, 0x3E, 0x1C, 0, 0, 0, 0, 0x1C
        DB 0, 0, 0
spr_0C:
        DB 3, 26
        DB 0, 0, 0xF, 0, 0xC0, 0, 0, 0, 0x3F
        DB 0xF, 0xF0, 0xC0, 0, 0, 0xFF, 0x30, 0xF8, 0x30
        DB 1, 0, 0xFF, 0xCF, 0xFC, 0xC8, 3, 1, 0xFF
        DB 0x3F, 0xFE, 0xF0, 7, 2, 0xFF, 0xDF, 0xFF, 0xF2
        DB 0xF, 5, 0xFF, 0x9F, 0xFE, 0xE4, 0xF, 5, 0xFF
        DB 0x9F, 0xFE, 0xD4, 0x1F, 0xB, 0xFF, 0x9F, 0xFF, 0xDA
        DB 0x3F, 0x17, 0xFF, 0xCF, 0xFF, 0xE6, 0x7F, 0x2F, 0xFF
        DB 0xCF, 0xFF, 0xFE, 0xFF, 0x5F, 0xFF, 0xE7, 0xFF, 0xFE
        DB 0xFF, 0x37, 0xFF, 0xF7, 0xFE, 0xFC, 0xFF, 0x65, 0xFF
        DB 0xFB, 0xFE, 0xFC, 0xFF, 0x7B, 0xFF, 0xBC, 0xFC, 0xF8
        DB 0x7F, 3, 0xFF, 0xBB, 0xF8, 0x60, 7, 3, 0xFF
        DB 0x83, 0xE0, 0, 3, 1, 0xFF, 0x3B, 0x80, 0
        DB 1, 0, 0xFF, 0x7F, 0xC0, 0, 0, 0, 0xFF
        DB 0x67, 0xF0, 0xC0, 0, 0, 0xFF, 0x67, 0xF8, 0xF0
        DB 0, 0, 0x7F, 0x3F, 0xF8, 0x30, 0, 0, 0x3F
        DB 0x1F, 0xF8, 0x30, 0, 0, 0x1F, 1, 0xF8, 0xF0
        DB 0, 0, 1, 0, 0xF0, 0xE0, 0, 0, 0
        DB 0, 0xE0, 0
spr_0D:
        DB 3, 26
        DB 0, 0, 0xF, 0, 0xC0, 0, 0, 0, 0x3F
        DB 0xF, 0xF0, 0xC0, 0, 0, 0xFF, 0x30, 0xF8, 0x30
        DB 1, 0, 0xFF, 0xCF, 0xFE, 0xC8, 3, 1, 0xFF
        DB 0x3F, 0xFF, 0xF2, 7, 2, 0xFF, 0xDF, 0xFF, 0xF2
        DB 0xF, 5, 0xFF, 0x9F, 0xFE, 0xE4, 0xF, 5, 0xFF
        DB 0x9F, 0xFE, 0xD4, 0x1F, 0xB, 0xFF, 0x9F, 0xFF, 0xDA
        DB 0x3F, 0x17, 0xFF, 0xCF, 0xFF, 0xE6, 0x7F, 0x2F, 0xFF
        DB 0xCF, 0xFF, 0xFE, 0xFF, 0x5F, 0xFF, 0xEF, 0xFF, 0xFE
        DB 0xFF, 0x37, 0xFF, 0xF7, 0xFE, 0xFC, 0xFF, 0x65, 0xFF
        DB 0xFB, 0xFE, 0xFC, 0xFF, 0x7B, 0xFF, 0xBC, 0xFC, 0xF8
        DB 0x7F, 3, 0xFF, 0xBB, 0xF8, 0x60, 7, 3, 0xFF
        DB 0x83, 0xF0, 0, 3, 1, 0xFF, 0x63, 0xF8, 0x70
        DB 1, 0, 0xFF, 0x23, 0xFC, 0xF8, 0, 0, 0x3F
        DB 0xF, 0xFC, 0x98, 0, 0, 0x7F, 0x3F, 0xFC, 0x98
        DB 0, 0, 0x7F, 0x33, 0xF8, 0xF0, 0, 0, 0x7F
        DB 0x33, 0xF0, 0xE0, 0, 0, 0x7F, 0x3E, 0xE0, 0
        DB 0, 0, 0x3E, 0x1C, 0, 0, 0, 0, 0x1C
        DB 0, 0, 0
spr_0E:
        DB 3, 26
        DB 0, 0, 0, 0, 0x48, 0, 0, 0, 0xF8
        DB 0, 0xFE, 0x48, 3, 0, 0xFF, 0xF8, 0xFF, 0xAA
        DB 0xF, 3, 0xFF, 7, 0xFE, 0x20, 0x1F, 0xC, 0xFF
        DB 0xF8, 0xFF, 0xD6, 0x3F, 0x13, 0xFF, 0xFF, 0xFF, 0xFE
        DB 0x7F, 0x1F, 0xFF, 0xFF, 0xFE, 0xDC, 0xFF, 0x57, 0xFF
        DB 0xFF, 0xFC, 0xC8, 0x7F, 0x27, 0xFF, 0xFD, 0xFC, 0xF8
        DB 0x7F, 0x27, 0xFF, 0xFD, 0xF8, 0xF0, 0xFF, 0x67, 0xFF
        DB 0xFD, 0xFC, 0xB8, 0xFF, 0x73, 0xFF, 0xFD, 0xFC, 0x58
        DB 0xFF, 0x73, 0xFF, 0xFE, 0xFC, 0xC8, 0x7F, 0x39, 0xFF
        DB 0xFF, 0xC8, 0x80, 0x7F, 0x3E, 0xFF, 0x9F, 0xC0, 0x80
        DB 0x3F, 0x1F, 0xFF, 0x6F, 0x80, 0, 0x7F, 0x2F, 0xFF
        DB 0x60, 0, 0, 0x7F, 0x27, 0xFF, 0x6E, 0, 0
        DB 0x3F, 0x10, 0xFF, 0x7F, 0x80, 0, 0x1F, 1, 0xFF
        DB 0xF3, 0x80, 0, 0xF, 7, 0xFF, 0xF3, 0x80, 0
        DB 0xF, 6, 0xFF, 0x7E, 0, 0, 0xF, 6, 0xFE
        DB 0x7E, 0, 0, 0xF, 7, 0xFC, 0xC0, 0, 0
        DB 7, 3, 0xC0, 0x80, 0, 0, 3, 0, 0x80
        DB 0, 0, 0
spr_0F:
        DB 3, 30
        DB 0, 0, 0x7E, 0, 0, 0, 1, 0, 0xFF
        DB 0x7E, 0x80, 0, 3, 0, 0xFF, 0xFF, 0xC0, 0x80
        DB 7, 0, 0xFF, 0x81, 0xE0, 0xC0, 0xF, 4, 0xFF
        DB 0x7E, 0xF0, 0x40, 0xF, 3, 0xFF, 0xFF, 0xF0, 0xC0
        DB 0x1F, 0xF, 0xFF, 0x81, 0xF8, 0xF0, 0x3F, 0x1E, 0xFF
        DB 0x7E, 0xFC, 0x78, 0x7F, 0x3C, 0xFF, 0xFF, 0xFE, 0xBC
        DB 0xFF, 0x78, 0xFF, 0xFF, 0xFF, 0xDE, 0xFF, 0x74, 0xFF
        DB 0xFF, 0xFF, 0xEE, 0xFF, 0x74, 0xFF, 0xFF, 0xFF, 0xEE
        DB 0xFF, 0x74, 0xFF, 0xFF, 0xFF, 0xEE, 0x7F, 0x34, 0xFF
        DB 0x81, 0xFE, 0xEC, 0x3F, 0x14, 0xFF, 0x7E, 0xFC, 0x28
        DB 0x1F, 3, 0xFF, 0xFF, 0xF8, 0xC0, 0x1F, 0xF, 0xFF
        DB 0x81, 0xF8, 0xF0, 0x3F, 0x1E, 0xFF, 0x7F, 0xFC, 0x78
        DB 0x7F, 0x3C, 0xFF, 0xFF, 0xFE, 0xBC, 0xFF, 0x78, 0xFF
        DB 0x7F, 0xFF, 0xDE, 0xFF, 0x74, 0xFF, 0x7F, 0xFF, 0xEE
        DB 0xFF, 0x74, 0xFF, 0x7F, 0xFF, 0xEE, 0xFF, 0x76, 0xFF
        DB 0x7F, 0xFF, 0xEE, 0x7F, 0x36, 0xFF, 0x3F, 0xFE, 0xEC
        DB 0x3F, 0x1B, 0xFF, 0x3F, 0xFC, 0xD8, 0x1F, 0xB, 0xFF
        DB 0x9F, 0xF8, 0xD0, 0xB, 1, 0xFF, 0xCF, 0xD0, 0x80
        DB 1, 0, 0xFF, 0xFF, 0x80, 0, 0, 0, 0xFF
        DB 0x3C, 0, 0, 0, 0, 0x3C, 0, 0, 0
spr_10:
        DB 3, 30
        DB 0, 0, 0x7E, 0, 0, 0, 1, 0, 0xFF
        DB 0x3E, 0x80, 0, 3, 0, 0xFF, 0xFF, 0xC0, 0x80
        DB 7, 0, 0xFF, 0xFF, 0xE0, 0xC0, 0xF, 4, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0xF, 4, 0xFF, 0x81, 0xF0, 0xE0
        DB 0xF, 4, 0xFF, 0x7E, 0xF0, 0x20, 0xF, 3, 0xFF
        DB 0xFF, 0xF0, 0xC0, 0x1F, 0xF, 0xFF, 0x81, 0xF8, 0xF0
        DB 0x3F, 0x1E, 0xFF, 0x7E, 0xFC, 0x78, 0x7F, 0x3C, 0xFF
        DB 0xFF, 0xFE, 0xBC, 0xFF, 0x78, 0xFF, 0x81, 0xFF, 0xDE
        DB 0xFF, 0x74, 0xFF, 0x7E, 0xFF, 0x2E, 0xFF, 0x73, 0xFF
        DB 0xFF, 0xFF, 0xCE, 0xFF, 0x6F, 0xFF, 0x81, 0xFF, 0xF8
        DB 0x7F, 0x1E, 0xFF, 0x7E, 0xFE, 0x78, 0x7F, 0x3C, 0xFF
        DB 0xFF, 0xFE, 0xBC, 0xFF, 0x78, 0xFF, 0xFF, 0xFF, 0xDE
        DB 0xFF, 0x74, 0xFF, 0xFF, 0xFF, 0xEE, 0xFF, 0x74, 0xFF
        DB 0xFF, 0xFF, 0xEE, 0xFF, 0x74, 0xFF, 0x7F, 0xFF, 0xEE
        DB 0x7F, 0x34, 0xFF, 0x7F, 0xFE, 0xEC, 0x3F, 0x16, 0xFF
        DB 0x7F, 0xFC, 0xE8, 0x1F, 6, 0xFF, 0x3F, 0xF8, 0xE0
        DB 7, 3, 0xFF, 0x3F, 0xE0, 0xC0, 7, 3, 0xFF
        DB 0x9F, 0xE0, 0xC0, 3, 1, 0xFF, 0xCF, 0xC0, 0x80
        DB 1, 0, 0xFF, 0xFF, 0x80, 0, 0, 0, 0xFF
        DB 0x3C, 0, 0, 0, 0, 0x3C, 0, 0, 0
spr_11:
        DB 4, 16
        DB 0x1F, 0, 0xC0, 0, 0, 0, 0, 0, 0x3F
        DB 0x1B, 0xE0, 0xC0, 0, 0, 0, 0, 0x7F, 0x37
        DB 0xF0, 0xE0, 0, 0, 0, 0, 0x7F, 0, 0xF0
        DB 0, 0, 0, 0, 0, 0xFF, 0x77, 0xF8, 0xF0
        DB 0, 0, 0, 0, 0xFF, 0x77, 0xFF, 0xF0, 0xFF
        DB 0, 0xFC, 0, 0xFF, 0x6F, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFE, 0xFC, 0xFF, 0x6F, 0xFF, 0xF0, 0xFF, 0, 0xFF
        DB 2, 0xFF, 0x6F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE
        DB 0xFF, 0x6F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xFC, 0xFF
        DB 0x77, 0xFF, 0xF0, 0xFF, 0, 0xFC, 0, 0xFF, 0x77
        DB 0xF8, 0xF0, 0, 0, 0, 0, 0x7F, 0, 0xF0
        DB 0, 0, 0, 0, 0, 0x7F, 0x37, 0xF0, 0xE0
        DB 0, 0, 0, 0, 0x3F, 0x1B, 0xE0, 0xC0, 0
        DB 0, 0, 0, 0x1F, 0, 0xC0, 0, 0, 0
        DB 0, 0
spr_12:
        DB 4, 18
        DB 0, 0, 0x7E, 0, 0, 0, 0, 0, 1
        DB 0, 0xFF, 0x5E, 0xC0, 0, 0, 0, 3, 1
        DB 0xFF, 0xBF, 0xF1, 0xC0, 0xE0, 0, 7, 3, 0xFF
        DB 0xBF, 0xFF, 0xF1, 0xF0, 0xE0, 0xF, 7, 0xFF, 0xDF
        DB 0xFF, 0xFF, 0xF8, 0xF0, 0xF, 7, 0xFF, 0xEF, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0x1F, 0xF, 0xFF, 0xF4, 0xFF, 0xFB
        DB 0xF8, 0x50, 0x1F, 0xF, 0xFF, 0xF3, 0xFF, 0x7F, 0xF8
        DB 0xF0, 0x1F, 0xF, 0xFF, 0xF3, 0xFF, 0xB8, 0xF8, 0
        DB 0x1F, 0xF, 0xFF, 0xF7, 0xFF, 0xCF, 0xF8, 0xF0, 0x1F
        DB 0xF, 0xFF, 0xF7, 0xFF, 0xF5, 0xF8, 0x50, 0x1F, 0xF
        DB 0xFF, 0xE7, 0xFF, 0xFF, 0xF8, 0xF0, 0xF, 7, 0xFF
        DB 0xD7, 0xFF, 0xFF, 0xF0, 0xE0, 0xF, 7, 0xFF, 0xBB
        DB 0xFF, 0xFF, 0xE0, 0x80, 7, 3, 0xFF, 0xBC, 0xFF
        DB 0xFC, 0x80, 0, 3, 1, 0xFF, 0xDF, 0xFC, 0x30
        DB 0, 0, 1, 0, 0xFF, 0x6F, 0xF0, 0x80, 0
        DB 0, 0, 0, 0x7F, 0, 0x80, 0, 0, 0
spr_13:
        DB 3, 11
        DB 0x10, 0, 0, 0, 8, 0, 0x78, 0x10, 0
        DB 0, 0x1E, 8, 0xF0, 0x60, 0, 0, 0xF, 6
        DB 0xE0, 0x80, 0, 0, 7, 1, 0x84, 0, 0
        DB 0, 0x41, 0, 0xE, 4, 0x44, 0, 0xE0, 0x40
        DB 0x1C, 8, 0xEE, 0x44, 0x70, 0x20, 0x39, 0x10, 0xCE
        DB 0x84, 0xC8, 0x10, 0x11, 0, 0xCE, 0x84, 0x10, 0
        DB 1, 0, 0xCE, 0x84, 0, 0, 0, 0, 0x84
        DB 0, 0, 0
spr_14:
        DB 5, 17
        DB 3, 0, 0x80, 0, 0, 0, 0, 0, 0
        DB 0, 0xF, 3, 0xC0, 0x80, 0, 0, 0, 0
        DB 0, 0, 0x1F, 0xF, 0xE0, 0xC0, 0, 0, 0
        DB 0, 0, 0, 0x3F, 0x1F, 0xE0, 0xC0, 0, 0
        DB 0, 0, 0, 0, 0x7F, 0x3F, 0xC0, 0x80, 0
        DB 0, 0, 0, 0, 0, 0x7F, 0x3E, 0x80, 0
        DB 0, 0, 0, 0, 0, 0, 0xFE, 0x7C, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0xFC, 0x58
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0xFC
        DB 0x58, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0xFE, 0x5C, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0xFF, 0x5E, 0x80, 0, 0, 0, 0, 0
        DB 0, 0, 0x7F, 0x2F, 0xFF, 0x80, 0xFF, 0, 0xFF
        DB 0, 0xFC, 0, 0x7F, 0x37, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFE, 0xFC, 0x3F, 0x18, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x1F, 7, 0xFF, 0
        DB 0xFF, 0, 0xFF, 0, 0xFF, 2, 7, 0, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xFC, 0, 0
        DB 0xFF, 0, 0xFF, 0, 0xFF, 0, 0xFC, 0
spr_15:
        DB 3, 8
        DB 0xFC, 0xFC, 0x6F, 0x6F, 0xFF, 0xFF, 0x7C, 0x7C, 0x2F
        DB 0x2F, 0xFF, 0xFF, 0x3E, 0x3E, 0x37, 0x37, 0xFF, 0xFF
        DB 0x1F, 0x1F, 0x17, 0x17, 0xFF, 0xFF, 7, 7, 0x8B
        DB 0x8B, 0xFF, 0xFF, 1, 1, 0x80, 0x80, 0, 0
        DB 0, 0, 0x65, 0x65, 0xFF, 0xFF, 0, 0, 0x65
        DB 0x65, 0xFF, 0xFF
spr_16:
        DB 3, 8
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFE, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC, 0xFC
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xF0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xC0, 0xC0, 0, 0, 3, 3, 0, 0
        DB 0xFF, 0xFF, 0xFC, 0xFC, 0, 0, 0xFF, 0xFF, 0xFC
        DB 0xFC, 0, 0
spr_17:
        DB 3, 22
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xC0, 0xC0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xE0, 0xE0, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xF0
        DB 0, 0, 0, 0, 0x78, 0x78, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0x3C, 0x3C, 0xFF, 0xFF, 0xFF, 0xFF, 0x9E, 0x9E
        DB 0, 0, 0, 0, 0xCE, 0xCE, 0, 0, 0
        DB 0, 0x6E, 0x6E, 0, 0, 0, 0, 0x6E, 0x6E
        DB 0, 0, 0, 0, 0x6E, 0x6E, 0, 0, 0
        DB 0, 0x6E, 0x6E, 0, 0, 0, 0, 0x6E, 0x6E
        DB 0, 0, 0, 0, 0x6E, 0x6E, 0, 0, 0
        DB 0, 0x6E, 0x6E, 0, 0, 0, 0, 0x6E, 0x6E
        DB 0, 0, 0, 0, 0xCE, 0xCE, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0x9E, 0x9E, 0xFF, 0xFF, 0xFF, 0xFF, 0x3C, 0x3C
        DB 0, 0, 0, 0, 0x78, 0x78, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xF0, 0xF0, 0xFF, 0xFF, 0xFF, 0xFF, 0xE0, 0xE0
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xC0, 0xC0
spr_18:
        DB 3, 16
        DB 0, 0, 0x7E, 0, 0, 0, 3, 0, 0xFF
        DB 0x7E, 0xC0, 0, 0xF, 3, 0xFF, 0xBD, 0xF0, 0xC0
        DB 0x1F, 0xE, 0xFF, 0x3C, 0xF8, 0x70, 0x3F, 0x16, 0xFF
        DB 0x18, 0xFC, 0x68, 0x7F, 0x23, 0xFF, 0x18, 0xFE, 0xC4
        DB 0x7F, 0x33, 0xFF, 0xFF, 0xFE, 0xCC, 0x3F, 0x13, 0xFF
        DB 0x99, 0xFC, 0xC8, 0x3F, 0x1F, 0xFF, 0x18, 0xFC, 0xF8
        DB 0x3F, 0x19, 0xFF, 0x18, 0xFC, 0x98, 0x1F, 9, 0xFF
        DB 0x99, 0xF8, 0x90, 0x1F, 8, 0xFF, 0xFF, 0xF8, 0x10
        DB 0x1F, 0xD, 0xFF, 0x81, 0xF8, 0xB0, 0xF, 6, 0x81
        DB 0, 0xF0, 0x60, 0xE, 4, 0, 0, 0x70, 0x20
        DB 4, 0, 0, 0, 0x20, 0
spr_19:
        DB 3, 19
        DB 0, 0, 8, 0, 0, 0, 2, 0, 0x1C
        DB 8, 0, 0, 7, 2, 0x1E, 0xC, 0x40, 0
        DB 7, 3, 0xBF, 0x1E, 0xE0, 0x40, 0x27, 3, 0xFF
        DB 0x3E, 0xE4, 0x40, 0x7F, 0x27, 0xFF, 0xBE, 0xEE, 0xC4
        DB 0x7F, 0x37, 0xFF, 0xFF, 0xFE, 0xCC, 0x7F, 0x37, 0xFF
        DB 0xFF, 0xFE, 0xDC, 0x7F, 0x3E, 0xFF, 0xFF, 0xFE, 0xFC
        DB 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0xFC, 0x3F, 0x18, 0xFF
        DB 0xFF, 0xFC, 0xF8, 0x3F, 0x1C, 0xFF, 0x7F, 0xFC, 0xF8
        DB 0x1F, 0xC, 0xFF, 0x7F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF
        DB 0x3F, 0xF8, 0xF0, 0xF, 7, 0xFF, 0x3F, 0xF0, 0xE0
        DB 7, 3, 0xFF, 0x9F, 0xE0, 0xC0, 3, 1, 0xFF
        DB 0xCF, 0xC0, 0x80, 1, 0, 0xFF, 0x7E, 0x80, 0
        DB 0, 0, 0x7E, 0, 0, 0
spr_1A:
        DB 3, 24
        DB 0, 0, 0xFF, 0, 0, 0, 7, 0, 0xFF
        DB 0xFF, 0xE0, 0, 0x1F, 7, 0xFF, 0xFF, 0xF8, 0xE0
        DB 0x3F, 0x17, 0xFF, 0xFF, 0xFC, 0xF8, 0x7F, 0x33, 0xFF
        DB 0, 0xFE, 0xFC, 0x7F, 0x38, 0xFF, 0xFF, 0xFE, 0x3C
        DB 0x3F, 0x1B, 0xFF, 0xFF, 0xFC, 0xD8, 0x3F, 0x17, 0xFF
        DB 0xFF, 0xFC, 0xE8, 0x1F, 0xF, 0xFF, 0xFF, 0xF8, 0xF0
        DB 0x3F, 0x1F, 0xFF, 0xF7, 0xFC, 0xF8, 0x7F, 0x3F, 0xFF
        DB 0xF7, 0xFE, 0xFC, 0x7F, 0x3E, 0xFF, 0xF7, 0xFE, 0xBC
        DB 0xFF, 0x7E, 0xFF, 0x73, 0xFF, 0x3E, 0xFF, 0x75, 0xFF
        DB 0x6A, 0xFF, 0xDE, 0xFF, 0x75, 0xFF, 0xAD, 0xFF, 0xDE
        DB 0xFF, 0x6B, 0xFF, 0xDF, 0xFF, 0xEA, 0xFF, 0x6F, 0xFF
        DB 0xFF, 0xFF, 0xF2, 0xFF, 0x5D, 0xFF, 0xFF, 0xFF, 0xFA
        DB 0x7F, 0x39, 0xFF, 0xEF, 0xFE, 0xF8, 0x3B, 0x11, 0xFF
        DB 0xEF, 0xF8, 0x70, 0x11, 0, 0xEF, 0xC7, 0xF0, 0x20
        DB 1, 0, 0xC7, 0x83, 0xA0, 0, 0, 0, 0x83
        DB 1, 0x80, 0, 0, 0, 1, 0, 0, 0
        DB 4, 0x19, 0, 0, 1, 0, 0x20, 0, 0
        DB 0, 0, 0, 0x13, 1, 0xF0, 0x20, 0, 0
        DB 0, 0, 0x3F, 0x11, 0xF2, 0x80, 0, 0, 1
        DB 0, 0x3F, 7, 0xFF, 0x62, 0, 0, 3, 1
        DB 0xFF, 0x1F, 0xFF, 0xB8, 0x20, 0, 0x13, 0, 0xFF
        DB 0x7F, 0xFF, 0xDE, 0xF4, 0x20, 0x3F, 0x11, 0xFF, 0xFF
        DB 0xFF, 0xEF, 0xFE, 0x84, 0x3F, 7, 0xFF, 0xFF, 0xFF
        DB 0xF7, 0xFE, 0xE4, 0x7F, 0x1F, 0xFF, 0xFF, 0xFF, 0xFB
        DB 0xFE, 0xF8, 0x7F, 0x3F, 0xFF, 0xFF, 0xFF, 0xFD, 0xFF
        DB 0xFE, 0x3F, 0x1F, 0xFF, 0xFF, 0xFF, 0xFE, 0xFF, 0xFE
        DB 0x1F, 0xF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0xF
        DB 7, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xBE, 7, 3
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xDE, 3, 1, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xEE, 1, 0, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xF6, 0, 0, 0xFF, 0x7F, 0xFF
        DB 0xFF, 0xFF, 0xFA, 0, 0, 0x7F, 0x3F, 0xFF, 0xFF
        DB 0xFF, 0xFC, 0, 0, 0x3F, 0x1F, 0xFF, 0xFF, 0xFE
        DB 0xF8, 0, 0, 0x1F, 0xF, 0xFF, 0xFF, 0xF8, 0xE0
        DB 0, 0, 0xF, 7, 0xFE, 0xFF, 0xE0, 0x80, 0
        DB 0, 7, 3, 0xF8, 0xFE, 0x80, 0, 0, 0
        DB 3, 1, 0xE0, 0xF8, 0, 0, 0, 0, 1
        DB 0, 0x80, 0xE0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0
spr_1B:
        DB 3, 32
        DB 0, 0, 0x3E, 0, 0, 0, 0, 0, 0xFF
        DB 0x3E, 0, 0, 1, 0, 0xFF, 0xFF, 0xE0, 0
        DB 3, 1, 0xFF, 0xFF, 0xF0, 0x60, 3, 1, 0xFF
        DB 0xFE, 0xF8, 0xF0, 3, 1, 0xFF, 0xFD, 0xF8, 0xF0
        DB 3, 1, 0xFF, 0x1B, 0xF0, 0xE0, 3, 0, 0xFF
        DB 0xE3, 0xE0, 0xC0, 3, 1, 0xFF, 0xF8, 0xC0, 0x80
        DB 7, 0, 0xFF, 0xFB, 0xC0, 0, 0xF, 7, 0xFF
        DB 0x7F, 0xC0, 0x80, 0x1F, 0xA, 0xFF, 0xBF, 0xC0, 0x80
        DB 0x3F, 0x1F, 0xFF, 0xBF, 0xE0, 0x80, 0x3F, 0x1F, 0xFF
        DB 0x67, 0xF0, 0x60, 0x3F, 0x1F, 0xFF, 0x61, 0xF8, 0x70
        DB 0x7F, 0x2F, 0xFF, 0x61, 0xF8, 0xB0, 0x7F, 0x2F, 0xFF
        DB 0x61, 0xF8, 0xB0, 0x7F, 0x2F, 0xFF, 0xF9, 0xF8, 0xB0
        DB 0x7F, 0x2F, 0xFF, 0xFF, 0xF8, 0xB0, 0x7F, 0x2F, 0xFF
        DB 0x83, 0xF8, 0x70, 0x7F, 0x32, 0xFF, 0x7C, 0xF0, 0xE0
        DB 0x7F, 0x3D, 0xFF, 0xFF, 0xE0, 0x40, 0x3F, 0x1B, 0xFF
        DB 0x83, 0xC0, 0x80, 0x1F, 7, 0xFF, 0x80, 0xE0, 0xC0
        DB 0xF, 5, 0xFF, 0x84, 0xE0, 0x40, 0xF, 5, 0xFF
        DB 0x88, 0xE0, 0x40, 0xF, 5, 0xFF, 0xE0, 0xC0, 0x80
        DB 7, 2, 0xFF, 0xFD, 0xC0, 0x80, 7, 2, 0xFF
        DB 0xFF, 0x80, 0, 3, 1, 0xFF, 0x3E, 0, 0
        DB 1, 0, 0xFE, 0xDC, 0, 0, 0, 0, 0xFC
        DB 0, 0, 0
spr_1C:
        DB 3, 25
        DB 0, 0, 0x3F, 0, 0, 0, 0, 0, 0xFF
        DB 0x3F, 0xC0, 0, 1, 0, 0xFF, 0xFF, 0xE0, 0xC0
        DB 3, 1, 0xFF, 0xFF, 0xF0, 0xE0, 7, 3, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0xF, 4, 0xFF, 0x7F, 0xF8, 0xF0
        DB 0x1F, 0, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x14, 0xFF
        DB 0x3F, 0xFC, 0xB8, 0x3F, 0x1F, 0xFF, 0xBF, 0xFC, 0xD8
        DB 0x3F, 0x19, 0xFF, 0xFF, 0xFC, 0xE8, 0x1F, 1, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0x1F, 5, 0xFF, 0xFF, 0xF8, 0xF0
        DB 0x3F, 0x1D, 0xFF, 0xFF, 0xF8, 0xF0, 0x3F, 0x1D, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0x1F, 0xF, 0xFF, 0xFF, 0xF8, 0xF0
        DB 0xF, 0, 0xFF, 0xFF, 0xF0, 0xE0, 0xF, 1, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0xBF, 0xE0, 0xC0
        DB 0x3F, 0x1F, 0xBF, 0x1F, 0xC0, 0x80, 0x3F, 0x17, 0x9F
        DB 0xF, 0xE0, 0, 0x3F, 0x13, 0x8F, 0, 0xF0, 0xE0
        DB 0x1F, 0xE, 3, 1, 0xF8, 0x70, 0xE, 0, 3
        DB 1, 0xF8, 0x30, 0, 0, 1, 0, 0xF0, 0xE0
        DB 0, 0, 0, 0, 0xE0, 0
spr_1D:
        DB 4, 29
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 0, 0xE0, 0, 0, 0, 0, 0
        DB 0x1F, 6, 0xF8, 0x20, 0, 0, 0, 0, 0x7F
        DB 0x1E, 0xFE, 0x58, 0, 0, 1, 0, 0xFF, 0x7D
        DB 0xFF, 0xAA, 0x80, 0, 7, 1, 0xFF, 0xFD, 0xFF
        DB 0x95, 0xE0, 0, 0x1F, 7, 0xFF, 0xFD, 0xFF, 0xAA
        DB 0xF8, 0xA0, 0x7F, 0x1F, 0xFF, 0xFD, 0xFF, 0x95, 0xFE
        DB 0x50, 0xFF, 0x7F, 0xFF, 0xFB, 0xFF, 0xCA, 0xFF, 0xAA
        DB 0x7F, 0x3F, 0xFF, 0xFB, 0xFF, 0xD5, 0xFE, 0x54, 0x7F
        DB 0x3F, 0xFF, 0xFB, 0xFF, 0xCA, 0xFE, 0xA8, 0x7F, 0x1F
        DB 0xFF, 0xFB, 0xFF, 0xD5, 0xFE, 0x50, 0x7F, 0x2F, 0xFF
        DB 0xF7, 0xFF, 0xEA, 0xFE, 0xA4, 0x3F, 0xF, 0xFF, 0xF7
        DB 0xFF, 0xE5, 0xFC, 0x50, 0x3F, 0x17, 0xFF, 0xF7, 0xFF
        DB 0xEA, 0xFC, 0xA8, 0x3F, 0x1B, 0xFF, 0xC0, 0xFF, 1
        DB 0xFC, 0x58, 0x1F, 0xB, 0xFF, 0x3F, 0xFF, 0xFC, 0xF8
        DB 0x90, 0x1F, 0xC, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0x30
        DB 0xF, 5, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xA0, 0xF
        DB 5, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xA0, 0xF, 5
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xA0, 7, 1, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xE0, 0x80, 3, 1, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xC0, 0x80, 1, 0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xC0, 0, 0, 0, 0xFF, 0x3F, 0xFF, 0xFC
        DB 0, 0, 0, 0, 0x3F, 0, 0xFC, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0
spr_1E:
        DB 4, 27
        DB 0, 0, 0x3F, 0, 0xFC, 0, 0, 0, 0
        DB 0, 0xFF, 0x2F, 0xFF, 0xF4, 0, 0, 1, 0
        DB 0xFF, 0xEF, 0xFF, 0xF5, 0x80, 0, 3, 1, 0xFF
        DB 0xE7, 0xFF, 0xF2, 0xC0, 0x80, 3, 1, 0xFF, 0xF7
        DB 0xFF, 0xE5, 0xC0, 0, 7, 3, 0xFF, 0xFB, 0xFF
        DB 0xCA, 0xE0, 0x80, 7, 3, 0xFF, 0xFB, 0xFF, 0xD5
        DB 0xE0, 0x40, 0xF, 7, 0xFF, 0xFD, 0xFF, 0xAA, 0xF0
        DB 0xA0, 0xF, 7, 0xFF, 0xFD, 0xFF, 0x95, 0xF0, 0x40
        DB 0x1F, 0xF, 0xFF, 0xFE, 0xFF, 0x2A, 0xF8, 0xB0, 0x1F
        DB 0xF, 0xFF, 0xFE, 0xFF, 0x55, 0xF8, 0x50, 0x3F, 0x1F
        DB 0xFF, 0xF9, 0xFF, 0x8A, 0xFC, 0xA8, 0x3F, 0x1F, 0xFF
        DB 0xE7, 0xFF, 0xE5, 0xFC, 0x50, 0x7F, 0x3F, 0xFF, 0x9F
        DB 0xFF, 0xF8, 0xFE, 0xA8, 0x7F, 0x3E, 0xFF, 0x7F, 0xFF
        DB 0xFE, 0xFE, 0x54, 0xFF, 0x79, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0x9A, 0xFF, 0x67, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xE4, 0xFF, 0x1F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8
        DB 0xFF, 0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x7F
        DB 0x1F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xF8, 0x1F, 7
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xE0, 7, 1, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xE0, 0x80, 1, 0, 0xFF, 0x7F
        DB 0xFF, 0xFE, 0x80, 0, 0, 0, 0x7F, 0x1F, 0xFE
        DB 0xF8, 0, 0, 0, 0, 0x1F, 7, 0xF8, 0xE0
        DB 0, 0, 0, 0, 7, 1, 0xE0, 0x80, 0
        DB 0, 0, 0, 1, 0, 0x80, 0, 0, 0
spr_1F:
        DB 4, 29
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 1, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x1F, 5, 0xF8, 0x20, 0, 0, 0, 0, 0x7F
        DB 0x1D, 0xFE, 0x50, 0, 0, 1, 0, 0xFF, 0x7B
        DB 0xFF, 0xAA, 0x80, 0, 7, 1, 0xFF, 0xFB, 0xFF
        DB 0x95, 0xE0, 0, 0x1F, 7, 0xFF, 0xF7, 0xFF, 0xCA
        DB 0xF8, 0xA0, 0x7F, 0x1F, 0xFF, 0xF0, 0xFF, 0x15, 0xFE
        DB 0x50, 0xFF, 0x7F, 0xFF, 0xF7, 0xFF, 0xCA, 0xFF, 0xAA
        DB 0x7F, 0x3F, 0xFF, 0xFB, 0xFF, 0x95, 0xFE, 0x54, 0x7F
        DB 0x3F, 0xFF, 0xFB, 0xFF, 0xAA, 0xFE, 0xA8, 0x3F, 0x1F
        DB 0xFF, 0xFD, 0xFF, 0x55, 0xFC, 0x50, 0x3F, 0x1F, 0xFF
        DB 0xFC, 0xFF, 0xAA, 0xFC, 0xA8, 0x1F, 0xF, 0xFF, 0xF9
        DB 0xFF, 0x95, 0xF8, 0x50, 0x3F, 0x1F, 0xFF, 0xE7, 0xFF
        DB 0xE2, 0xFC, 0xA0, 0x3F, 0x1F, 0xFF, 0x9F, 0xFF, 0xF9
        DB 0xFC, 0x50, 0x7F, 0x3E, 0xFF, 0x7F, 0xFF, 0xFE, 0xFE
        DB 0x28, 0x7F, 0x39, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x94
        DB 0xFF, 0x67, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xE2, 0xFF
        DB 0x1F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xFF, 0x7F
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x7F, 0x1F, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFE, 0xF8, 0x1F, 7, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xF8, 0xE0, 7, 1, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xE0, 0x80, 1, 0, 0xFF, 0x7F, 0xFF, 0xFE
        DB 0x80, 0, 0, 0, 0x7F, 0x1F, 0xFE, 0xF8, 0
        DB 0, 0, 0, 0x1F, 7, 0xF8, 0xE0, 0, 0
        DB 0, 0, 7, 1, 0xE0, 0x80, 0, 0, 0
        DB 0, 1, 0, 0x80, 0, 0, 0
spr_20:
        DB 3, 25
        DB 0, 0, 0x7E, 0, 0, 0, 1, 0, 0xFF
        DB 0x7E, 0x80, 0, 3, 1, 0xFF, 0xF7, 0xE0, 0x80
        DB 7, 3, 0xFF, 0xFB, 0xF4, 0xE0, 0xF, 7, 0xFF
        DB 0x83, 0xFE, 0xF4, 0xF, 7, 0xFF, 7, 0xFF, 0xF2
        DB 0xF, 6, 0xFF, 0x3F, 0xFF, 0xF6, 7, 2, 0xFF
        DB 0x47, 0xFE, 0xF4, 7, 3, 0xFF, 0xBF, 0xFC, 0xA0
        DB 3, 1, 0xFF, 0x7E, 0xFC, 0x58, 1, 0, 0xFF
        DB 0xFD, 0xFE, 0xBC, 3, 1, 0xFF, 0xFF, 0xFE, 0xBC
        DB 3, 1, 0xFF, 0xFF, 0xFC, 0xD8, 3, 1, 0xFF
        DB 0xB7, 0xF8, 0xE0, 3, 1, 0xFF, 0x72, 0xE0, 0xC0
        DB 7, 0, 0xFF, 0xFE, 0xE0, 0x40, 0xF, 7, 0xFF
        DB 0x5F, 0xC0, 0x80, 0x1F, 0xF, 0xFF, 0xBF, 0x80, 0
        DB 0x1F, 0xB, 0xFF, 0x9C, 0xC0, 0x80, 0x1F, 9, 0xFF
        DB 0x81, 0xE0, 0, 0xF, 7, 0x83, 0, 0xF0, 0xE0
        DB 7, 0, 3, 1, 0xF8, 0x70, 0, 0, 3
        DB 1, 0xF8, 0x30, 0, 0, 1, 0, 0xF0, 0xE0
        DB 0, 0, 0, 0, 0xE0, 0
spr_21:
        DB 4, 25
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 1, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x1F, 7, 0xF8, 0xE0, 0, 0, 0, 0, 0x7F
        DB 0x1E, 0xFE, 0x78, 0, 0, 1, 0, 0xFF, 0x79
        DB 0xFF, 0x9E, 0x80, 0, 7, 1, 0xFF, 0xE7, 0xFF
        DB 0xE7, 0xE0, 0x80, 0x1F, 7, 0xFF, 0x9C, 0xFF, 0x39
        DB 0xF8, 0xE0, 0x7F, 0x1E, 0xFF, 0x78, 0xFF, 0xCE, 0xFE
        DB 0x78, 0xFF, 0x79, 0xFF, 0xF4, 0xFF, 0xEF, 0xFF, 0x9E
        DB 0xFF, 0x66, 0xFF, 0x14, 0xFF, 0x28, 0xFF, 0x66, 0xFF
        DB 0x1C, 0xFF, 0x63, 0xFF, 0xC1, 0xFF, 0xB8, 0xFF, 0x7A
        DB 0xFF, 0x77, 0xFF, 0xE9, 0xFF, 0xDE, 0x7F, 0x1A, 0xFF
        DB 0x77, 0xFF, 0xE9, 0xFE, 0xD8, 0x1F, 2, 0xFF, 0x73
        DB 0xFF, 0xC9, 0xF8, 0xC0, 7, 2, 0xFF, 0x70, 0xFF
        DB 9, 0xE0, 0xC0, 7, 2, 0xFF, 0x71, 0xFF, 0xC9
        DB 0xE0, 0xC0, 7, 2, 0xFF, 0x11, 0xFF, 0xC9, 0xE0
        DB 0xC0, 7, 1, 0xFF, 0xE1, 0xFF, 0xC9, 0xE0, 0xC0
        DB 7, 3, 0xFF, 0xF1, 0xFF, 0xC9, 0xE0, 0xC0, 7
        DB 3, 0xFF, 0xF0, 0xFF, 0x48, 0xE0, 0x40, 3, 1
        DB 0xFF, 0xE7, 0xFF, 0x87, 0xE0, 0x80, 1, 0, 0xFF
        DB 0xF, 0xFF, 0xCF, 0xE0, 0xC0, 0, 0, 0x1F, 0xF
        DB 0xFF, 0xCF, 0xE0, 0xC0, 0, 0, 0xF, 7, 0xCF
        DB 0x87, 0xC0, 0x80, 0, 0, 7, 0, 0x87, 0
        DB 0x80, 0
spr_22:
        DB 2, 62
        DB 0xF, 0, 0x80, 0, 0x1F, 0xB, 0xE0, 0, 0x3F
        DB 0x1B, 0xF8, 0x60, 0x3F, 0x1B, 0xFE, 0x78, 0x3F, 0x1B
        DB 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF
        DB 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E
        DB 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F
        DB 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B
        DB 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF
        DB 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E
        DB 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F
        DB 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B
        DB 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF
        DB 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E
        DB 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F
        DB 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B
        DB 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF
        DB 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E
        DB 0x3F, 0x1B, 0xFF, 0x7E, 0x3F, 0x1B, 0xFF, 0x7E, 0x3F
        DB 0x1B, 0xFF, 0x7F, 0x3F, 0x1B, 0xFF, 0x7F, 0x3F, 0x1B
        DB 0xFF, 0x7F, 0x3F, 0x1A, 0xFF, 0x7F, 0x3F, 0x19, 0xFF
        DB 0xBF, 0x3F, 3, 0xFF, 0xBF, 0x1F, 0xD, 0xFF, 0xDF
        DB 0x1F, 0xD, 0xFF, 0xEF, 0xF, 6, 0xFF, 0xEF, 7
        DB 3, 0xFF, 0x77, 7, 3, 0xFF, 0x7B, 3, 1
        DB 0xFF, 0xB9, 1, 0, 0xFF, 0xD6, 1, 0, 0xFF
        DB 0xCF, 0, 0, 0xFF, 0x33, 0, 0, 0x7F, 0x1C
        DB 0, 0, 0x1F, 7, 0, 0, 7, 1, 0
        DB 0, 1, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0
spr_23:
        DB 3, 48
        DB 0, 0, 0, 0, 0x1C, 0, 0, 0, 0
        DB 0, 0x7E, 0x14, 0, 0, 1, 0, 0xFF, 0x56
        DB 0, 0, 7, 1, 0xFF, 0xD6, 0, 0, 0x1F
        DB 7, 0xFF, 0xD6, 0, 0, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x1F, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0, 0, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x1F, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0, 0, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x1F, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0, 0, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x1F, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0, 0, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x1F, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0, 0, 0x3F, 0x1E, 0xFF, 0xD6
        DB 0, 0, 0x3F, 0x18, 0xFF, 0xD6, 0, 0, 0x3F
        DB 0x12, 0xFF, 0xD6, 0x80, 0, 0x3F, 0x14, 0xFF, 0xD6
        DB 0xC0, 0x80, 0x3F, 0x12, 0xFF, 0xD6, 0xC0, 0x80, 0x3F
        DB 0x14, 0xFF, 0xD6, 0xE0, 0xC0, 0x3F, 0x11, 0xFF, 0xD6
        DB 0xE0, 0xC0, 0x3F, 0x17, 0xFF, 0xD6, 0xF8, 0xE0, 0x3F
        DB 0x1F, 0xFF, 0xD6, 0xFE, 0xF8, 0x3F, 0x1F, 0xFF, 0xD6
        DB 0xFF, 0xFE, 0xBF, 0x1F, 0xFF, 0xD6, 0xFF, 0xFF, 0xFF
        DB 0x9F, 0xFF, 0xAE, 0xFF, 0xFF, 0xFF, 0xE7, 0xFF, 0x5E
        DB 0xFF, 0xFF, 0xFF, 0xF8, 0xFF, 0xBE, 0xFF, 0xFF, 0xFF
        DB 0xFE, 0xFF, 0x7E, 0xFF, 0x7F, 0xFF, 0xFF, 0xFF, 0xFE
        DB 0xFF, 0x9F, 0xFF, 0xFF, 0xFF, 0xFE, 0xFF, 0xE7, 0xFF
        DB 0xFF, 0xFF, 0xFC, 0xFF, 0xF9, 0xFF, 0xFF, 0xFF, 0xFA
        DB 0xFF, 0x3E, 0xFF, 0x7F, 0xFE, 0xF4, 0xFF, 0xCF, 0xFF
        DB 0x9F, 0xFE, 0xEC, 0xFF, 0x73, 0xFF, 0xE7, 0xFC, 0xD8
        DB 0x7F, 0x1C, 0xFF, 0xF9, 0xF8, 0xB0, 0x1F, 7, 0xFF
        DB 0x3E, 0xF0, 0x60, 7, 1, 0xFF, 0xCF, 0xE0, 0x40
        DB 1, 0, 0xFF, 0x72, 0xC0, 0, 0, 0, 0x7E
        DB 0x1C, 0, 0, 0, 0, 0x1C, 0, 0, 0
spr_24:
        DB 3, 56
        DB 0, 0, 0, 0, 3, 0, 0, 0, 0
        DB 0, 0xF, 3, 0, 0, 0, 0, 0x3F, 0xF
        DB 0, 0, 0, 0, 0xFF, 0x3F, 0, 0, 3
        DB 0, 0xFF, 0xFF, 0, 0, 0xF, 3, 0xFF, 0xFF
        DB 0, 0, 0x3F, 7, 0xFF, 0xFF, 0, 0, 0xFF
        DB 0x3B, 0xFF, 0xFC, 3, 0, 0xFF, 0xFD, 0xFF, 0xF3
        DB 0xF, 3, 0xFF, 0xFE, 0xFF, 0xCF, 0x3F, 7, 0xFF
        DB 0xFF, 0xFF, 0x3F, 0xFF, 0x2F, 0xFF, 0xFF, 0xFF, 0x7F
        DB 0xFF, 0xEF, 0xFF, 0xFE, 0xFF, 0xFF, 0xFF, 0xDF, 0xFF
        DB 0xFE, 0xFF, 0xFF, 0xFF, 0xDF, 0xFF, 0xFD, 0xFF, 0xFF
        DB 0xFF, 0xBF, 0xFF, 0xFD, 0xFF, 0xFF, 0xFF, 0xBF, 0xFF
        DB 0xFB, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF, 0xFB, 0xFF, 0xFF
        DB 0xFF, 0x7F, 0xFF, 0xF7, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF
        DB 0xF7, 0xFF, 0xFF, 0xFF, 0xBF, 0xFF, 0xCB, 0xFF, 0xFC
        DB 0xFF, 0xDF, 0xFF, 0x3D, 0xFF, 0xF3, 0xFF, 0xEC, 0xFF
        DB 0xFE, 0xFF, 0xCF, 0xFF, 0xF3, 0xFF, 0xFF, 0xFF, 0x3F
        DB 0xFF, 0xEF, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF, 0xEF, 0xFF
        DB 0xFE, 0xFF, 0xFF, 0xFF, 0xDF, 0xFF, 0xFE, 0xFF, 0xFF
        DB 0xFF, 0xDF, 0xFF, 0xFD, 0xFF, 0xFF, 0xFF, 0xBF, 0xFF
        DB 0xFD, 0xFF, 0xFF, 0xFF, 0xBF, 0xFF, 0xFB, 0xFF, 0xFF
        DB 0xFF, 0x7F, 0xFF, 0xFB, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF
        DB 0xF7, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF, 0xF7, 0xFF, 0xFF
        DB 0xFF, 0xBF, 0xFF, 0xCB, 0xFF, 0xFC, 0xFF, 0xDF, 0xFF
        DB 0x3D, 0xFF, 0xF3, 0xFF, 0xEC, 0xFF, 0xFE, 0xFF, 0xCC
        DB 0xFF, 0xE3, 0xFF, 0xFF, 0xFC, 0x30, 0xFF, 0xEF, 0xFF
        DB 0xFF, 0xF0, 0x40, 0xFF, 0xEF, 0xFF, 0xFE, 0xC0, 0x80
        DB 0xFF, 0xDF, 0xFF, 0xFE, 0xC0, 0x80, 0xFF, 0xDF, 0xFF
        DB 0xFD, 0x80, 0, 0xFF, 0xBF, 0xFF, 0xFD, 0x80, 0
        DB 0xFF, 0xBF, 0xFF, 0xFA, 0, 0, 0xFF, 0x7F, 0xFF
        DB 0xFA, 0, 0, 0xFF, 0x7F, 0xFE, 0xF4, 0, 0
        DB 0xFF, 0x7F, 0xFE, 0xF4, 0, 0, 0xFF, 0xBF, 0xFE
        DB 0xC4, 0, 0, 0xFF, 0x5F, 0xFF, 0x3A, 0, 0
        DB 0x7F, 0x2C, 0xFF, 0xC5, 0x80, 0, 0x3F, 0x13, 0xC5
        DB 0, 0, 0, 0x7F, 0x2C, 0, 0, 0, 0
        DB 0x7C, 0x28, 0, 0, 0, 0, 0xF8, 0x50, 0
        DB 0, 0, 0, 0xF8, 0x50, 0, 0, 0, 0
        DB 0xF0, 0xA0, 0, 0, 0, 0, 0xE0, 0, 0
        DB 0, 0, 0
spr_25:
        DB 2, 52
        DB 0, 0, 3, 0, 0, 0, 0xF, 3, 0
        DB 0, 0x3F, 7, 0, 0, 0xFF, 0x3B, 3, 0
        DB 0xFF, 0xFD, 0xF, 3, 0xFF, 0xFE, 0x3F, 7, 0xFF
        DB 0xFF, 0xFF, 0x2F, 0xFF, 0xFF, 0xFF, 0xEF, 0xFF, 0xFE
        DB 0xFF, 0xDF, 0xFF, 0xFE, 0xFF, 0xDF, 0xFF, 0xFD, 0xFF
        DB 0xBF, 0xFF, 0xFD, 0xFF, 0xBF, 0xFF, 0xFB, 0xFF, 0x7F
        DB 0xFF, 0xFB, 0xFF, 0x7F, 0xFF, 0xF7, 0xFF, 0x7F, 0xFF
        DB 0xF7, 0xFF, 0xBF, 0xFF, 0xCB, 0xFF, 0xDF, 0xFF, 0x3D
        DB 0xFF, 0xEC, 0xFF, 0xFE, 0xFF, 0xF3, 0xFF, 0xFF, 0xFF
        DB 0xEF, 0xFF, 0xFF, 0xFF, 0xEF, 0xFF, 0xFE, 0xFF, 0xDF
        DB 0xFF, 0xFE, 0xFF, 0xDF, 0xFF, 0xFD, 0xFF, 0xBF, 0xFF
        DB 0xFD, 0xFF, 0xBF, 0xFF, 0xFB, 0xFF, 0x7F, 0xFF, 0xFB
        DB 0xFF, 0x7F, 0xFF, 0xF7, 0xFF, 0x7F, 0xFF, 0xF7, 0xFF
        DB 0xBF, 0xFF, 0xCB, 0xFF, 0xDF, 0xFF, 0x3D, 0xFF, 0xEC
        DB 0xFF, 0xFE, 0xFF, 0xE3, 0xFF, 0xFF, 0xFF, 0xEF, 0xFF
        DB 0xFF, 0xFF, 0xEF, 0xFF, 0xFE, 0xFF, 0xDF, 0xFF, 0xFE
        DB 0xFF, 0xDF, 0xFF, 0xFD, 0xFF, 0xBF, 0xFF, 0xFD, 0xFF
        DB 0xBF, 0xFF, 0xFA, 0xFF, 0x7F, 0xFF, 0xFA, 0xFF, 0x7F
        DB 0xFE, 0xF4, 0xFF, 0x7F, 0xFE, 0xF4, 0xFF, 0xBF, 0xFE
        DB 0xC4, 0xFF, 0x5F, 0xFF, 0x3A, 0x7F, 0x2C, 0xFF, 0xC5
        DB 0x3F, 0x13, 0xC5, 0, 0x7F, 0x2C, 0, 0, 0x7C
        DB 0x28, 0, 0, 0xF8, 0x50, 0, 0, 0xF8, 0x50
        DB 0, 0, 0xF0, 0xA0, 0, 0, 0xE0, 0, 0
        DB 0
spr_26:
        DB 4, 32
        DB 0xEF, 0xEF, 0xFF, 0xFF, 0x70, 0x70, 0, 0, 0xEF
        DB 0xEF, 0xFF, 0xFF, 0x70, 0x70, 0, 0, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xF0, 0xF0, 0, 0, 0x80, 0x80, 0
        DB 0, 0x20, 0x20, 0, 0, 0x7F, 0x7F, 0xFC, 0xFC
        DB 0x10, 0x10, 0, 0, 0x3F, 0x3F, 0x83, 0x83, 0xE0
        DB 0xE0, 0, 0, 0x10, 0x10, 0x7F, 0x7F, 0xF0, 0xF0
        DB 0, 0, 0x3F, 0x3F, 0xFF, 0xFF, 0x20, 0x20, 0
        DB 0, 0x7F, 0x7F, 0xF9, 0xF9, 0x98, 0x98, 0, 0
        DB 0xFF, 0xFF, 0xC6, 0xC6, 0x3C, 0x3C, 0, 0, 0x7E
        DB 0x7E, 0x39, 0x39, 0xDE, 0xDE, 0, 0, 0x38, 0x38
        DB 0xE7, 0xE7, 0xEF, 0xEF, 0, 0, 0x17, 0x17, 0x9F
        DB 0x9F, 0xF7, 0xF7, 0x57, 0x57, 0x3E, 0x3E, 0x7F, 0x7F
        DB 0xFA, 0xFA, 0xEF, 0xEF, 0x79, 0x79, 0xFF, 0xFF, 0xFC
        DB 0xFC, 0x67, 0x67, 0xE7, 0xE7, 0xFF, 0xFF, 0xFD, 0xFD
        DB 0x64, 0x64, 0xF, 0xF, 0xFF, 0xFF, 0xFD, 0xFD, 0xE7
        DB 0xE7, 0xF7, 0xF7, 0xFF, 0xFF, 0xFA, 0xFA, 0xE7, 0xE7
        DB 0x7B, 0x7B, 0xFF, 0xFF, 0xFA, 0xFA, 0xD7, 0xD7, 0x3D
        DB 0x3D, 0xFF, 0xFF, 0xF5, 0xF5, 0xD7, 0xD7, 0x1E, 0x1E
        DB 0xFF, 0xFF, 0xF5, 0xF5, 0xD7, 0xD7, 0xF, 0xF, 0x7F
        DB 0x7F, 0xED, 0xED, 0xD7, 0xD7, 7, 7, 0xBF, 0xBF
        DB 0xEB, 0xEB, 0xD7, 0xD7, 3, 3, 0xDF, 0xDF, 0xDB
        DB 0xDB, 0xB7, 0xB7, 1, 1, 0xEF, 0xEF, 0xD3, 0xD3
        DB 0xB7, 0xB7, 0, 0, 0xF7, 0xF7, 0xB7, 0xB7, 0xB7
        DB 0xB7, 0, 0, 0x7B, 0x7B, 0xB7, 0xB7, 0xB7, 0xB7
        DB 0, 0, 0x3D, 0x3D, 0x6F, 0x6F, 0xB7, 0xB7, 0
        DB 0, 0x1E, 0x1E, 0x7F, 0x7F, 0xF4, 0xF4, 0, 0
        DB 0xE, 0xE, 0xEF, 0xEF, 0xB7, 0xB7, 0, 0, 6
        DB 6, 0xC7, 0xC7, 0x17, 0x17, 0, 0, 2, 2
        DB 0x82, 0x82, 0xF, 0xF
spr_27:
        DB 1, 24
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xFF
spr_28:
        DB 3, 1
        DB 0xEF, 0xEF, 0xFF, 0xFF, 0x70, 0x70
spr_29:
        DB 1, 8
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xC3, 0xC3, 0xC3, 0xC3, 0xC3
        DB 0xC3, 0xC3, 0xC3, 0xFF, 0xFF, 0xFF, 0xFF
spr_2A:
        DB 2, 12
        DB 0xFB, 0xFB, 0, 0, 0xF1, 0xF1, 0xC0, 0xC0, 0xE0
        DB 0xE0, 0xE0, 0xE0, 0x70, 0x70, 0x70, 0x70, 0x38, 0x38
        DB 0xF8, 0xF8, 0x1D, 0x1D, 0xFC, 0xFC, 0xF, 0xF, 0xFE
        DB 0xFE, 7, 7, 0xFF, 0xFF, 3, 3, 0xFF, 0xFF
        DB 1, 1, 0xFC, 0xFC, 0, 0, 0xF0, 0xF0, 0
        DB 0, 0x40, 0x40
spr_2B:
        DB 2, 16
        DB 0xFF, 0xFF, 0xF0, 0xF0, 0x1F, 0x1F, 0xF0, 0xF0, 0x1F
        DB 0x1F, 0x38, 0x38, 0xE, 0xE, 0x38, 0x38, 0xE, 0xE
        DB 0x1C, 0x1C, 7, 7, 0x1C, 0x1C, 7, 7, 0xE
        DB 0xE, 3, 3, 0x9E, 0x9E, 3, 3, 0xFF, 0xFF
        DB 1, 1, 0xFC, 0xFC, 1, 1, 0xF0, 0xF0, 0
        DB 0, 0xC0, 0xC0, 3, 3, 0, 0, 0xC, 0xC
        DB 0, 0, 0x30, 0x30, 0, 0, 0xC0, 0xC0, 0
        DB 0
spr_2C:
        DB 2, 8
        DB 0, 0, 3, 3, 0, 0, 0xC, 0xC, 0
        DB 0, 0x30, 0x30, 0, 0, 0xC0, 0xC0, 3, 3
        DB 0, 0, 0xC, 0xC, 0, 0, 0x30, 0x30, 0
        DB 0, 0xC0, 0xC0, 0, 0
spr_2D:
        DB 4, 24
        DB 0, 0, 1, 0, 0x80, 0, 0, 0, 0
        DB 0, 7, 1, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x1F, 6, 0xF8, 0xE0, 0, 0, 0, 0, 0x7F
        DB 0x1E, 0xFE, 0xF8, 0, 0, 1, 0, 0xFF, 0x7E
        DB 0xFF, 0xFE, 0x80, 0, 7, 1, 0xFF, 0xFA, 0xFF
        DB 0xFF, 0xE0, 0x80, 0x1F, 7, 0xFF, 0xE2, 0xFF, 0xFF
        DB 0xF8, 0xE0, 0x7F, 0x1F, 0xFF, 0x9A, 0xFF, 0xFF, 0xFE
        DB 0xF8, 0xFF, 0x7E, 0xFF, 0x7A, 0xFF, 0xFF, 0xFF, 0xFE
        DB 0x7F, 0x38, 0xFF, 0xFA, 0xFF, 0xFF, 0xFE, 0xFC, 0x3F
        DB 0x1D, 0xFF, 0x7A, 0xFF, 0xFF, 0xFC, 0xF8, 0x1F, 0xE
        DB 0xFF, 0x9A, 0xFF, 0xFF, 0xF8, 0xF0, 0xF, 7, 0xFF
        DB 0x6A, 0xFF, 0xFF, 0xF0, 0xE0, 7, 3, 0xFF, 0xBA
        DB 0xFF, 0xFF, 0xE0, 0xC0, 3, 1, 0xFF, 0xDA, 0xFF
        DB 0xFF, 0xC0, 0x80, 1, 0, 0xFF, 0xEA, 0xFF, 0xFF
        DB 0x80, 0, 0, 0, 0xFF, 0x72, 0xFF, 0xFE, 0
        DB 0, 0, 0, 0x7F, 0x3A, 0xFE, 0xFC, 0, 0
        DB 0, 0, 0x3F, 0x1E, 0xFC, 0xF8, 0, 0, 0
        DB 0, 0x1F, 0xE, 0xF8, 0xF0, 0, 0, 0, 0
        DB 0xF, 6, 0xF0, 0xE0, 0, 0, 0, 0, 7
        DB 2, 0xE0, 0xC0, 0, 0, 0, 0, 3, 1
        DB 0xC0, 0x80, 0, 0, 0, 0, 1, 0, 0x80
        DB 0, 0, 0
spr_2E:
        DB 2, 17
        DB 0xE, 0, 0x38, 0, 0x1F, 0xE, 0x7C, 0x38, 0x1F
        DB 0xB, 0xFC, 0x78, 0xF, 5, 0xF8, 0x70, 7, 3
        DB 0xF0, 0x60, 0xF, 3, 0xF8, 0xE0, 0x1F, 0xD, 0xFC
        DB 0xF8, 0x1F, 0xD, 0xFC, 0xF8, 0x1F, 0xD, 0xFC, 0xF8
        DB 0x1F, 0xD, 0xFC, 0xF8, 0x1F, 0xE, 0xFC, 0x38, 0xF
        DB 1, 0xF8, 0xC0, 0xF, 7, 0xF8, 0xF0, 0xF, 7
        DB 0xF8, 0xF0, 7, 2, 0xF0, 0xA0, 7, 3, 0xF0
        DB 0xE0, 3, 0, 0xE0, 0
spr_2F:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 3, 0, 0xFC, 0
        DB 0x3F, 0, 0xC0, 0, 7, 3, 0xFE, 0xFC, 0x7F
        DB 0x3F, 0xE0, 0xC0, 3, 1, 0xFC, 0xF8, 0x3F, 0x1F
        DB 0xC0, 0x80, 1, 0, 0xF8, 0xF0, 0x1F, 0xF, 0x80
        DB 0, 3, 0, 0xFF, 0, 0xFF, 0, 0xC0, 0
        DB 7, 3, 0xFF, 0xFF, 0xFF, 0xFF, 0xE0, 0xC0, 0xF
        DB 3, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xC0, 0x1F, 0xB
        DB 0xFF, 0xF0, 0xFF, 0xF, 0xF8, 0xD0, 0x1F, 0xB, 0xFF
        DB 0xF7, 0xFF, 0xEF, 0xF8, 0xD0, 0x1F, 0xB, 0xFF, 0xF7
        DB 0xFF, 0xEF, 0xF8, 0xD0, 0x1F, 9, 0xFF, 0xF0, 0xFF
        DB 0xF, 0xF8, 0xB0, 0x1F, 0xD, 0xFF, 0xF8, 0xFF, 0x1F
        DB 0xF8, 0xB0, 0x1F, 0xD, 0xFF, 0xFB, 0xFF, 0xDF, 0xF8
        DB 0xB0
spr_30:
        DB 4, 16
        DB 0x1F, 0xD, 0xFF, 0xF8, 0xFF, 0x1F, 0xF8, 0xB0, 0x1F
        DB 0xD, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xB0, 0xF, 5
        DB 0xFF, 0, 0xFF, 0, 0xF0, 0xA0, 5, 0, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xA0, 0, 0, 0, 0xFF, 0
        DB 0xFF, 0, 0x80, 0, 1, 0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0x80, 0, 1, 0, 0xFF, 0xF9, 0xFF, 0x9F
        DB 0x80, 0, 0, 0, 0xFF, 0x74, 0xFF, 0x2E, 0
        DB 0, 0, 0, 0xFF, 0x76, 0xFF, 0x6E, 0, 0
        DB 0, 0, 0x7F, 0x39, 0xFE, 0x9C, 0, 0, 0
        DB 0, 0x7F, 0x3F, 0xFE, 0xFC, 0, 0, 0, 0
        DB 0x7F, 0x20, 0xFE, 4, 0, 0, 0, 0, 0x3F
        DB 0x1F, 0xFC, 0xF8, 0, 0, 0, 0, 0x3F, 0x1F
        DB 0xFC, 0xF8, 0, 0, 0, 0, 0x1F, 0, 0xF8
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0
spr_31:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 3, 0, 0xFC, 0
        DB 0x3F, 0, 0xC0, 0, 7, 3, 0xFE, 0xFC, 0x7F
        DB 0x3F, 0xE0, 0xC0, 3, 1, 0xFC, 0xF8, 0x3F, 0x1F
        DB 0xC0, 0x80, 1, 0, 0xF8, 0xF0, 0x1F, 0xF, 0x80
        DB 0, 3, 0, 0xFF, 0, 0xFF, 0, 0xC0, 0
        DB 7, 3, 0xFF, 0xFF, 0xFF, 0xFF, 0xE0, 0xC0, 0xF
        DB 3, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0, 0xC0, 0x1F, 0xB
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xD0, 0x1F, 0xB, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xF8, 0xD0, 0x1F, 0xB, 0xFF, 0xFF
        DB 0xFF, 0xFF, 0xF8, 0xD0, 0x1F, 9, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xF8, 0xB0, 0x1F, 0xD, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0xF8, 0xB0, 0x1F, 0xD, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8
        DB 0xB0
spr_32:
        DB 4, 16
        DB 0x1F, 0xD, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xB0, 0x1F
        DB 0xD, 0xFF, 0xFF, 0xFF, 0xFF, 0xF8, 0xB0, 0xF, 5
        DB 0xFF, 0, 0xFF, 0, 0xF0, 0xA0, 5, 0, 0xFF
        DB 0xFF, 0xFF, 0xFF, 0xA0, 0, 0, 0, 0xFF, 0
        DB 0xFF, 0, 0, 0, 1, 0, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0x80, 0, 1, 0, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0x80, 0, 0, 0, 0xFF, 0x7F, 0xFF, 0xFE, 0
        DB 0, 0, 0, 0xFF, 0x7F, 0xFF, 0xFE, 0, 0
        DB 0, 0, 0x7F, 0x3F, 0xFE, 0xFC, 0, 0, 0
        DB 0, 0x7F, 0x3F, 0xFE, 0xFC, 0, 0, 0, 0
        DB 0x7F, 0x20, 0xFE, 4, 0, 0, 0, 0, 0x3F
        DB 0x1F, 0xFC, 0xF8, 0, 0, 0, 0, 0x3F, 0x1F
        DB 0xFC, 0xF8, 0, 0, 0, 0, 0x1F, 0, 0xF8
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0
spr_33:
        DB 4, 17
        DB 0, 0, 0x7F, 0, 0xFE, 0, 0, 0, 0
        DB 0, 0xFF, 0x7F, 0xFF, 0xFE, 0, 0, 0, 0
        DB 0xFF, 0x3F, 0xFF, 0xFA, 0, 0, 0, 0, 0xFF
        DB 0x5F, 0xFE, 0xE4, 0, 0, 0, 0, 0x7F, 0x2F
        DB 0xFC, 0xB8, 0, 0, 0, 0, 0xFF, 0, 0xFF
        DB 0, 0, 0, 1, 0, 0xFF, 0xFF, 0xFF, 0xFF
        DB 0x80, 0, 1, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0x80
        DB 0, 1, 0, 0xFF, 0xFC, 0xFF, 0x3F, 0x80, 0
        DB 1, 0, 0xFF, 0xFC, 0xFF, 0x1F, 0x80, 0, 1
        DB 0, 0xFF, 0xFE, 0xFF, 0x5F, 0x80, 0, 1, 0
        DB 0xFF, 0xFE, 0xFF, 0x5E, 0, 0, 0, 0, 0xFF
        DB 0x7C, 0xFF, 0x5E, 0, 0, 0, 0, 0xFF, 0x7C
        DB 0xFF, 0xBE, 0, 0, 1, 0, 0xFF, 0xFC, 0xFF
        DB 0xBF, 0x80, 0, 1, 0, 0xFF, 0xFC, 0xFF, 0xBF
        DB 0x80, 0, 1, 0, 0xFF, 0xFD, 0xFF, 0xBF, 0x80
        DB 0
spr_34:
        DB 4, 17
        DB 1, 0, 0xFF, 0xBC, 0xFF, 0x7D, 0x80, 0, 1
        DB 0, 0xFF, 0xBF, 0xFF, 0xFD, 0x80, 0, 0, 0
        DB 0xFF, 0x7F, 0xFF, 0xFE, 0, 0, 0, 0, 0xFF
        DB 0x40, 0xFF, 2, 0, 0, 0, 0, 0xFF, 0x5F
        DB 0xFF, 0xFA, 0, 0, 0, 0, 0xFF, 0x40, 0xFF
        DB 2, 0, 0, 0, 0, 0x7F, 0x3F, 0xFE, 0xFC
        DB 0, 0, 0, 0, 0x7F, 0x3F, 0xFE, 0xFC, 0
        DB 0, 0, 0, 0x7F, 0x3F, 0xFE, 0xFC, 0, 0
        DB 0, 0, 0x7F, 0x2F, 0xFE, 0xF4, 0, 0, 0
        DB 0, 0x7F, 0x37, 0xFE, 0xEC, 0, 0, 0, 0
        DB 0x7F, 0x37, 0xFE, 0xEC, 0, 0, 0, 0, 0x3F
        DB 0x18, 0xFC, 0x18, 0, 0, 0, 0, 0x3F, 0x1B
        DB 0xFC, 0xD8, 0, 0, 0, 0, 0x1F, 0xB, 0xF8
        DB 0xD0, 0, 0, 0, 0, 0x1F, 0xF, 0xF8, 0xF0
        DB 0, 0, 0, 0, 0xF, 0, 0xF0, 0, 0
        DB 0
spr_35:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0x1E, 0, 0, 0, 0, 0, 0, 0, 0x7F
        DB 0x1A, 0x80, 0, 0, 0, 1, 0, 0xFF, 0x77
        DB 0xE3, 0x80, 0x80, 0, 7, 1, 0xFF, 0xE3, 0xFF
        DB 0xE3, 0xF0, 0x80, 0xF, 7, 0xFF, 0xCC, 0xFF, 0xCF
        DB 0xFC, 0x70, 7, 3, 0xFF, 0x3B, 0xFF, 0x1C, 0xFE
        DB 0xFC, 3, 0, 0xFF, 0xFB, 0xFF, 0xCB, 0xFC, 0xF8
        DB 7, 3, 0xFF, 0xFB, 0xFF, 0xF3, 0xF8, 0xF0, 0xF
        DB 7, 0xFF, 0xC3, 0xFF, 0x1C, 0xF0, 0xE0, 0x1F, 0xF
        DB 0xFF, 0xC3, 0xFF, 0x27, 0xE0, 0, 0x1F, 0xF, 0xFF
        DB 0x93, 0xFF, 0x33, 0xE0, 0xC0, 0x1F, 0xF, 0xFF, 0x13
        DB 0xFF, 0x19, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x2B, 0xFF
        DB 9, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x2B, 0xFF, 0xA1
        DB 0xE0, 0xC0, 0x1F, 0xE, 0xFF, 0xDB, 0xFF, 0xB9, 0xE0
        DB 0xC0
spr_36:
        DB 4, 17
        DB 0x1F, 0xE, 0xFF, 0x31, 0xFF, 0xCB, 0xE0, 0xC0, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x73, 0xC0, 0x80, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xC0, 0x80, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xC0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 7, 3, 0xFF, 0xFB, 0xFF, 0x38, 0
        DB 0, 0xF, 7, 0xFF, 0xF6, 0xFF, 0x9E, 0x80, 0
        DB 7, 3, 0xFF, 0xF6, 0xFF, 0xE7, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xEB, 0xFF, 0x37, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xC6, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_37:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0xF, 0, 0, 0, 0, 0, 0, 0
        DB 0x3F, 0xD, 0xC0, 0, 0, 0, 0, 0, 0xFF
        DB 0x3B, 0xF0, 0xC0, 0, 0, 3, 0, 0xFF, 0xF7
        DB 0xF8, 0xF0, 0, 0, 7, 3, 0xFF, 0xF3, 0xFF
        DB 0xE0, 0, 0, 3, 1, 0xFF, 0xCC, 0xFF, 0xC7
        DB 0xE0, 0, 1, 0, 0xFF, 0x3B, 0xFF, 0x1E, 0xF8
        DB 0xE0, 3, 0, 0xFF, 0xFB, 0xFF, 0xC9, 0xFC, 0xF8
        DB 7, 3, 0xFF, 0x9B, 0xFF, 0xF3, 0xF8, 0xF0, 0xF
        DB 6, 0xFF, 0x5B, 0xFF, 0x1C, 0xF0, 0xE0, 0x1F, 0xE
        DB 0xFF, 0x5B, 0xFF, 0x27, 0xE0, 0, 0x1F, 0xE, 0xFF
        DB 0x3B, 0xFF, 0x33, 0xE0, 0xC0, 0x1F, 0xF, 0xFF, 0x3B
        DB 0xFF, 0x19, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x5B, 0xFF
        DB 9, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x5B, 0xFF, 0xA1
        DB 0xE0, 0xC0, 0x1F, 0xE, 0xFF, 0xBB, 0xFF, 0xB9, 0xE0
        DB 0xC0
spr_38:
        DB 4, 17
        DB 0x1F, 0xE, 0xFF, 0x71, 0xFF, 0xCB, 0xE0, 0xC0, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x73, 0xC0, 0x80, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xC0, 0x80, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xC0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 7, 3, 0xFF, 0xFB, 0xFF, 0x38, 0
        DB 0, 0xF, 7, 0xFF, 0xF6, 0xFF, 0x9E, 0x80, 0
        DB 7, 3, 0xFF, 0xF6, 0xFF, 0xE7, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xEB, 0xFF, 0x37, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xC6, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_39:
        DB 4, 17
        DB 0, 0, 7, 0, 0x80, 0, 0, 0, 0
        DB 0, 0x1F, 6, 0xE0, 0x80, 0, 0, 0, 0
        DB 0x7F, 0x1D, 0xF8, 0xE0, 0, 0, 1, 0, 0xFF
        DB 0x7B, 0xFC, 0xF8, 0, 0, 3, 1, 0xFF, 0xF7
        DB 0xF8, 0xF0, 0, 0, 1, 0, 0xFF, 0xF3, 0xF0
        DB 0xE0, 0, 0, 0, 0, 0xFF, 0x4C, 0xFE, 0xC0
        DB 0, 0, 0, 0, 0xFF, 0x3B, 0xFF, 0xE, 0xC0
        DB 0, 3, 0, 0xFF, 0xFB, 0xFF, 0xDD, 0xF0, 0xC0
        DB 7, 3, 0xFF, 0xFB, 0xFF, 0xF3, 0xF8, 0xF0, 0xF
        DB 7, 0xFF, 0xFB, 0xFF, 0x1C, 0xF0, 0xE0, 0x1F, 0xF
        DB 0xFF, 0xFB, 0xFF, 0x27, 0xE0, 0, 0x1F, 8, 0xFF
        DB 0xFB, 0xFF, 0x3B, 0xE0, 0xC0, 0x1F, 0, 0xFF, 0x3B
        DB 0xFF, 0x19, 0xF0, 0xE0, 0x1F, 0, 0xFF, 0x5B, 0xFF
        DB 9, 0xF0, 0xE0, 0x1F, 0xC, 0xFF, 0x5B, 0xFF, 0xA1
        DB 0xF8, 0xD0, 0x1F, 0xE, 0xFF, 0xBB, 0xFF, 0xB9, 0xF8
        DB 0xD0
spr_3A:
        DB 4, 17
        DB 0x1F, 0xF, 0xFF, 0x71, 0xFF, 0xCB, 0xF8, 0xD0, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x73, 0xF8, 0xB0, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xF0, 0xA0, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xE0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 7, 3, 0xFF, 0xFB, 0xFF, 0x38, 0
        DB 0, 0xF, 7, 0xFF, 0xF6, 0xFF, 0x9E, 0x80, 0
        DB 7, 3, 0xFF, 0xF6, 0xFF, 0xE7, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xCB, 0xFF, 0x37, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xC6, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_3B:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0xD, 0, 0, 0, 0, 0, 0, 0
        DB 0x3F, 0xD, 0xC0, 0, 0, 0, 0, 0, 0xFF
        DB 0x3D, 0xF0, 0xC0, 0, 0, 3, 0, 0xFF, 0xFD
        DB 0xF8, 0xF0, 0, 0, 7, 3, 0xFF, 0xF3, 0xF8
        DB 0xF0, 0, 0, 3, 0, 0xFF, 0xCC, 0xF0, 0xE0
        DB 0, 0, 0, 0, 0xFF, 0x3B, 0xFC, 0, 0
        DB 0, 3, 0, 0xFF, 0xFB, 0xFF, 0xD4, 0, 0
        DB 7, 3, 0xFF, 0xFB, 0xFF, 0xF3, 0xC0, 0, 0xF
        DB 7, 0xFF, 0xC3, 0xFF, 0xFC, 0xE0, 0xC0, 0x1F, 0xF
        DB 0xFF, 0xD3, 0xFF, 0xFF, 0xC0, 0, 0x1F, 0xF, 0xFF
        DB 0xD3, 0xFF, 0xFF, 0xE0, 0xC0, 0x1F, 0xF, 0xFF, 0x13
        DB 0xFF, 0xFF, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x2B, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x2B, 0xFF, 0xFF
        DB 0xE0, 0xC0, 0x1F, 0xE, 0xFF, 0xDB, 0xFF, 0xFF, 0xE0
        DB 0xC0
spr_3C:
        DB 4, 17
        DB 0x1F, 0xE, 0xFF, 0x31, 0xFF, 0xFF, 0xE0, 0xC0, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x7F, 0xC0, 0x80, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xC0, 0x80, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xC0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 7, 3, 0xFF, 0xFB, 0xFF, 0xF8, 0
        DB 0, 0xF, 7, 0xFF, 0xF7, 0xFF, 0xFE, 0x80, 0
        DB 7, 3, 0xFF, 0xF7, 0xFF, 0xFF, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xEB, 0xFF, 0xFF, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xFE, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_3D:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0x1A, 0, 0, 0, 0, 0, 0, 0, 0x7F
        DB 0x1A, 0x80, 0, 0, 0, 1, 0, 0xFF, 0x7B
        DB 0xE0, 0x80, 0, 0, 7, 1, 0xFF, 0xF3, 0xF0
        DB 0xE0, 0, 0, 0xF, 7, 0xFF, 0xCC, 0xFA, 0xE0
        DB 0, 0, 7, 1, 0xFF, 0x3B, 0xFF, 0xA, 0x80
        DB 0, 3, 0, 0xFF, 0xFB, 0xFF, 0xCB, 0xE0, 0x80
        DB 7, 3, 0xFF, 0x9B, 0xFF, 0xF3, 0xF0, 0xE0, 0xF
        DB 6, 0xFF, 0x1B, 0xFF, 0xFC, 0xF0, 0xE0, 0x1F, 0xE
        DB 0xFF, 0x5B, 0xFF, 0xFF, 0xE0, 0, 0x1F, 0xF, 0xFF
        DB 0x3B, 0xFF, 0xFF, 0xE0, 0xC0, 0x1F, 0xF, 0xFF, 0x5B
        DB 0xFF, 0xFF, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x5B, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0x1F, 0xE, 0xFF, 0x5B, 0xFF, 0xFF
        DB 0xE0, 0xC0, 0x1F, 0xE, 0xFF, 0xBB, 0xFF, 0xFF, 0xE0
        DB 0xC0
spr_3E:
        DB 4, 17
        DB 0x1F, 0xE, 0xFF, 0x71, 0xFF, 0xFF, 0xE0, 0xC0, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x7F, 0xC0, 0x80, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xC0, 0x80, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xC0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 0xF, 3, 0xFF, 0xFB, 0xFF, 0xF8, 0
        DB 0, 0xF, 7, 0xFF, 0xF7, 0xFF, 0xFE, 0x80, 0
        DB 7, 3, 0xFF, 0xF7, 0xFF, 0xFF, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xEB, 0xFF, 0xFF, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xFE, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_3F:
        DB 4, 17
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0x34
        DB 0, 0, 0, 0, 0, 0, 0, 0xFF, 0x34
        DB 0, 0, 0, 0, 3, 0, 0xFF, 0xF3, 0xC5
        DB 0, 0, 0, 0xF, 3, 0xFF, 0xCC, 0xFF, 0xC5
        DB 0xC0, 0, 0x1F, 0xF, 0xFF, 0x3B, 0xFF, 0x1D, 0xF0
        DB 0xC0, 0xF, 0, 0xFF, 0xFB, 0xFF, 0xCD, 0xF8, 0xF0
        DB 7, 3, 0xFF, 0xFB, 0xFF, 0xF0, 0xF8, 0x70, 0xF
        DB 7, 0xFF, 0xFB, 0xFF, 0xFC, 0xF0, 0x20, 0x1F, 0xF
        DB 0xFF, 0xFB, 0xFF, 0xFF, 0xE0, 0, 0x1F, 8, 0xFF
        DB 0xFB, 0xFF, 0xFF, 0xE0, 0xC0, 0xF, 0, 0xFF, 0x3B
        DB 0xFF, 0xFF, 0xF0, 0xE0, 0xF, 0, 0xFF, 0x5B, 0xFF
        DB 0xFF, 0xF0, 0xE0, 0x1F, 0xC, 0xFF, 0x5B, 0xFF, 0xFF
        DB 0xF8, 0xD0, 0x1F, 0xE, 0xFF, 0xBB, 0xFF, 0xFF, 0xFC
        DB 0xD8
spr_40:
        DB 4, 17
        DB 0x1F, 0xF, 0xFF, 0x71, 0xFF, 0xFF, 0xFC, 0xD8, 0xF
        DB 7, 0xFF, 0xCE, 0xFF, 0x7F, 0xF8, 0xB0, 0xF, 7
        DB 0xFF, 0x3F, 0xFF, 0x9F, 0xF0, 0xA0, 0xF, 4, 0xFF
        DB 0xF1, 0xFF, 0xE7, 0xE0, 0x80, 7, 3, 0xFF, 0xCE
        DB 0xFF, 0x79, 0xC0, 0x80, 0xF, 7, 0xFF, 0x3B, 0xFF
        DB 0x9E, 0x80, 0, 7, 0, 0xFF, 0xFB, 0xFF, 0xE7
        DB 0x80, 0, 7, 3, 0xFF, 0xFB, 0xFF, 0xF8, 0
        DB 0, 0xF, 7, 0xFF, 0xF7, 0xFF, 0xFE, 0x80, 0
        DB 7, 3, 0xFF, 0xF7, 0xFF, 0xFF, 0xC0, 0x80, 3
        DB 1, 0xFF, 0xEB, 0xFF, 0xFF, 0x80, 0, 1, 0
        DB 0xFF, 0x9C, 0xFF, 0xFE, 0, 0, 0, 0, 0xFF
        DB 0x7F, 0xFE, 0x3C, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFC, 0xC8, 0, 0, 0, 0, 0x1F, 7, 0xF8
        DB 0xE0, 0, 0, 0, 0, 7, 1, 0xE0, 0x80
        DB 0, 0, 0, 0, 1, 0, 0x80, 0, 0
        DB 0
spr_41:
        DB 1, 48
        DB 3, 0, 0xF, 3, 0x3F, 7, 0xFF, 0x2F, 0xFF
        DB 0xEF, 0xFF, 0xDF, 0xFF, 0xDF, 0xFF, 0xBF, 0xFF, 0xBF
        DB 0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0xBF, 0xFF
        DB 0xDF, 0xFF, 0xEC, 0xFF, 0xF3, 0xFF, 0xEF, 0xFF, 0xEF
        DB 0xFF, 0xDF, 0xFF, 0xDF, 0xFF, 0xBF, 0xFF, 0xBF, 0xFF
        DB 0x7F, 0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0xBF, 0xFF, 0xDF
        DB 0xFF, 0xEC, 0xFF, 0xE3, 0xFF, 0xEF, 0xFF, 0xEF, 0xFF
        DB 0xDF, 0xFF, 0xDF, 0xFF, 0xBF, 0xFF, 0xBF, 0xFF, 0x7F
        DB 0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0xBF, 0xFF, 0x5F, 0x7F
        DB 0x2C, 0x3F, 0x13, 0x7F, 0x2C, 0x7C, 0x28, 0xF8, 0x50
        DB 0xF8, 0x50, 0xF0, 0xA0, 0xE0, 0
spr_42:
        DB 3, 20
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 8, 0, 0, 0, 0, 0
        DB 0x1C, 8, 0, 0, 0, 0, 8, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0x20, 0
        DB 0, 0, 0, 0, 0x70, 0x20, 0, 0, 0
        DB 0, 0x20, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0x10, 0, 0
        DB 0, 0, 0, 0x38, 0x10, 0, 0, 0x80, 0
        DB 0x10, 0, 0x11, 0, 0xC0, 0x80, 0, 0, 0x38
        DB 0x10, 0x80, 0, 0, 0, 0x7C, 0x38, 0, 0
        DB 0, 0, 0x38, 0x10, 0, 0, 0, 0, 0x10
        DB 0, 0, 0, 1, 0, 0, 0, 0, 0
        DB 3, 1, 0x80, 0, 0, 0, 1, 0, 0
        DB 0, 0, 0
spr_43:
        DB 3, 21
        DB 0, 0, 0, 0, 0, 0, 8, 0, 0
        DB 0, 0, 0, 0x1C, 8, 0, 0, 0, 0
        DB 0x3E, 0x1C, 0, 0, 0, 0, 0x1C, 8, 0
        DB 0, 0, 0, 8, 0, 0x1C, 8, 0x70, 0x20
        DB 0, 0, 0x3E, 0x1C, 0xF8, 0x70, 1, 0, 0x1C
        DB 8, 0x70, 0x20, 3, 1, 0x88, 0, 0x20, 0
        DB 0x11, 0, 0, 0, 0, 0, 0x38, 0x10, 0
        DB 0, 0x80, 0, 0x7C, 0x38, 0x11, 0, 0xC0, 0x80
        DB 0x38, 0x10, 0x3B, 0x11, 0xE0, 0xC0, 0x10, 0, 0x7D
        DB 0x38, 0xC0, 0x80, 0, 0, 0xFE, 0x7C, 0x80, 0
        DB 0, 0, 0x7C, 0x38, 0, 0, 1, 0, 0x38
        DB 0x10, 0, 0, 3, 1, 0x90, 0, 0, 0
        DB 7, 3, 0xC0, 0x80, 0, 0, 3, 1, 0x80
        DB 0, 0, 0, 1, 0, 0, 0, 0, 0
spr_44:
        DB 3, 23
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 8, 0, 0, 0, 0, 0
        DB 0x1C, 8, 8, 0, 0, 0, 8, 0, 0x1C
        DB 8, 0, 0, 0, 0, 0x3E, 0x1C, 0x20, 0
        DB 1, 0, 0x7F, 0x3E, 0x70, 0x20, 3, 1, 0xBE
        DB 0x1C, 0x20, 0, 0x17, 3, 0xDC, 0x88, 0, 0
        DB 0x3B, 0x11, 0x88, 0, 0x80, 0, 0x7D, 0x38, 0x11
        DB 0, 0xC0, 0x80, 0xFE, 0x7C, 0x3B, 0x11, 0xE0, 0xC0
        DB 0x7C, 0x38, 0x7F, 0x3B, 0xF0, 0xE0, 0x38, 0x10, 0xFF
        DB 0x7D, 0xE0, 0xC0, 0x11, 0, 0xFF, 0xFE, 0xC0, 0x80
        DB 0, 0, 0xFE, 0x7C, 0x80, 0, 0, 0, 0x7C
        DB 0x38, 0, 0, 1, 0, 0x38, 0x10, 0, 0
        DB 3, 1, 0x90, 0, 0, 0, 1, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0x80, 0
        DB 0, 0, 1, 0, 0xC0, 0x80, 0, 0, 0
        DB 0, 0x80, 0
spr_45:
        DB 3, 24
        DB 0, 0, 0, 0, 0, 0, 8, 0, 0
        DB 0, 0, 0, 0x1C, 8, 8, 0, 0, 0
        DB 0x3E, 0x1C, 0x1C, 1, 0, 0, 0x1C, 8, 0x3E
        DB 0x1C, 0x20, 0, 9, 0, 0x7F, 0x3E, 0x70, 0x20
        DB 3, 1, 0xFF, 0x7F, 0xF8, 0x70, 0x17, 3, 0xFF
        DB 0xBE, 0x70, 0x20, 0x3F, 0x17, 0xFE, 0xDC, 0x20, 0
        DB 0x7F, 0x3B, 0xDC, 0x88, 0, 0, 0xFF, 0x7D, 0x88
        DB 0, 0x80, 0, 0xFF, 0xFE, 1, 0, 0xC0, 0x80
        DB 0xFE, 0x7C, 0x13, 1, 0xE0, 0xC0, 0x7C, 0x38, 0x39
        DB 0x10, 0xC8, 0x80, 0x38, 0x10, 0x7C, 0x38, 0x9C, 8
        DB 0x10, 0, 0x38, 0x10, 8, 0, 1, 0, 0x10
        DB 0, 0, 0, 3, 0x10, 0x80, 0, 0, 0
        DB 7, 3, 0xC0, 0x80, 0, 0, 3, 0x10, 0x80
        DB 0, 0x80, 0, 1, 0, 9, 0, 0xC0, 0x80
        DB 0, 0, 0x1F, 9, 0xE0, 0xC0, 0, 0, 9
        DB 0, 0xC0, 0x80, 0, 0, 0, 0, 0x80, 0
spr_46:
        DB 3, 24
        DB 8, 0, 0x70, 0x20, 0, 0, 0x1C, 8, 0xF8
        DB 0x70, 8, 0, 0x3F, 0x1C, 0xFC, 0xF8, 0x3C, 8
        DB 0x7F, 0x36, 0xF8, 0x70, 0x78, 0x20, 0x3E, 0x1C, 0x78
        DB 0x20, 0xF8, 0x70, 0x1C, 8, 0x3D, 8, 0xFC, 0xF8
        DB 8, 0, 0x3F, 0x1D, 0xFE, 0xFC, 1, 0, 0x1D
        DB 8, 0xFC, 0xF8, 0x13, 1, 0xC8, 0, 0xF8, 0x70
        DB 0x39, 0x10, 0xE0, 0x40, 0x70, 0x40, 0x7C, 0x38, 0x50
        DB 0, 0x20, 0, 0xFE, 0x7C, 0x38, 0x10, 0x80, 0
        DB 0x7F, 0x3A, 0x7D, 0x38, 0xC8, 0x80, 0x3A, 0x10, 0xFE
        DB 0x7C, 0x9C, 8, 0x11, 0, 0xFF, 0xFE, 0x3E, 0x1C
        DB 1, 0, 0xFF, 0x7C, 0x1C, 8, 3, 1, 0xFF
        DB 0x39, 0x88, 0, 7, 3, 0xF9, 0x90, 0, 0
        DB 0xF, 7, 0xF0, 0xC0, 0x80, 0, 7, 3, 0xC1
        DB 0x80, 0xC0, 0x80, 3, 1, 0x8B, 1, 0xE0, 0xC0
        DB 1, 0, 0x1F, 0xB, 0xF0, 0xE0, 0, 0, 0xB
        DB 1, 0xE0, 0xC0, 0, 0, 1, 0, 0xC0, 0x80
spr_47:
        DB 3, 24
        DB 0x1C, 8, 0, 0, 8, 0, 0x3E, 0x1C, 0x20
        DB 0, 0x1C, 8, 0x7F, 0x3E, 0x78, 0x20, 0x3E, 0x1C
        DB 0xFF, 0x7F, 0xBC, 8, 0x1C, 8, 0x7F, 0x3E, 0x3E
        DB 0x1C, 0x28, 0, 0x3F, 0x1C, 0x7F, 0x3E, 0x70, 0x20
        DB 0x1F, 9, 0xFF, 0x7F, 0xF8, 0x70, 0xF, 3, 0xFF
        DB 0xBE, 0x70, 0x20, 0xF, 7, 0xFE, 0xDC, 0xA0, 0
        DB 7, 3, 0xDD, 0x88, 0xC0, 0x80, 0x13, 1, 0x8B
        DB 1, 0xE0, 0xC0, 0x3B, 0x10, 7, 3, 0xF8, 0xE0
        DB 0x17, 2, 0x13, 1, 0xFC, 0xC8, 0xF, 7, 0xB9
        DB 0x10, 0xFE, 0x9C, 7, 2, 0x7D, 0x38, 0xFF, 0x3E
        DB 3, 1, 0xBB, 0x11, 0xBE, 0x1C, 7, 3, 0xD7
        DB 0x83, 0xDC, 0x11, 0xF, 7, 0xE3, 0xC1, 0x88, 0
        DB 0x1F, 0xF, 0xF9, 0xE0, 0, 0, 0xF, 7, 0xFC
        DB 0xC8, 0x80, 0, 7, 3, 0xFF, 0x9C, 0xC0, 0x80
        DB 3, 1, 0xFF, 0x3F, 0xE0, 0xC0, 1, 0, 0xBF
        DB 0x1C, 0xC0, 0x80, 0, 0, 0x1C, 8, 0x80, 0
spr_48:
        DB 4, 25
        DB 0, 0, 0x1F, 0, 0xF8, 0, 0, 0, 0
        DB 0, 0xFF, 0x1F, 0xFF, 0xF8, 0, 0, 3, 0
        DB 0xFF, 0xFF, 0xFF, 0xFF, 0xC0, 0, 7, 3, 0xFF
        DB 0xE0, 0xFF, 7, 0xE0, 0xC0, 0xF, 7, 0xFF, 0x1F
        DB 0xFF, 0xF8, 0xF0, 0xE0, 0x1F, 0xC, 0xFF, 0xFF, 0xFF
        DB 0xFF, 0xF8, 0x30, 0x3F, 0x18, 0xFF, 0x7F, 0xFF, 0xFF
        DB 0xFC, 0xD8, 0x3F, 0x10, 0xFF, 0x7F, 0xFF, 0xFF, 0xFC
        DB 0xE8, 0x3F, 8, 0xFF, 0x7F, 0xFF, 0xFF, 0xFC, 0xF0
        DB 0x3F, 0x1C, 0xFF, 0x3F, 0xFF, 0xFF, 0xFC, 0xF8, 0x3F
        DB 0x1E, 0xFF, 0x3C, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1E
        DB 0xFF, 0x23, 0xFF, 0xC7, 0xFC, 0xF8, 0x1F, 0xF, 0xFF
        DB 0x5F, 0xFF, 0xF9, 0xF8, 0xF0, 0xF, 7, 0xFF, 0x9F
        DB 0xFF, 0xFE, 0xF0, 0xE0, 7, 2, 0xFF, 0x9C, 0xFF
        DB 0x3F, 0xE0, 0x40, 3, 0, 0xFF, 0x83, 0xFF, 0xC7
        DB 0xC0, 0, 3, 1, 0xFF, 0x9E, 0xFF, 0x79, 0xC0
        DB 0x80, 3, 1, 0xFF, 0x7C, 0xFF, 0x3E, 0xC0, 0x80
        DB 3, 1, 0xFF, 0x7F, 0xFF, 0xFE, 0xC0, 0x80, 3
        DB 0, 0xFF, 0xE7, 0xFF, 0xE7, 0xC0, 0, 1, 0
        DB 0xFF, 0xE3, 0xFF, 0xC7, 0x80, 0, 0, 0, 0xFF
        DB 0x73, 0xFF, 0xCE, 0, 0, 0, 0, 0x7F, 0x1F
        DB 0xFE, 0xF8, 0, 0, 0, 0, 0x1F, 3, 0xF8
        DB 0xC0, 0, 0, 0, 0, 3, 0, 0xC0, 0
        DB 0, 0
spr_49:
        DB 3, 24
        DB 0, 0, 0x3C, 0, 0, 0, 3, 0, 0x7E
        DB 0x3C, 0xC0, 0, 7, 3, 0xFF, 0x7E, 0xE0, 0xC0
        DB 0xF, 7, 0xFF, 0x42, 0xF0, 0xE0, 0xF, 6, 0xFF
        DB 0x3C, 0xF0, 0x60, 0xF, 1, 0xFF, 0xFF, 0xF0, 0x80
        DB 0xF, 3, 0xFF, 0x7F, 0xF0, 0xE0, 0x1F, 0xC, 0xFF
        DB 0x7F, 0xF8, 0xF0, 0x3F, 0x1C, 0xFF, 0x7F, 0xFC, 0xF8
        DB 0x3F, 0x1C, 0xFF, 0x7F, 0xFC, 0xF8, 0x3F, 0x1C, 0xFF
        DB 0x7F, 0xFC, 0xF8, 0x3F, 0x1C, 0xFF, 0x43, 0xFC, 0xF8
        DB 0x3F, 0x1D, 0xFF, 0xBC, 0xFC, 0x78, 0x3F, 0x1A, 0xFF
        DB 0x7F, 0xFC, 0x98, 0x3F, 0x14, 0xFF, 0x3F, 0xFC, 0xE8
        DB 0x3F, 0xF, 0xFF, 0x1F, 0xFC, 0xF0, 0x3F, 0x1F, 0xFF
        DB 0x8F, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xEF, 0xFC, 0xF8
        DB 0x3F, 0x1F, 0xFF, 0xFF, 0xFC, 0xF8, 0x1F, 0xF, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0xF, 7, 0xFF, 0xFF, 0xF0, 0xE0
        DB 7, 1, 0xFF, 0xFF, 0xE0, 0x80, 1, 0, 0xFF
        DB 0x3C, 0x80, 0, 0, 0, 0x3C, 0, 0, 0
spr_4A:
        DB 3, 23
        DB 0, 0, 0x18, 0, 0, 0, 0, 0, 0x3C
        DB 0x18, 0, 0, 1, 0, 0xFF, 0x3C, 0x80, 0
        DB 3, 1, 0xFF, 0xBD, 0xC0, 0x80, 7, 3, 0xFF
        DB 0xA5, 0xE0, 0xC0, 7, 3, 0xFF, 0x99, 0xE0, 0xC0
        DB 7, 2, 0xFF, 0x6E, 0xE0, 0x40, 7, 1, 0xFF
        DB 0xEF, 0xE0, 0x80, 0x1F, 7, 0xFF, 0xEF, 0xF8, 0xE0
        DB 0x3F, 0x1F, 0xFF, 0xEF, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF
        DB 0xEF, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF, 0xEF, 0xFC, 0xF8
        DB 0x3F, 0x1F, 0xFF, 0xEF, 0xFC, 0xF8, 0x3F, 0x1F, 0xFF
        DB 0x99, 0xFC, 0xF8, 0x3F, 0x1E, 0xFF, 0x7E, 0xFC, 0x78
        DB 0x3F, 0x19, 0xFF, 0xFF, 0xFC, 0x98, 0x3F, 0x17, 0xFF
        DB 0xFF, 0xFC, 0xE8, 0x3F, 0x1F, 0xFF, 0xFF, 0xFC, 0xF8
        DB 0x1F, 7, 0xFF, 0xFF, 0xF8, 0xE0, 7, 1, 0xFF
        DB 0xFF, 0xE0, 0x80, 1, 0, 0xFF, 0x7E, 0x80, 0
        DB 0, 0, 0x7E, 0x18, 0, 0, 0, 0, 0x18
        DB 0, 0, 0
spr_4B:
        DB 3, 19
        DB 0, 0, 0x18, 0, 0, 0, 0, 0, 0x3C
        DB 0x18, 0, 0, 1, 0, 0xFF, 0x3C, 0x80, 0
        DB 3, 1, 0xFF, 0xBD, 0xC0, 0x80, 7, 3, 0xFF
        DB 0xA5, 0xE0, 0xC0, 7, 3, 0xFF, 0x99, 0xE0, 0xC0
        DB 7, 2, 0xFF, 0x6E, 0xE0, 0x40, 0xF, 1, 0xFF
        DB 0xEF, 0xF0, 0x80, 0x3F, 7, 0xFF, 0xEF, 0xFC, 0xE0
        DB 0x3F, 0x1F, 0xFF, 0xEF, 0xFC, 0xF8, 0x1F, 0xF, 0xFF
        DB 0xEF, 0xF8, 0xF0, 0xF, 7, 0xFF, 0xEF, 0xF0, 0xE0
        DB 7, 3, 0xFF, 0xEF, 0xE0, 0xC0, 3, 1, 0xFF
        DB 0xEF, 0xC0, 0x80, 1, 0, 0xFF, 0xEF, 0x80, 0
        DB 0, 0, 0xFF, 0x6E, 0, 0, 0, 0, 0x7E
        DB 0x2C, 0, 0, 0, 0, 0x3C, 0x18, 0, 0
        DB 0, 0, 0x18, 0, 0, 0
spr_4C:
        DB 3, 21
        DB 0, 0, 0x3C, 0, 0, 0, 3, 0, 0x7E
        DB 0x3C, 0xC0, 0, 7, 3, 0xFF, 0x7E, 0xE0, 0xC0
        DB 0xF, 7, 0xFF, 0x42, 0xF0, 0xE0, 0xF, 6, 0xFF
        DB 0x3C, 0xF0, 0x60, 0xF, 1, 0xFF, 0xFF, 0xF0, 0x80
        DB 0xF, 7, 0xFF, 0xFF, 0xF0, 0xE0, 0x1F, 0xF, 0xFF
        DB 0xFF, 0xF8, 0xF0, 0x3F, 0x1F, 0xFF, 0xFF, 0xFC, 0xF8
        DB 0x3F, 0x1F, 0xFF, 0x3F, 0xFC, 0xF8, 0x3F, 0x1E, 0xFF
        DB 0x3F, 0xFC, 0xF8, 0x3F, 0x1C, 0xFF, 0x3F, 0xFC, 0xF8
        DB 0x1F, 0xC, 0xFF, 0x3F, 0xF8, 0xF0, 0x1F, 0xE, 0xFF
        DB 0x1F, 0xF8, 0xF0, 0xF, 6, 0xFF, 0x1F, 0xF0, 0xE0
        DB 0xF, 7, 0xFF, 0xF, 0xF0, 0xE0, 7, 3, 0xFF
        DB 0x8F, 0xE0, 0xC0, 3, 1, 0xFF, 0xCF, 0xC0, 0x80
        DB 1, 0, 0xFF, 0x7E, 0x80, 0, 0, 0, 0x7E
        DB 0x18, 0, 0, 0, 0, 0x18, 0, 0, 0
        ; ---------------------------------------------------------------------------
START:
        ld hl, seed_1
        ld bc, 0x788   ; number of bytes to clear
        ld a, (other_objs_here+0x70)
        push af
        call clr_mem
        pop af
        ld (seed_1), a
        call sub_A8F1
        jr loc_A650
        ; ---------------------------------------------------------------------------
start_menu:
        ld hl, objs_wiped_cnt
        ld bc, 0x780   ; number of bytes to clear
        call clr_mem
loc_A650:
        call build_lookup_tbls
        xor a
        ld (not_1st_screen), a
        ld (flags12_1), a   ; in player sprite 1
        ld a, 5   ; 5 lives_to_start
        ld (lives), a
        ld hl, 0x60   ; '`'
        ld (unk_5B36), hl
        ld hl, 0
        ld (unk_5B38), hl
        ld hl, seed_1
        ld a, (seed_2)
        add a, (hl)
        ld (hl), a
        call clear_scrn
        call do_menu_selection
        ld de, start_game_tune
        call play_audio
        call init_start_location
        call init_special_objects
        call set_room_attrs
player_dies:
        call lose_life
game_loop:
        call build_screen_objects
        ; START OF FUNCTION CHUNK FOR lose_life
onscreen_loop:
        ld ix, graphic_objs_tbl
update_sprite_loop:
        ld sp, 0xF100
        ld hl, ret_from_tbl_jp   ; return address
        push hl   ; save on stack
        ld a, (ix+24)   ; sprite data width (bytes)
        ld (ix+28), a   ; old sprite data width (bytes)
        ld a, (ix+25)   ; sprite data height (lines)
        ld (ix+29), a   ; old sprite data height (lines)
        ld a, (ix+26)   ; pixel X
        ld (ix+30), a   ; old pixel X
        ld a, (ix+27)   ; pixel Y
        ld (ix+31), a   ; old pixel Y
jump_to_upd_object:
        ld l, (ix+0)
        ld bc, upd_sprite_jmp_tbl
jump_to_tbl_entry:
        ld h, 0
        add hl, hl
        add hl, bc
        ld a, (hl)
        inc hl
        ld h, (hl)
        ld l, a
        jp (hl)
        ; END OF FUNCTION CHUNK FOR lose_life
        ; ---------------------------------------------------------------------------
ret_from_tbl_jp:
        ld a, r
        ld c, a
        ld a, (seed_3)
        add a, c
        ld (seed_3), a
        ld bc, 32
        add ix, bc   ; next sprite to update
        push ix
        pop hl
        ld bc, font   ; end of table?
        and a
        sbc hl, bc
        jr nc, done_sprite_updates   ; yes, exit
        jr update_sprite_loop
        ; ---------------------------------------------------------------------------
done_sprite_updates:
        ld hl, (seed_2)
        inc hl
        ld (seed_2), hl
        ld a, (seed_3)
        add a, (hl)
        add a, l
        add a, h
        ld (seed_3), a
        ld hl, not_1st_screen
        set 0, (hl)   ; update special objs tbl next time
        call list_objects_to_draw
        call render_dynamic_objects
        ld a, (byte_5B24)
        and a
        jp nz, loc_A741
        ld a, (rendered_objs_cnt)
        neg
        add a, 6
        ld b, a
        jp m, loc_A715
        jr z, loc_A715
game_delay:
        ld hl, 0x300
loc_A70E:
        dec hl
        ld a, l
        or h
        jr nz, loc_A70E
        djnz game_delay
loc_A715:
        call sub_AD66
        ld a, (render_status_info)
        and a
        jr z, loc_A72E
        call display_panel
        call colour_something
loc_A724:
        xor a
        ld (render_status_info), a
        call update_screen
        call reset_objs_wipe_flag
loc_A72E:
        call audio_CE22
        ld ix, graphic_objs_tbl
        ld a, (ix+0)
        or (ix+32)
        jp z, player_dies
        jp onscreen_loop
        ; ---------------------------------------------------------------------------
loc_A741:
        ld a, (render_status_info)
        and a
        jr z, loc_A72E
        jr loc_A724
        ; =============== S U B R O U T I N E =======================================
colour_something:
        ld a, (curr_room_attrib)
        or 0x40   ; '@'             ; set bright
        call fill_attr
        ld a, 0x47   ; 'G'
        ld de,  zxaram+0x2CE
        ld b, 2
        call fill_DE
        ld de,  zxaram+0x2EE
        ld b, 4
        call fill_DE
        call sub_A7AE
        call sub_BCAB
        ld a, (curr_room_attrib)
        cpl
        and 7
        add a, 0x42   ; 'B'
        ld (light_years_attr), a
        ld de, light_years_attr
        ld hl, 0x7A0
        call print_text
        call sub_A7A3
        ld hl,  zxaram+0x284
        ld (hl), 0x47   ; 'G'
        inc hl
        ld (hl), 0x47   ; 'G'
        ld hl,  zxaram+0x241
        ld bc, 0x303
        ld a, (light_years_attr)
        call fill_window
        jp print_lives
        ; End of function colour_something
        ; ---------------------------------------------------------------------------
light_years_attr:
        DB 0x45
aLightYear:
        DB "LIGHT YEAR"   ; 'S'
        DB 0xD3
        ; =============== S U B R O U T I N E =======================================
sub_A7A3:
        ld de, unk_5B40
        ld hl,  vidbuf+0x3E4
        ld b, 1
        jp print_BCD_number
        ; End of function sub_A7A3
        ; =============== S U B R O U T I N E =======================================
sub_A7AE:
        ld hl,  zxaram+0x299
        ld de, byte_A7CA
        ld bc, 0x603
loc_A7B7:
        push bc
        push hl
loc_A7B9:
        ld a, (de)
        inc de
        ld (hl), a
        inc hl
        djnz loc_A7B9
        pop hl
        ld a, 32
        call add_HL_A
        pop bc
        dec c
        jr nz, loc_A7B7
        ret
        ; End of function sub_A7AE
        ; ---------------------------------------------------------------------------
byte_A7CA:
        DB 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42, 0x47, 0x47, 0x47, 0x47, 0x42, 0x42, 0x42
        DB 0x42, 0x42, 0x42, 0x42
        ; =============== S U B R O U T I N E =======================================
reset_objs_wipe_flag:
        ld b, 56
        ld de, 32
        ld hl,  graphic_objs_tbl+7
loc_A7E4:
        res 5, (hl)
        add hl, de
        djnz loc_A7E4
        ret
        ; End of function reset_objs_wipe_flag
        ; ---------------------------------------------------------------------------
upd_sprite_jmp_tbl:
        DW no_update
        DW no_update
        DW upd_02   ; arch (near side)
        DW upd_03   ; arch (far side)
        DW no_update   ; menu
        DW no_update   ; menu
        DW no_update   ; menu
        DW no_update   ; panel
        DW no_update   ; panel
        DW no_update   ; panel
        DW no_update   ; panel
        DW upd_0B
        DW upd_0C   ; extra life
        DW upd_0D   ; wall
        DW upd_0E   ; wall
        DW upd_0F   ; wall
        DW upd_10_to_17   ; player (bottom half)
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_10_to_17   ;   "
        DW upd_18_to_1B   ; player (bottom half) facing front
        DW upd_18_to_1B   ;   "
        DW upd_18_to_1B   ; player (bottom half) facing side
        DW upd_18_to_1B   ;   "
        DW upd_1C   ; rhombus block fat bottom
        DW upd_1D   ; rhombus block fat top
        DW upd_1E   ; block
        DW upd_1F   ; block moving up and down
        DW upd_20_to_2B   ; player (top half)
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_20_to_2B   ;   "
        DW upd_2C   ; block fall on contact
        DW upd_2D   ; block collapse
        DW upd_2E   ; broken egg - killer
        DW upd_2F   ; block move up/down while player on
        DW upd_30_to_36_40   ; sparkles
        DW upd_30_to_36_40   ;  "
        DW upd_30_to_36_40   ;   "
        DW upd_30_to_36_40   ;   "
        DW upd_30_to_36_40   ;   "
        DW upd_30_to_36_40   ;   "
        DW upd_30_to_36_40   ;   "
        DW upd_37   ; sparkles
        DW upd_38_to_3E   ; sparkles
        DW upd_38_to_3E   ;   "
        DW upd_38_to_3E   ;   "
        DW upd_38_to_3E   ;   "
        DW upd_38_to_3E   ;   "
        DW upd_38_to_3E   ;   "
        DW upd_38_to_3E   ;   "
        DW upd_3F   ; sparkles
        DW upd_30_to_36_40   ; sparkles
        DW upd_41
        DW upd_42   ; block move east-west
        DW upd_43   ; block move north-south
        DW upd_44   ; block slide off north
        DW upd_45   ; block slide off east
        DW upd_46   ; block slide off south
        DW upd_47   ; block slide off west
        DW upd_48_4B   ; pyramid-killer
        DW upd_49   ; top of broken egg - killer
        DW upd_4A   ; cryonaught looking east/west
        DW upd_48_4B   ; tubes-killer
        DW upd_4C_4F   ; sparkles
        DW upd_4C_4F   ;   "
        DW upd_4C_4F   ;   "
        DW upd_4C_4F   ;   "
        DW upd_50
        DW upd_51_to_53
        DW upd_51_to_53
        DW upd_51_to_53
        DW no_update   ; panel
        DW upd_55_58_to_5B   ; oil
        DW upd_56_57   ; robot mouse moving circuit
        DW upd_56_57   ; robot mouse moving east-west
        DW upd_55_58_to_5B
        DW upd_55_58_to_5B
        DW upd_55_58_to_5B
        DW upd_55_58_to_5B
        DW upd_5C
        DW upd_5D
        DW upd_5E_5F   ; robot mouse moving north-south
        DW upd_5E_5F
        DW upd_60_to_63   ; cylinder
        DW upd_60_to_63   ; square
        DW upd_60_to_63   ; pyramid
        DW upd_60_to_63   ; semisphere
        DW upd_64_to_67   ; cylinder
        DW upd_64_to_67   ; square
        DW upd_64_to_67   ; pyramid
        DW upd_64_to_67   ; semisphere
        DW upd_68_to_6B   ; cylinder
        DW upd_68_to_6B   ; square
        DW upd_68_to_6B   ; pyramid
        DW upd_68_to_6B   ; semisphere
        DW upd_6C_to_6F   ; sparkles
        DW upd_6C_to_6F   ;   "
        DW upd_6C_to_6F   ;   "
        DW upd_6C_to_6F   ;   "
        DW upd_70_to_73   ; object dropoff for cylinder
        DW upd_70_to_73   ; object dropoff for square
        DW upd_70_to_73   ; object dropoff for pyramid
        DW upd_70_to_73   ; object dropoff for semi-sphere
        DW upd_74_to_77   ; clockwork mouse
        DW upd_74_to_77   ;   "
        DW upd_74_to_77   ;   "
        DW upd_74_to_77   ;   "
        DW upd_78_79   ; cylinder ???
        DW upd_78_79   ; cylinder ???
        DW upd_7A_7B   ; remote control arrow - west/north
        DW upd_7A_7B   ; remote control arrow - east/south
        DW upd_7C_to_7F   ; remote control robot
        DW upd_7C_to_7F   ;   "
        DW upd_7C_to_7F   ;   "
        DW upd_7C_to_7F   ;   "
        DW upd_80   ; remote control block
        DW upd_81   ; spikey domed - killer
        DW upd_82   ; land mine - killer
        ; ---------------------------------------------------------------------------
no_update:
        ret
        ; =============== S U B R O U T I N E =======================================
sub_A8F1:
        ld hl, 0
        ld a, r
        rla
        ret
        ; End of function sub_A8F1
        ; ---------------------------------------------------------------------------
        jp (hl)
        ; ---------------------------------------------------------------------------
upd_82:
        call upd_1E
        call set_both_deadly_flags
        bit 0, (ix+16)
        jr nz, loc_A921
        ld a, (byte_5B43)
        and a
        ret nz
        ld a, (seed_3)
        inc a
        and 3
        ret nz
        ld a, 1
        ld (byte_5B43), a
        ld (ix+16), a
        ld a, (ix+3)
        add a, 0x30   ; '0'
        ld (ix+17), a
loc_A921:
        bit 1, (ix+16)
        jr z, loc_A93D
        call dec_dZ_and_update_XYZ
        bit 2, (ix+12)
        jr z, loc_A937
        xor a
        ld (ix+16), a
        ld (byte_5B43), a
loc_A937:
        call audio_B63C
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_A93D:
        ld (ix+11), 3
        call dec_dZ_and_update_XYZ
        ld a, (ix+3)
        cp (ix+17)
        jr nc, loc_A954
        bit 2, (ix+12)
        jr nz, loc_A954
        jr loc_A937
        ; ---------------------------------------------------------------------------
loc_A954:
        set 1, (ix+16)
        jr loc_A937
        ; ---------------------------------------------------------------------------
upd_5D:
        ld a, (ix-5)
        add a, 0x10
        ld (ix+27), a
        ld a, (ix-16)
        ld (ix+16), a
        ld a, (ix-25)
        ld (ix+7), a
        jp upd_55_58_to_5B
        ; ---------------------------------------------------------------------------
upd_5C:
        ld a, (ix+17)
        cp 0x40   ; '@'
        jr c, loc_A991
        cp 0x80   ; ''
        jr nc, loc_A996
        ld a, (ix+27)
        cp 0x28   ; '('
        jr c, loc_A991
        sub 3
        ld (ix+27), a
loc_A988:
        call audio_B63F
        call set_wipe_and_draw_flags
loc_A98E:
        jp upd_55_58_to_5B
        ; ---------------------------------------------------------------------------
loc_A991:
        inc (ix+17)
        jr loc_A98E
        ; ---------------------------------------------------------------------------
loc_A996:
        ld a, (ix+27)
        cp 0x80   ; ''
        jr nc, loc_A9A8
        add a, 3
        ld (ix+27), a
        ld (ix+16), 0x47   ; 'G'
        jr loc_A988
        ; ---------------------------------------------------------------------------
loc_A9A8:
        ld de, obj_5C_tune
        call play_audio
        jp start_menu
        ; ---------------------------------------------------------------------------
upd_81:
        call adj_m4_m12
        ld a, (ix+9)
        or (ix+10)
        or (ix+11)
        jp z, set_both_deadly_flags
        ld (ix+0), 0x36   ; '6'
        jp set_deadly_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_7C_to_7F:
        call upd_1E
        ld hl, unk_5B42
        ld a, (hl)
        and 0x80   ; ''
        jr z, loc_A9FE
        ld a, (ix+16)
        and 0xC0   ; 'À'
        jr z, loc_A9F1
        bit 7, (ix+16)
        jr nz, loc_AA06
        ld a, (hl)
        and 0x3F   ; '?'
        jr nz, loc_AA15
        res 7, (hl)
        res 6, (ix+16)
        xor a
        ld (ix+9), a
        ld (ix+10), a
loc_A9F1:
        call dec_dZ_and_update_XYZ
        call is_obj_moving
        ret z
        call audio_B63C
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_A9FE:
        set 7, (hl)
        set 7, (ix+16)
        jr loc_A9F1
        ; ---------------------------------------------------------------------------
loc_AA06:
        ld a, (hl)
        and 0x7F   ; ''
        jr z, loc_A9F1
        ld a, (ix+16)
        and 0x3F   ; '?'
        or 0x40   ; '@'
        ld (ix+16), a
loc_AA15:
        ld a, (hl)
        ld (hl), 0x80   ; ''
        dec a
        rlca
        and 0x7E   ; '~'
        ld hl, byte_AA43
        call add_HL_A
        ld a, (hl)
        inc hl
        ld (ix+9), a
        ld a, (hl)
        dec hl
        ld (ix+10), a
        call sub_B18C
        ld a, (ix+9)
        or (ix+10)
        jr z, loc_AA3A
        call dec_dZ_and_update_XYZ
loc_AA3A:
        ld hl, byte_B6A9
        call audio_B690
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
byte_AA43:
        DB 0, 0, 0xFE, 0, 0, 2, 2, 0, 0, 0xFE
        ; ---------------------------------------------------------------------------
upd_80:
        call upd_1E
        ld a, (ix+11)
        and a
        ret z
        xor a
        ld (ix+11), a
        ld hl, unk_5B42
        ld a, (hl)
        and 0x80   ; ''
        or 1
        ld (hl), a
        ret
        ; ---------------------------------------------------------------------------
upd_7A_7B:
        call upd_1E
        ld a, (ix+11)
        and a
        ret z
        xor a
        ld (ix+11), a
        ld a, (ix+7)
        rlca
        and 0x80   ; ''
        ld c, a
        ld a, (ix+0)
        and 1
        or c
        rlca
        add a, 2
        ld c, a
        ld hl, unk_5B42
        ld a, (hl)
        and 0x80   ; ''
        or c
        ld (hl), a
        ret
        ; ---------------------------------------------------------------------------
upd_78_79:
        call adj_m4_m12
        ld bc, 0x101
        call sub_B165
        call dec_dZ_and_update_XYZ
        call sub_B185
        ld hl, 0xB6AD
        call audio_B690
        jp set_deadly_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_74_to_77:
        call adj_m6_m12
        call dec_dZ_and_update_XYZ
        ld a, (ix+9)
        or (ix+10)
        jr z, loc_AAC1
        ld a, (ix+12)
        and 3
        jr nz, loc_AAC1
        dec (ix+16)
        jr z, loc_AAC1
loc_AABB:
        call sub_B185
        jp set_deadly_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_AAC1:
        call toggle_FE_bit4_x32
        ld a, (seed_2+1)
        ld c, a
        ld a, (seed_3)
        xor c
        and 0xF
        ld (ix+16), a
        ld a, (ix+7)
        xor 0x40   ; '@'
        ld (ix+7), a
        ld a, (seed_3)
        and 1
        jr z, loc_AB0C
        bit 6, (ix+7)
        jr z, loc_AAEE
loc_AAE6:
        ld a, (ix+0)
        xor 2
        ld (ix+0), a
loc_AAEE:
        ld a, (seed_2)
        and 3
        add a, 2
        bit 1, (ix+0)
        jr nz, loc_AAFD
        neg
loc_AAFD:
        bit 6, (ix+7)
        jr nz, loc_AB14
        ld (ix+9), a
        ld (ix+10), 0
        jr loc_AABB
        ; ---------------------------------------------------------------------------
loc_AB0C:
        bit 6, (ix+7)
        jr z, loc_AAE6
        jr loc_AAEE
        ; ---------------------------------------------------------------------------
loc_AB14:
        neg
        ld (ix+10), a
        ld (ix+9), 0
        jr loc_AABB
        ; ---------------------------------------------------------------------------
        ld a, (ix+9)
        and a
        jp p, loc_AB28
        neg
loc_AB28:
        ld c, a
        ld a, (ix+10)
        and a
        jp p, loc_AB32
        neg
loc_AB32:
        cp c
        jr c, loc_AB4B
        ld a, (ix+9)
        and a
        jp p, loc_AB45
        res 1, (ix+0)
loc_AB40:
        res 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_AB45:
        set 1, (ix+0)
        jr loc_AB40
        ; ---------------------------------------------------------------------------
loc_AB4B:
        ld a, (ix+10)
        and a
        jp p, loc_AB5B
        set 1, (ix+0)
loc_AB56:
        set 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_AB5B:
        res 1, (ix+0)
        jr loc_AB56
        ; ---------------------------------------------------------------------------
upd_51_to_53:
        ld hl, 0x5B41
        ld a, (hl)
        and a
        jr z, loc_ABDA
        ld a, 0xE7   ; 'ç'
        call read_key
        jp nz, start_menu
        bit 0, (ix+17)
        jr nz, loc_AB91
        bit 7, (hl)
        jr nz, loc_ABDA
        ld a, (seed_3)
        cpl
        and 3
        jr nz, loc_ABDA
        push hl
        call sub_B619
        pop hl
        set 0, (ix+17)
        set 7, (hl)
        ld (ix+15), 6
loc_AB91:
        ld a, (ix+0)
        and 1
        jr z, loc_ABDD
        ld a, (ix+26)
        xor (ix+17)
        and 0x80   ; ''
        ld a, 8
        jr z, loc_ABA6
        neg
loc_ABA6:
        add a, (ix+26)
        ld (ix+26), a
loc_ABAC:
        dec (ix+15)
        jr nz, loc_ABD7
        ld (ix+15), 6
        ld a, (ix+17)
        xor 0x80   ; ''
        ld (ix+17), a
        and 0x80   ; ''
        jr z, loc_ABC6
        call sub_B676
        jr loc_ABD7
        ; ---------------------------------------------------------------------------
loc_ABC6:
        res 0, (ix+17)
        res 7, (hl)
        inc (hl)
        ld a, (hl)
        and 0x7F   ; ''
        cp 0x10
        jr nz, loc_ABD7
        jp start_menu
        ; ---------------------------------------------------------------------------
loc_ABD7:
        call set_wipe_and_draw_flags
loc_ABDA:
        jp upd_55_58_to_5B
        ; ---------------------------------------------------------------------------
loc_ABDD:
        ld a, (ix+27)
        add a, 0x20   ; ' '
        xor (ix+17)
        and 0x80   ; ''
        ld a, 4
        jr z, loc_ABED
        neg
loc_ABED:
        add a, (ix+27)
        ld (ix+27), a
        jr loc_ABAC
        ; ---------------------------------------------------------------------------
upd_50:
        ld a, (seed_2)
        ld c, a
        and 7
        jr nz, upd_55_58_to_5B
        bit 3, c
        jr z, loc_AC03
        add a, 0x46   ; 'F'
loc_AC03:
        ld (ix+16), a
        call toggle_FE_bit4_x16
        inc (ix+17)
        ld a, (ix+17)
        cp 0x10
        jr nz, upd_55_58_to_5B
        ld a, 1
        ld (byte_5B41), a
        ld (ix+0), a
        call upd_55_58_to_5B
        jp set_wipe_and_draw_flags
        ; =============== S U B R O U T I N E =======================================
upd_55_58_to_5B:
        ld a, (ix+24)
        or (ix+25)
        ret z
        ld l, (ix+26)
        ld b, (ix+24)
        ld a, l
        and 7
        jr z, loc_AC34
        inc b
loc_AC34:
        ld h, (ix+27)
        ld a, h
        rrca
        rrca
        rrca
        and 0x1F
        ld c, a
        ld a, (ix+25)
        dec a
        add a, h
        rrca
        rrca
        rrca
        and 0x1F
        sub c
        inc a
        ld c, a
        call calc_attrib_addr
        ex de, hl
        ld a, (ix+16)
        ld de, 0x20   ; ' '
loc_AC55:
        push bc
        push hl
        ld c, a
loc_AC58:
        ld a, (hl)
        cp 0x44   ; 'D'
        jr z, loc_AC5E
        ld (hl), c
loc_AC5E:
        inc l
        djnz loc_AC58
        ld a, c
        pop hl
        pop bc
        and a
        sbc hl, de
        dec c
        jr nz, loc_AC55
        ret
        ; End of function upd_55_58_to_5B
        ; very different to Knight Lore
        ; =============== S U B R O U T I N E =======================================
something_with_special_objs:
        ld de, unk_5B3C
        ld b, 4
        call zero_DE
        ld hl, location_tbl
loc_AC76:
        ld c, (hl)
        inc hl
        ld b, (hl)   ; entry size
loc_AC79:
        ld a, (hl)
        inc hl
        inc a   ; end of bg blocks?
        jr z, check_1st_fg_block   ; yes, skip
        djnz loc_AC79
loc_AC80:
        ld bc, block_type_tbl
        and a
        sbc hl, bc   ; done?
        ret nc   ; yes, exit
        add hl, bc   ; next entry
        jr loc_AC76
        ; ---------------------------------------------------------------------------
check_1st_fg_block:
        dec b
        ld a, (hl)   ; fg object
        and 0xF8   ; 'ø'
        cp 0xA8   ; '¨'
        jr z, loc_AC9C
        cp 0xB0   ; '°'
        jr z, loc_AC9C
loc_AC96:
        ld a, b
        call add_HL_A   ; next entry
        jr loc_AC80
        ; ---------------------------------------------------------------------------
loc_AC9C:
        ld iy, special_objs_tbl
loc_ACA0:
        ld a, (iy+8)
        cp c   ; same as current screen?
        jr z, loc_ACC2   ; yes, go
loc_ACA6:
        ld de, 9
        add iy, de   ; next entry
        push hl
        push iy
        pop hl
        ld de, sprite_tbl   ; end of table
        and a
        sbc hl, de   ; done?
        push hl
        pop iy
        pop hl
        jr nc, loc_ACD6   ; no, skip
        ld de, sprite_tbl
        add iy, de   ; fix iy
        jr loc_ACA0   ; next special object
        ; ---------------------------------------------------------------------------
loc_ACC2:
        ld a, (iy+0)
        sub 0x64   ; 'd'
        cp 4
        jr nc, loc_ACA6
        ld a, (unk_5B3E)
        add a, 1
        daa
        ld (unk_5B3E), a
        jr loc_AC96
        ; ---------------------------------------------------------------------------
loc_ACD6:
        ld de, unk_5B3D
        ex de, hl
        ld a, (de)
        and 7
        inc a
        add a, (hl)
        daa
        ld (hl), a
        dec hl
        ld a, (hl)
        adc a, 0
        daa
        ld (hl), a
        ex de, hl
        ld a, (hl)
        and 7
        add a, 2
        ld e, a
        call add_HL_A
        ld a, e
        neg
        add a, b
        ld b, a
        jr z, loc_AD07
        ld a, (hl)
        and 0xF8   ; 'ø'
        cp 0xA8   ; '¨'
        jr z, loc_ACD6
        cp 0xB0   ; '°'
        jr z, loc_ACD6
        ld a, b
        call add_HL_A
loc_AD07:
        ld a, (unk_5B3F)
        add a, 1
        daa
        ld (unk_5B3F), a
        jp loc_AC80
        ; End of function something_with_special_objs
        ; ---------------------------------------------------------------------------
upd_49:
        call set_both_deadly_flags
        call sub_BF47
        ld a, (byte_5B3B)
        and a
        ret nz
        bit 2, (ix+13)
        jr nz, loc_AD37
        ld hl, 0x5B3A
        ld a, (hl)
        and a
        ret nz
        ld a, (seed_3)
        cp 0x10
        ret nc
        set 2, (ix+13)
        ld (hl), 1
        ret
        ; ---------------------------------------------------------------------------
loc_AD37:
        call dec_dZ_and_update_XYZ
        call sub_AD54
        bit 2, (ix+12)
        jr nz, loc_AD49
        call audio_B63C
loc_AD46:
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_AD49:
        res 2, (ix+13)
        ld hl, 0x5B3A
        ld (hl), 0
        jr loc_AD46
        ; =============== S U B R O U T I N E =======================================
sub_AD54:
        ld a, (ix+12)
        and 4
        ld c, a
        ret z
        ld a, (ix+15)
        cp c
        ld (ix+15), c
        call nz, sub_B676
        ret
        ; End of function sub_AD54
        ; =============== S U B R O U T I N E =======================================
sub_AD66:
        call sub_ADC9
        call sub_ADE5
        ld hl,  vidbuf+0x2FA
        ld de, unk_5B36
        ld b, 4
        push hl
        ld hl, ascii_chars
        ld (gfxbase_8x8), hl
        pop hl
loc_AD7C:
        ld a, (de)
        inc de
        call sub_ADB0
        djnz loc_AD7C
        ld hl,  vidbuf+0x21D
        ld b, 8
        ld de, 0x20   ; ' '
loc_AD8B:
        ld a, (hl)
        cpl
        ld (hl), a
        add hl, de
        djnz loc_AD8B
        ld bc, 0x10D0
        call BC_to_Attr_In_DE
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld bc, 0x804
        call blit_to_screen
        ld hl, 0x5B36
        ld b, 4
        xor a
loc_ADA8:
        or (hl)
        inc hl
        djnz loc_ADA8
        jp z, game_over
        ret
        ; End of function sub_AD66
        ; =============== S U B R O U T I N E =======================================
sub_ADB0:
        push bc
        push de
        push hl
        ld l, a
        srl l
        srl l
        srl l
        srl l   ; L=A/16
        ld h, 0
        add hl, hl
        add hl, hl
        add hl, hl   ; HL=L*8=(A/16)*8=A/2???
        and 0xF
        call add_HL_A   ; HL=A*3/2???
        jp loc_BBFA
        ; End of function sub_ADB0
        ; =============== S U B R O U T I N E =======================================
sub_ADC9:
        ld hl, unk_5B39
        ld b, 4
        ld a, (hl)
        and 7
        ret nz
loc_ADD2:
        ld a, (hl)
        ld c, a
        and 0xF0   ; 'ð'
        jr z, loc_ADDE
        sub 0x10
        or 7
        ld (hl), a
        ret
        ; ---------------------------------------------------------------------------
loc_ADDE:
        ld a, 0x97   ; ''
        ld (hl), a
        dec hl
        djnz loc_ADD2
        ret
        ; End of function sub_ADC9
        ; =============== S U B R O U T I N E =======================================
sub_ADE5:
        ld hl, unk_5B39
        ld b, 4
loc_ADEA:
        ld a, (hl)
        and 7
        ret z
        dec (hl)
        dec hl
        djnz loc_ADEA
        ret
        ; End of function sub_ADE5
        ; =============== S U B R O U T I N E =======================================
set_wipe_and_draw_IY:
        push iy
        push ix
        push iy
        pop ix
        call set_wipe_and_draw_flags
        pop ix
        pop iy
        ret
        ; End of function set_wipe_and_draw_IY
        ; =============== S U B R O U T I N E =======================================
sub_AE03:
        ld iy, 0x5C08
        ld de, 0x20   ; ' '
        ld b, 0x34   ; '4'
loc_AE0C:
        ld a, (iy+0)
        sub l
        cp h
        ret c
        add iy, de
        djnz loc_AE0C
        ret
        ; End of function sub_AE03
        ; ---------------------------------------------------------------------------
upd_68_to_6B:
        call adj_m5_m12
        call sub_AE81
        jp nz, loc_B3BB
        ld a, (ix-29)
        add a, 0xD
        ld (ix+3), a
        dec (ix+16)
        ret nz
        set 2, (ix+0)
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_6C_to_6F:
        call adj_m5_m12
        call sub_AE81
        jp nz, loc_B3BB
        ld a, (ix-29)
        add a, 0xD
        ld (ix+3), a
        call sub_B18C
        and 3
        ld c, a
        ld a, (ix-32)
        and 3
        cp c
        jr nz, loc_AE5A
        res 2, (ix+0)
        ld (ix+16), 2
loc_AE5A:
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_64_to_67:
        call adj_m5_m12
        xor a
        ld (ix+9), a
        ld (ix+10), a
        ret
        ; ---------------------------------------------------------------------------
upd_70_to_73:
        call adj_m7_m16
        call sub_AE81
        ret nz
        ld a, (ix+32)
        and a
        ret nz
        ld a, (ix+0)
        and 3
        or 0x6C   ; 'l'
        ld (ix+32), a
        jp calc_pixel_XY_IY
        ; =============== S U B R O U T I N E =======================================
sub_AE81:
        ld a, (special_objs_here)
        ld c, a
        ld a, (byte_5BE8)
        or c
        ret
        ; End of function sub_AE81
        ; =============== S U B R O U T I N E =======================================
calc_pixel_XY_IY:
        push ix
        push iy
        pop ix
        call calc_pixel_XY
        pop ix
        ret
        ; End of function calc_pixel_XY_IY
        ; ---------------------------------------------------------------------------
upd_4A:
        jp adj_m4_m12
        ; =============== S U B R O U T I N E =======================================
find_special_objs_here:
        ld de, special_objs_here
        exx
        ld iy, special_objs_tbl
        ld b, (ix+8)
loc_AEA4:
        ld a, (iy+0)
        and a
        jr z, loc_AEE6
        ld a, (iy+8)
        cp b
        jr nz, loc_AEE6
        push iy
        exx
        pop hl
        push hl
        ld a, (hl)
        inc hl
        ld (de), a
        inc de
        inc hl
        inc hl
        inc hl
        inc hl
        ld bc, 3
        ldir
        ex de, hl
        ld (hl), 5
        inc hl
        ld (hl), 5
        inc hl
        ld (hl), 0xC
        inc hl
        ld (hl), 0x14
        inc hl
        ex de, hl
        ld a, (hl)
        inc hl
        ld (de), a
        inc de
        ld b, 7
        call zero_DE
        pop bc
        ld a, c
        ld (de), a
        inc de
        ld a, b
        ld (de), a
        inc de
        ld b, 0xE
        call zero_DE
        exx
loc_AEE6:
        ld de, 9
        add iy, de
        push iy
        pop hl
        ld de, 0x7827
        and a
        sbc hl, de
        jr c, loc_AEA4
        exx
loc_AEF7:
        ld hl, 0x5C08
        and a
        sbc hl, de
        ret z
        ld b, 0x20   ; ' '
        call zero_DE
        jr loc_AEF7
        ; End of function find_special_objs_here
        ; =============== S U B R O U T I N E =======================================
update_special_objs:
        ld iy, special_objs_here
loc_AF09:
        ld a, (iy+0)
        sub 0x60   ; '`'
        cp 8
        jr nc, loc_AF2E
        ld e, (iy+16)
        ld d, (iy+17)
        ld a, (iy+0)
        ld (de), a
        inc de
        inc de
        inc de
        inc de
        inc de
        push iy
        pop hl
        inc hl
        ld bc, 3
        ldir
        ld a, (iy+8)
        ld (de), a
loc_AF2E:
        ld bc, 32
        add iy, bc
        push iy
        pop hl
        ld bc, other_objs_here
        and a
        sbc hl, bc
        jr c, loc_AF09
        ret
        ; End of function update_special_objs
        ; almost the same as Knight Lore
        ; =============== S U B R O U T I N E =======================================
init_special_objects:
        ld hl, special_objs_tbl
        ld a, (seed_1)
        ld e, a
        ld a, r
        add a, e
        ld e, a
        ld a, (seed_3)
        ld d, a
loc_AF4E:
        dec d
        ld a, d
        and 0xF
        jr z, loc_AF75
        ld a, e
        and 3
        or 0x60   ; '`'
loc_AF59:
        ld (hl), a
        inc hl
        inc e
        push de
        ex de, hl
        ld hl, 4
        add hl, de
        ex de, hl
        ld bc, 4
        ldir
        ex de, hl
        push hl
        ld bc, sprite_tbl   ; end of special objs?
        and a
        sbc hl, bc
        pop hl
        pop de
        jr c, loc_AF4E   ; no, loop
        ret
        ; ---------------------------------------------------------------------------
loc_AF75:
        ld a, 0xC
        jr loc_AF59
        ; End of function init_special_objects
        ; ---------------------------------------------------------------------------
upd_60_to_63:
        call adj_m5_m12
        ld hl, 0x470
        call sub_AE03
        jr nc, loc_AFD0
        ld a, (iy+0)
        and 3
        ld c, a
        ld a, (ix+0)
        and 3
        cp c
        jr nz, loc_AFD0
        ld a, (ix+1)
        sub (iy+1)
        jr z, loc_AFA1
        ld a, 1
        jp m, loc_AFA1
        neg
loc_AFA1:
        ld (ix+9), a
        ld a, (ix+2)
        sub (iy+2)
        jr z, loc_AFB3
        ld a, 1
        jp m, loc_AFB3
        neg
loc_AFB3:
        ld (ix+10), a
        ld a, (ix+1)
        cp (iy+1)
        jr nz, loc_AFD0
        ld a, (ix+2)
        cp (iy+2)
        jr nz, loc_AFD0
        ld a, (iy+3)
        add a, 0xC
        cp (ix+3)
        jr z, loc_AFE7
loc_AFD0:
        call dec_dZ_and_update_XYZ
        bit 0, (ix+13)
        jr nz, loc_AFDD
        call is_obj_moving
        ret z
loc_AFDD:
        res 0, (ix+13)
        call clear_dX_dY
        jp audio_set_wipe_draw_flags
        ; ---------------------------------------------------------------------------
loc_AFE7:
        ld a, (ix+0)
        xor (iy+0)
        and 3
        jr z, loc_AFF8
        ld (ix+0), 0x40   ; '@'
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_AFF8:
        ld a, (ix+0)
        or 4
        ld (ix+0), a
        call audio_set_wipe_draw_flags
        ld d, 0x10
loc_B005:
        ld hl, zxaram
        ld bc, 0x300
loc_B00B:
        ld a, (hl)
        and 0xF8   ; 'ø'
        ld e, a
        ld a, (hl)
        inc a
        and 7
        or e
        ld (hl), a
        inc hl
        dec bc
        ld a, b
        or c
        jr nz, loc_B00B
        call sub_B5EE
        ld bc, 0x200
loc_B021:
        dec bc
        ld a, b
        or c
        jr nz, loc_B021
        dec d
        jr nz, loc_B005
        ld hl, (word_5B34)
        ld a, (hl)
        or 7
        ld (hl), a
        and 7
        ld (curr_room_attrib), a
        call colour_something
        ld hl, 0x5B40
        ld a, (hl)
        add a, 1
        daa
        ld (hl), a
        cp 0x24   ; '$'
        jr nz, loc_B04C
        ld a, 1
        ld (byte_5B23), a
        jp game_over
        ; ---------------------------------------------------------------------------
loc_B04C:
        call sub_A7A3
        ld bc, 0x1820
        jp sub_BF2F
        ; ---------------------------------------------------------------------------
upd_0B:
        call adj_m6_m12
        call sub_B1E5
        ld a, (ix-23)   ; dX?
        or (ix-22)   ; dY?
        or (ix-21)   ; dZ?
        ret z
        call loc_B6C0
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_5E_5F:
        call adj_m6_m12
        call sub_B1FA
        ld a, (ix+9)
        or (ix+10)
        jr z, loc_B08A
        call dec_dZ_and_update_XYZ
        ld a, (ix+11)
        and a
        call nz, audio_B63C
        ld a, (ix+12)
        and 3
        jr z, loc_B0A2
loc_B08A:
        call sub_B619
        ld a, (seed_3)
        and 1
        jr z, loc_B0A8
        call sub_B0DD
loc_B097:
        call sub_B0E7
        sla (ix+9)
        sla (ix+10)
loc_B0A2:
        call sub_B20B
        jp set_deadly_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_B0A8:
        call sub_B0AD
        jr loc_B097
        ; =============== S U B R O U T I N E =======================================
sub_B0AD:
        bit 0, (ix+0)
        jr nz, loc_B0C2
        bit 6, (ix+7)
        jr nz, loc_B0CE
        set 0, (ix+0)
loc_B0BD:
        set 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_B0C2:
        bit 6, (ix+7)
        jr nz, loc_B0D7
        res 0, (ix+0)
        jr loc_B0BD
        ; ---------------------------------------------------------------------------
loc_B0CE:
        res 0, (ix+0)
loc_B0D2:
        res 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_B0D7:
        set 0, (ix+0)
        jr loc_B0D2
        ; End of function sub_B0AD
        ; =============== S U B R O U T I N E =======================================
sub_B0DD:
        ld a, (ix+0)
        xor 1
        ld (ix+0), a
        jr sub_B0AD
        ; End of function sub_B0DD
        ; =============== S U B R O U T I N E =======================================
sub_B0E7:
        ld a, (ix+7)
        rlca
        rlca
        rlca
        and 2
        ld b, a
        ld a, (ix+0)
        and 1
        or b
        sla a
        ld hl, 0xB108
        call add_HL_A
        ld a, (hl)
        inc hl
        ld (ix+9), a
        ld a, (hl)
        ld (ix+10), a
        ret
        ; End of function sub_B0E7
        ; ---------------------------------------------------------------------------
        DB 0xFF, 0, 1, 0, 0, 1, 0, 0xFF
        ; ---------------------------------------------------------------------------
upd_56_57:
        call adj_m6_m12
        call sub_B1FA
loc_B116:
        ld a, (ix+9)
        and a
        jr z, loc_B13C
        ld (ix+16), a
        call dec_dZ_and_update_XYZ
        bit 0, (ix+12)
        jr z, loc_B136
        ld a, (ix+16)
        neg
        ld (ix+9), a
loc_B130:
        call sub_B619
        call sub_B1AE
loc_B136:
        call sub_B20B
        jp set_deadly_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_B13C:
        ld a, (ix+10)
        and a
        jr z, loc_B158
        ld (ix+16), a
        call dec_dZ_and_update_XYZ
        bit 1, (ix+12)
        jr z, loc_B136
        ld a, (ix+16)
        neg
        ld (ix+10), a
        jr loc_B130
        ; ---------------------------------------------------------------------------
loc_B158:
        call sub_B0E7
        sla (ix+9)
        sla (ix+10)
        jr loc_B116
        ; =============== S U B R O U T I N E =======================================
sub_B165:
        ld hl,  graphic_objs_tbl+1
        ld a, (ix+1)   ; Y
        sub (hl)   ; sub X
        inc hl
        ld a, c
        jp m, loc_B173
        neg
loc_B173:
        ld (ix+9), a
        ld a, (ix+2)
        sub (hl)
        inc hl
        ld a, b
        jp m, loc_B181
        neg
loc_B181:
        ld (ix+10), a
        ret
        ; End of function sub_B165
        ; =============== S U B R O U T I N E =======================================
sub_B185:
        ld a, (ix+0)
        xor 1
        jr loc_B198
        ; End of function sub_B185
        ; =============== S U B R O U T I N E =======================================
sub_B18C:
        ld a, (ix+0)
        ld c, a
        and 0xFC   ; 'ü'
        ld b, a
        ld a, c
        inc a
        and 3
        or b
loc_B198:
        ld (ix+0), a
        ret
        ; End of function sub_B18C
        ; ---------------------------------------------------------------------------
upd_4C_4F:
        call adj_m4_m12
        ld bc, 0x404
        call sub_B165
        call dec_dZ_and_update_XYZ
        call sub_B18C
        jp audio_set_wipe_draw_flags
        ; =============== S U B R O U T I N E =======================================
sub_B1AE:
        ld a, (ix+9)
        or (ix+10)
        ret z
        ld a, (ix+9)
        cp (ix+10)
        jr c, loc_B1D0
        bit 7, a
        jr nz, loc_B1CA
        set 0, (ix+0)
loc_B1C5:
        res 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_B1CA:
        res 0, (ix+0)
        jr loc_B1C5
        ; ---------------------------------------------------------------------------
loc_B1D0:
        bit 7, (ix+10)
        jr z, loc_B1DF
        set 0, (ix+0)
loc_B1DA:
        set 6, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_B1DF:
        res 0, (ix+0)
        jr loc_B1DA
        ; End of function sub_B1AE
        ; =============== S U B R O U T I N E =======================================
sub_B1E5:
        ld a, (ix-31)
        ld (ix+1), a   ; X
        ld a, (ix-30)
        ld (ix+2), a   ; Y
        ld a, (ix-29)
        sub 12
        ld (ix+3), a   ; Z
        ret
        ; End of function sub_B1E5
        ; =============== S U B R O U T I N E =======================================
sub_B1FA:
        ld a, (ix+3)
        sub 12
        ld (ix+3), a
        sla (ix+6)
        set 1, (ix+39)
        ret
        ; End of function sub_B1FA
        ; =============== S U B R O U T I N E =======================================
sub_B20B:
        ld a, (ix+3)
        add a, 12
        ld (ix+3), a
        srl (ix+6)
        res 1, (ix+39)
        ret
        ; End of function sub_B20B
        ; ---------------------------------------------------------------------------
upd_43:
        call audio_B64F
        ld hl, 0x20A
        jr loc_B22A
        ; ---------------------------------------------------------------------------
upd_42:
        call audio_B64A
        ld hl, 0x109
loc_B22A:
        ld a, h
        ld (loc_B249+2), a
        ld a, l
        ld (loc_B25A+2), a
        call upd_1E
        push ix
        pop bc
        ld a, c
        rrca
        and 0x10
        ld c, a
        ld a, (seed_2)
        add a, c
        bit 4, a
        jr z, loc_B246
        cpl
loc_B246:
        and 0xF
        ld c, a
loc_B249:
        ld a, (ix+1)
        add a, 8
        and 0xF
        cp c
        jp z, set_wipe_and_draw_flags
        ld a, 1
        jr c, loc_B25A
        neg
loc_B25A:
        ld (ix+9), a
        ld (ix+11), 1
        call dec_dZ_and_update_XYZ
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_44:
        ld (ix+10), 2
loc_B26B:
        call upd_1E
        ld a, (ix+11)
        and a
        call nz, toggle_FE_bit4_x32
        xor a
        ld (ix+11), a
        ret
        ; ---------------------------------------------------------------------------
upd_45:
        ld (ix+9), 2
        jr loc_B26B
        ; ---------------------------------------------------------------------------
upd_46:
        ld (ix+10), 0xFE   ; 'þ'
        jr loc_B26B
        ; ---------------------------------------------------------------------------
upd_47:
        ld (ix+9), 0xFE   ; 'þ'
        jr loc_B26B
        ; ---------------------------------------------------------------------------
upd_2D:
        call upd_1E
        bit 3, (ix+13)
        res 3, (ix+13)
        ret z
        ld (ix+0), 0x40   ; '@'
        jp upd_30_to_36_40
        ; ---------------------------------------------------------------------------
upd_48_4B:
        call upd_1E
        jr set_both_deadly_flags
        ; ---------------------------------------------------------------------------
upd_2E:
        call adj_m4_m12
        ; =============== S U B R O U T I N E =======================================
set_both_deadly_flags:
        ld a, (ix+13)   ; flags13
        or 0xA0   ; ' '
        ld (ix+13), a
        ret
        ; End of function set_both_deadly_flags
        ; ---------------------------------------------------------------------------
set_deadly_wipe_and_draw_flags:
        call set_both_deadly_flags
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_2C:
        call upd_1E
        bit 3, (ix+13)
        res 3, (ix+13)
        ret z
        ld (ix+11), 0   ; dZ=0
        call dec_dZ_and_update_XYZ
        ld (ix+11), 0   ; dZ=0
        bit 2, (ix+12)
        jr nz, loc_B2D6
        call audio_B63C
loc_B2D6:
        jp set_wipe_and_draw_flags
        ; =============== S U B R O U T I N E =======================================
save_XYZ:
        ld hl, tmp_XYZ
        ld a, (ix+1)   ; X
        ld (hl), a
        inc hl
        ld a, (ix+2)   ; Y
        ld (hl), a
        inc hl
        ld a, (ix+3)   ; Z
        ld (hl), a
        ret
        ; End of function save_XYZ
        ; compare object X,Y,Z with tmp copies
        ; - returns Z=same, NZ=not
        ; =============== S U B R O U T I N E =======================================
cmp_tmp_XYZ:
        ld hl, tmp_XYZ
        ld a, (ix+1)   ; X
        cp (hl)   ; same as tmp?
        ret nz   ; no, exit
        inc hl
        ld a, (ix+2)   ; Y
        cp (hl)   ; same as tmp?
        ret nz   ; no, exit
        inc hl
        ld a, (ix+3)   ; Z
        cp (hl)   ; same as tmp?
        ret
        ; End of function cmp_tmp_XYZ
        ; ---------------------------------------------------------------------------
upd_1C:
        call upd_1E
loc_B302:
        call save_XYZ
        call dec_dZ_and_update_XYZ
        call is_obj_moving
        jr nz, loc_B314   ; yes, skip
        call cmp_tmp_XYZ   ; has it moved?
        ret z   ; no, exit
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_B314:
        call clear_dX_dY
        jp audio_set_wipe_draw_flags
        ; ---------------------------------------------------------------------------
upd_1D:
        call adj_m6_m16
        jr loc_B302
        ; ---------------------------------------------------------------------------
upd_2F:
        call upd_1E
        ld a, (byte_5B25)
        and a
        jr nz, loc_B330
        ld a, (ix+3)
        add a, 0x30   ; '0'
        ld (byte_5B25), a
loc_B330:
        bit 3, (ix+13)
        res 3, (ix+13)
        jr nz, loc_B34E
        bit 2, (ix+12)
        ret z
upd_1F:
        call upd_1E
        ld a, (byte_5B25)
        and a
        jr nz, loc_B34E
        ld a, (ix+3)
        ld (byte_5B25), a
loc_B34E:
        call audio_B63C
        xor a
        ld (ix+9), a
        ld (ix+10), a
        bit 2, (ix+13)
        jr nz, loc_B371
        ld (ix+11), a
        call dec_dZ_and_update_XYZ
        bit 2, (ix+12)
        jr z, loc_B36E
        set 2, (ix+13)
loc_B36E:
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_B371:
        ld (ix+11), 3
        call dec_dZ_and_update_XYZ
        bit 2, (ix+12)
        jr z, loc_B38C
        ld (ix+11), 4
        xor a
        ld (ix+9), a
        ld (ix+10), a
        call dec_dZ_and_update_XYZ
loc_B38C:
        ld a, (byte_5B25)
        cp (ix+3)
        jr nc, loc_B36E
        res 2, (ix+13)
        jr loc_B36E
        ; ---------------------------------------------------------------------------
loc_B39A:
        ld (ix+0), 0x30   ; '0'
        set 1, (ix+7)
        jr loc_B3AA
        ; ---------------------------------------------------------------------------
upd_30_to_36_40:
        call adj_m4_m12
        inc (ix+0)
loc_B3AA:
        call sub_B5EE
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_41:
        ld l, (ix+16)
        ld h, (ix+17)
        ld (hl), 0
upd_37:
        call adj_m4_m12
loc_B3BB:
        ld (ix+0), 1
        ; =============== S U B R O U T I N E =======================================
audio_set_wipe_draw_flags:
        call audio_B654
        jp set_wipe_and_draw_flags
        ; End of function audio_set_wipe_draw_flags
        ; ---------------------------------------------------------------------------
start_game_tune:
        DB 0x25, 0x28, 0x2C, 0x25, 0x2A, 0x2D, 0x2C, 0x2A
        DB 0x28, 0x2C, 0x2A, 0x28, 0x27, 0x2A, 0x28, 0x27
        DB 0x65, 0xFF
obj_5C_tune:
        DB 0x25, 0x28, 0x2C, 0x25, 0x2A, 0x2D, 0x2C, 0x2A
        DB 0x28, 0x2C, 0x2A, 0x28, 0x27, 0x2A, 0x28, 0x27
        DB 0x25, 0x28, 0x2C, 0x25, 0x2A, 0x2D, 0x2C, 0x2A
        DB 0x28, 0x25, 0x27, 0x2C, 0x28, 0x25, 0x65, 0xFF
game_over_tune:
        DB 0x25, 0x29, 0x2C, 0x29, 0x24, 0x29, 0x2C, 0x29
        DB 0x22, 0x27, 0x2A, 0x27, 0x21, 0x27, 0x2A, 0x27
        DB 0x20, 0x25, 0x29, 0x25, 0x1F, 0x25, 0x29, 0x25
        DB 0x1E, 0x24, 0x27, 0x24, 0x20, 0x24, 0x27, 0x24
        DB 0x25, 0x29, 0x2C, 0x29, 0x24, 0x29, 0x2C, 0x29
        DB 0x22, 0x27, 0x2A, 0x27, 0x21, 0x27, 0x2A, 0x27
        DB 0x20, 0x25, 0x29, 0x25, 0x1F, 0x25, 0x29, 0x25
        DB 0x1E, 0x24, 0x27, 0x24, 0x25, 0x29, 0x65, 0xFF
game_complete_tune:
        DB 0x1B, 0x1D, 0x1E, 0x1B, 0x1D, 0x1E, 0x20, 0x1D
        DB 0x1E, 0x20, 0x22, 0x1E, 0x1D, 0x1E, 0x20, 0x1D
        DB 0x1B, 0x1D, 0x1E, 0x1B, 0x1A, 0x1B, 0x1D, 0x1A
        DB 0x9B, 0xFF
menu_tune:
        DB 0x19, 0x25, 0x19, 0x25, 0x19, 0x19, 0x25, 0x19
        DB 0x25, 0x19, 0x19, 0x25, 0x19, 0x25, 0x19, 0x1B
        DB 0x1C, 0x28, 0x1C, 0x28, 0x1C, 0x28, 0x1C, 0x28
        DB 0x1B, 0x27, 0x1B, 0x27, 0x17, 0x23, 0x17, 0x23
        DB 0x19, 0x25, 0x19, 0x25, 0x19, 0x19, 0x25, 0x19
        DB 0x25, 0x19, 0x19, 0x25, 0x19, 0x25, 0x19, 0x1B
        DB 0x1C, 0x2F, 0x1C, 0x2F, 0x1C, 0x2F, 0x1C, 0x2F
        DB 0x1B, 0x2A, 0x1B, 0x2A, 0x17, 0x2A, 0x17, 0x2A
        DB 0x19, 0x2C, 0x19, 0x2C, 0x19, 0x19, 0x2C, 0x19
        DB 0x2C, 0x19, 0x19, 0x2C, 0x19, 0x2C, 0x19, 0xFF
        ; =============== S U B R O U T I N E =======================================
play_audio_wait_key:
        ld hl, audio_played
        ld a, (hl)
        and a
        ret nz
        set 0, (hl)
        ; End of function play_audio_wait_key
        ; =============== S U B R O U T I N E =======================================
play_audio_until_keypress:
        xor a
        call read_key
        jr z, loc_B4B0
        ret
        ; ---------------------------------------------------------------------------
loc_B4B0:
        ld a, (de)
        cp 0xFF
        jr z, end_audio
        call sub_B4C5
        jr play_audio_until_keypress
        ; End of function play_audio_until_keypress
        ; =============== S U B R O U T I N E =======================================
play_audio:
        ld a, (de)
        cp 0xFF
        jr z, end_audio
        call sub_B4C5
        jr play_audio
        ; ---------------------------------------------------------------------------
end_audio:
        ret
        ; End of function play_audio
        ; =============== S U B R O U T I N E =======================================
sub_B4C5:
        and 0x3F   ; '?'
        jr z, loc_B507
        ld l, a
        ld h, 0
        add hl, hl
        call add_HL_A
        ld bc, freq_tbl
        add hl, bc
        ld b, (hl)
        inc hl
        ld c, (hl)
        inc hl
        ld l, (hl)
        ld h, 0
        ld a, (de)
        rlca
        rlca
        and 3
        inc a
        push de
        ld e, l
        ld d, h
loc_B4E4:
        dec a
        jr z, loc_B4EA
        add hl, de
        jr loc_B4E4
        ; ---------------------------------------------------------------------------
loc_B4EA:
        pop de
loc_B4EB:
        push bc
        xor a
        out (0xFE), a
loc_B4EF:
        djnz loc_B4EF
        dec c
        jr nz, loc_B4EF
        pop bc
        push bc
        ld a, 0x10
        out (0xFE), a
loc_B4FA:
        djnz loc_B4FA
        dec c
        jr nz, loc_B4FA
        pop bc
        dec hl
        ld a, h
        or l
        jr nz, loc_B4EB
        inc de
        ret
        ; ---------------------------------------------------------------------------
loc_B507:
        ld a, (de)
        inc de
        rlca
        rlca
        and 3
        inc a
        ld l, a
        ld bc, 0x430B
loc_B512:
        push bc
loc_B513:
        dec bc
        ld a, b
        or c
        jr nz, loc_B513
        pop bc
        dec l
        jr nz, loc_B512
        ret
        ; End of function sub_B4C5
        ; ---------------------------------------------------------------------------
freq_tbl:
        DB 0, 0, 0
        DB 0xF4, 0xA, 8
        DB 0x65, 0xA, 9
        DB 0xDE, 9, 9
        DB 0x5E, 9, 0xA
        DB 0xE7, 8, 0xA
        DB 0x75, 8, 0xB
        DB 0xA, 8, 0xC
        DB 0xA5, 7, 0xC
        DB 0x45, 7, 0xD
        DB 0xEB, 6, 0xE
        DB 0x96, 6, 0xF
        DB 0x46, 6, 0xF
        DB 0xFA, 5, 0x10
        DB 0xB3, 5, 0x11
        DB 0x6F, 5, 0x12
        DB 0x2F, 5, 0x13
        DB 0xF3, 4, 0x15
        DB 0xF3, 4, 0x16
        DB 0x85, 4, 0x17
        DB 0x52, 4, 0x19
        DB 0x23, 4, 0x1A
        DB 0xF6, 3, 0x1C
        DB 0xCB, 3, 0x1D
        DB 0xA3, 3, 0x1F
        DB 0x7D, 3, 0x21
        DB 0x59, 3, 0x23
        DB 0x38, 3, 0x25
        DB 0x18, 3, 0x27
        DB 0xFA, 2, 0x29
        DB 0xDD, 2, 0x2C
        DB 0xC2, 2, 0x2E
        DB 0xA9, 2, 0x31
        DB 0x91, 2, 0x34
        DB 0x7B, 2, 0x37
        DB 0x66, 2, 0x3A
        DB 0x51, 2, 0x3E
        DB 0x3F, 2, 0x41
        DB 0x2D, 2, 0x45
        DB 0x1C, 2, 0x49
        DB 0xC, 2, 0x4E
        DB 0xFD, 1, 0x52
        DB 0xEF, 1, 0x57
        DB 0xE2, 1, 0x5D
        DB 0xD5, 1, 0x62
        DB 0xC9, 1, 0x68
        DB 0xBD, 1, 0x6E
        DB 0xB3, 1, 0x75
        DB 0xA9, 1, 0x7B
        DB 0x9F, 1, 0x83
        DB 0x96, 1, 0x8B
        DB 0x8E, 1, 0x93
        DB 0x86, 1, 0x9C
        DB 0x7E, 1, 0xA5
        DB 0x77, 1, 0xAF
        DB 0x71, 1, 0xB9
        DB 0x6A, 1, 0xC4
        DB 0x64, 1, 0xD0
        DB 0x5F, 1, 0xDC
        DB 0x59, 1, 0xE9
        DB 0x54, 1, 0xF7
        ; ---------------------------------------------------------------------------
        ld a, (seed_2)
        and 7
        ld l, a
        ld h, 0
        ld bc, byte_B5E6
        add hl, bc
        ld b, (hl)
        ld c, 4
        jp toggle_FE_bit4_xC
        ; ---------------------------------------------------------------------------
byte_B5E6:
        DB 0xA0, 0xB0, 0xC0, 0x90, 0xA0, 0xE0, 0x80, 0x60
        ; =============== S U B R O U T I N E =======================================
sub_B5EE:
        ld a, (ix+0)
        cpl
        and 0x1F
        ld e, a
        ld hl, 0x1234
loc_B5F8:
        ld a, (hl)
        inc hl
        ld b, a
        ld c, 2
        call toggle_FE_bit4_xC
        dec e
        jr nz, loc_B5F8
        ret
        ; End of function sub_B5EE
        ; =============== S U B R O U T I N E =======================================
sub_B604:
        ld a, (ix+0)
        rlca
        rlca
        and 0x1F
        or 3
        ld c, a
loc_B60E:
        ld a, c
        rlca
        rlca
        ld b, a
        call toggle_FE_bit4
        dec c
        jr nz, loc_B60E
        ret
        ; End of function sub_B604
        ; =============== S U B R O U T I N E =======================================
sub_B619:
        ld hl, 0
        ld e, 4
loc_B61E:
        ld c, 3
        ld a, (hl)
        inc hl
        or 0xC0   ; 'À'
        ld b, a
        call toggle_FE_bit4_xC
        dec e
        jr nz, loc_B61E
        ret
        ; End of function sub_B619
        ; =============== S U B R O U T I N E =======================================
audio_B62C:
        ld c, 0x20   ; ' '
loc_B62E:
        ld a, c
        rrca
        rrca
        rrca
        rrca
        rrca
        ld b, a
        call toggle_FE_bit4
        dec c
        jr nz, loc_B62E
        ret
        ; End of function audio_B62C
        ; =============== S U B R O U T I N E =======================================
audio_B63C:
        ld a, (ix+3)
audio_B63F:
        add a, 0x40   ; '@'
        cpl
        rlca
        rlca
        ld b, a
        ld c, 6
        jp toggle_FE_bit4_xC
        ; End of function audio_B63C
        ; =============== S U B R O U T I N E =======================================
audio_B64A:
        ld a, (ix+1)
        jr audio_B63F
        ; End of function audio_B64A
        ; =============== S U B R O U T I N E =======================================
audio_B64F:
        ld a, (ix+2)
        jr audio_B63F
        ; End of function audio_B64F
        ; =============== S U B R O U T I N E =======================================
audio_B654:
        ld a, (ix+1)   ; X
        add a, (ix+2)   ; +Y
        add a, (ix+3)   ; +Z
        jr audio_B63F
        ; End of function audio_B654
        ; ---------------------------------------------------------------------------
        ld a, (ix+0)
        rlca
        rlca
        rlca
        and 0x18
        add a, 0x10
        ld c, a
audio_B66A:
        ld a, c
        xor 0x55   ; 'U'
        add a, c
        ld b, a
        call toggle_FE_bit4
        dec c
        jr nz, audio_B66A
        ret
        ; =============== S U B R O U T I N E =======================================
sub_B676:
        ld a, (seed_3)
        ld l, a
        ld a, (seed_2)
        and 0x1F
        ld h, a
        ld e, 0x10
loc_B682:
        ld a, (hl)
        inc hl
        and 0x7F   ; ''
        ld b, a
        ld c, 2
        call toggle_FE_bit4_xC
        dec e
        jr nz, loc_B682
        ret
        ; End of function sub_B676
        ; =============== S U B R O U T I N E =======================================
audio_B690:
        ld a, (seed_2)
        and 3
        call add_HL_A
        ld c, (hl)
loc_B699:
        ld a, (seed_2)
        xor c
        and 0x1F
        or 0x40   ; '@'
        ld b, a
        call toggle_FE_bit4
        dec c
        jr nz, loc_B699
        ret
        ; End of function audio_B690
        ; ---------------------------------------------------------------------------
byte_B6A9:
        DB 8, 0xC, 0x10, 0x14, 0x18, 0x14, 0x10, 0xC
        ; =============== S U B R O U T I N E =======================================
toggle_FE_bit4_x16:
        ld bc, 0x8010
        jr toggle_FE_bit4_xC
        ; ---------------------------------------------------------------------------
toggle_FE_bit4_x24:
        ld bc, 0x5018
        jr toggle_FE_bit4_xC
        ; ---------------------------------------------------------------------------
toggle_FE_bit4_x32:
        ld bc, 0x3020
        jr toggle_FE_bit4_xC
        ; ---------------------------------------------------------------------------
loc_B6C0:
        ld a, (ix+0)
        and 1
        ret nz
        ld b, 0x80   ; ''
        ld a, (seed_2)
        cpl
        jr loc_B6D9
        ; ---------------------------------------------------------------------------
audio_B6CE:
        ld a, (ix+0)
        and 1
        ret nz
loc_B6D4:
        ld b, 0x60   ; '`'
        ld a, (seed_2)
loc_B6D9:
        bit 1, a
        jr z, loc_B6E6
        ld a, (ix+3)
        add a, 0x40   ; '@'
        cpl
        srl a
        ld b, a
loc_B6E6:
        ld a, (ix+1)
        srl a
        ld c, a
        ld a, (ix+2)
        neg
        srl a
        add a, c
        rrca
        rrca
        rrca
        rrca
        and 0xF
        ld c, a
toggle_FE_bit4_xC:
        call toggle_FE_bit4
        dec c
        jr nz, toggle_FE_bit4_xC
        ret
        ; End of function toggle_FE_bit4_x16
        ; =============== S U B R O U T I N E =======================================
toggle_FE_bit4:
        ld a, 0x10
        out (0xFE), a
        ld a, b
loc_B707:
        djnz loc_B707
        ld b, a
        xor a
        out (0xFE), a
        ld a, b
loc_B70E:
        djnz loc_B70E
        ld b, a
        ret
        ; End of function toggle_FE_bit4
        ; Identical to Knight Lore (except #objs)
        ; =============== S U B R O U T I N E =======================================
do_any_objs_intersect:
        push bc
        push de
        push hl
        push iy
        ld iy, graphic_objs_tbl
        ld b, 56
        ld c, 0
        ld l, c
        ld h, c
        set 1, (ix+7)
loc_B725:
        call is_object_not_ignored
        jr z, loc_B743
        call do_objs_intersect_on_x
        jr nc, loc_B743
        call do_objs_intersect_on_y
        jr nc, loc_B743
        call do_objs_intersect_on_z
        jr nc, loc_B743
loc_B739:
        pop iy
        pop hl
        pop de
        pop bc
        res 1, (ix+7)
        ret
        ; ---------------------------------------------------------------------------
loc_B743:
        ld de, 32
        add iy, de
        djnz loc_B725
        and a
        jr loc_B739
        ; End of function do_any_objs_intersect
        ; identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
is_object_not_ignored:
        ld a, (iy+0)
        and a
        ret z
        ld a, (iy+7)
        cpl
        and 2
        ret
        ; End of function is_object_not_ignored
        ; =============== S U B R O U T I N E =======================================
read_key:
        out (0xFD), a
        in a, (0xFE)
        cpl
        and 0x1F
        ret
        ; End of function read_key
        ; ---------------------------------------------------------------------------
        ; START OF FUNCTION CHUNK FOR lose_life
game_over:
        call update_special_objs
        ld a, (byte_5B23)
        and a
        jp nz, game_complete_msg
loc_B76B:
        call clear_scrn_buffer
        call clear_scrn
        ld de, gameover_colours
        exx
        ld hl, gameover_xy
        ld de, aGameOver   ; "GAME OVEÒ"
        ld b, 7
        call display_text_list
        call count_screens
        rlca
        and 0xC0   ; 'À'
        ld c, a
        ld a, (byte_5B23)
        and 1
        or c
        rlca
        rlca
        rlca
        and 0xE
        ld l, a
        ld h, 0
        ld bc, rating_tbl
        add hl, bc   ; get entry
        ld e, (hl)
        inc hl
        ld d, (hl)   ; DE=ptr message
        ld hl, 0x2758
        call print_text
        call something_with_special_objs
        call print_some_number
        call print_border
        call update_screen
loc_B7AE:
        xor a
        call read_key
        jr nz, loc_B7AE
        ld de, game_over_tune
        call play_audio_until_keypress
        ld b, 8
        call play_audio_timed_key
        ld a, 1
        ld (byte_5B24), a
        call clear_scrn_buffer
        call print_border
        call update_screen
        call clr_graphic_objs_tbl
        call clr_attr
        ld a, (byte_5B23)
        and a
        jr nz, loc_B7F0
        ld hl, 0x9F48
        ld de, msg_Reprogramming
        call print_text
        ld de, byte_B82A
loc_B7E5:
        call set_graphic_flags7_pixelXY
        ld a, 1
        ld (render_status_info), a
        jp onscreen_loop
        ; ---------------------------------------------------------------------------
loc_B7F0:
        ld de, byte_B853
        jr loc_B7E5
        ; END OF FUNCTION CHUNK FOR lose_life
        ; ---------------------------------------------------------------------------
msg_Reprogramming:
        DB 0xC6   ; Æ
aReProgramming:
        DB "RE<PROGRAMMIN"
        DB 0xC7
        ; =============== S U B R O U T I N E =======================================
set_graphic_flags7_pixelXY:
        ld iy, graphic_objs_tbl
        ld bc, 32
loc_B80B:
        ld a, (de)
        inc de
        and a
        ret z
        ld (iy+0), a
        ld a, (de)
        inc de
        ld (iy+7), a
        ld a, (de)
        inc de
        ld (iy+16), a
        ld a, (de)
        inc de
        ld (iy+26), a
        ld a, (de)
        inc de
        ld (iy+27), a
        add iy, bc
        jr loc_B80B
        ; End of function set_graphic_flags7_pixelXY
        ; ---------------------------------------------------------------------------
        ; graphic_no, flags7, plyr graphic_no, pixelX, pixelY
byte_B82A:
        DB 0x51, 0x10, 0x42, 0xB8, 0x50
        DB 0x53, 0x10, 0x47, 0x20, 0x50
        DB 0x52, 0x10, 0x44, 0x78, 0x7C
        DB 0x58, 0x10, 0x45, 0x68, 0x40
        DB 0x59, 0x10, 0x45, 0x80, 0x40
        DB 0x5A, 0x10, 0x45, 0x70, 0x45
        DB 0x5B, 0x10, 0x45, 0x70, 0x55
        DB 0x50, 0x10, 0x46, 0x74, 0x68
        DB 0
byte_B853:
        DB 0x5C, 0x10, 7, 0x70, 0x80
        DB 0x5D, 0x10, 7, 0x70, 0x90
        DB 0x55, 0x10, 0x44, 0x6C, 0x20
        DB 0
        ; ---------------------------------------------------------------------------
        ; START OF FUNCTION CHUNK FOR build_screen_objects
flag_room_visited:
        ld a, (graphic_objs_tbl+8)
        ld c, a
        rrca
        rrca
        rrca
        and 0x1F
        ld l, a
        ld h, 0
        ld a, c
        rlca
        rlca
        rlca
        and 0x38   ; '8'
        or 0xC6   ; 'Æ'             ; SET 0,(HL)
        ld (byte_B87F), a   ; self_modifying code
        ld bc, scrn_visited
        add hl, bc   ; offset to room flag
        ; END OF FUNCTION CHUNK FOR build_screen_objects
        ; ---------------------------------------------------------------------------
        DB 0xCB   ; Ë                    ; set n,(HL)
byte_B87F:
        DB 0xC6   ; flag as visited
        ; ---------------------------------------------------------------------------
        ret
        ; =============== S U B R O U T I N E =======================================
count_screens:
        ld e, 0
        ld bc, 0x820   ; 8 bits, 32 bytes
        ld hl, scrn_visited
next_screen:
        push bc
        ld a, (hl)
        inc hl
loc_B88C:
        rrca
        jr nc, loc_B890
        inc e
loc_B890:
        djnz loc_B88C
        pop bc
        dec c
        jr nz, next_screen
        ld a, e
        dec a
        ret
        ; End of function count_screens
        ; =============== S U B R O U T I N E =======================================
play_audio_timed_key:
        ld hl, 0
loc_B89C:
        xor a
        call read_key
        ret nz
        dec hl
        ld a, h
        or l
        jr nz, loc_B89C
        djnz loc_B89C
        ret
        ; End of function play_audio_timed_key
        ; ---------------------------------------------------------------------------
        ; START OF FUNCTION CHUNK FOR lose_life
game_complete_msg:
        call clear_scrn_buffer
        call clear_scrn
        ld de, complete_colours
        exx
        ld hl, complete_xy
        ld de, aTheStationHasArrived   ; "THE STATION HAS ARRIVEÄ"
        ld b, 7
        xor a
        ld (suppress_border), a
        call display_text_list
        ld de, game_complete_tune
        call play_audio
        ld b, 8
        call play_audio_timed_key
        jp loc_B76B
        ; END OF FUNCTION CHUNK FOR lose_life
        ; ---------------------------------------------------------------------------
complete_colours:
        DB 0x45, 0x45, 0x44, 0x43, 0x43, 0x42, 0x42
complete_xy:
        DB 0x20, 0x8F
        DB 0x58, 0x7F
        DB 0x28, 0x6F
        DB 0x48, 0x5F
        DB 0x48, 0x4F
        DB 0x48, 0x3F
        DB 0x58, 0x2F
aTheStationHasArrived:
        DB "THE STATION HAS ARRIVE"
        DB 0xC4
aFromSpace:
        DB "FROM SPAC"
        DB 0xC5
aThrustersGentlySlow:
        DB "THRUSTERS GENTLY SLO"
        DB 0xD7
aTheActivation:
        DB "THE ACTIVATIO"
        DB 0xCE
aCircuitsHeld:
        DB "CIRCUITS  HEL"
        DB 0xC4
aAllCryonaught:
        DB "ALL CRYONAUGH"
        DB 0xD4
aSystemsGo:
        DB "SYSTEMS G"
        DB 0xCF
gameover_colours:
        DB 0x47, 0x46, 0x46, 0x45, 0x45, 0x43, 0x44
gameover_xy:
        DB 0x58, 0x9F
        DB 0x30, 0x8F
        DB 0x30, 0x7F
        DB 0x28, 0x6F
        DB 0x30, 0x5F
        DB 0x28, 0x4F
        DB 0x48, 0x37
aGameOver:
        DB "GAME OVE"
        DB 0xD2
aActivatedCryogenic:
        DB "ACTIVATED CRYOGENI"
        DB 0xC3
aChambers_1:
        DB "CHAMBERS;;;;;;;;; "
        DB 0xA0
aUnactivatedCryogenic:
        DB "UNACTIVATED CRYOGENI"
        DB 0xC3
aChambers_2:
        DB "CHAMBERS;;;;;;;;; "
        DB 0xA0
aCryonaughtsLost:
        DB "CRYONAUGHTS LOST;  "
        DB 0xA0
aOverallRating:
        DB "OVERALL RATIN"
        DB 0xC7
rating_tbl:
        DW msg_POOR
        DW msg_AVERAGE
        DW msg_FAIR
        DW msg_GOOD
        DW msg_EXCELLENT
        DW msg_MARVELLOUS
        DW msg_HERO
        DW msg_ADVENTURER
msg_POOR:
        DB 0x47   ; G
aPoor:
        DB "   POO"
        DB 0xD2
msg_AVERAGE:
        DB 0x47   ; G
aAverage:
        DB " AVERAG"
        DB 0xC5
msg_FAIR:
        DB 0x47   ; G
aFair:
        DB "   FAI"
        DB 0xD2
msg_GOOD:
        DB 0x47   ; G
aGood:
        DB "   GOO"
        DB 0xC4
msg_EXCELLENT:
        DB 0x47   ; G
aExcellent:
        DB "EXCELLEN"
        DB 0xD4
msg_MARVELLOUS:
        DB 0x47   ; G
aMarvellous:
        DB "MARVELLOU"
        DB 0xD3
msg_HERO:
        DB 0x47   ; G
aHero:
        DB "   HER"
        DB 0xCF
msg_ADVENTURER:
        DB 0x47   ; G
aAdventurer:
        DB "ADVENTURE"
        DB 0xD2
        ; =============== S U B R O U T I N E =======================================
print_some_number:
        ld hl, ascii_chars
        ld (gfxbase_8x8), hl
        ld de, unk_5B3C
        ld hl,  vidbuf+0x9F6
        ld b, 2
        call print_BCD_lsd
        ld hl,  vidbuf+0xFF7
        ld b, 1
        call print_BCD_msd
        ld hl,  vidbuf+0xBF7
        ld b, 1
        jp print_BCD_msd
        ; End of function print_some_number
        ; =============== S U B R O U T I N E =======================================
print_lives:
        ld de, lives
        ld b, 1
        ld hl,  vidbuf+0xF0
        jp print_BCD_number
        ; ---------------------------------------------------------------------------
print_BCD_number:
        push hl
        ld hl, ascii_chars
        ld (gfxbase_8x8), hl
        pop hl
        ; End of function print_lives
        ; =============== S U B R O U T I N E =======================================
print_BCD_msd:
        ld a, (de)   ; get char
        rrca
        rrca
        rrca
        rrca   ; high->low nibble
        and 0xF
        call print_8x8
        ; End of function print_BCD_msd
        ; =============== S U B R O U T I N E =======================================
print_BCD_lsd:
        ld a, (de)   ; get char
        and 0xF   ; low nibble
        call print_8x8
        inc de
        djnz print_BCD_msd
        ret
        ; End of function print_BCD_lsd
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
do_menu_selection:
        xor a
        ld (suppress_border), a
        ld hl, menu_colours
        ld b, 8
loc_BA87:
        res 7, (hl)
        inc hl
        djnz loc_BA87
        call clear_scrn_buffer
        call display_menu
        call flash_menu
menu_loop:
        call display_menu
        ld de, menu_tune
        call play_audio_wait_key
        ld a, 0xF7   ; '÷'
        call read_key
        ld e, a
        ld a, (user_input_method)
        ld (tmp_input_method), a
        bit 0, e
        jr z, check_for_kempston_jpystick
        and 0xF9   ; 'ù'
check_for_kempston_jpystick:
        bit 1, e
        jr z, check_for_cursor_joystick
        and 0xF9   ; 'ù'
        or 2
check_for_cursor_joystick:
        bit 2, e
        jr z, check_for_interface_ii
        and 0xF9   ; 'ù'
        or 4
check_for_interface_ii:
        bit 3, e
        jr z, check_for_dierctional_control
        or 6
check_for_dierctional_control:
        ld (user_input_method), a
        ld hl, directional
        bit 4, e
        jr z, unset_directional
        bit 0, (hl)
        jr nz, check_for_start_game
        set 0, (hl)
        ld a, (user_input_method)
        xor 8
        ld (user_input_method), a
check_for_start_game:
        ld hl, tmp_input_method
        cp (hl)
        call nz, toggle_FE_bit4_x16
        ld a, 0xEF   ; 'ï'
        call read_key
        bit 0, a
        ret nz
        ld hl, seed_1
        inc (hl)
        call flash_menu
        jp menu_loop
        ; ---------------------------------------------------------------------------
unset_directional:
        res 0, (hl)
        jr check_for_start_game
        ; End of function do_menu_selection
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
flash_menu:
        ld hl,  menu_colours+1
        ld a, (user_input_method)
        rrca
        and 3
        ld b, 4
        call toggle_selected
        res 7, (hl)
        ld a, (user_input_method)
        and 8
        ret z
        set 7, (hl)
        ret
        ; End of function flash_menu
        ; ---------------------------------------------------------------------------
menu_colours:
        DB 0x43, 0x44, 0x44, 0x44, 0x44, 0x45, 0x47, 0x47
menu_xy:
        DB 0x68, 0x9F
        DB 0x30, 0x8F
        DB 0x30, 0x7F
        DB 0x30, 0x6F
        DB 0x30, 0x5F
        DB 0x30, 0x4F
        DB 0x30, 0x3F
        DB 0x50, 0x27
aAlien:
        DB "ALIEN "
        DB 0xB8
a1Keyboard:
        DB "1 KEYBOAR"
        DB 0xC4
a2KempstonJoystick:
        DB "2 KEMPSTON JOYSTIC"
        DB 0xCB
a3CursorJoystick:
        DB "3 CURSOR JOYSTIC"
        DB 0xCB
a4InterfaceII:
        DB "4 INTERFACE I"
        DB 0xC9
a5DirectionalControl:
        DB "5 DIRECTIONAL CONTRO"
        DB 0xCC
a0StartGame:
        DB "0 START GAM"
        DB 0xC5
a1985ACG:
        DB "> 1985 A;C;G"
        DB 0xBB
        ; =============== S U B R O U T I N E =======================================
print_text_in_colour:
        push hl
        ld hl, font-0x100   ; so we can use ASCII
        ld (gfxbase_8x8), hl
        pop bc
        push bc
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld a, (tmp_attrib)
        ex af, af'
        jr loc_BBC2
        ; End of function print_text_in_colour
        ; =============== S U B R O U T I N E =======================================
print_text:
        push hl
        ld hl, font-0x100   ; sp we can use ASCII
        ld (gfxbase_8x8), hl
        pop bc
        push bc
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld a, (de)
        ex af, af'
        inc de
loc_BBC2:
        exx
        pop hl
        push de
        call calc_attrib_addr
        ld l, e
        ld h, d
        pop de
loc_BBCB:
        exx
        ld a, (de)
        bit 7, a
        jr nz, loc_BBDE
        push de
        call print_8x8
        pop de
        inc de
        exx
        ex af, af'
        ld (hl), a
        inc l
        ex af, af'
        jr loc_BBCB
        ; ---------------------------------------------------------------------------
loc_BBDE:
        and 0x7F   ; ''
        push de
        call print_8x8
        pop de
        inc de
        exx
        ex af, af'
        ld (hl), a
        exx
        ret
        ; End of function print_text
        ; =============== S U B R O U T I N E =======================================
print_8x8:
        cp 0x20   ; ' '
        jr nz, loc_BBF1
        ld a, 0x3D   ; '='
loc_BBF1:
        push bc
        push de
        push hl
        ld l, a
        ld h, 0
        add hl, hl
        add hl, hl
        add hl, hl
loc_BBFA:
        ld de, (gfxbase_8x8)
        add hl, de
        ex de, hl
        pop hl
        ld b, 8
loc_BC03:
        ld a, (de)
        ld (hl), a
        inc de
        push bc
        ld bc, 0xFFE0
        add hl, bc
        pop bc
        djnz loc_BC03
        pop de
        ld bc, 0x101
        add hl, bc
        pop bc
        ret
        ; End of function print_8x8
        ; =============== S U B R O U T I N E =======================================
toggle_selected:
        and a
        jr nz, loc_BC1F
loc_BC18:
        set 7, (hl)
        jr loc_BC21
        ; ---------------------------------------------------------------------------
loc_BC1C:
        dec a
        jr z, loc_BC18
loc_BC1F:
        res 7, (hl)
loc_BC21:
        inc hl
        djnz loc_BC1C
        ret
        ; End of function toggle_selected
        ; =============== S U B R O U T I N E =======================================
display_menu:
        ld de, menu_colours
        exx
        ld hl, menu_xy
        ld de, aAlien   ; "ALIEN ¸"
        ld b, 8
        ; End of function display_menu
        ; =============== S U B R O U T I N E =======================================
display_text_list:
        exx
        ld a, (de)
        ld (tmp_attrib), a
        inc de
        exx
        push bc
        ld a, (hl)
        inc hl
        inc hl
        push hl
        dec hl
        ld h, (hl)
        ld l, a
        call print_text_in_colour
        pop hl
        pop bc
        djnz display_text_list
        ld a, (suppress_border)
        and a
        ret nz
        inc a
        ld (suppress_border), a
        call print_border
        jp update_screen
        ; End of function display_text_list
        ; =============== S U B R O U T I N E =======================================
multiple_print_sprite:
        push bc
        push de
        push hl
        call print_sprite
        pop hl
        pop de
        pop bc
        ld a, (ix+26)
        add a, e
        ld (ix+26), a
        ld a, (ix+27)
        add a, d
        ld (ix+27), a
        djnz multiple_print_sprite
        ret
        ; End of function multiple_print_sprite
        ; ---------------------------------------------------------------------------
upd_38_to_3E:
        call sub_BF47
        ld a, (seed_2)
        cpl
        and 1
        ret nz
        inc (ix+0)
        call sub_B604
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
upd_3F:
        call sub_BF47
        xor a
        ld (ix+9), a
        ld (ix+10), a
        ld (ix+11), a
        res 6, (ix+13)
        ld a, (ix+16)
        ld (ix+0), a
        jp jump_to_upd_object
        ; =============== S U B R O U T I N E =======================================
display_objects_carried:
        ld a, (byte_5B23)
        and a
        ret nz
        ld a, (objects_carried_changed)
        and a
        ret z
        xor a
        ld (objects_carried_changed), a
        ; End of function display_objects_carried
        ; =============== S U B R O U T I N E =======================================
sub_BCAB:
        push ix
        ld ix, sprite_scratchpad
        ld b, 3
        ld hl, byte_5B7C
loc_BCB6:
        push bc
        push hl
        ld a, b
        neg
        add a, 3
        sla a
        sla a
        sla a
        ld c, a
        sla a
        add a, c
        add a, 8
        ld (ix+26), a   ; pixelX
        ld (ix+27), 0   ; pixelY
        ld c, (ix+26)   ; pixelX
        ld b, (ix+27)   ; pixelY
        push hl
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld bc, 0x318
        xor a
        call fill_window
        pop hl
        ld a, (hl)
        and a
        jr z, loc_BCF2
        res 6, (ix+7)
        ld (ix+0), a
        call print_sprite
loc_BCF2:
        ld c, (ix+26)
        ld b, (ix+27)
        call BC_to_Attr_In_DE
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld bc, 0x1803
        call blit_to_screen
        pop hl
        pop bc
        push bc
        push hl
        ld a, (hl)
        and 0xF
        ld e, a
        ld d, 0
        ld hl, byte_BD34
        add hl, de
        ld c, (hl)
        ld l, (ix+26)
        ld a, (ix+27)
        add a, 0x17
        ld h, a
        call calc_attrib_addr
        ex de, hl
        ld a, c
        ld bc, 0x303
        call fill_window
        pop hl
        pop bc
        inc hl
        inc hl
        inc hl
        inc hl
        djnz loc_BCB6
        pop ix
        ret
        ; End of function sub_BCAB
        ; ---------------------------------------------------------------------------
byte_BD34:
        DB 0x42, 0x43, 0x45, 0x47
sprite_scratchpad:
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
chk_pickup_drop:
        ld hl, user_input_method
        ld a, (hl)
        and 6
        ld a, (user_input)
        jr z, loc_BD68
        bit 3, (hl)
        jr z, loc_BD68
        rrca
loc_BD68:
        and 0x10
        ret
        ; End of function chk_pickup_drop
        ; Identical to Knight Lore - almost
        ; - no handling of cauldron room
        ; - very slightly different call
        ; =============== S U B R O U T I N E =======================================
handle_pickup_drop:
        ld a, (pickup_drop_pressed)
        and a
        jp nz, loc_BDFD
        call chk_pickup_drop
        ret z
        call chk_plyr_OOB
        ret nc
        bit 3, (ix+12)
        ret nz
        bit 2, (ix+12)
        ret z
        xor a
        ld (cant_drop), a
        ld a, (ix+3)
        ld b, a
        add a, 12
        ld (ix+3), a
        call do_any_objs_intersect
        ld (ix+3), b
        jr nc, loc_BD9E
        ld a, 1
        ld (cant_drop), a
loc_BD9E:
        call toggle_FE_bit4_x16
        ld a, 1
        ld (pickup_drop_pressed), a
        ld (objects_carried_changed), a
        ld b, 2
        ld l, (ix+4)
        ld a, l
        add a, 4
        ld (ix+4), a
        ld h, (ix+5)
        ld a, h
        add a, 4
        ld (ix+5), a
        push hl
        ld l, (ix+6)
        ld a, l
        add a, 4
        ld (ix+6), a
        push hl
        ld iy, special_objs_here
loc_BDCC:
        call can_pickup_spec_obj
        jp c, pickup_object
        ld de, 32
        add iy, de
        djnz loc_BDCC
        call chk_pickup_drop
        jr z, done_pickup_drop
        ld b, 2
        ld iy, special_objs_here
        ld de, 32
loc_BDE7:
        ld a, (iy+0)
        and a
        jr z, loc_BE06
        add iy, de
        djnz loc_BDE7
done_pickup_drop:
        pop hl
        ld (ix+6), l
        pop hl
        ld (ix+4), l
        ld (ix+5), h
        ret
        ; ---------------------------------------------------------------------------
loc_BDFD:
        call chk_pickup_drop
        ret nz
        xor a
        ld (pickup_drop_pressed), a
        ret
        ; ---------------------------------------------------------------------------
loc_BE06:
        ld hl, byte_5B84
        ld a, (hl)
        inc hl
        and a
        jr z, adjust_carried
        ld a, (cant_drop)
        and a
        jr nz, done_pickup_drop
        dec hl
        ld a, (hl)
        inc hl
        ld (iy+0), a
        push hl
        ld bc, 3
        push ix
        pop hl
        push iy
        pop de
        inc de
        inc hl
        ldir
        ld a, (ix+3)
        add a, 12
        ld (ix+3), a
        ld a, (ix+35)
        add a, 12
        ld (ix+35), a
        call calc_pixel_XY_IY
drop_object:
        ld (iy+4), 5
        ld (iy+5), 5
        ld (iy+6), 12
        pop hl
        ld a, (hl)
        inc hl
        ld (iy+7), a
        ld a, (ix+8)
        ld (iy+8), a
        ld a, (hl)
        inc hl
        ld (iy+16), a
        ld a, (hl)
        ld (iy+17), a
        set 0, (iy+13)
adjust_carried:
        ld hl,  byte_5B80+3
        ld de, end_of_objects_carried
        ld bc, 12
        lddr
        ld de, inventory
        ld b, 4
        call zero_DE
        jp done_pickup_drop
        ; ---------------------------------------------------------------------------
pickup_object:
        ld hl, inventory
        xor a
        ld (byte_5B3B), a
        ld a, (iy+0)
        ld (hl), a
        inc hl
        ld a, (iy+7)
        ld (hl), a
        inc hl
        ld e, (iy+16)
        ld d, (iy+17)
        xor a
        ld (de), a
        ld (hl), e
        inc hl
        ld (hl), d
        call set_wipe_and_draw_IY
        ld (iy+0), 1
        ld hl, byte_5B84
        ld a, (hl)
        inc hl
        and a
        jr z, adjust_carried
        ld (iy+0), a
        push hl
        jr drop_object
        ; End of function handle_pickup_drop
        ; Identical to Knight Lore (except #special objs)
        ; =============== S U B R O U T I N E =======================================
can_pickup_spec_obj:
        ld a, (iy+0)
        sub 0x60   ; '`'
        cp 4
        ret nc
        ; Identical to Knight Lore
        ; - sets C flag if TRUE
is_on_or_near_obj:
        push bc
        ld bc, 0
        ld l, c
        ld h, c
        call do_objs_intersect_on_x
        jr nc, loc_BED4
        call do_objs_intersect_on_y
        jr nc, loc_BED4
        ld a, (ix+3)
        sub 4
        ld (ix+3), a
        call do_objs_intersect_on_z
        push af
        ld a, (ix+3)
        add a, 4
        ld (ix+3), a
        pop af
loc_BED4:
        pop bc
        ret
        ; End of function can_pickup_spec_obj
        ; =============== S U B R O U T I N E =======================================
is_obj_moving:
        ld a, (ix+9)   ; dX
        or (ix+10)   ; dY
        or (ix+11)   ; dZ
        ret
        ; End of function is_obj_moving
        ; ---------------------------------------------------------------------------
        ; extra life
upd_0C:
        call adj_m2_m8
        push ix
        pop iy
        ld ix, graphic_objs_tbl
        inc (ix+4)   ; plyr bottom width
        inc (ix+5)   ; plyr bottom depth
        call is_on_or_near_obj
        dec (ix+4)   ; plyr bottom width
        dec (ix+5)   ; plyr bottom depth
        push iy
        pop ix
        jr nc, loc_BF22   ; not close, skip
        ld (ix+0), 0x40   ; '@'      ; sparkles
        call adj_m4_m12
        ld l, (ix+16)
        ld h, (ix+17)
        xor a
        ld (hl), a   ; plyr graphic
        ld (byte_5B3B), a
        ld hl, lives
        inc (hl)   ; extra life!
        call toggle_FE_bit4_x16
        call print_lives
        ld bc, 0x80   ; ''
        call sub_BF2F
loc_BF22:
        call dec_dZ_and_update_XYZ
        call is_obj_moving
        ret z
        call clear_dX_dY
        jp audio_set_wipe_draw_flags
        ; =============== S U B R O U T I N E =======================================
sub_BF2F:
        call BC_to_Attr_In_DE
        call calc_screen_buffer_addr
        ld l, c
        ld h, b
        ld bc, 0x802
        jp blit_to_screen
        ; End of function sub_BF2F
        ; =============== S U B R O U T I N E =======================================
upd_1E:
        ld hl, 0xF7F0
        jr set_pixel_adj
        ; End of function upd_1E
        ; ---------------------------------------------------------------------------
        ld hl, 0xF7F4
        jr set_pixel_adj
        ; =============== S U B R O U T I N E =======================================
sub_BF47:
        ld hl, 0xF8F4
        jr set_pixel_adj
        ; End of function sub_BF47
        ; =============== S U B R O U T I N E =======================================
adj_m7_m16:
        ld hl, 0xF9F0   ; -7,-16
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
upd_0D:
        ld hl, 0xF9F4
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m6_m16:
        ld hl, 0xFAF0
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m6_m12:
        ld hl, 0xFAF4
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m5_m12:
        ld hl, 0xFBF4
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
upd_0F:
        ld hl, 0xFBF8
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m4_m12:
        ld hl, 0xFCF4
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m3_m16:
        ld hl, 0xFDF0
        jr set_pixel_adj
        ; ---------------------------------------------------------------------------
upd_0E:
        ld hl, 0xFDFC
        ; Identical to Knight Lore
set_pixel_adj:
        ld (ix+18), l
        ld (ix+19), h
        ret
        ; End of function adj_m7_m16
        ; =============== S U B R O U T I N E =======================================
adj_m2_m8:
        ld hl, 0xFEF8   ; -2,-8
        jr set_pixel_adj
        ; End of function adj_m2_m8
        ; ---------------------------------------------------------------------------
        ; Different to Knight Lore
        ; - unrolled the loop and using self-modifying code
fill_window:
        push af
        ld a, b   ; #bytes
        neg
        and 7
        add a, a   ; calc JR operand
        ld (loc_BF95+1), a   ; patch code
        ld a, 32   ; 32 bytes/line
        sub b   ; sub #bytes for offset
        ld e, a
        ld d, 0
        ld b, c   ; #lines
        pop af
loc_BF95:
        jr loc_BF95
        ; ---------------------------------------------------------------------------
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        ld (hl), a
        inc hl
        add hl, de
        djnz loc_BF95
        ret
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
set_wipe_and_draw_flags:
        ld a, (ix+7)
        or 0x30   ; '0'
        ld (ix+7), a
        jp set_draw_objs_overlapped
        ; End of function set_wipe_and_draw_flags
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
dec_dZ_and_update_XYZ:
        dec (ix+11)
        call adj_for_out_of_bounds
        ; fallthrough into add_dXYZ (intentional)
        ; End of function dec_dZ_and_update_XYZ
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
add_dXYZ:
        ld a, (ix+1)
        add a, (ix+9)
        ld (ix+1), a
        ld a, (ix+2)
        add a, (ix+10)
        ld (ix+2), a
        ld a, (ix+3)
        add a, (ix+11)
        ld (ix+3), a
        ret
        ; End of function add_dXYZ
        ; ---------------------------------------------------------------------------
upd_03:
        bit 6, (ix+7)
        jr nz, adj_m4_m8
        ld hl, 0xFBF0   ; -5,-16
        jp set_pixel_adj
        ; ---------------------------------------------------------------------------
adj_m4_m8:
        ld hl, 0xFCF8
        jp set_pixel_adj
        ; ---------------------------------------------------------------------------
upd_02:
        bit 6, (ix+7)
        jr nz, loc_C013
        ld hl, 0xF9FA   ; -7,-6
        call set_pixel_adj
        ld a, (ix+2)   ; Y
        add a, 13   ; Y+13
        ld (ix+10), a   ; dY=Y+13
        ld a, (ix+1)   ; X
        ld (ix+9), a   ; dX=X
        ld hl, 0x60F
loc_C007:
        ld a, (ix+3)
        ld (ix+11), a   ; dZ=Z
        call sub_C082
        jp loc_C02C
        ; ---------------------------------------------------------------------------
loc_C013:
        ld hl, 0xFAF6
        call set_pixel_adj
        ld a, (ix+1)   ; X
        sub 13   ; X-13
        ld (ix+9), a   ; dX=X-13
        ld a, (ix+2)   ; Y
        ld (ix+10), a   ; dY=Y
        ld hl, 0xF06
        jr loc_C007
        ; ---------------------------------------------------------------------------
loc_C02C:
        ld hl, 0xF0F
        ld iy, graphic_objs_tbl
        ld a, (iy+0)   ; player graphic no.
        and a   ; zero?
        ret z   ; yes, exit
        bit 3, (iy+7)
        ret z
        call sub_C099
        ret nc
        push bc
        ld bc, off_C048
        jp loc_C312
        ; ---------------------------------------------------------------------------
off_C048:
        DW loc_C050
        DW loc_C050
        DW loc_C069
        DW loc_C069
        ; ---------------------------------------------------------------------------
loc_C050:
        bit 6, (iy+7)
        jr nz, loc_C080
        ld a, (ix+10)
        cp (iy+2)
        jr z, loc_C080
        ld a, 1
        jr nc, loc_C064
        neg
loc_C064:
        ld (iy+15), a
        jr loc_C080
        ; ---------------------------------------------------------------------------
loc_C069:
        bit 6, (iy+7)
        jr z, loc_C080
        ld a, (ix+9)
        cp (iy+1)
        jr z, loc_C080
        ld a, 1
        jr nc, loc_C07D
        neg
loc_C07D:
        ld (iy+14), a
loc_C080:
        pop bc
        ret
        ; =============== S U B R O U T I N E =======================================
sub_C082:
        ld iy, graphic_objs_tbl
        ld a, (iy+0)   ; player graphic no.
        and a   ; zero?
        ret z   ; yes, exit
        bit 3, (iy+7)
        ret z
        call sub_C099
        ret nc
        set 0, (iy+7)
        ret
        ; End of function sub_C082
        ; =============== S U B R O U T I N E =======================================
sub_C099:
        ld a, (ix+9)
        sub (iy+1)
        jr nc, loc_C0A3
        neg
loc_C0A3:
        cp l
        ret nc
        ld a, (ix+10)
        sub (iy+2)
        jr nc, loc_C0AF
        neg
loc_C0AF:
        cp h
        ret nc
        ld a, (ix+11)
        sub (iy+3)
        jr nc, loc_C0BB
        neg
loc_C0BB:
        cp 4
        ret
        ; End of function sub_C099
        ; ---------------------------------------------------------------------------
        ; player bottom
upd_10_to_17:
        call adj_m7_m16
        bit 6, (ix+13)
        jr z, loc_C0CE
        set 6, (ix+45)
        jp loc_B39A
        ; ---------------------------------------------------------------------------
loc_C0CE:
        ld (ix+6), 23
        ld (ix+38), 0   ; height (next sprite)=0
        call check_user_input
        call handle_pickup_drop
        call handle_left_right
        call handle_jump
        call handle_forward
        call chk_plyr_OOB
        jr nc, loc_C10A
loc_C0EA:
        set 1, (ix+39)
        call move_player
        res 1, (ix+39)
        ld a, (ix+12)
        sub 0x10
        jr c, loc_C0FF
        ld (ix+12), a
loc_C0FF:
        ld (ix+6), 0xC
        ld (ix+38), 0xB
        jp set_wipe_and_draw_flags
        ; ---------------------------------------------------------------------------
loc_C10A:
        ld a, (ix+11)
        and a
        jp m, loc_C0EA
        xor a
        ld (ix+11), a
        jr loc_C0EA
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
chk_plyr_OOB:
        ld hl, (room_size_X)
        ld a, l
        sub (ix+4)
        ld l, a
        ld a, h
        sub (ix+5)
        ld h, a
        ld a, (ix+1)
        sub 128
        jp p, loc_C12E
        neg
loc_C12E:
        cp l
        ret nc
        ld a, (ix+2)
        sub 128
        jp p, loc_C13A
        neg
loc_C13A:
        cp h
        ret
        ; End of function chk_plyr_OOB
        ; Differs from Knight Lore in the latter half
        ; - eg. doesn't seem to debounce
        ; =============== S U B R O U T I N E =======================================
handle_left_right:
        ld hl, user_input_method
        ld a, (hl)
        and 6
        jr z, loc_C18F
        bit 3, (hl)
        jr z, loc_C18F
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 2, (ix+12)
        ret z
        bit 0, c
        jr nz, loc_C15B
        bit 2, c
        jr nz, loc_C16A
loc_C15B:
        bit 1, c
        jr nz, loc_C176
        bit 4, c
        jr nz, loc_C17D
        bit 0, c
        jr nz, loc_C186
        res 2, c
        ret
        ; ---------------------------------------------------------------------------
loc_C16A:
        call get_sprite_dir
        cp 2
loc_C16F:
        jr z, loc_C18C
        cpl
loc_C172:
        and 1
        jr loc_C1A0
        ; ---------------------------------------------------------------------------
loc_C176:
        call get_sprite_dir
        cp 1
        jr loc_C16F
        ; ---------------------------------------------------------------------------
loc_C17D:
        call get_sprite_dir
        cp 3
loc_C182:
        jr z, loc_C18C
        jr loc_C172
        ; ---------------------------------------------------------------------------
loc_C186:
        call get_sprite_dir
        and a
        jr loc_C182
        ; ---------------------------------------------------------------------------
loc_C18C:
        set 2, c
        ret
        ; ---------------------------------------------------------------------------
loc_C18F:
        ld a, c
        and 3
        ret z
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 3, (ix+12)
        ret nz
        bit 1, c
loc_C1A0:
        jr nz, loc_C1AB
        res 0, (ix+13)
        ld hl, byte_C1DA
        jr loc_C1B2
        ; ---------------------------------------------------------------------------
loc_C1AB:
        set 0, (ix+13)
        ld hl, byte_C1D2
loc_C1B2:
        ld a, (ix+13)
        or 2
        ld (ix+13), a
        call get_sprite_dir
        ; End of function handle_left_right
        ; =============== S U B R O U T I N E =======================================
sub_C1BD:
        rlca
        and 6
        call add_HL_A
        ld a, (hl)
        inc hl
        ld (ix+0), a
        ld a, (ix+7)
        and 0xBF   ; '¿'
        or (hl)
        ld (ix+7), a
        ret
        ; End of function sub_C1BD
        ; ---------------------------------------------------------------------------
byte_C1D2:
        DB 0x18, 0, 0x19, 0, 0x1A, 0, 0x1B, 0x40
byte_C1DA:
        DB 0x1B, 0x40, 0x1A, 0, 0x18, 0, 0x19, 0
        ; ---------------------------------------------------------------------------
upd_18_to_1B:
        call adj_m7_m16
        ld (ix+6), 0x17
        ld (ix+38), 0
        call check_user_input
        ld a, (ix+13)
        and 6
        jr z, loc_C208
        ld a, (ix+13)
        sub 2
        ld (ix+13), a
        set 1, (ix+39)
        call sub_C2BC
        jr loc_C221
        ; ---------------------------------------------------------------------------
loc_C208:
        bit 0, (ix+13)
        jr z, loc_C228
        ld hl, byte_C22D
loc_C211:
        ld a, (ix+0)
        call sub_C1BD
        call loc_B6D4
        set 1, (ix+39)
        call sub_C2B3
loc_C221:
        res 1, (ix+39)
        jp loc_C0FF
        ; ---------------------------------------------------------------------------
loc_C228:
        ld hl, byte_C235
        jr loc_C211
        ; ---------------------------------------------------------------------------
byte_C22D:
        DB 0x11, 0x40, 0x15, 0x40, 0x15, 0, 0x11, 0
byte_C235:
        DB 0x11, 0, 0x15, 0, 0x11, 0x40, 0x15, 0x40
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
handle_jump:
        bit 3, c
        ret z
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 3, (ix+12)
        ret nz
        ld a, (ix+11)
        inc a
        ret m
        set 3, (ix+12)
        ld (ix+11), 8
        push bc
        call audio_B62C
        pop bc
        ret
        ; End of function handle_jump
        ; Different to Knight Lore
        ; =============== S U B R O U T I N E =======================================
handle_forward:
        ld a, (ix+0)
        sub 0x18
        cp 4
        ret c
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        jr nz, loc_C277
        bit 3, (ix+12)
        jr nz, loc_C277
        bit 2, c
        jr z, loc_C28C
loc_C277:
        push bc
        call audio_B6CE
        pop bc
loc_C27C:
        ld a, (ix+0)
        ld e, a
        inc a
        and 3
        ld d, a
        ld a, e
        and 0xFC   ; 'ü'
        or d
        ld (ix+0), a
        ret
        ; ---------------------------------------------------------------------------
loc_C28C:
        ld a, (ix+0)
        and 3
        cp 1
        ret z
        jr loc_C27C
        ; End of function handle_forward
        ; Similar but different to Knight Lore
        ; =============== S U B R O U T I N E =======================================
move_player:
        ld a, (byte_5B24)
        and a
        jr z, loc_C2A0
        ld (ix+11), 2
loc_C2A0:
        bit 3, (ix+12)
        jr nz, loc_C2B7
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        jr nz, loc_C2B7
        bit 3, (ix+0)
        jr nz, sub_C2BC
        ; End of function move_player
        ; =============== S U B R O U T I N E =======================================
sub_C2B3:
        bit 2, c
        jr z, sub_C2BC
loc_C2B7:
        push bc
        call calc_plyr_dXY
        pop bc
        ; End of function sub_C2B3
        ; =============== S U B R O U T I N E =======================================
sub_C2BC:
        ld a, (ix+11)
        and a
        jp m, loc_C2C7
        bit 3, c
        jr nz, loc_C2C8
loc_C2C7:
        dec a
loc_C2C8:
        dec a
        ld (ix+11), a   ; dZ
        ld (tmp_dZ), a
        add a, 2
        call m, audio_B63C
        call adj_for_out_of_bounds
        call handle_exit_screen
        call add_dXYZ
        bit 2, (ix+12)
        jr z, clear_dX_dY
        ld a, (tmp_dZ)
        and a
        jp p, clear_dX_dY
        res 3, (ix+12)
        ; Identical to Knight Lore
clear_dX_dY:
        xor a
        ld (ix+9), a   ; dX=0
        ld (ix+10), a   ; dY=0
        ret
        ; End of function sub_C2BC
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
calc_plyr_dXY:
        ld a, (ix+9)
        add a, (ix+14)
        ld (ix+9), a
        ld a, (ix+10)
        add a, (ix+15)
        ld (ix+10), a
        xor a
        ld (ix+14), a
        ld (ix+15), a
        ld bc, off_C32F
loc_C312:
        call get_sprite_dir
        ld l, a
        jp jump_to_tbl_entry
        ; End of function calc_plyr_dXY
        ; Different to Knight Lore
        ; =============== S U B R O U T I N E =======================================
get_sprite_dir:
        push hl
        ld a, (ix+7)
        rrca
        rrca
        rrca
        and 8
        ld l, a
        ld a, (ix+0)
        and 4
        or l
        rrca
        rrca
        and 3
        pop hl
        ret
        ; End of function get_sprite_dir
        ; ---------------------------------------------------------------------------
off_C32F:
        DW move_plyr_W   ; dX -= 3
        DW move_plyr_E   ; dX += 3
        DW move_plyr_N   ; dY += 3
        DW move_plyr_S   ; dY -= 3
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
move_plyr_W:
        ld a, (ix+9)
        add a, 0xFD   ; 'ý'
loc_C33C:
        ld (ix+9), a
        ret
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
move_plyr_E:
        ld a, (ix+9)
        add a, 3
        jr loc_C33C
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
move_plyr_N:
        ld a, (ix+10)
        add a, 3
loc_C34C:
        ld (ix+10), a
        ret
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
move_plyr_S:
        ld a, (ix+10)
        add a, 0xFD   ; 'ý'
        jr loc_C34C
        ; =============== S U B R O U T I N E =======================================
adj_dZ_for_out_of_bounds:
        ld a, (room_size_Z)
        ld d, a
loc_C35B:
        ld a, (ix+3)
        add a, h
        cp d
        ret nc
        set 2, (ix+12)
        ld a, h
        call adj_d_for_out_of_bounds
        ld h, a
        jr nz, loc_C35B
        ret
        ; End of function adj_dZ_for_out_of_bounds
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
handle_exit_screen:
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 0, (ix+7)
        ret z
        res 0, (ix+7)
        ld bc, screen_move_tbl
        ld hl, (room_size_X)
        push hl
        jp loc_C312
        ; End of function handle_exit_screen
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
adj_d_for_out_of_bounds:
        and a
        ret z
        jp p, loc_C38D
        inc a
        inc a
loc_C38D:
        dec a
        ret
        ; End of function adj_d_for_out_of_bounds
        ; ---------------------------------------------------------------------------
screen_move_tbl:
        DW screen_west
        DW screen_east
        DW screen_north
        DW screen_south
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
screen_west:
        pop hl
        ld a, 128
        sub l
        ld l, a
        ld a, (ix+1)
        add a, (ix+9)
        add a, (ix+4)
        cp l
        ret nc
        ld (ix+1), 0
        ld a, (ix+8)
        ld l, a
        dec a
        ; Identical to Knight Lore
screen_e_w:
        and 0xF
        ld h, a
        ld a, l
        and 0xF0   ; 'ð'
        or h
        ; Identical to Knight Lore (except sparkle sprite)
exit_screen:
        ld (ix+8), a
        ld a, (ix+12)
        or 0x40   ; '@'
        ld (ix+12), a
        ld a, (ix+0)
        sub 0x10
        cp 0x40   ; '@'
        ret nc
        inc sp
        inc sp
        inc sp
        inc sp
        push ix
        pop hl
        ld de, plyr_spr_1_scratchpad
        ld bc, 64
        ldir
        ld a, (plyr_spr_1_scratchpad)
        ld (byte_CA2D), a
        ld a, (plyr_spr_2_scratchpad)
        ld (byte_CA4D), a
        ld a, 0x38   ; '8'          ; sparkles
        ld (plyr_spr_1_scratchpad), a
        ld (plyr_spr_2_scratchpad), a
        jp game_loop
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
screen_east:
        pop hl
        ld a, l
        add a, 128
        ld l, a
        ld a, (ix+1)
        add a, (ix+9)
        sub (ix+4)
        cp l
        ret c
        ld (ix+1), 0xFF
        ld a, (ix+8)
        ld l, a
        inc a
        jr screen_e_w
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
screen_north:
        pop hl
        ld a, h
        add a, 128
        ld h, a
        ld a, (ix+2)
        add a, (ix+10)
        sub (ix+5)
        cp h
        ret c
        ld (ix+2), 0xFF
        ld a, (ix+8)
        add a, 16
        jr exit_screen
        ; ---------------------------------------------------------------------------
        ; Identical to Knight Lore
screen_south:
        pop hl
        ld a, 128
        sub h
        ld h, a
        ld a, (ix+2)
        add a, (ix+10)
        add a, (ix+5)
        cp h
        ret nc
        ld (ix+2), 0
        ld a, (ix+8)
        sub 16
        jp exit_screen
        ; Identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
adj_for_out_of_bounds:
        bit 1, (ix+7)
        ret nz
        set 1, (ix+7)
        ld a, (ix+12)
        and 0xF8   ; 'ø'
        ld (ix+12), a
        ld l, 0
        ld c, l
        ld a, (ix+11)
        and a
        ld h, a
        jr z, dZ_ok
        call adj_dZ_for_out_of_bounds
        ld a, h
        and a
        jr z, dZ_ok
        call adj_dZ_for_obj_intersect
dZ_ok:
        ld a, (ix+9)
        and a
        ld c, a
        jr z, loc_C478
        call adj_dX_for_out_of_bounds
        ld a, c
        and a
        jr z, loc_C478
        call adj_dX_for_obj_intersect
loc_C478:
        ld a, (ix+10)
        and a
        ld l, a
        jr z, loc_C489
        call adj_dY_for_out_of_bounds
        ld a, l
        and a
        jr z, loc_C489
        call adj_dY_for_obj_intersect
loc_C489:
        ld (ix+9), c
        ld (ix+10), l
        ld (ix+11), h
        res 1, (ix+7)
        ret
        ; End of function adj_for_out_of_bounds
        ; =============== S U B R O U T I N E =======================================
adj_dX_for_obj_intersect:
        ld iy, graphic_objs_tbl
        ld b, 56
loc_C49D:
        call is_object_not_ignored
        jr z, loc_C4DE
        call do_objs_intersect_on_y
        jr nc, loc_C4DE
        call do_objs_intersect_on_z
        jr nc, loc_C4DE
loc_C4AC:
        call do_objs_intersect_on_x
        jr nc, loc_C4DE
        set 0, (ix+12)
        ld a, (ix+13)
        rrca
        and 0x40   ; '@'
        or (iy+13)
        ld (iy+13), a
        rlca
        and 0x40   ; '@'
        or (ix+13)
        ld (ix+13), a
        bit 2, (iy+7)
        jr z, loc_C4D6
        ld a, (ix+9)
        ld (iy+9), a
loc_C4D6:
        ld a, c
        call adj_d_for_out_of_bounds
        ld c, a
        ret z
        jr loc_C4AC
        ; ---------------------------------------------------------------------------
loc_C4DE:
        ld de, 32
        add iy, de
        djnz loc_C49D
        ret
        ; End of function adj_dX_for_obj_intersect
        ; =============== S U B R O U T I N E =======================================
adj_dY_for_obj_intersect:
        ld iy, graphic_objs_tbl
        ld b, 56
loc_C4EC:
        call is_object_not_ignored
        jr z, loc_C52D
        call do_objs_intersect_on_x
        jr nc, loc_C52D
        call do_objs_intersect_on_z
        jr nc, loc_C52D
loc_C4FB:
        call do_objs_intersect_on_y
        jr nc, loc_C52D
        set 1, (ix+12)
        ld a, (ix+13)
        rrca
        and 0x40   ; '@'
        or (iy+13)
        ld (iy+13), a
        rlca
        and 0x40   ; '@'
        or (ix+13)
        ld (ix+13), a
        bit 2, (iy+7)
        jr z, loc_C525
        ld a, (ix+10)
        ld (iy+10), a
loc_C525:
        ld a, l
        call adj_d_for_out_of_bounds
        ld l, a
        ret z
        jr loc_C4FB
        ; ---------------------------------------------------------------------------
loc_C52D:
        ld de, 32
        add iy, de
        djnz loc_C4EC
        ret
        ; End of function adj_dY_for_obj_intersect
        ; =============== S U B R O U T I N E =======================================
adj_dZ_for_obj_intersect:
        ld iy, graphic_objs_tbl
        ld b, 56
loc_C53B:
        call is_object_not_ignored
        jr z, loc_C5A1
        call do_objs_intersect_on_x
        jr nc, loc_C5A1
        call do_objs_intersect_on_y
        jr nc, loc_C5A1
loc_C54A:
        call do_objs_intersect_on_z
        jr nc, loc_C5A1
        set 2, (ix+12)
        ld a, (ix+13)
        rrca
        and 0x40   ; '@'
        or (iy+13)
        ld (iy+13), a
        rlca
        and 0x40   ; '@'
        or (ix+13)
        ld (ix+13), a
        bit 2, (ix+7)
        jr z, loc_C599
        ld a, (ix+0)
        sub 0x10
        cp 0x20   ; ' '
        jr nc, loc_C57B
        set 3, (iy+13)
loc_C57B:
        ld a, (ix+11)
        ld (iy+11), a
        ld a, (ix+9)
        and a
        jr nz, loc_C58D
        ld a, (iy+9)
        ld (ix+9), a
loc_C58D:
        ld a, (ix+10)
        and a
        jr nz, loc_C599
        ld a, (iy+10)
        ld (ix+10), a
loc_C599:
        ld a, h
        call adj_d_for_out_of_bounds
        ld h, a
        ret z
        jr loc_C54A
        ; ---------------------------------------------------------------------------
loc_C5A1:
        ld de, 32
        add iy, de
        djnz loc_C53B
        ret
        ; End of function adj_dZ_for_obj_intersect
        ; identical to Knight Lore
        ; =============== S U B R O U T I N E =======================================
do_objs_intersect_on_x:
        ld a, (ix+4)
        add a, (iy+4)
        ld d, a
        ld a, (ix+1)
        add a, c
        sub (iy+1)
        jp p, loc_C5BC
        neg
loc_C5BC:
        sub d
        ret
        ; End of function do_objs_intersect_on_x
        ; =============== S U B R O U T I N E =======================================
do_objs_intersect_on_y:
        ld a, (ix+5)
        add a, (iy+5)
        ld d, a
        ld a, (ix+2)
        add a, l
        sub (iy+2)
        jp p, loc_C5D1
        neg
loc_C5D1:
        sub d
        ret
        ; End of function do_objs_intersect_on_y
        ; =============== S U B R O U T I N E =======================================
do_objs_intersect_on_z:
        ld a, (ix+3)
        add a, h
        sub (iy+3)
        jp p, loc_C5E4
        neg
        ld d, (ix+6)
loc_C5E2:
        sub d
        ret
        ; ---------------------------------------------------------------------------
loc_C5E4:
        ld d, (iy+6)
        jr loc_C5E2
        ; End of function do_objs_intersect_on_z
        ; =============== S U B R O U T I N E =======================================
adj_dX_for_out_of_bounds:
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 0, (ix+7)
        ret nz
        ld a, (room_size_X)
        ld b, a
loc_C5F8:
        ld a, (ix+1)
        add a, c
        sub 128
        jr nc, loc_C602
        neg
loc_C602:
        add a, (ix+4)
        cp b
        ret c
        set 0, (ix+12)
        ld a, c
        call adj_d_for_out_of_bounds
        ld c, a
        jr nz, loc_C5F8
        ret
        ; End of function adj_dX_for_out_of_bounds
        ; =============== S U B R O U T I N E =======================================
adj_dY_for_out_of_bounds:
        ld a, (ix+12)
        and 0xF0   ; 'ð'
        ret nz
        bit 0, (ix+7)
        ret nz
        ld a, (room_size_Y)
        ld b, a
loc_C622:
        ld a, (ix+2)
        add a, l
        sub 0x80   ; ''
        jr nc, loc_C62C
        neg
loc_C62C:
        add a, (ix+5)
        cp b
        ret c
        set 1, (ix+12)
        ld a, l
        call adj_d_for_out_of_bounds
        ld l, a
        jr nz, loc_C622
        ret
        ; End of function adj_dY_for_out_of_bounds
        ; =============== S U B R O U T I N E =======================================
calc_2d_info:
        call calc_pixel_XY
        call flip_sprite
        ld a, (ix+26)   ; pixel X
        and 7   ; bit offset
        ld a, (de)   ; ptr sprite data
        inc de   ; ptr height
        jr z, loc_C64D
        inc a
loc_C64D:
        and 0xF
        ld (ix+24), a   ; sprite data width (bytes)
        ld a, (de)
        ld (ix+25), a   ; sprite data height (lines)
        ret
        ; End of function calc_2d_info
        ; =============== S U B R O U T I N E =======================================
set_draw_objs_overlapped:
        ld iy, graphic_objs_tbl
        call calc_2d_info
        ld b, 56   ; max objects
        ld a, (ix+26)   ; pixel X
        rrca
        rrca
        rrca
        and 0x1F
        ld l, a
        ld a, (ix+30)
        rrca
        rrca
        rrca
        and 0x1F
        ld h, a
        cp l
        jr c, loc_C676
        ld a, l
loc_C676:
        ld e, a
        ld a, l
        add a, (ix+24)
        ld l, a
        ld a, h
        add a, (ix+28)
        cp l
        jr nc, loc_C684
        ld a, l
loc_C684:
        sub e
        ld d, a
        ld a, (ix+27)
        cp (ix+31)
        jr c, loc_C691
        ld a, (ix+31)
loc_C691:
        ld l, a
        ld a, (ix+27)
        add a, (ix+25)
        ld h, a
        ld a, (ix+31)
        add a, (ix+29)
        cp h
        jr nc, loc_C6A3
        ld a, h
loc_C6A3:
        sub l
        ld h, a
loc_C6A5:
        ld a, (iy+0)
        and a
        jr z, loc_C6CC
        bit 4, (iy+7)
        jr nz, loc_C6CC
        ld a, (iy+26)
        rrca
        rrca
        rrca
        and 0x1F
        sub e
        jr c, loc_C6D6
        cp d
loc_C6BD:
        jr nc, loc_C6CC
        ld a, (iy+27)
        sub l
        jr c, loc_C6DD
        cp h
loc_C6C6:
        jr nc, loc_C6CC
        set 4, (iy+7)
loc_C6CC:
        exx
        ld de, 32
        add iy, de
        exx
        djnz loc_C6A5
        ret
        ; ---------------------------------------------------------------------------
loc_C6D6:
        neg
        cp (iy+24)
        jr loc_C6BD
        ; ---------------------------------------------------------------------------
loc_C6DD:
        neg
        cp (iy+25)
        jr loc_C6C6
        ; End of function set_draw_objs_overlapped
        ; ---------------------------------------------------------------------------
upd_20_to_2B:
        call adj_m3_m16
        bit 6, (ix+13)
        jr z, loc_C6F4
        set 6, (ix-19)
        jp loc_B39A
        ; ---------------------------------------------------------------------------
loc_C6F4:
        push ix
        pop de
        ld hl, 0xFFE0
        add hl, de
        push hl
        pop iy
        inc de
        inc hl
        ld bc, 7
        ldir
        dec (ix+6)
        ld a, (iy+0)
        add a, 0x10
        ld (ix+0), a
        ld a, (iy+3)
        add a, 12
        ld (ix+3), a
        call set_draw_objs_overlapped
        ret
        ; =============== S U B R O U T I N E =======================================
list_objects_to_draw:
        push ix
        ld b, 56   ; max objects
        ld de, 32
        ld ix, graphic_objs_tbl
        ld hl, objects_to_draw
        ld c, 0
loc_C72C:
        ld a, (ix+0)
        and a
        jr z, loc_C73A
        bit 4, (ix+7)
        jr z, loc_C73A
        ld (hl), c
        inc hl
loc_C73A:
        inc c
        add ix, de
        djnz loc_C72C
        ld a, 0xFF
        ld (hl), a
        pop ix
        ret
        ; End of function list_objects_to_draw
        ; ---------------------------------------------------------------------------
objects_to_draw:
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xAF, 0x32, 0x1E, 0x5B, 0xDD, 0xE5, 0xFD, 0xE5
        ; ---------------------------------------------------------------------------
calc_display_order_and_render:
        ld de, objects_to_draw
loc_C790:
        ld a, (de)
        inc de
        cp 0xFF
        jp z, loc_C8EA
        bit 7, a
        jr nz, loc_C790
        call get_ptr_object
        ld (render_obj_1), de
        push hl
        pop ix
loc_C7A5:
        ld a, (de)
        inc de
        cp 0xFF
        jp z, loc_C8D5
        bit 7, a
        jr nz, loc_C7A5
        call get_ptr_object
        ld (render_obj_2), de
        push hl
        pop iy
        push ix
        pop bc
        and a
        sbc hl, bc
        jr z, loc_C7A5
        ld c, 0
        ld a, (iy+3)
        add a, (iy+6)
        ld l, a
        ld a, (ix+3)
        sub l
        jr nc, loc_C7E0
        ld a, (ix+3)
        add a, (ix+6)
        ld l, a
        ld a, (iy+3)
        sub l
        jr c, loc_C7DF
        inc c
loc_C7DF:
        inc c
loc_C7E0:
        ld a, (iy+2)
        add a, (iy+5)
        ld l, a
        ld a, (ix+2)
        sub (ix+5)
        sub l
        jr nc, loc_C806
        ld a, (ix+2)
        add a, (ix+5)
        ld l, a
        ld a, (iy+2)
        sub (iy+5)
        sub l
        ld a, c
        jr c, loc_C803
        add a, 3
loc_C803:
        add a, 3
        ld c, a
loc_C806:
        ld a, (iy+1)
        add a, (iy+4)
        ld l, a
        ld a, (ix+1)
        sub (ix+4)
        sub l
        jr nc, loc_C82C
        ld a, (ix+1)
        add a, (ix+4)
        ld l, a
        ld a, (iy+1)
        sub (iy+4)
        sub l
        ld a, c
        jr c, loc_C829
        add a, 9
loc_C829:
        add a, 9
        ld c, a
loc_C82C:
        ld l, c
        ld bc, off_C833
        jp jump_to_tbl_entry
        ; ---------------------------------------------------------------------------
off_C833:
        DW continue_1
        DW continue_1
        DW continue_1
        DW d_3467121516
        DW d_3467121516
        DW continue_1
        DW d_3467121516
        DW d_3467121516
        DW continue_1
        DW continue_1
        DW continue_2
        DW continue_2
        DW d_3467121516
        DW objs_coincide
        DW continue_2
        DW d_3467121516
        DW d_3467121516
        DW continue_1
        DW continue_1
        DW continue_2
        DW continue_2
        DW continue_1
        DW continue_2
        DW continue_2
        DW continue_1
        DW continue_1
        DW continue_1
        ; ---------------------------------------------------------------------------
continue_1:
        jp loc_C7A5
        ; ---------------------------------------------------------------------------
continue_2:
        jp loc_C7A5
        ; ---------------------------------------------------------------------------
d_3467121516:
        ld hl, (render_obj_2)
        dec hl
        ld c, (hl)
        ld de, render_list
loc_C877:
        ld a, (de)
        cp 0xFF
        jr z, loc_C882
        cp c
        jr z, loc_C898
        inc de
        jr loc_C877
        ; ---------------------------------------------------------------------------
loc_C882:
        ld a, c
        ld (de), a
        inc de
        ld a, 0xFF
        ld (de), a
        push iy
        pop ix
        ld hl, (render_obj_2)
        ld (render_obj_1), hl
        ld de, objects_to_draw
        jp loc_C7A5
        ; ---------------------------------------------------------------------------
loc_C898:
        ld hl, objects_to_draw
loc_C89B:
        ld a, (hl)
        inc hl
        cp 0xFF
        jp z, calc_display_order_and_render
        cp c
        jr nz, loc_C89B
        push iy
        pop ix
        jr loc_C8D8
        ; ---------------------------------------------------------------------------
objs_coincide:
        ld a, (ix+7)
        or (iy+7)
        and 2
        jp nz, loc_C7A5
        ld a, (ix+0)
        sub 0x60   ; '`'
        cp 4
        jr nc, loc_C8C5
        ld (ix+0), 0x40   ; '@'
        jr loc_C8D2
        ; ---------------------------------------------------------------------------
loc_C8C5:
        ld a, (iy+0)
        sub 0x60   ; '`'
        cp 4
        jr nc, loc_C8D2
        ld (iy+0), 0x40   ; '@'
loc_C8D2:
        jp loc_C7A5
        ; ---------------------------------------------------------------------------
loc_C8D5:
        ld hl, (render_obj_1)
loc_C8D8:
        dec hl
        set 7, (hl)
        ld a, 0xFF
        ld (render_list), a
        ld hl, rendered_objs_cnt
        inc (hl)
        call loc_D013
        jp calc_display_order_and_render
        ; ---------------------------------------------------------------------------
loc_C8EA:
        pop iy
        pop ix
        ret
        ; ---------------------------------------------------------------------------
render_list:
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        DB 0xFF
        ; =============== S U B R O U T I N E =======================================
check_user_input:
        ld a, (byte_5B23)
        ld c, a
        ld a, (byte_5B24)
        or c
        ld c, 0
        jp nz, finished_input
        ld a, (user_input_method)
        rrca
        and 3
        jp z, keyboard
        dec a
        jr z, kempston
        dec a
        jr z, cursor
interfaceii:
        ld a, 0xF7   ; '÷'
        call read_key
        push bc
        ld b, 5
loc_C923:
        rra
        rl c
        djnz loc_C923
        ld a, c
        pop bc
        ld c, a
        ld a, 0xEF   ; 'ï'
        call read_key
        or c
        ld c, 0
        bit 0, a
        jr z, loc_C939
        set 3, c
loc_C939:
        bit 1, a
        jr z, loc_C93F
        set 2, c
loc_C93F:
        bit 2, a
        jr z, loc_C945
        set 4, c
loc_C945:
        bit 3, a
        jr z, loc_C94B
        set 1, c
loc_C94B:
        bit 4, a
        jr z, loc_C951
        set 0, c
loc_C951:
        jp finished_input
        ; ---------------------------------------------------------------------------
kempston:
        in a, (0x1F)
        ld c, 0
        bit 0, a
        jr z, loc_C95E
        set 1, c
loc_C95E:
        bit 1, a
        jr z, loc_C964
        set 0, c
loc_C964:
        bit 2, a
        jr z, loc_C96A
        set 4, c
loc_C96A:
        bit 3, a
        jr z, loc_C970
        set 2, c
loc_C970:
        bit 4, a
        jr z, loc_C976
        set 3, c
loc_C976:
        jp finished_input
        ; ---------------------------------------------------------------------------
cursor:
        ld c, 0
        ld a, 0xF7   ; '÷'
        call read_key
        bit 4, a
        jr z, loc_C986
        set 0, c
loc_C986:
        ld a, 0xEF   ; 'ï'
        call read_key
        bit 0, a
        jr z, loc_C991
        set 3, c
loc_C991:
        bit 3, a
        jr z, loc_C997
        set 2, c
loc_C997:
        bit 2, a
        jr z, loc_C99D
        set 1, c
loc_C99D:
        bit 4, a
        jr z, finished_input
        set 4, c
        jr finished_input
        ; ---------------------------------------------------------------------------
keyboard:
        ld a, 0xFE   ; 'þ'
        call read_key
        rrca
        ld c, a
        and 3
        srl c
        srl c
        or c
        and 3
        ld c, a
        ld a, 0x7F   ; ''
        call read_key
        bit 1, a
        jr z, loc_C9C1
        set 1, c
loc_C9C1:
        bit 2, a
        jr z, loc_C9C7
        set 0, c
loc_C9C7:
        bit 3, a
        jr z, loc_C9CD
        set 1, c
loc_C9CD:
        bit 4, a
        jr z, loc_C9D3
        set 0, c
loc_C9D3:
        ld a, 0xBD   ; '½'
        call read_key
        jr z, loc_C9DC
        set 2, c
loc_C9DC:
        ld a, 0xDB   ; 'Û'
        call read_key
        jr z, loc_C9E5
        set 3, c
loc_C9E5:
        ld a, 0xE7   ; 'ç'
        call read_key
        jr z, finished_input
        set 4, c
finished_input:
        ld a, 0x7E   ; '~'
        call read_key
        and 0x1E
        push bc
        ld b, a
        ld a, 0x99   ; ''
        call read_key
        or b
        pop bc
        jr z, loc_CA02
        set 5, c
loc_CA02:
        ld a, c
        ld (user_input), a
        ret
        ; End of function check_user_input
        ; =============== S U B R O U T I N E =======================================
lose_life:
        ; FUNCTION CHUNK AT RAM:A68E SIZE 00000032 BYTES
        ; FUNCTION CHUNK AT RAM:B761 SIZE 00000094 BYTES
        ; FUNCTION CHUNK AT RAM:B8A9 SIZE 00000027 BYTES
        ld hl, plyr_spr_1_scratchpad
        ld de, graphic_objs_tbl
        push de
        pop ix
        ld bc, 64
        ldir
        ld hl, lives
        dec (hl)
        jp m, game_over
        ret
        ; End of function lose_life
        ; ---------------------------------------------------------------------------
plyr_spr_1_scratchpad:
        DB 0, 0, 0, 0, 0, 0, 0, 0
start_loc_1:
        DB 0, 0, 0, 0
flags12_1:
        DB 0, 0, 0, 0
byte_CA2D:
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
plyr_spr_2_scratchpad:
        DB 0, 0, 0, 0, 0, 0, 0, 0
start_loc_2:
        DB 0, 0, 0, 0, 0, 0, 0, 0
byte_CA4D:
        DB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
plyr_spr_init_data:
        DB 0x38, 0x80, 0x80, 0x40, 7, 7, 0xC, 0x1C, 0x38, 0x80, 0x80, 0x4C, 7, 7, 0xB, 0x1C
        ; =============== S U B R O U T I N E =======================================
init_start_location:
        ld hl, plyr_spr_init_data
        ld de, plyr_spr_1_scratchpad
        ld bc, 8
        ldir
        ld de, plyr_spr_2_scratchpad
        ld bc, 8
        ldir
        ld a, 22
        ld (byte_CA2D), a
        ld a, 38
        ld (byte_CA4D), a
        ld a, (seed_1)
        and 3
        ld l, a
        ld h, 0
        ld bc, start_locations
        add hl, bc
        ld a, (hl)
        ld (start_loc_1), a
        ld (start_loc_2), a
        ret
        ; End of function init_start_location
        ; ---------------------------------------------------------------------------
start_locations:
        DB 19, 78, 136, 215
        ; =============== S U B R O U T I N E =======================================
build_screen_objects:
        ; FUNCTION CHUNK AT RAM:B863 SIZE 0000001B BYTES
        ld a, (not_1st_screen)
        and a
        jr z, loc_CAAB
        call update_special_objs
loc_CAAB:
        call retrieve_screen
        call clear_scrn_buffer
        call find_special_objs_here
        call adjust_plyr_xyz_for_room_size
        xor a
        ld (unk_5B3A), a
        ld (unk_5B42), a
        ld (byte_5B43), a
        ld a, (graphic_objs_tbl+8)
        cpl
        and 1
        ld (byte_5B3B), a
        ld a, 1
        ld (render_status_info), a
        jp flag_room_visited
        ; End of function build_screen_objects
        ; =============== S U B R O U T I N E =======================================
set_room_attrs:
        ld hl, location_tbl
        ld bc, block_type_tbl   ; end of location table
        inc hl
loc_CAD9:
        ld e, (hl)
        inc hl
        ld a, (hl)   ; size and attributes
        rrca
        rrca
        rrca
        and 7   ; attr2
        ld d, a
        ld a, (hl)   ; size and attributes
        and 0xF8   ; 'ø'             ; mask off attr1
        or d   ; set attr1=attr2
        ld (hl), a   ; store
        ld d, 0
        add hl, de   ; next entry
        and a
        sbc hl, bc   ; done?
        ret nc   ; yes, return
        add hl, bc
        jr loc_CAD9   ; loop
        ; End of function set_room_attrs
        ; =============== S U B R O U T I N E =======================================
transfer_sprite:
        ld a, (hl)
        inc hl
        ld (ix+0), a
        ld a, (hl)
        inc hl
        ld (ix+7), a
        ld a, (hl)
        inc hl
        ld (ix+26), a
        ld a, (hl)
        inc hl
        ld (ix+27), a
        ret
        ; End of function transfer_sprite
        ; =============== S U B R O U T I N E =======================================
transfer_sprite_and_print:
        call transfer_sprite
        push hl
        call print_sprite
        pop hl
        ret
        ; End of function transfer_sprite_and_print
        ; =============== S U B R O U T I N E =======================================
display_panel:
        ld ix, sprite_scratchpad
        ld hl, panel_data
        call transfer_sprite
        ld de, 0xF810
        ld b, 5
        call multiple_print_sprite
        call transfer_sprite
        ld de, 0x800
        ld b, 6
        call multiple_print_sprite
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite
        ld de, 0xF8F0
        ld b, 5
        call multiple_print_sprite
        call transfer_sprite
        ld de, 0x800
        ld b, 6
        call multiple_print_sprite
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        jp transfer_sprite_and_print
        ; End of function display_panel
        ; ---------------------------------------------------------------------------
panel_data:
        DB 9, 0, 0x10, 0x30
        DB 0xA, 0, 0, 0
        DB 7, 0, 0, 0x30
        DB 8, 0, 0x60, 0
        DB 9, 0x40, 0xE0, 0x30
        DB 0xA, 0x40, 0xF8, 0
        DB 7, 0x40, 0xF0, 0x30
        DB 8, 0x40, 0x90, 0
        DB 0xC, 0, 0x70, 0
        DB 0x54, 0, 0xE0, 9
        DB 0x54, 0x40, 0xC8, 9
        DB 0x83, 0, 8, 0x18
        ; =============== S U B R O U T I N E =======================================
print_border:
        ld ix, sprite_scratchpad
        ld hl, border_data
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite_and_print
        call transfer_sprite
        ld de, 8
        ld b, 24
        call multiple_print_sprite
        call transfer_sprite
        ld b, 24
        call multiple_print_sprite
        call transfer_sprite
        ld de, 0x100
        ld b, 128
        call multiple_print_sprite
        call transfer_sprite
        ld b, 128
        jp multiple_print_sprite
        ; End of function print_border
        ; ---------------------------------------------------------------------------
border_data:
        DB 4, 0, 0, 0xA0
        DB 4, 0x40, 0xE0, 0xA0
        DB 4, 0xC0, 0xE0, 0
        DB 4, 0x80, 0, 0
        DB 6, 0, 0x20, 0xA8
        DB 6, 0x80, 0x20, 0
        DB 5, 0, 0, 0x20
        DB 5, 0x40, 0xE8, 0x20
        ; ---------------------------------------------------------------------------
colour_panel:
        xor a
        ld hl,  zxaram+0x2B6
        ld bc, 0x103
        call fill_window
        ld hl,  zxaram+0x2BD
        ld bc, 0x103
        call fill_window
        ld a, 0x42   ; 'B'
        ld hl,  zxaram+0x297
        ld bc, 0x604
        jp fill_window
        ; =============== S U B R O U T I N E =======================================
adjust_plyr_xyz_for_room_size:
        ld a, (room_size_X)
        sub 2
        ld l, a
        ld a, (room_size_Y)
        sub 2
        ld h, a
        ld a, (ix+1)
        and a
        jr z, loc_CC60
        inc a
        jr z, loc_CC50
        ld a, (ix+2)
        and a
        jr z, loc_CC43
        inc a
        jr z, loc_CC20
        ret
        ; ---------------------------------------------------------------------------
loc_CC20:
        ld c, 0xC8   ; 'È'
        call adjust_plyr_Z_for_arch
        ld a, 0x80   ; ''
        sub h
        sub (ix+5)
loc_CC2B:
        ld (ix+2), a
loc_CC2E:
        set 4, (ix+7)
        set 4, (ix+39)
        ld a, (ix+1)
        ld (ix+33), a
        ld a, (ix+2)
        ld (ix+34), a
        ret
        ; ---------------------------------------------------------------------------
loc_CC43:
        ld c, 0x52   ; 'R'
        call adjust_plyr_Z_for_arch
        ld a, h
        add a, 0x80   ; ''
        add a, (ix+5)
        jr loc_CC2B
        ; ---------------------------------------------------------------------------
loc_CC50:
        ld c, 0xAE   ; '®'
        call adjust_plyr_Z_for_arch
        ld a, 0x80   ; ''
        sub l
        sub (ix+4)
loc_CC5B:
        ld (ix+1), a
        jr loc_CC2E
        ; ---------------------------------------------------------------------------
loc_CC60:
        ld c, 0x38   ; '8'
        call adjust_plyr_Z_for_arch
        ld a, l
        add a, 0x80   ; ''
        add a, (ix+4)
        jr loc_CC5B
        ; End of function adjust_plyr_xyz_for_room_size
        ; =============== S U B R O U T I N E =======================================
adjust_plyr_Z_for_arch:
        ld iy, other_objs_here
        ld de, 0x40   ; '@'
        ld b, 4
loc_CC76:
        ld a, (iy+0)
        cp 4
        ret nc
        ld a, (iy+1)
        add a, (iy+2)
        cp c
        jr z, loc_CC8A
        add iy, de
        djnz loc_CC76
        ret
        ; ---------------------------------------------------------------------------
loc_CC8A:
        ld a, (iy+3)
        ld (ix+3), a
        add a, 12
        ld (ix+35), a
        ret
        ; End of function adjust_plyr_Z_for_arch
        ; =============== S U B R O U T I N E =======================================
get_ptr_object:
        push bc
        and 0x7F   ; ''
        ld l, a
        ld h, 0
        add hl, hl
        add hl, hl
        add hl, hl
        add hl, hl
        add hl, hl
        ld bc, graphic_objs_tbl
        add hl, bc
        pop bc
        ret
        ; End of function get_ptr_object
        ; =============== S U B R O U T I N E =======================================
retrieve_screen:
        ld hl, block_type_tbl
        ld (block_type_tbl_base), hl
        xor a
        ld (unk_5B19), a
        ld (byte_5B25), a
        ld de, other_objs_here
        ld bc, block_type_tbl
        ld hl, location_tbl
find_screen:
        ld a, (hl)
        inc hl
        cp (ix+8)
        jr z, found_screen
        ld a, (hl)
        call add_HL_A
        and a
        sbc hl, bc
        jr nc, zero_end_of_graphic_objs_tbl
        add hl, bc
        jr find_screen
        ; ---------------------------------------------------------------------------
zero_end_of_graphic_objs_tbl:
        ld hl, font
        and a
        sbc hl, de
        ret z
        ld b, 32
        call zero_DE
        jr zero_end_of_graphic_objs_tbl
        ; ---------------------------------------------------------------------------
found_screen:
        ld b, (hl)
        inc hl
        ld a, (hl)
        and 7
        ld (curr_room_attrib), a
        ld (word_5B34), hl
        push de
        ex de, hl
        ld a, (de)
        inc de
        rlca
        rlca
        and 3
        ld c, a
        add a, a
        add a, c
        ld hl, room_size_tbl
        call add_HL_A
        ld a, (hl)
        inc hl
        ld (room_size_X), a
        ld a, (hl)
        inc hl
        ld (room_size_Y), a
        ld a, (hl)
        ld (room_size_Z), a
        dec b
        dec b
        ex de, hl
        pop de
next_bg_obj:
        ld a, (hl)
        inc hl
        cp 0xFF
        jr z, find_fg_objs
        push bc
        push hl
        ld l, a
        ld h, 0
        add hl, hl
        ld bc, background_type_tbl
        add hl, bc
        ld a, (hl)
        inc hl
        ld h, (hl)
        ld l, a
next_bg_obj_sprite:
        ld bc, 8
        ldir
        ld a, (ix+8)
        ld (de), a
        inc de
        ld b, 0x17
        call zero_DE
        ld a, (hl)
        and a
        jr nz, next_bg_obj_sprite
        pop hl
        pop bc
        djnz next_bg_obj
        jp zero_end_of_graphic_objs_tbl
        ; ---------------------------------------------------------------------------
find_fg_objs:
        dec b
        push iy
        push de
        pop iy
next_fg_obj:
        ld a, (hl)
        and 7
        inc a
        ld c, a
        ld a, (hl)
        inc hl
        dec b
        ld d, (hl)
        inc hl
        push hl
        rrca
        rrca
        and 0x3E   ; '>'
        jp z, loc_CE00
        cp 0x3E   ; '>'
        jp z, loc_CDF0
        ld hl, (block_type_tbl_base)
        call add_HL_A
        ld a, (hl)
        inc hl
        ld h, (hl)
        ld l, a
next_fg_obj_in_count:
        push hl
next_fg_obj_sprite:
        ld a, (hl)
        inc hl
        ld (iy+0), a
        ld a, (hl)
        inc hl
        ld (iy+4), a
        ld a, (hl)
        inc hl
        ld (iy+5), a
        ld a, (hl)
        inc hl
        ld (iy+6), a
        ld a, (hl)
        inc hl
        ld (iy+7), a
        ld a, (ix+8)
        ld (iy+8), a
        ld a, (unk_5B19)
        rlca
        rlca
        rlca
        and 8
        ld e, a
        ld a, d
        rlca
        rlca
        rlca
        rlca
        and 0x70   ; 'p'
        add a, e
        add a, 0x48   ; 'H'
        ld (iy+1), a
        ld a, (unk_5B19)
        rlca
        rlca
        and 8
        ld e, a
        ld a, d
        rlca
        and 0x70   ; 'p'
        add a, e
        add a, 0x48   ; 'H'
        ld (iy+2), a
        ld a, d
        rlca
        rlca
        and 3
        add a, a
        add a, a
        ld e, a
        add a, a
        add a, e
        ld e, a
        ld a, (unk_5B19)
        add a, e
        and 0xFC   ; 'ü'
        ld e, a
        ld a, (room_size_Z)
        add a, e
        ld (iy+3), a
        push bc
        ld bc, 9
        add iy, bc
        ld b, 0x17
loc_CDCA:
        ld (iy+0), 0
        inc iy
        djnz loc_CDCA
        pop bc
        ld a, (hl)
        and a
        jr nz, next_fg_obj_sprite
        pop de
        pop hl
        dec b
        jr z, loc_CDE8
        dec c
        jp z, next_fg_obj
        ld a, (hl)
        inc hl
        push hl
        ex de, hl
        ld d, a
        jp next_fg_obj_in_count
        ; ---------------------------------------------------------------------------
loc_CDE8:
        push iy
        pop de
        pop iy
        jp zero_end_of_graphic_objs_tbl
        ; ---------------------------------------------------------------------------
loc_CDF0:
        ld hl, (block_type_tbl_base)
        ld a, 0x40   ; '@'
        call add_HL_A
        ld (block_type_tbl_base), hl
loc_CDFB:
        dec b
        pop hl
        jp next_fg_obj
        ; ---------------------------------------------------------------------------
loc_CE00:
        ld a, d
        ld (unk_5B19), a
        jr loc_CDFB
        ; End of function retrieve_screen
        ; =============== S U B R O U T I N E =======================================
add_HL_A:
        add a, l
        ld l, a
        ld a, h
        adc a, 0
        ld h, a
        ret
        ; End of function add_HL_A
        ; =============== S U B R O U T I N E =======================================
HL_equals_DE_x_A:
        push bc
        ld hl, 0
        ld b, 8
loc_CE13:
        add hl, hl
        rlca
        jr nc, loc_CE18
        add hl, de
loc_CE18:
        djnz loc_CE13
        pop bc
        ret
        ; End of function HL_equals_DE_x_A
        ; =============== S U B R O U T I N E =======================================
zero_DE:
        xor a
fill_DE:
        ld (de), a
        inc de
        djnz fill_DE
        ret
        ; End of function zero_DE
        ; =============== S U B R O U T I N E =======================================
audio_CE22:
        ld a, 0x7E   ; '~'
        call read_key
        bit 0, a
        ret z
        and 0x1E
        ret nz
loc_CE2D:
        ld a, 0x7E   ; '~'
        call read_key
        bit 0, a
        jr nz, loc_CE2D
        call toggle_FE_bit4_x24
loc_CE39:
        ld a, 0x7E   ; '~'
        call read_key
        bit 0, a
        jr z, loc_CE39
loc_CE42:
        ld a, 0x7E   ; '~'
        call read_key
        bit 0, a
        jr nz, loc_CE42
        jp toggle_FE_bit4_x24
        ; End of function audio_CE22
        ; =============== S U B R O U T I N E =======================================
clr_graphic_objs_tbl:
        ld hl, graphic_objs_tbl
        ld bc, 0x700
        jr clr_mem
        ; End of function clr_graphic_objs_tbl
        ; =============== S U B R O U T I N E =======================================
clr_mem:
        ld e, 0
fill_mem:
        ld (hl), e
        inc hl
        dec bc
        ld a, b
        or c
        jr nz, fill_mem
        ret
        ; End of function clr_mem
        ; ---------------------------------------------------------------------------
        ; START OF FUNCTION CHUNK FOR clear_scrn
loc_CE60:
        ld hl, zxvram
        ld bc, 0x1800
        jr clr_mem
        ; END OF FUNCTION CHUNK FOR clear_scrn
        ; =============== S U B R O U T I N E =======================================
clr_attr:
        ld a, 0x42   ; 'B'
fill_attr:
        ld e, a
        ld hl, zxaram
        ld bc, 0x300
        jr fill_mem
        ; End of function clr_attr
        ; =============== S U B R O U T I N E =======================================
clear_scrn:
        ; FUNCTION CHUNK AT RAM:CE60 SIZE 00000008 BYTES
        xor a
        out (0xFE), a
        call clr_attr
        jr loc_CE60
        ; End of function clear_scrn
        ; =============== S U B R O U T I N E =======================================
clear_scrn_buffer:
        ld bc, 0x1800
        ld hl, vidbuf
        ld e, 0
        jr fill_mem
        ; End of function clear_scrn_buffer
        ; =============== S U B R O U T I N E =======================================
update_screen:
        ld hl, vidbuf
        ld de,  zxvram+0x17E0
        ld bc, 0xC020
loc_CE8E:
        push bc
        push de
        ld b, 0
        ldir
        pop de
        dec d
        ld a, d
        cpl
        and 7
        jr nz, loc_CEA6
        ld a, e
        sub 0x20   ; ' '
        ld e, a
        jr c, loc_CEA6
        ld a, d
        add a, 8
        ld d, a
loc_CEA6:
        pop bc
        dec b
        jr nz, loc_CE8E
        ret
        ; End of function update_screen
        ; =============== S U B R O U T I N E =======================================
render_dynamic_objects:
        xor a
        ld (objs_wiped_cnt), a
        push ix
        ld a, (render_status_info)
        and a
        jp nz, loc_CF5F
        ld hl, objects_to_draw
        ld (tmp_objects_to_draw), hl
wipe_next_object:
        ld hl, (tmp_objects_to_draw)
        ld a, (hl)
        inc hl
        ld (tmp_objects_to_draw), hl
        cp 0xFF
        jp z, loc_CF5F
        call get_ptr_object
        push hl
        pop ix
        bit 5, (ix+7)
        jr z, wipe_next_object
        res 5, (ix+7)
        ld a, (ix+26)
        sub (ix+30)
        jp c, loc_CF55
        ld c, (ix+30)
loc_CEE7:
        ld a, (ix+30)
        rrca
        rrca
        rrca
        and 0x1F
        add a, (ix+28)
        ld e, a
        ld a, (ix+26)
        rrca
        rrca
        rrca
        and 0x1F
        add a, (ix+24)
        cp e
        jr c, loc_CF02
        ld e, a
loc_CF02:
        ld a, c
        rrca
        rrca
        rrca
        and 0x1F
        ld b, a
        ld a, e
        sub b
        ld h, a
        ld a, (ix+27)
        sub (ix+31)
        jr c, loc_CF5A
        ld b, (ix+31)
loc_CF17:
        ld a, (ix+31)
        add a, (ix+29)
        ld e, a
        ld a, (ix+27)
        add a, (ix+25)
        cp e
        jr nc, loc_CF28
        ld a, e
loc_CF28:
        sub b
        ld l, a
        ld a, b
        cp 0xC0   ; 'À'
        jr nc, wipe_next_object
        add a, l
        sub 0xC0   ; 'À'
        jr c, loc_CF38
        neg
        add a, l
        ld l, a
loc_CF38:
        call BC_to_Attr_In_DE
        call calc_screen_buffer_addr
        ld a, l
        ld l, c
        ld c, a
        ld a, h
        ld h, b
        ld b, a
        ld a, (objs_wiped_cnt)
        inc a
        ld (objs_wiped_cnt), a
        push bc
        push de
        push hl
        xor a
        call fill_window
        jp wipe_next_object
        ; ---------------------------------------------------------------------------
loc_CF55:
        ld c, (ix+26)
        jr loc_CEE7
        ; ---------------------------------------------------------------------------
loc_CF5A:
        ld b, (ix+27)
        jr loc_CF17
        ; ---------------------------------------------------------------------------
loc_CF5F:
        call objects_to_draw+0x40
        call display_objects_carried
        ld hl, objs_wiped_cnt
        ld a, (rendered_objs_cnt)
        add a, (hl)
        ld (rendered_objs_cnt), a
loc_CF6F:
        ld hl, objs_wiped_cnt
        ld a, (hl)
        and a
        jr z, loc_CF82
        dec (hl)
        pop hl
        pop de
        pop bc
        ld a, b
        ld b, c
        ld c, a
        call blit_to_screen
        jr loc_CF6F
        ; ---------------------------------------------------------------------------
loc_CF82:
        pop ix
        ret
        ; End of function render_dynamic_objects
        ; =============== S U B R O U T I N E =======================================
blit_to_screen:
        push bc
        push de
        push hl
        ld b, 0
        ldir
        pop hl
        ld de, 0x20   ; ' '
        add hl, de
        pop de
        dec d
        ld a, d
        cpl
        and 7
        jr nz, loc_CFA3
        ld a, e
        sub 0x20   ; ' '
        ld e, a
        jr c, loc_CFA3
        ld a, d
        add a, 8
        ld d, a
loc_CFA3:
        pop bc
        djnz blit_to_screen
        ret
        ; End of function blit_to_screen
        ; =============== S U B R O U T I N E =======================================
build_lookup_tbls:
        ld l, 0
loc_CFA9:
        ld d, 0
        ld e, l
        ld h, 0xFF
        ld b, 7
loc_CFB0:
        sla e
        rl d
        ld a, e
        cpl
        ld (hl), a
        dec h
        ld a, d
        cpl
        ld (hl), a
        dec h
        djnz loc_CFB0
        inc l
        jr nz, loc_CFA9
        ld hl, 0xF100
loc_CFC4:
        ld d, l
        ld b, 8
loc_CFC7:
        srl d
        rl e
        djnz loc_CFC7
        ld (hl), e
        inc l
        jr nz, loc_CFC4
        ret
        ; End of function build_lookup_tbls
        ; Identical to Knight Lore with prelude (up to ret NZ)
        ; and sub 104->40
        ; =============== S U B R O U T I N E =======================================
calc_pixel_XY:
        ld a, (byte_5B24)
        and a
        scf
        ret nz
        ld a, (ix+1)   ; X
        add a, (ix+2)   ; add Y
        sub 128
        add a, (ix+18)   ; add pixel_x_adj
        ld (ix+26), a   ; pixel X
        ld a, (ix+2)   ; Y
        sub (ix+1)   ; subtract X
        add a, 128
        srl a
        add a, (ix+3)   ; add Z
        sub 40
        add a, (ix+19)   ; add pixel_y_adj
        ld (ix+27), a   ; pixel Y
        cp 192   ; bottom line of screen?
        ret
        ; End of function calc_pixel_XY
        ; =============== S U B R O U T I N E =======================================
flip_sprite:
        ; FUNCTION CHUNK AT RAM:D174 SIZE 00000077 BYTES
        ld l, (ix+0)
        ld h, 0
        add hl, hl
        ld bc, sprite_tbl
        add hl, bc
        ld e, (hl)
        inc hl
        ld d, (hl)
        ld a, (de)
        and a
        jp nz, vflip_sprite_data
        inc sp
        inc sp
        ret
        ; End of function flip_sprite
        ; ---------------------------------------------------------------------------
loc_D013:
        ld a, (ix+0)
        cp 1
        jr nz, loc_D01F
        ld (ix+0), 0
        ret
        ; ---------------------------------------------------------------------------
loc_D01F:
        res 4, (ix+7)
        call calc_pixel_XY
        ret nc
print_sprite:
        call flip_sprite
        ld a, (ix+26)
        and 7
        jr z, loc_D07E
        rlca
        and 0xE
        or 0xF0   ; 'ð'
        ld h, a
        ld a, (de)
        inc de
        and 7
        inc a
        ld b, a
        ld (ix+24), a
        dec a
        and 7
        add a, a
        add a, a
        add a, a
        add a, a
        neg
        add a, 0x50   ; 'P'
loc_D04B:
        ld (loc_D0BB+1), a
        ld a, b
        cpl
        add a, 0x22   ; '"'
        ld (loc_D10F+1), a
        ld a, (de)
        inc de
        ld (ix+25), a
        add a, (ix+27)
        sub 0xC0   ; 'À'
        jr c, loc_D069
        neg
        add a, (ix+25)
        ld (ix+25), a
loc_D069:
        ld c, (ix+26)
        ld b, (ix+27)
        call calc_screen_buffer_addr
        ld (tmp_SP), sp
        ex de, hl
        ld sp, hl
        ex de, hl
        ld a, (ix+25)
        jr loc_D0B9
        ; ---------------------------------------------------------------------------
loc_D07E:
        ld a, (de)
        inc de
        and 0xF
        ld (ix+24), a
        ld b, a
        add a, a
        add a, a
        add a, a
        neg
        sub 6
        jr loc_D04B
        ; ---------------------------------------------------------------------------
        pop de
        ld a, (bc)
        cpl
        or e
        cpl
        or d
        ld (bc), a
        inc bc
        pop de
        ld a, (bc)
        cpl
        or e
        cpl
        or d
        ld (bc), a
        inc bc
        pop de
        ld a, (bc)
        cpl
        or e
        cpl
        or d
        ld (bc), a
        inc bc
        pop de
        ld a, (bc)
        cpl
        or e
        cpl
        or d
        ld (bc), a
        inc bc
        pop de
        ld a, (bc)
        cpl
        or e
        cpl
        or d
        ld (bc), a
        jp loc_D10E
        ; ---------------------------------------------------------------------------
loc_D0B9:
        ex af, af'
        ld a, (bc)
loc_D0BB:
        jr loc_D0BB
        ; ---------------------------------------------------------------------------
        pop de
        ld l, e
        and (hl)
        ld l, d
        xor (hl)
        cpl
        ld (bc), a
        inc bc
        inc h
        ld l, e
        ld a, (bc)
        and (hl)
        ld l, d
        xor (hl)
        cpl
        dec h
        pop de
        ld l, e
        and (hl)
        ld l, d
        xor (hl)
        cpl
        ld (bc), a
        inc bc
        inc h
        ld l, e
        ld a, (bc)
        and (hl)
        ld l, d
        xor (hl)
        cpl
        dec h
        pop de
        ld l, e
        and (hl)
        ld l, d
        xor (hl)
        cpl
        ld (bc), a
        inc bc
        inc h
        ld l, e
        ld a, (bc)
        and (hl)
        ld l, d
        xor (hl)
        cpl
        dec h
        pop de
        ld l, e
        and (hl)
        ld l, d
        xor (hl)
        cpl
        ld (bc), a
        inc bc
        inc h
        ld l, e
        ld a, (bc)
        and (hl)
        ld l, d
        xor (hl)
        cpl
        dec h
        pop de
        ld l, e
        and (hl)
        ld l, d
        xor (hl)
        cpl
        ld (bc), a
        inc bc
        inc h
        ld l, e
        ld a, (bc)
        and (hl)
        ld l, d
        xor (hl)
        cpl
        dec h
        ld (bc), a
loc_D10E:
        ld a, c
loc_D10F:
        add a, 0
        ld c, a
        ld a, b
        adc a, 0
        ld b, a
        ex af, af'
        dec a
        jp nz, loc_D0B9
        ld sp, (tmp_SP)
        ret
        ; =============== S U B R O U T I N E =======================================
calc_screen_buffer_addr:
        push hl
        srl b
        rr c
        srl b
        rr c
        srl b
        rr c
        ld hl, vidbuf
        add hl, bc
        ld c, l
        ld b, h
        pop hl
        ret
        ; End of function calc_screen_buffer_addr
        ; =============== S U B R O U T I N E =======================================
BC_to_Attr_In_DE:
        ld a, c
        rrca
        rrca
        rrca
        and 0x1F
        ld e, a
        ld a, b
        cpl
        and 7
        ex af, af'
        ld a, b
        cpl
        rlca
        rlca
        and 0xE0   ; 'à'
        or e
        ld e, a
        ld a, b
        cpl
        rrca
        rrca
        rrca
        and 0x18
        ld d, a
        ex af, af'
        or d
        add a, 0x38   ; '8'
        ld d, a
        ret
        ; End of function BC_to_Attr_In_DE
        ; =============== S U B R O U T I N E =======================================
calc_attrib_addr:
        push hl
        ld a, h
        cpl
        ld h, a
        srl h
        srl h
        srl h
        srl h
        rr l
        srl h
        rr l
        srl h
        rr l
        ld de,  zxvram+0x1700
        add hl, de
        ex de, hl
        pop hl
        ret
        ; End of function calc_attrib_addr
        ; ---------------------------------------------------------------------------
        ; START OF FUNCTION CHUNK FOR flip_sprite
vflip_sprite_data:
        push de
        ld a, (de)
        xor (ix+7)
        and 0x80   ; ''
        jr z, loc_D1AF
        ld a, (de)
        xor 0x80   ; ''
        ld (de), a
        rlca
        and 0x7E   ; '~'
        ld b, a
        inc de
        ld a, (de)
        ld c, a
        inc de
        push de
        ld e, b
        ld d, 0
        call HL_equals_DE_x_A
        pop de
        add hl, de
        ex de, hl
        ld a, b
        call add_HL_A
        dec de
        dec hl
        srl c
loc_D19B:
        push bc
vflip_sprite_line_pair:
        ld a, (de)
        ld c, (hl)
        ld (hl), a
        ld a, c
        ld (de), a
        dec hl
        dec de
        djnz vflip_sprite_line_pair
        pop bc
        ld a, b
        sla a
        call add_HL_A
        dec c
        jr nz, loc_D19B
loc_D1AF:
        pop de
        push de
        ld a, (de)
        xor (ix+7)
        and 0x40   ; '@'
        jr z, loc_D1E9
        ld a, (de)
        xor 0x40   ; '@'
        ld (de), a
        and 0xF
        ld b, a
        ld c, a
        inc de
        ld a, (de)
        ex af, af'
        inc de
        ex de, hl
        push hl
        exx
        pop hl
        ld b, 0xF1   ; 'ñ'
        exx
loc_D1CC:
        exx
        ld c, (hl)
        ld a, (bc)
        ld e, a
        inc hl
        ld c, (hl)
        ld a, (bc)
        ld d, a
        inc hl
        push de
        exx
        djnz loc_D1CC
        ld b, c
loc_D1DA:
        pop de
        ld (hl), e
        inc hl
        ld (hl), d
        inc hl
        djnz loc_D1DA
        ex af, af'
        dec a
        jr z, loc_D1E9
        ex af, af'
        ld b, c
        jr loc_D1CC
        ; ---------------------------------------------------------------------------
loc_D1E9:
        pop de
        ret
        ; END OF FUNCTION CHUNK FOR flip_sprite
        ; end of 'RAM'
        ; ===========================================================================
        ; Segment type: Regular
        ORG 0xD200
vidbuf:
        DS 0x1800
        ; end of 'VRAM'
        ; end of file

        SAVEBIN "build/alien8_zx.bin", 0x4000, 0xC000
