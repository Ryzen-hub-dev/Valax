-- VALAX SHIELD v9 | protected by ValaxScrub
local HttpService = game:GetService('HttpService')
local bitlib = bit32 or bit
if not bitlib then error('[VALAX] bit library missing') end
local bxor, band = bitlib.bxor, bitlib.band
local lshift, rshift = bitlib.lshift, bitlib.rshift
local BUILD_ID = "4V-1nT_QrzWi2jMhjBQ"
local HWID = "AUTO_LOCK_ON_FIRST_RUN"
local PRI = "https://py.valaxscrub.shop/activate_stage"
local FAL = "https://py.valaxscrub.shop/python/activate_stage"
local PARTS = 6
local SEED = 1304571603
local MIN_OPS = 2
local MAX_OPS = 7
local DATA_B64 = table.concat({
  "uju+9qkP7SlDcL6boWjCbtkHpQ2Oikn9eONDAVA5FFzZCtaqhZGshz3kSs2xW4QsMFpNWwNjQEVeQV7/Ude4V7HSnn80NNsqljQhztHoVxwObD840nfVcfWkPA6Q/bTcHc96+wQRaAGw3FIeHkIyOLYJZV5/uZ+Eu71ZzZUR90KqLwszFAoN",
  "pTcCg7zpZe16kXjfTYyqrxsAZh8T5X5LaTEcABQ5tcgsHt9vWHWupdJ2sQ3yg8k/jiyFYVS/Nq9MRAGeRrj9T3TPk+iTz4aINvWgbaff3mUGQPGMzWOU+QnmghzvOIGYf1D25W8OIZq47Oal2HTbH5jzSies3feHiNaNNnf0Dacho623Yjc8",
  "W3Oo0YCxuEf/ZNzrgvQc+lCSVpeImBidNBVzCJhrzyXRabJDkeOu2e03csy+V+8XIKA5OaGN1Id04ViihdmqyXKHQZvBqk+Uz35q49S4FMoiGbNGgRIvEm6HCxNYNPbpv1CcNegKHGQDDmNQw77GR4a48EjyR6Y2RdZpJjGq1iDUOOkwhMNf",
  "5WAWVSYfQcC8/KdX3xYxDD/3kaV1bbMksxAWhT1eorTyrJWBU2YZ98fblhMszYm1m7AIjAASTtVFgCLIJho54jcC463AffhzDYpl9LyJZjrms/iA+A7Rgu3+79t051uV94+sxmAfy/T9EfWzeHXFsr4dtYQSB2WSjYRd5cSxQfHawFIHnqBZ",
  "Nt8KR3PAn1fpHjHAYoN18quAjKFtqRUUGsPh1/C08nMuxuYwQl5pEBGtsT3UvDx6j4tc7jqCoJD+cXhbpE6n+H2No+Whc/wczIoN/aK2VIe/l0Z2CxmiY471au+Tzk4PPgVHgOoqPUWxB3wkFLQNCIA1i3RHlNVcRyeA6SwvKaL5AUX7a/bg",
  "GXkum39HD6V861z9+4DUZuAAAPjl3FkZ4mNtCBFsyEXHubohJ5pz0HTLpGLx6jejyIITKiWbc9g2KtfTNosUVB+/PgzVtPW6ndUpl8I0TNJPsHsNOis8qsWbtL5BakK3Tdj7efIVn1wdWhbGmHlI3sp0Q6MSbfMBEm02mNIUioJV9U6cCs0+",
  "AHPBIl/katGpcMBTMUCv6qSiCdD99+Lu5VeE0KtxUu1M2sNQ2Hj0OYigm4E0uQ5F+yN9Q1fHXWmWqYh28MBpwDJa59HlSpKsPelh4VR+8dt6/G8QadiMgG024JZHy06SVMrU5OgSg8wu4YdKfp/iuQf44kdcmw6HyyMEVyUn3Ct4H4KirrLm",
  "6qJApzygiTCKkOUlng1wAGQ/ZLVTQSf5YX6ZTASlM0yiUon95IJNCdngdYv2ag9mNqluap/V8bEnJpLbv2cX5jf0LYmuQvwjE50QpTTYdFOzNECNILFWraFP+/CfCL2dJ4Q0F6glKsO6RrxtUeo5gtDwgbMxWKlRq/LsH5PuYxdi2gfD0/Wp",
  "wmD9lgVuZsP41RLWRWLZ0PmH+Z433rG5EfTTL3gJ7TWFnNKK7Fwja88d070zNzo1Cc/PKJbXsArRBUO2QUvY3+IRNbB9pFNOdaA+19+z4t2RJIh8di6U5f8xrCe+ASbiGnljg9EbilLj/DWEuevMPZZoD2SDSqNKScVU7o8lf1MOl0aunY7P",
  "3x9t5k1YD9sKrGVsidnoXRTplyOGOckwJYs+ZDyVlKqc7q4/ulEOFZhEvt023XGKWkuNLO+J6Fg3MlFP0hSZXJGSMooSrCf7EcVFC8rZ5uJoqr02X0dqJfGDo2fX04dWkBccn5HUOMu8DH6q5/PiRusrQMWyriLk1Ol8MKLCbj6ApQKwgf5x",
  "8n5T34pjnXCeWVOnS+Cofw9ueNCWSK5HN6Gl5l/3OTEjtbrog36EfL//mMZox56RTXy7NWAdfUVe3AL0BengFzQCPoljqObFHGzwQxUMYN9nU6n1FzEZ6DQz9aIAT6d+fgvdRmpGiLs2dZrjT7ccj/SWUU0Mkp9RjLhIeXOtDroxus7rYLh/",
  "HIsgEymHKqg6GOZ1XWjSwJ4y4pMVTB9PLJVKMKMAD0mXKtx6gLwjzoKzr9N1VsNdOMa8Kn84kA7DVDygtUM9ou0kDZ8gx8OJ1WV8oWYq4hxceWcvo2/yMUhGnzOh0kynYjDvnWuv/UD5953POan44VBWJXiPva1GIuphrpI7ngoozPBHyGLT",
  "Hl+x3wCbRojpe2PW5JzT2OzrgmWq5k2GL1o2iEtFYsgqcAKHgKufv6+DPfWE9GMU9OmY2Op0spEggpToM6iSDj4qFQUUXJbFmumepHzo1kGDECQ4zNXRR5ZXCkCvWEbNIhWhAmxv4kQw9gnMibhNLFi65vyk61u6kv0LiwZPVOi7eZ6aJTim",
  "xgM4XmZhspPNTJRebJKxlsLDfw8xzNemmkZBSH2PkPzs4xPFPbd+m9iqeG6jW0aLZkfyrFM8Dyig98BLbhHNOWXksiEPVlhHvqmD1sbv1yKWfvkNdHvmmObq75m8Ui+hbd+ZbmX+wDVQU9paZa4mKwN4M5VTZt2WTIOVMc2RgakCyoTdE3Dx",
  "8fQE4R2o1wW0cP6np69KbF8aUcDgatuvNiY7SDtdHBufKEIyw1fxPqdruSMa39y9jde4KRxGguVqdIUiO/2z3ajiz3P2AdZeY4s7BTPUuIyAUiPzoMOrVvmCyCiGUZx7R90sQ9iK63/rh14cKKb1ZpjuCQ6RSZogZiCD+M/xneWVI77SD9+w",
  "Wyzw3z/IXQ78V2g/9lGuE0XMjPWNvGvs6+BUk6+M49diviqq7z1YRZV7Bwv7bsM44vjdTv0oNUUh7+8h8eQhA93XhLmtEscHZgICrjZc1F1t7KyeIFLlsQOAJTQDUmUc4XAXA9tZvIgc5wywCrTPLOnppgT+PL9vEITDQqkbDDkwVHLH+jTh",
  "ZqSordY60m9qPoC69xOgORCFoAzg3djLNlrvAEbg4au1P1lJ29cxH4oOMwCoWkWjJUS+yK3YTcQrQHb/VdNr2+MGC2O3JLRjOpWymyb3e9EiE+IKkUJep6i3bD16SBF/guBocYxtVMZmUZVLjw4ngsRKtxcYmI3GZ7wfNNO9quxLfC2A2Gq/",
  "CrXugvmY7OT2uSkQAEKZ+J4YhmGjOw3qTM51YnDWTgx4POwaicNrUHUTxUHmdn07jHZ0SxSPFJTmR6ko0VRl426X7IZHa4jeSDNYUC12k76hz6+ZzXpYlRL4XpzUbkzRaRsVIdmrlr9LD5aKXNbua5fp45pBc2VFwVMFO5bO16SYJJEJ+0aR",
  "+ITrqVp54Ofy0+bu1jL8j1rQFz4cx+4F8KXSmAZp6Vva86AzjozQlP+xirO894W7k01bQvW6+Do93IjQHv9FjPdHznxY2cspHmrEZ7WbsMoJ5h5pGlcU92/vgaHLtXl/j52RcMV5J1GKhRz1PjmAR8XeuRHG9fGmPKpppGbCezZ66pZharv1",
  "yuCCdZblY6icQLsCil4ldnw3hKCPptc7EeWPYwgx3JSjiu7rQPB+8ThR8Bu8MffKwU8V6q167I8+bw7Fq1hUlPlSOyCrN7Zv9gSQ7+zUKpdfL/yzVFuD1yMF54ZZNAuybrhMhEGmcCxwmJUoXzNUd2IgNsNONrmFTzJxE1p0NXDwcDVycaca",
  "cGcNsbGgTjyAXgGHhE+qaCaMRW2P/oEGjlb5c6jSzNmfU6gx4rqDxHBhv9gpDBA2tTrdLIKXy0H/RX68Wno1s/GIpPjze8i0vHXdZytr4lTmRVKd+Q0x7vvggUC2rn/Ka7vwClPpulyzuI2k2A6dDJXNmoLlzxfWDkBVNz8hiy1Dgup9+4k4",
  "sZWzOsoVTRYysOF/T1s1lgAq6UypKGdCnoLNE2ENd2ayG7rXgcaOJbsqSsGXQG53zPsdV/Jb4GRxp5tsVbDUDMXwTlTaHZaPw1MzsCoJH5pgWwnuRVZFTk7SW4yGI/eg/gQBk+V389sJoVYYm4d5vdE8VcbDfWiTNOUgsk1F2T/KtK7sxPj7",
  "dBkNj6Oi29Iukt9BDl2YFUbEuMs7jJ1AIGcS14pZRGsgjDJLed5TfyWnR61wx83Zvzqadj0OsnrFsOOS47gOFxhU/J9iw6eT9mumaFIVUvI8me6GgqjP43wwx6MSx33R29bu8Q1IW6EOUHJHRTonjwQ5PU54vIPeImSuXN12ac2XbEUjuYH6",
  "1SPyi2Stshbx8qpDJHa8X5bB2WlO6JMSSeM9YxshKj7l4IC0y4X8BaDHkAoqp/Gg4Uzb4xD6w74Aq3ERMeSWmpaiCsF+kHgDh9m6MDhf+/CAcaicOIEdo6c9+lBrhetDNOC4v8yqxMCLSihITTP0nRWlMAQ4l5bpCXXqhD6pYI/dR6uAJ0Wd",
  "nl2klrgNC1dpVPUi/XfMq7zLF9q8YyctdqzShAB6nlVxtXRJys1uKSM+FVyqxiQw0Ta0S552tThyQsyvVyuWkasL8fXImVz63JBcxdzZ25uui8Ds+cXWYVj7mY8zwqeRTjaeL3ad9Z+C9w8Vnb54yqQUgr6+3nEsP4rz+cZwok1He0y5aHEV",
  "to4zbYQc2Z8qeJLfp3ds9XV7Nr3dqXUrXRP8caMYG3Lb4D8gYdShCw98rhlGJvte1MTIW8ZPk/dp1wtbxEXCK38A2OSQlhEGQ9KxO/mO7hiLaE0MAkLxCdUx989mYrPQAndY/oQT/Ol3rgkVcnBhOJMZ14Cz7Wk9wVOt9qbOMbUu4jz8wZeH",
  "wMI4dRP1mtxRjFPtwtLSGFe0YLZ41MMo0+yNHdynMf/fZq9GF/EiuSh540oKL5iDrhejBIJPM8WOaJ+TeFIk9tNrHFx9EpopLmVmgEtVD9uHGtKguhay0bIZ344tAQrTDGRqFk789/TgtVCVRv7xaB/aO3UnWEGmgmi+JE7iqkxTkPxlfEqU",
  "Es9qgCG6yGMVJlHDkAGuznrEywkSA2H6wqEOJQHjXx1wvMRyJg7fNcBGCuYmBYLTn2Rhog/ABnGYuv0ZZ+DqmwmkHyx2dt3FM2KJ0RFBtqIfieYVTBe6YZRIvuv2eg0J0K4KxP6F0ivn9Hi9ydjECKS+ujEC61BCHRAgC8GbXLG3AgZUwaX0",
  "17JnjHZvCSClVFsAslSFglPBkFu1nIcAJd8BNSd10WpUg0djhEf23MYi7C62tDaCIzAq+uNM0cqGWwy/lYHCPXmjAHBE1x6c9wpq2vbD7rTfHOvCL8Dq7K778mnp4tJYwNbMUPyPhm89e4c61XYE9S9sEKzDoqmrSMZYNu22RUk76nqNd4nX",
  "h4Zmg20+/A9iEW8RFlbK1smxNmaE/JNh0u7i9A1haiQNnxsOnlvUCkw3JN+LnCSDPlc7K9CidAexuptE7O2nQFTI0BbycaHRZw6lb+NN4uf3nWwyfcgrzxSXSMaNvW60KBsuJcF29gPj8PMHIZOJ9qa9gB4mzihwIfCaZbnUSJ5c/zCH5LK1",
  "sXhVvcdZsKULd5RUqgSS8egEoBANpqY2fCwstWfppY2L/3EbM+DXd8/WhrSn9kTJEUOmVcQMZXWjPF+/jqSJAlfVCYM05PfjEZcFS82xAyoBjOBZjvBCtUqu3fkLcLi/LbO5d6Nr5+3Sc3M+GmEPp10dp8Mky3+ymPG0XaUeMCyjIGyy0cNY",
  "pgENZVz1MqlUjKD93e+vukBSaubqvEvQ8LuSqmOAPg2uPBfN/OL8K9ogBo/UGqy9aux8hCrW9pOxPp+u1vB4AUhlAG7Md5LBiH7zWji5QkjfWohLNmDRSgTCkHs6zM521BfejC0czxyy1y5Ggqtq6FeqQ4otdHfwwSdQG96lbzgXWFzct61g",
  "EkMUIs/yschZGd485RWATAlx1h64Jhz++8K70aBLnPhniEI/R8gYWCHqHVrRGv+9o95UeMITLT4S82BDlXyZtHGbFi6ZyfJrTzb0hAUcGJS3E8LpDKnK72dwzKUImWuH/NYx+/kmstM05atMo0aVcd1zRP83yHKaZ5+8fW+8947KBLwVGd86",
  "z3GZos8MJ+nv88EpNn0HCXHIVTGjbeuoMb68M1JAW7ONHzNe8R8Mz2sfuB0yUXK3ynajHCsC34gamqsIMqHKa9WH/CaXR6pyf6P4a+Hi9444QRyOIIDkBmITjBEqxAnEJBICA9AbVEZ0Gx6+WoENssrG1nSyFHqigXkYT/yJVDGRJNB3SQ1+",
  "qwka4+k6KJrVLA7lzbGH/OdTBeHDjiqgDYB7gcSRFquci0KkzMuFJc6aHTNfuJPQa8EUK6XbVY0ZYK+5cuW9k2y+UH5gwcdffkRduiZpG7Yige9yxPXxNauCedAGlmG+i9cckuF57ukwRSeFquhgnMkWNuld06zxA8rG78jt94auKgs1Z9jB",
  "kMOtH91nFvPz9q5V/lwjaL8p4YVI5MzepVIH5DvBTLiwrC4V010Cg58JW/3k/TFYLPrmifSOmpYnQkVOgfWcPVoMGjPOVmaKbytP2C+UWNKNvfTLuD/7IOn2R2f++hSQWembj8VyNsGvt5un4BJEZbWkXng9ji1xbYjLKQG4OMzIiXx8LsrM",
  "9sa8Trw0fJUkrc0uxRZAUx2ZYYQTPQqG9GXhB7cexH3a1gxAF0m4CE3Zo3v8D/ZTFWM68SFnFhjq3wTUyalzc52Lt9GaVxVbHRR7f9MnrBGqeo+yLm4S4XbMlSAaVil2vF6RMDijJ1H5Jp8B4S7DHYG3yzUZZDHHiHYXOgmFanebmFwZpivS",
  "Bg7fs0YHeE/kdsAgCnhMqYjGMl5yA/thWAt95OIqOHXgfKc26JFNhFue1vvWbn7en7pshv/GLAuwIhvKtZtEGCzAHmM2s7+nrpUw9IwZYvPLXJU/vXuoq9OPrI5WRoWs85/dErxzzEbb11hzsQEcTqA3O4KgJ3QC8yntiw0n3HfaJE3fUAb2",
  "7smGAIMXq7Qapuq0TdfFTzOu0ZRBXgfmVcYMktONlDmf31O/9ygLfn/qVQ+9yTKuZl77tMAANPIfK3Z75ZqOgal6Dq/UvCq9CTPiTaJoDPzk7vMOjMuugAGoIt7+GjbG1TOVIpj0U3w2rMfwr3jbd7ewNZ9J07zoEfVa7rFnz65i0Z96Y3KA",
  "lVNezr0+U5y3pdtKsKPgQnnWTnYdqPEj3FkdCK/P+JPT+CQ4Etd3Kp0iBfi50g6Ct6LIfrlomV2y1oQaqhW4xCH+XxBz1tDsa8mGYRy3GJZ+kPWxGxJsAAZQr1osQutzfweIv8lw0kWBiKzJG4NH1SSZJR8S8y8md8/OZs6wEIaF4PtJ/ThC",
  "buUNX6kVHBj6F/8WbqmpQIuib1zmO7VF4nQyJsAh59ejHCf24EpJ0inZFDNyqjCa65xbWkCWtlu1wM1gb1eH9Z62GsSuWMzANI0QFSsrkiKGjTXMI4p92yTMoMKdKrtFIhGcecNJqbt5u1nwfPskdomA+PZqY0QBsQ47ofnKpODMFMIkqbZf",
  "dqVpoZthx2zbi+Bak7ypcB14a/ohqw8mUoRXz+JdAbhcU67ZIT4s91ZV+FSXRobpriz+4XRR6ylN+RnuZZVi9Evy395cfqSuCTjnDTID/tX83RV0Iwm+HWgq1dNIy+Y9hMOYVOpXIZDCF6/+x7M7v1TIuXuQgLKWmKPqG4oVASQzERk1Ugjb",
  "4Vg7F6L8nNYXPOtbUu2wyx4fdeDGHjfzuDsmdDMiE4RoPrs0DXdAzmzOpWYNbS+nKpDuzgm3pWLF7TB9xXWu6Z5P1BDHmOdvwFQRynuwlcEbmO+V0RtyrKq1CJFLYyKhC7DWn7mURaW01H1gLTHBQVN5ETC261VHdTm3iFJCCQ0IPBmOaa2k",
  "Rest5hBewvInKovQRtkReZXd6Rdmr65qHORyZ6jzPZdprE7osL+Hq1AMtc7lMS8pBPmg1djhk+2IgyRy1O4xSb0UNrP4zy9FMvzjOXEImj0q8SjwQ2YxsNtm2KfNHCVkLJo97+OS23XKINkleDaMpd3XwEtvYNwnQo+ESUDDjkzZqQaMz3b1",
  "QZqFNXwogPIwuoUVI5KQd6g/CKKaLBlAadxI3MKtmOwnUBLiYJw84wKJpHv/+5LIoo+EmSPYjsRuyIXuQ5jHBVAGYvyXIkTx8dmmc1oyrmjllWMADlbCQDHfK5xJRGcSw6WdFEVoWCtwj0cRYHACYQT31FU3j1U4E0PooPgr9g0T5ZtNYyl1",
  "D225Zip0JqeHjkDsl6yAYaJ+VUZKoMnv9FN8oWZqTgYELdNNm4vHu1HRDQsAew22rzN0aHE3iwApG8gR6LNS8qROMhRX0NcXrOFkoyz+vLbvXLXkyFE0YFVmZ31tCDMW07P0QrjzfQ/YrGiFHlZ2AH6rY2SlnwAvuZ0RBbd0n+PMveVWRx4s",
  "FKALw+DuufiwD+Pn7SKBefIZK5BUl3WAgCoVYLkHURG1tNjHqf5BMCD6ZHo4Jsksx4HEZYd+pDOf8aWAVGNjAOhVQ1FRY1ka2B5KC4M7slPrR4LsT98Mtvpfo9WAtkAtkx7qR1ouUlEiHvfRDDJeDbe5J1ice2VIbXCfExthv5i9FxAgo0TA",
  "J5VXfv/61pne19hI6OiWXO5T7PGLpLb0escYEz9VK+Q3wyBGcDROWOOcUnDyUiLq9jF1HzFfef0rOfXVFbPy/FVSHdutmPfrPfJSO71fQx0j3brfLy5JxE8IFAypQ85and8SW4qu4NqSTHAhOncAj38E5qT1AJOBZiz4vWDMgM/eocNC/bSx",
  "pTV3hIOxaIwiTGNLWgWpgTEjXLvaG3O3AJTHYvq3rH4vLZeZW5kilMSqn2uTt/gdFziLn2yUUn3AHUy3IFdn7RAdAVQ1FiIGT/4ixD4YNQHsJyTc2DHTpC+KACzaeFmKmzLUmAj2M7jE4DxKZWgSHKmHMwUhl97Olpd3iBSFSmnlt6L679B4",
  "IXKvMatCFwRoPjXcZ7z9418CoGe3WqFyImwju2aEsIIGJ/8j0piV57FW0BNsrjY1W1lev66CiqklUvpoj8JbdwFIcYbksDLKuxYtycqjzzAG2ULuTI+BTEvlB8A30TeYkZopjtV5dGWBZr6w5Dt8z+QvZWQn/sCTky6JY/gHO5m7qoz2V47z",
  "KJ2oWiZb4tUMXQeJPxVOUGB5G6DSbCoIG14ViGrcK/MIrUN4hHIr9ynd3HcBvzuOv/ROHv5cqiv0OcJQroB8slWWPOmcVmJEMnp93cd+dLpCyVD1G5Oj03c4MUsxm58UDhJOFD1y9k3mWlRSGhJ4kfvEMwt82R6k4EVZ32scxYHQ+ofwqudb",
  "X7WVTt8E3mxOtjOvb58S31EX/brdHaMkXlELZSz/0pOhBW/5hSkL3xj0v8Ce5Tx0xA6L4m0ONQHr4QBdkYdvNTt7NMmBaWFUjZVQo+wWi79WOzW/sE8ZWKAeah/vP1Nxidh4hgJz4B5LboC0YyfkTNm9thDOgXcm6hfNdIIHbMdmHlGd40zu",
  "rNqsvV6N/kSbyY+nDT4bMvV/jeWtovEQNDBG7HZzkipdrU88OLYX0MTmwS3vb0wNQsfjCcRlxDVQ7rOnIcL/zEwEng2xFTVm8zNW1MT8ezmtes2PjKt/S5ENIlxm6AyABmPdnJtUOkLilQkyyrfVR3ZINybvdQSVWivW3Zc5qCNifmThkYso",
  "nYwxGBPAA+VtVCnbmCR/uJGTI3GSi8E/nb1/VPuFwSopK2N/5mQSsACtCRxKWSb6sySwD7LXczPb7I2Ubj4hJTsRNJh+Dc6baqIBNOH6LQ+E1o4fDOt1Hwdsj25v3f2HCoucQraQMFkejX5ASG/1y/Bc+2Do5s9SZQWKQHyFBCuw3I1c4oWe",
  "hALjQdDy7f6i5XhR9WHPIi7XVX4nQfJHEEFW7KO+ql53IhTeIMNqOnR+y0BfiBiKcOJySEKGqsWV+h+bIlfP/5aWq4Q5HNx4unU0ElxJE1ucLNKN5DO5FIqCX3tdmf74e0dynTWYsa8ZjN1X2mVXirDH1PzD6+7ZgmOxwZdXWEm4beGxiPDi",
  "6Gt6OtWOWKNkf22qIORSMS168pCKrU2YJkfGrmYtz9xLYdLsR4bzjAl1fbz42OtlSV6a/gJkd0FLffzITq9sNjeasifVivstze2FDRmDYOMOV8WckiCgctB7j16uWTWlRteG2v/xpZLMQtTwCwu5Hzohs6aChcc6U8QaiHuapczJ3OIt7b6M",
  "h5v7ANsn56uQe9/IlYOM2rWLrDPteMzOL9bi6NX7T+uQmR/z5KoduufNvu0RLWxyHDzLOJa854qS6K/u01w5c5NInbGyjciOQcWhqj1uFipxSecayy/smzzqDkkIuNcgLRbxwBYE9TUmpp1XpG2IQSVacxd2Kew9WThto1te5tJwtRWOdhEL",
  "7Q07fS9LOP2EgR/wHakica2y5RpKIKfsjlrFvlMeLkhoiH37O7hhci8mncojxM/mxQKUApHsq5KR2YLmPZisyMdihPBNK6EhaRWHyHgOjfUb9QMOQMHib7IyiZPqdGv3cBFmiudFQe8C/QvUhvRWaBo9h/BIzGDinQ/Hlltqa+AgHZXQL9SR",
  "x6nU628mcM/oSkFxMfFWOjCD56pEvwqBWAsc5AuIS0ZElFtblcVR6IpEZl1/hXOrwKC3XRHP6E9An3t7dtozsjk5TNVBDxewml8mUdXdLs0S/DEMRMApCHcyjPRk4qabOQe4nSRrgvQtuBFW64hu0InCMtTv1XUHYXgcS/4YORHE9o7wuQ62",
  "l0DWJiE12I0VBiDPj6PtYUrmbnZEeNVDabSdS+QbwXlum9TLkJQ4eoSNjN7lejMcc37Sl4uRO+Xr7vIkWPlzvOEoJEpdA6kAYRHod/k5nzgUp/Ycxjft3KfyQckXnGwvkOJhp1095bYMkJz7kJQOMnwpwmPvLmv6HFanCOl4B3Ll2E41dPt9",
  "Gm1IVNXgASSQiOTaJ1sOEVDfDLSG3NGSfSd7LkXw2rec1opQ+nTVK6seVbL3Nok5iQiAp0KFKuWJ4wxJPyjRWo9RrSVjY6E49ra+Koo8ym87IJcN7GiPV3N8WuWjyzEj2/2DK2enHdL+r/x+cSgiZbDC1CbbxuCU+6Bz7VLTFcPpcyx2innN",
  "Yd8Sg5YpsSJocpus8elqI116joHP1isJR9DxGrxD+u19b6dzAN1Q9hBQ2BlyIGY22Bl1dMaqjDnLpzjr3oZwlrK2fnvalKfYSwuzqVAoBfQCSRQOeKPw+brtsA/q44/3C1QG7N3/v+BZLBIlilCQBhq/qlBurxVCfMnW2MNuqeqRfglXsyUR",
  "ec3cdiMWDZ0YXIPwYCzbPBsp/phTuvG0nYPyke3kc4ItL3B1/xqhWsD5WDT6exLsxu88SkKts0nX/+/MiJNfnMzLjsG6+/yCw0ZrAzY++8VHJsdBlld1eG+OkPPqy1rPlSWhxv3BTgtngral4BVo2nuVSys35Ctc5C2y9sKIHyYGUPgy3UN3",
  "gb5e6vAbFMl1un+Pv+TBPmaXF3ONbZkPEY8VKW+it4V8FOl3wxsjXrJkldUi3cDX8P64L0zJYgy+liPLP08hqpfbIhXAq9fj5XLpQ8erp90vcWdam6WlhpbVtW8tb23OGDiPUKsFaOGVrNzy6oGiUKW4g107SREq97rrhIo3oHpoWVtClcGe",
  "JgrYXyLx0fz9jSQ1DN/vuXSIpp1AOF1xxUM1E/OWdvfJXg1ziMey1VofFyWk7COpreR6zJZVyAZlrL4MDPEdSsEgJPqGMcALatp06Mvchq6W+3rNyBhIfWqdVQpAEuadlMTxPNuUGv50OiEJlU5MyLKrg89wCz7EqoLUwPuwupyX5lrGzI2z",
  "e2V3wF3gvMFsGKw5AsnmS/o1RhICxwf1FKyuLCWjedFzALED2BfTjy8R4VCrcNUd0P0gM86Af1fJYuThVScaI8FhqZ6Ir1r/cKd5zLAU/sQ84p+siOvs+FJCi4DOB5PsH915XQoJmWFk92bgYygHMhu6exVOnYmNyznJSbTRhN7S8zyeBPOb",
  "AmTu380XNdmEAPtdH7E30U1KIXd2pyyno47wZgKMzL/CGYajM5sO0neSC7LLo4Dxyxw53xAcP0cSa8xoW/jvQaOCky+DDK4hfv6MvP0DyVC+isIoDnXm4ePwLjFL0ICOtH67NVFWr9Oj8dFeQReoHscz8LKFLQ8TeOKcxky0cH6pNtXBmmOb",
  "2SNBc3Bb3CNkYkGUUJ+ydwXydcMN82rV7evizv57jG2Fq6kKg2fvfrRiTjq05Qq2tJeG3OUQQeVzfWv/NrUeM6LOq6bmyb7962HfdjBnWRT0h9+3Q793hHnppUHqQAJ5/5hz2+ThvmTh7i3j1etyOnpmrozV01caU9uhwK+b8mcoSj6cyvzU",
  "6Hz/LR8t6vDDytGb/hcjB3sFJAyhbMq3BUM51aRjNMZgCb5jE3SqJ2pcZKMaKvGaQJYo8d5lqiM4V02wsXHMpPJdpjnHPwPvLQeao+4Ra5EwdCc10W15Z04U0U2pi/Xao8HQNjgkswtlKUSglN5R+d+HFn7qRZNWdt18/pJW1FzSXy93q0kV",
  "9dQJd4bsp4XxZubAkoJCKsAkZ7jQb47v/9COUcUcszASDw701v15JGTUWvmYDCa7/bZY3YylyeY3Du2dz8jno5Sh8bbZbA0iZa8mFVafpwbBqbvArPmJniSArGMcInRlgopkEYXW3htkufbfXs8+URc9/Br8wm4k6YYhnJzhu0EXmG4Hte4c",
  "DQ2oVDPfybDJgYjUN1xocT+qLd0ptmRBOUwTyWrAX2cdXv3P+/9X4qOP89e/CJYcxpPj3BMK/riAde2BCYLnxX09zN03t4iFXJYVRGpM3KGtJilkVrveJHMQJTIX6ncQ3nABryuXtpVydpuA8sDB8BN7XeGlY3lzpnDVMppIJnvtzVGndZmu",
  "LoSoCLaSHp3MxaCTt+BinFUzM+lI+E6WfnSQhTgqZgN6y7RbEdZbsvGQftjHaLWE73A5sslmzQdvaYPghYtOnfYJQ8m03ydwJ7fkWPOTS1H1GQsH5CmbAH/wOMd9exobT7yxV6Pz/yCS3QPfoMqYHz7OWqzyNnJoie7UP2Kin09Y292iXtaV",
  "+KnCHVqZTiFlEvC0UQAx7Ytek35/Rnsm4yksJndLt3ZZPi/uhxxlvfoP5RcwUP1MM4O3Ipl2LZHMCvh1Z5kRaV3ZCS/LCQIaD8kCF7XW5XyoP58cU3onfT/pwnDlKj2rRxhx2oH8K5VCzbXfk3pL8gmeyz7ZkXJLdL5NDTwdWcc+B80pmh0K",
  "CLH4wg24dtYXgnki4wZkqfXr1WCE+3Vnz1jBMiWernz2+v1xusd+p9OJrDSs3hE8Wy96VJm1IwMopBGKHWQjTSwa2UuDP1lg93G/IIjiKhh9A5KctAl+lXTCB/rb5NbKBu3E5Xo5rCH0mAW43OZPp/TvzOnbjA4dGec3qSfVWS8dWoDS+tIC",
  "NW82uf2Hxsf0gLr6/i49kKD++o5b4WF+QATfRSfSCyB8wJwLy++xLBXuv++ZG9a1cDWUx5FjMlmfDdA28902r4Ilnd/FxgA5BABh7r7tv1W1EtaFxCKBcr6KCmtmEN3v/VSWcj5MjIkDfYl2nms1sRNCPRthlVL8fB7fXBV7x9gXBg0S+fIg",
  "1171jE7+VCMTgR6J6QGZWhS3C8m6pA2h2tWLvVITrpf4ma2muw/4BFKognGhaf7xhKdb3izN5bpCQivMIb5ZibiVwPCX50rYE2vFrZfMCJvI9+/9YuKrvFybSufe89XBk5aYCtJgk6oLH7Yhm07Iyke6+nGYPtHPAoqnKIsB3CN9xek3cEcA",
  "5YM0K+QS1gQkQrR2A/DPIFR4ugjGzfo=",
})
local function rol8(v, n) n = n % 8 return band(lshift(v, n) + rshift(v, 8 - n), 0xff) end
local function ror8(v, n) n = n % 8 return band(rshift(v, n) + lshift(v, 8 - n), 0xff) end
local function lcg(x) return band((1103515245 * x + 12345), 0xffffffff) end
local function reverse_byte(v, idx, token)
 local state = band(bxor(bxor(SEED, ((idx + 1) * 2654435761)), ((token + 1) * 2246822519)), 0xffffffff)
 local spread = (MAX_OPS - MIN_OPS) + 1
 local n = MIN_OPS + (state % spread)
 state = lcg(state)
 local ops = {}
 for r = 1, n do
  local op = band(state, 0x0f)
  state = lcg(state)
  local par = (band(bxor(bxor(bxor(state, (idx * 17)), (token * 31)), (r - 1)), 0xffffffff) % 255) + 1
  state = lcg(state)
  ops[r] = {op, par}
 end
 local cur = v
 for r = n, 1, -1 do
  local op = ops[r][1]
  local par = ops[r][2]
  if op == 0 then cur = bxor(cur, par)
  elseif op == 1 then cur = band(cur - par, 0xff)
  elseif op == 2 then cur = band(cur + par, 0xff)
  elseif op == 3 then cur = ror8(cur, (par % 7) + 1)
  elseif op == 4 then cur = rol8(cur, (par % 7) + 1) end
 end
 return cur
end
local ok_raw, raw = pcall(function() return HttpService:Base64Decode(DATA_B64) end)
if not ok_raw or type(raw) ~= 'string' then warn('[VALAX] Base64 decode failed') return end
local DATA = {}
for i = 1, #raw do DATA[i] = string.byte(raw, i) end
local function post_json(url, payload) return HttpService:PostAsync(url, HttpService:JSONEncode(payload), Enum.HttpContentType.ApplicationJson) end
for stage = 0, PARTS - 1 do
 local req = {build_id = BUILD_ID, hwid = HWID, stage = stage, nonce = tostring(math.random(100000, 999999)) .. tostring(os.clock())}
 local ok, resp = pcall(function() return post_json(PRI, req) end)
 if not ok then ok, resp = pcall(function() return post_json(FAL, req) end) end
 if not ok then warn('[VALAX] Backend unreachable') return end
 local j = HttpService:JSONDecode(resp)
 if not j or j.status ~= 'ok' then warn('[VALAX] Activation failed') return end
 local off = tonumber(j.offset) or -1
 local len = tonumber(j.length) or 0
 local token = tonumber(j.mutation_token) or 0
 if off < 0 or len <= 0 then warn('[VALAX] Invalid stage payload') return end
 local ok_pad, pad_raw = pcall(function() return HttpService:Base64Decode(j.pad_b64 or '') end)
 if not ok_pad or type(pad_raw) ~= 'string' or #pad_raw ~= len then warn('[VALAX] Pad mismatch') return end
 for i = 0, len - 1 do
  local pos = off + i + 1
  local b = DATA[pos]
  if b == nil then warn('[VALAX] Range overflow') return end
  local dec = reverse_byte(b, pos - 1, token)
  DATA[pos] = bxor(dec, string.byte(pad_raw, i + 1))
 end
 task.wait(math.random() * 0.03)
end
local chars = {}
for i = 1, #DATA do chars[i] = string.char(DATA[i]); DATA[i] = 0 end
local src = table.concat(chars)
chars = nil; collectgarbage()
local loader = (loadstring or load)(src, '@Valax_Shield_v9')
if type(loader) ~= 'function' then warn('[VALAX] Compile failed') return end
local run_ok, run_err = pcall(loader)
if not run_ok then warn('[VALAX] Runtime error: ' .. tostring(run_err)) end
warn('[VALAX] Activation complete')