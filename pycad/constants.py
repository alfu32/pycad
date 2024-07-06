

TOLERANCE = 2

lwindex = [0, 5, 9, 13, 15, 18, 20, 25,
           30, 35, 40, 50, 53, 60, 70, 80,
           90, 100, 106, 120, 140, 158, 200,
           ]
lwrindex = {0: 0, 5: 1, 9: 2, 13: 3, 15: 4, 18: 5, 20: 5, 25: 6,
            30: 7, 35: 8, 40: 9, 50: 10, 53: 11, 60: 12, 70: 13, 80: 13,
            90: 14, 100: 15, 106: 16, 120: 17, 140: 18, 158: 19, 200: 20,
            }
linetypes = {
    "Continuous": [],
    "Dashed": [10, 10],  # 10 units on, 10 units off
    "DashedLarge": [20, 10],  # 10 units on, 10 units off
    "Dotted": [1, 10],  # 1 unit on, 10 units off
    "DottedLarge": [1, 20],  # 1 unit on, 10 units off
    "DashDot": [10, 5, 1, 5],  # 10 units on, 5 units off, 1 unit on, 5 units off
    "DashDotLarge": [20, 10, 1, 10],  # 10 units on, 5 units off, 1 unit on, 5 units off
    "DashDotDot": [10, 5, 1, 5, 1, 5],  # 10 units on, 5 units off, 1 unit on, 5 units off, 1 unit on, 5 units off
    "DashDotDotLarge": [20, 10, 1, 10, 1, 10]
    # 10 units on, 5 units off, 1 unit on, 5 units off, 1 unit on, 5 units off
}

dxf_app_id = "e8ec01b43m15-PYCAD-1.0.0"