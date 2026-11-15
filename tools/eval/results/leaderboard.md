# WaterfallBench leaderboard (single-call harness)

| model | tasks | fully resolved % | non-trivial acc % | line-item acc % | ±$1 acc % | answered % | mean input tok | mean output tok | mean s | est $/task | est $ total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-6-astra | 20 | 95.0 | 99.2 | 99.6 | 100.0 | 100.0 | 407,039 | 2,558 | 64 | 8.33 | 166.65 |
| anthropic/claude-fable-5-2 | 20 | 95.0 | 99.1 | 99.6 | 100.0 | 100.0 | 632,454 | 3,053 | 35 | 5.18 | 103.64 |
| openai/gpt-6-luna | 20 | 90.0 | 99.2 | 98.7 | 98.7 | 100.0 | 407,039 | 7,811 | 87 | 0.09 | 1.75 |
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
