# WaterfallBench leaderboard (single-call harness)

| model | tasks | fully resolved % | non-trivial acc % | line-item acc % | ±$1 acc % | answered % | mean input tok | mean output tok | mean s | est $/task | est $ total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-6-astra | 20 | 95.0 | 99.2 | 99.6 | 100.0 | 100.0 | 407,039 | 2,558 | 64 | 8.33 | 166.65 |
| anthropic/claude-fable-5-2 | 20 | 95.0 | 99.1 | 99.6 | 100.0 | 100.0 | 632,454 | 3,053 | 35 | 5.18 | 103.64 |
| openai/gpt-6-luna | 20 | 90.0 | 99.2 | 98.7 | 98.7 | 100.0 | 407,039 | 7,811 | 87 | 0.09 | 1.75 |
| fireworks/glm-5p3 | 20 | 75.0 | 95.7 | 98.0 | 98.5 | 100.0 | 420,329 | 21,057 | 161 | 0.68 | 13.62 |
| fireworks/minimax-m3p1-flash | 20 | 50.0 | 89.0 | 89.1 | 90.1 | 95.0 | 400,871 | 17,419 | 106 | 0.07 | 1.41 |
| fireworks/kimi-k3p1-pro | 20 | 45.0 | 92.3 | 96.1 | 96.1 | 100.0 | 412,055 | 6,632 | 107 | 0.89 | 17.81 |
| anthropic/claude-haiku-5-5 | 20 | 40.0 | 85.8 | 93.8 | 95.7 | 100.0 | 632,454 | 10,714 | 59 | 0.34 | 6.86 |

## Per task

| model | task | category | fully resolved | non-trivial | line-item | ±$1 | fields | input tok | output tok | est $ | s | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-haiku-5-5 | fw-carmax-2025-2-2025-04 | C1 | no | 89% | 96% | 96% | 24 | 629,698 | 9,344 | 0.34 | 53 |  |
| anthropic/claude-haiku-5-5 | fw-carmax-2025-3-2025-07 | C1 | no | 83% | 93% | 96% | 27 | 632,551 | 12,242 | 0.35 | 64 |  |
| anthropic/claude-haiku-5-5 | fw-carmax-2025-4-2025-10 | C1 | no | 83% | 93% | 93% | 27 | 633,700 | 10,387 | 0.34 | 59 |  |
| anthropic/claude-haiku-5-5 | fw-carmax-2026-1-2026-01 | C1 | no | 75% | 89% | 89% | 27 | 647,530 | 12,302 | 0.35 | 66 |  |
| anthropic/claude-haiku-5-5 | fw-carmax-2026-2-2026-04 | C1 | yes | 100% | 100% | 100% | 27 | 647,909 | 10,797 | 0.35 | 46 |  |
| anthropic/claude-haiku-5-5 | fw-carmax-2026-3-2026-07 | C1 | no | 73% | 88% | 100% | 24 | 614,998 | 9,681 | 0.33 | 53 |  |
| anthropic/claude-haiku-5-5 | fw-deere-2025-b-2025-08 | C1 | yes | 100% | 100% | 100% | 16 | 503,783 | 9,445 | 0.28 | 49 |  |
| anthropic/claude-haiku-5-5 | fw-deere-2026-2026-04 | C1 | no | 86% | 94% | 94% | 16 | 501,473 | 9,958 | 0.28 | 55 |  |
| anthropic/claude-haiku-5-5 | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 522,651 | 10,628 | 0.29 | 58 |  |
| anthropic/claude-haiku-5-5 | fw-nissanlease-2025-a-2025-01 | C1 | no | 75% | 88% | 100% | 24 | 725,064 | 6,931 | 0.38 | 47 |  |
| anthropic/claude-haiku-5-5 | fw-nissanlease-2025-b-2025-07 | C1 | no | 75% | 88% | 88% | 24 | 712,865 | 7,584 | 0.38 | 51 |  |
| anthropic/claude-haiku-5-5 | fw-nissanlease-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 24 | 739,161 | 8,448 | 0.39 | 53 |  |
| anthropic/claude-haiku-5-5 | fw-nissanlease-2026-b-2026-07 | C1 | no | 75% | 88% | 88% | 24 | 732,825 | 6,759 | 0.38 | 46 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2025-a-2025-01 | C1 | no | 57% | 86% | 90% | 21 | 614,546 | 13,398 | 0.34 | 74 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2025-b-2025-05 | C1 | yes | 100% | 100% | 100% | 21 | 624,079 | 11,271 | 0.34 | 61 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2025-c-2025-08 | C1 | yes | 100% | 100% | 100% | 20 | 629,893 | 14,560 | 0.35 | 73 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2025-d-2025-10 | C1 | yes | 100% | 100% | 100% | 21 | 638,804 | 14,449 | 0.36 | 81 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2026-a-2026-02 | C1 | no | 89% | 95% | 100% | 22 | 627,265 | 10,998 | 0.34 | 48 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2026-b-2026-05 | C1 | no | 56% | 82% | 82% | 22 | 633,802 | 12,931 | 0.35 | 68 |  |
| anthropic/claude-haiku-5-5 | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 636,492 | 12,175 | 0.35 | 68 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 629,698 | 2,022 | 5.12 | 20 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2025-3-2025-07 | C1 | yes | 100% | 100% | 100% | 27 | 632,551 | 2,805 | 5.17 | 26 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2025-4-2025-10 | C1 | yes | 100% | 100% | 100% | 27 | 633,700 | 2,198 | 5.16 | 22 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2026-1-2026-01 | C1 | yes | 100% | 100% | 100% | 27 | 647,530 | 2,160 | 5.27 | 56 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2026-2-2026-04 | C1 | yes | 100% | 100% | 100% | 27 | 647,909 | 1,925 | 5.26 | 20 |  |
| anthropic/claude-fable-5-2 | fw-carmax-2026-3-2026-07 | C1 | no | 82% | 92% | 100% | 24 | 614,998 | 1,827 | 4.99 | 19 |  |
| anthropic/claude-fable-5-2 | fw-deere-2025-b-2025-08 | C1 | yes | 100% | 100% | 100% | 16 | 503,783 | 2,356 | 4.12 | 25 |  |
| anthropic/claude-fable-5-2 | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 501,473 | 1,940 | 4.09 | 20 |  |
| anthropic/claude-fable-5-2 | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 522,651 | 2,628 | 4.29 | 28 |  |
| anthropic/claude-fable-5-2 | fw-nissanlease-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 24 | 725,064 | 1,768 | 5.87 | 47 |  |
| anthropic/claude-fable-5-2 | fw-nissanlease-2025-b-2025-07 | C1 | yes | 100% | 100% | 100% | 24 | 712,865 | 1,820 | 5.78 | 20 |  |
| anthropic/claude-fable-5-2 | fw-nissanlease-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 24 | 739,161 | 1,662 | 5.98 | 19 |  |
| anthropic/claude-fable-5-2 | fw-nissanlease-2026-b-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 732,825 | 1,898 | 5.94 | 20 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 21 | 614,546 | 2,773 | 5.03 | 28 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2025-b-2025-05 | C1 | yes | 100% | 100% | 100% | 21 | 624,079 | 2,923 | 5.11 | 30 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2025-c-2025-08 | C1 | yes | 100% | 100% | 100% | 20 | 629,893 | 4,891 | 5.23 | 50 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2025-d-2025-10 | C1 | yes | 100% | 100% | 100% | 21 | 638,804 | 3,371 | 5.25 | 36 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 22 | 627,265 | 6,807 | 5.29 | 69 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2026-b-2026-05 | C1 | yes | 100% | 100% | 100% | 22 | 633,802 | 4,575 | 5.25 | 61 |  |
| anthropic/claude-fable-5-2 | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 636,492 | 8,716 | 5.44 | 91 |  |
| openai/gpt-6-astra | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 398,211 | 1,752 | 8.10 | 69 |  |
| openai/gpt-6-astra | fw-carmax-2025-3-2025-07 | C1 | yes | 100% | 100% | 100% | 27 | 400,779 | 1,584 | 8.13 | 43 |  |
| openai/gpt-6-astra | fw-carmax-2025-4-2025-10 | C1 | yes | 100% | 100% | 100% | 27 | 401,588 | 1,910 | 8.18 | 38 |  |
| openai/gpt-6-astra | fw-carmax-2026-1-2026-01 | C1 | yes | 100% | 100% | 100% | 27 | 410,151 | 1,657 | 8.33 | 35 |  |
| openai/gpt-6-astra | fw-carmax-2026-2-2026-04 | C1 | yes | 100% | 100% | 100% | 27 | 410,413 | 1,471 | 8.32 | 29 |  |
| openai/gpt-6-astra | fw-carmax-2026-3-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 390,877 | 1,516 | 7.93 | 29 |  |
| openai/gpt-6-astra | fw-deere-2025-b-2025-08 | C1 | yes | 100% | 100% | 100% | 16 | 322,822 | 3,891 | 6.75 | 100 |  |
| openai/gpt-6-astra | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 321,931 | 2,665 | 6.64 | 70 |  |
| openai/gpt-6-astra | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 336,546 | 3,179 | 6.97 | 82 |  |
| openai/gpt-6-astra | fw-nissanlease-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 24 | 484,137 | 1,420 | 9.79 | 50 |  |
| openai/gpt-6-astra | fw-nissanlease-2025-b-2025-07 | C1 | yes | 100% | 100% | 100% | 24 | 470,971 | 1,374 | 9.52 | 42 |  |
| openai/gpt-6-astra | fw-nissanlease-2026-a-2026-02 | C1 | no | 83% | 92% | 100% | 24 | 492,958 | 1,293 | 9.96 | 29 |  |
| openai/gpt-6-astra | fw-nissanlease-2026-b-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 487,029 | 1,335 | 9.84 | 28 |  |
| openai/gpt-6-astra | fw-worldomni-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 21 | 391,696 | 3,363 | 8.09 | 82 |  |
| openai/gpt-6-astra | fw-worldomni-2025-b-2025-05 | C1 | yes | 100% | 100% | 100% | 21 | 396,898 | 2,342 | 8.11 | 86 |  |
| openai/gpt-6-astra | fw-worldomni-2025-c-2025-08 | C1 | yes | 100% | 100% | 100% | 20 | 402,057 | 4,541 | 8.38 | 105 |  |
| openai/gpt-6-astra | fw-worldomni-2025-d-2025-10 | C1 | yes | 100% | 100% | 100% | 21 | 408,222 | 3,242 | 8.41 | 71 |  |
| openai/gpt-6-astra | fw-worldomni-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 22 | 400,744 | 2,856 | 8.23 | 67 |  |
| openai/gpt-6-astra | fw-worldomni-2026-b-2026-05 | C1 | yes | 100% | 100% | 100% | 22 | 404,933 | 4,112 | 8.41 | 91 |  |
| openai/gpt-6-astra | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 407,818 | 5,648 | 8.58 | 138 |  |
| openai/gpt-6-luna | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 398,211 | 5,462 | 0.08 | 66 |  |
| openai/gpt-6-luna | fw-carmax-2025-3-2025-07 | C1 | yes | 100% | 100% | 100% | 27 | 400,779 | 6,977 | 0.09 | 81 |  |
| openai/gpt-6-luna | fw-carmax-2025-4-2025-10 | C1 | yes | 100% | 100% | 100% | 27 | 401,588 | 5,897 | 0.08 | 63 |  |
| openai/gpt-6-luna | fw-carmax-2026-1-2026-01 | C1 | no | 83% | 93% | 93% | 27 | 410,151 | 6,758 | 0.09 | 72 |  |
| openai/gpt-6-luna | fw-carmax-2026-2-2026-04 | C1 | yes | 100% | 100% | 100% | 27 | 410,413 | 6,781 | 0.09 | 82 |  |
| openai/gpt-6-luna | fw-carmax-2026-3-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 390,877 | 6,476 | 0.08 | 72 |  |
| openai/gpt-6-luna | fw-deere-2025-b-2025-08 | C1 | yes | 100% | 100% | 100% | 16 | 322,822 | 11,691 | 0.07 | 132 |  |
| openai/gpt-6-luna | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 321,931 | 9,163 | 0.07 | 105 |  |
| openai/gpt-6-luna | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 336,546 | 10,531 | 0.08 | 118 |  |
| openai/gpt-6-luna | fw-nissanlease-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 24 | 484,137 | 4,249 | 0.10 | 50 |  |
| openai/gpt-6-luna | fw-nissanlease-2025-b-2025-07 | C1 | yes | 100% | 100% | 100% | 24 | 470,971 | 4,244 | 0.10 | 48 |  |
| openai/gpt-6-luna | fw-nissanlease-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 24 | 492,958 | 6,569 | 0.10 | 70 |  |
| openai/gpt-6-luna | fw-nissanlease-2026-b-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 487,029 | 4,815 | 0.10 | 54 |  |
| openai/gpt-6-luna | fw-worldomni-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 21 | 391,696 | 10,079 | 0.09 | 108 |  |
| openai/gpt-6-luna | fw-worldomni-2025-b-2025-05 | C1 | yes | 100% | 100% | 100% | 21 | 396,898 | 9,019 | 0.09 | 92 |  |
| openai/gpt-6-luna | fw-worldomni-2025-c-2025-08 | C1 | yes | 100% | 100% | 100% | 20 | 402,057 | 9,541 | 0.09 | 108 |  |
| openai/gpt-6-luna | fw-worldomni-2025-d-2025-10 | C1 | no | 100% | 81% | 81% | 21 | 408,222 | 6,813 | 0.09 | 76 |  |
| openai/gpt-6-luna | fw-worldomni-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 22 | 400,744 | 10,308 | 0.09 | 110 |  |
| openai/gpt-6-luna | fw-worldomni-2026-b-2026-05 | C1 | yes | 100% | 100% | 100% | 22 | 404,933 | 12,681 | 0.09 | 135 |  |
| openai/gpt-6-luna | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 407,818 | 8,161 | 0.09 | 89 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 403,541 | 3,867 | 0.85 | 77 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2025-3-2025-07 | C1 | yes | 100% | 100% | 100% | 27 | 406,118 | 5,035 | 0.86 | 96 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2025-4-2025-10 | C1 | no | 75% | 89% | 89% | 27 | 406,905 | 3,173 | 0.85 | 57 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2026-1-2026-01 | C1 | yes | 100% | 100% | 100% | 27 | 415,556 | 4,855 | 0.88 | 85 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2026-2-2026-04 | C1 | no | 83% | 93% | 93% | 27 | 415,825 | 4,697 | 0.88 | 65 |  |
| fireworks/kimi-k3p1-pro | fw-carmax-2026-3-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 396,144 | 3,722 | 0.83 | 60 |  |
| fireworks/kimi-k3p1-pro | fw-deere-2025-b-2025-08 | C1 | no | 86% | 94% | 94% | 16 | 328,000 | 19,460 | 0.85 | 241 |  |
| fireworks/kimi-k3p1-pro | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 327,167 | 18,133 | 0.84 | 251 |  |
| fireworks/kimi-k3p1-pro | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 342,112 | 12,953 | 0.81 | 258 |  |
| fireworks/kimi-k3p1-pro | fw-nissanlease-2025-a-2025-01 | C1 | no | 83% | 92% | 92% | 24 | 487,898 | 3,466 | 1.01 | 50 |  |
| fireworks/kimi-k3p1-pro | fw-nissanlease-2025-b-2025-07 | C1 | no | 92% | 96% | 96% | 24 | 474,692 | 2,620 | 0.98 | 55 |  |
| fireworks/kimi-k3p1-pro | fw-nissanlease-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 24 | 496,760 | 3,875 | 1.03 | 63 |  |
| fireworks/kimi-k3p1-pro | fw-nissanlease-2026-b-2026-07 | C1 | no | 75% | 88% | 88% | 24 | 490,801 | 3,407 | 1.02 | 80 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 21 | 396,811 | 4,900 | 0.84 | 87 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2025-b-2025-05 | C1 | no | 100% | 95% | 95% | 21 | 402,342 | 3,915 | 0.84 | 64 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2025-c-2025-08 | C1 | no | 86% | 95% | 95% | 20 | 407,447 | 7,881 | 0.89 | 142 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2025-d-2025-10 | C1 | no | 100% | 95% | 95% | 21 | 413,675 | 5,099 | 0.88 | 64 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2026-a-2026-02 | C1 | no | 89% | 95% | 95% | 22 | 405,930 | 6,296 | 0.87 | 107 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2026-b-2026-05 | C1 | yes | 100% | 100% | 100% | 22 | 410,311 | 10,130 | 0.92 | 158 |  |
| fireworks/kimi-k3p1-pro | fw-worldomni-2026-c-2026-08 | C1 | no | 78% | 91% | 91% | 22 | 413,064 | 5,162 | 0.88 | 75 |  |
| fireworks/minimax-m3p1-flash | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 392,007 | 5,713 | 0.06 | 44 |  |
| fireworks/minimax-m3p1-flash | fw-carmax-2025-3-2025-07 | C1 | no | 0% | 0% | 0% | 27 | 394,580 | 14,088 | 0.07 | 80 | ValueError: no JSON object in the reply |
| fireworks/minimax-m3p1-flash | fw-carmax-2025-4-2025-10 | C1 | no | 83% | 93% | 93% | 27 | 395,401 | 16,231 | 0.07 | 98 |  |
| fireworks/minimax-m3p1-flash | fw-carmax-2026-1-2026-01 | C1 | yes | 100% | 100% | 100% | 27 | 403,661 | 17,031 | 0.07 | 104 |  |
| fireworks/minimax-m3p1-flash | fw-carmax-2026-2-2026-04 | C1 | no | 83% | 93% | 100% | 27 | 403,866 | 14,147 | 0.07 | 88 |  |
| fireworks/minimax-m3p1-flash | fw-carmax-2026-3-2026-07 | C1 | no | 73% | 88% | 100% | 24 | 384,547 | 16,891 | 0.07 | 98 |  |
| fireworks/minimax-m3p1-flash | fw-deere-2025-b-2025-08 | C1 | yes | 100% | 100% | 100% | 16 | 318,842 | 27,209 | 0.06 | 162 |  |
| fireworks/minimax-m3p1-flash | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 317,805 | 21,757 | 0.06 | 133 |  |
| fireworks/minimax-m3p1-flash | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 331,999 | 18,155 | 0.06 | 110 |  |
| fireworks/minimax-m3p1-flash | fw-nissanlease-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 24 | 477,652 | 6,556 | 0.08 | 48 |  |
| fireworks/minimax-m3p1-flash | fw-nissanlease-2025-b-2025-07 | C1 | yes | 100% | 100% | 100% | 24 | 464,683 | 5,885 | 0.07 | 50 |  |
| fireworks/minimax-m3p1-flash | fw-nissanlease-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 24 | 486,477 | 8,723 | 0.08 | 59 |  |
| fireworks/minimax-m3p1-flash | fw-nissanlease-2026-b-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 480,565 | 7,653 | 0.08 | 53 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2025-a-2025-01 | C1 | no | 86% | 95% | 95% | 21 | 385,037 | 18,679 | 0.07 | 108 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2025-b-2025-05 | C1 | no | 100% | 95% | 95% | 21 | 390,227 | 14,036 | 0.07 | 85 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2025-c-2025-08 | C1 | no | 100% | 80% | 80% | 20 | 395,338 | 43,102 | 0.09 | 251 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2025-d-2025-10 | C1 | no | 100% | 76% | 76% | 21 | 401,471 | 34,636 | 0.08 | 208 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2026-a-2026-02 | C1 | no | 78% | 73% | 73% | 22 | 393,957 | 11,620 | 0.07 | 72 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2026-b-2026-05 | C1 | no | 78% | 91% | 91% | 22 | 398,217 | 27,797 | 0.08 | 158 |  |
| fireworks/minimax-m3p1-flash | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 401,080 | 18,463 | 0.07 | 108 |  |
| fireworks/glm-5p3 | fw-carmax-2025-2-2025-04 | C1 | yes | 100% | 100% | 100% | 24 | 407,034 | 8,143 | 0.61 | 63 |  |
| fireworks/glm-5p3 | fw-carmax-2025-3-2025-07 | C1 | yes | 100% | 100% | 100% | 27 | 409,628 | 22,285 | 0.67 | 154 |  |
| fireworks/glm-5p3 | fw-carmax-2025-4-2025-10 | C1 | no | 83% | 93% | 93% | 27 | 410,392 | 19,863 | 0.66 | 141 |  |
| fireworks/glm-5p3 | fw-carmax-2026-1-2026-01 | C1 | yes | 100% | 100% | 100% | 27 | 419,008 | 13,366 | 0.65 | 98 |  |
| fireworks/glm-5p3 | fw-carmax-2026-2-2026-04 | C1 | yes | 100% | 100% | 100% | 27 | 419,313 | 16,110 | 0.66 | 113 |  |
| fireworks/glm-5p3 | fw-carmax-2026-3-2026-07 | C1 | yes | 100% | 100% | 100% | 24 | 399,484 | 14,081 | 0.62 | 103 |  |
| fireworks/glm-5p3 | fw-deere-2025-b-2025-08 | C1 | no | 86% | 94% | 94% | 16 | 334,742 | 38,573 | 0.64 | 294 |  |
| fireworks/glm-5p3 | fw-deere-2026-2026-04 | C1 | yes | 100% | 100% | 100% | 16 | 334,063 | 31,172 | 0.60 | 263 |  |
| fireworks/glm-5p3 | fw-deere-2026-b-2026-08 | C1 | yes | 100% | 100% | 100% | 16 | 349,194 | 25,994 | 0.60 | 194 |  |
| fireworks/glm-5p3 | fw-nissanlease-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 24 | 505,106 | 11,084 | 0.76 | 90 |  |
| fireworks/glm-5p3 | fw-nissanlease-2025-b-2025-07 | C1 | yes | 100% | 100% | 100% | 24 | 489,957 | 9,730 | 0.73 | 80 |  |
| fireworks/glm-5p3 | fw-nissanlease-2026-a-2026-02 | C1 | no | 83% | 92% | 100% | 24 | 514,377 | 9,634 | 0.76 | 85 |  |
| fireworks/glm-5p3 | fw-nissanlease-2026-b-2026-07 | C1 | no | 75% | 88% | 88% | 24 | 507,382 | 24,036 | 0.82 | 174 |  |
| fireworks/glm-5p3 | fw-worldomni-2025-a-2025-01 | C1 | yes | 100% | 100% | 100% | 21 | 404,350 | 30,879 | 0.70 | 266 |  |
| fireworks/glm-5p3 | fw-worldomni-2025-b-2025-05 | C1 | yes | 100% | 100% | 100% | 21 | 410,252 | 15,321 | 0.64 | 115 |  |
| fireworks/glm-5p3 | fw-worldomni-2025-c-2025-08 | C1 | yes | 100% | 100% | 100% | 20 | 415,567 | 38,975 | 0.75 | 316 |  |
| fireworks/glm-5p3 | fw-worldomni-2025-d-2025-10 | C1 | no | 86% | 95% | 95% | 21 | 422,268 | 14,500 | 0.66 | 108 |  |
| fireworks/glm-5p3 | fw-worldomni-2026-a-2026-02 | C1 | yes | 100% | 100% | 100% | 22 | 413,938 | 41,014 | 0.76 | 282 |  |
| fireworks/glm-5p3 | fw-worldomni-2026-b-2026-05 | C1 | yes | 100% | 100% | 100% | 22 | 418,681 | 12,747 | 0.64 | 110 |  |
| fireworks/glm-5p3 | fw-worldomni-2026-c-2026-08 | C1 | yes | 100% | 100% | 100% | 22 | 421,843 | 23,631 | 0.69 | 169 |  |
